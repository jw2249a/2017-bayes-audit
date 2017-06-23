# multi.py
# Ronald L. Rivest
# June 23, 2017
# python3

"""
Prototype code for auditing an election having both multiple contests and
multiple paper ballot collections (e.g. multiple jurisdictions).
Possibly relevant to Colorado state-wide post-election audits in Nov 2017.
"""

"""
Assumes each paper ballot collection is 'pure' in the sense that every
ballot in that collection has the same ballot type.  That is, every
ballot in the collection shows the same set of contests.
"""

""" 
This code corresponds to the what Audit Central needs to do.
"""

# MIT License

import argparse
import json
import numpy as np                
import os

##############################################################################
## myprint  (like logging, maybe, but maybe simpler)
##############################################################################
myprint_switches = ["std"]                 

def myprint(*args, **kwargs):
    """ variant print statement, 
        with myprint_switch="foo" kwarg allowed.
        if no myprint_switch given, then myprint_switch=std is assumed.
    """
    if "myprint_switch" in kwargs:
        switch = kwargs["myprint_switch"]
        if switch in myprint_switches:
            del kwargs["myprint_switch"]
            print(*args, **kwargs)
    elif "std" in myprint_switches:
        print(*args, **kwargs)

##############################################################################
## Random number generation
##############################################################################

# see numpy.random.RandomState documentation
# Random states used in the program:
# auditRandomState        -- controls random sampling and other audit aspects
# syntheticRandomState    -- controls generation of synthetic vote datasets

## Gamma distribution
## https://docs.scipy.org/doc/numpy-1.11.0/reference/generated/numpy.random.gamma.html
# from numpy.random import gamma
# To generate random gamma variate with mean k:
# gamma(k)  or rs.gamma(k) where rs is a numpy.random.RandomState object

def gamma(k, rs=None):
    """ 
    Return sample from gamma distribution with mean k.
    Differs from standard one that it allows k==0, which returns 0.
    Parameter rs, if present, is a numpy.random.RandomState object.
    """
    global auditRandomState
    if rs==None:
        rs = auditRandomState
    if k<=0.0:
        return 0.0
    return rs.gamma(k)

## Dirichlet distribution

def dirichlet(tally):
    """ 
    Given tally dict mapping vote ids (vids) to nonnegative reals (counts), 
    return dict mapping those vids to elements of Dirichlet distribution on
    those vids, where tally values are used as Dirichlet hyperparameters.
    The values produced sum to one.
    """
    dir = {vid: gamma(tally[vid]) for vid in tally}
    total = sum(dir.values())
    dir = {vid: dir[vid]/total for vid in dir}
    return dir

##############################################################################
## Elections
##############################################################################

class Election(object):

    """
    All relevant attributes of an election are stored within an Election 
    object.

    For compatibility with json, an Election object should be viewed as 
    the root of a tree of dicts, where all keys are strings, and the leaves are
    strings or numbers.

    In comments: 
       [dicts] an object of type "cids->reals" is a dict mapping cids to reals,
           and an object of type "cids->pcbids->vids->string" is a nested 
           set of dicts, the top level keyed by a cid, and so on.
       [lists] an object of type [bids] is a list of ballot ids.
    Glossary:
        bid    a ballot id (e.g. "Arapahoe-Box12-234")
        cid    a contest id (e.g. "Denver-Mayor")
        pbcid  a paper-ballot collection id (e.g. "Denver-precinct24")
        vid    a vote id (e.g. "Yes" or "JohnSmith")
    All ids are required by this code to not contain whitespace.
    """

    def __init__(self):

        e = self

        ### election structure
        e.election_type = "Synthetic"  # string, either "Synthetic" or "Real"
        e.synthetic_seed = 8 # seed for synthetic generation of random votes
        e.cids = []          # [cids]           list of contest ids
        e.pbcids = []        # [pcbids]         list of paper ballot collection ids
        e.bids = {}          # pbcid->[bids]   list of ballot ids for each pcbid
        e.rel = {}           # cid->pbcid->"True"
                             # (relevance; only relevant pbcids in e.rel[cid])
        e.vvids = {}         # cid->[vids]   givs list of valid (CANDIDATE) votes
                             # (which are strings)
        e.ivids = {}         # cid->[vids]  gives list of invalid (NONCANDIDATE)
                             # votes (which are strings),
                             # must include "Invalid", "Overvote", "Undervote",
                             # and possibly "noCVR" (for noCVR pbcs)
        e.vids = {}          # cid->[vids]
                             # maps cid to union of e.vvids[cid] and e.ivids[cid]
                             # note that e.vids is used for both reported votes
                             # (e.rv) and for actual votes (e.av)
        e.collection_type = {}  # pbcid-> "CVR" or "noCVR"

        ### election data (reported election results)
        e.n = {}             # e.n[pbcid] number ballots cast in collection pbcid
        e.t = {}             # cid->pbcid-> vid->reals    (counts)
        e.ro = {}            # cid->vid   (reported outcome)
        # computed from the above 
        e.totcid = {}        # cid->reals  (total # votes cast in contest)
        e.totvot = {}        # cid->vid->reals  (number of votes recd by vid in cid)
        e.rv = {}            # cid->pbcid->bid->[vids]     (reported votes)
                             # e.rv is like e.av (reported votes; actual votes)
        e.nr = {}            # cid->pbcid->vid->count
                             # (vid is reported vote in whole pbcid)
        e.error_rate = 0.0001# error rate used in model for generating
                             # synthetic reported votes

        ### audit
        e.audit_seed = None   # seed for pseudo-random number generation for audit
        e.risk_limit = {}     # cid->reals  (risk limit for that contest)
        e.audit_rate = {}     # pbcid->int  (# ballots that can be audited per stage)
        e.stage = "0"         # current stage number (in progress) or last stage completed
        e.last_stage = "-1"   # previous stage (just one less, in string form)
        e.max_stages = 100    # maximum number of stages allowed in audit
        e.pseudocount = 0.5   # hyperparameter for prior distribution
                              # (e.g. 0.5 for Jeffrey's distribution)
        e.recount_threshold = 0.95 # if e.risk[e.stage][cid] exceeds 0.95,
                                   # then full recount called for cid
        e.n_trials = 100000   # number of trials used to estimate risk
                              # in compute_contest_risk
        ## stage-dependent: (stage # input is stage when computed)
        e.plan = {}           # stage->pbcid->reals (sample size wanted after next draw)
        e.risk = {}           # stage->cid->reals  (risk (that e.ro[cid] is wrong))
        e.contest_status = {} # stage->cid-> one of 
                              # "Auditing", "Just Watching",
                              # "Risk Limit Reached", "Full Recount Needed"
                              # initially must be "Auditing" or "Just Watching"
        e.election_status = {} # stage->list of contest statuses, at most once each
        # sample info
        e.av = {}             # cid->pbcid->bid->vid
                              # (actual votes; sampled ballots)
        e.s = {}              # stage->pbcid->ints (number of ballots sampled so far)
        # computed from the above
        e.st = {}             # stage->cid->pbcid->vid->vid->count
                              # (first vid is reported vote, second is actual vote)
        e.sr = {}             # stage->cid->pbcid->vid->count
                              # (vid is reported vote in sample)

##############################################################################
## Election structure I/O and validation
##############################################################################

def finish_election_structure(e):
    """ Compute attributes of e that are derivative from others. """

    for cid in e.cids:
        if "noCVR" not in e.ivids[cid] and \
           any([e.collection_type[pbcid]=="noCVR" \
                for pbcid in e.rel[cid]]):
            e.ivids[cid].append("noCVR")

    for cid in e.cids:
        e.vids[cid] = sorted(e.vvids[cid]+e.ivids[cid])


def myerror(msg):
    """ Print error message and halt immediately """
    
    print("FATAL ERROR:", msg)
    raise Exception


warnings_given = 0
def mywarning(msg):
    """ Print error message, but keep going.
        Keep track as to how many warnings have been given.
    """

    global warnings_given
    warnings_given += 1
    print("WARNING: msg")


def check_id(id):
    if not isinstance(id, str) or not id.isprintable():
        mywarning("id is not string or is not printable: {}".format(id))
    for c in id:
        if c.isspace():
            mywarning("id `id` contains whitespace.")
            break


def check_election_structure(e):
    
    if e.election_type not in ["Synthetic", "Real"]:
        myerror("Unknown election_type:{}.".format(e.election_type))

    if not isinstance(e.cids, (list, tuple)):
        myerror("e.cids is not a list or a tuple.")
    if len(e.cids)==0:
        myerror("e.cids is an empty list of contests.")
    for cid in e.cids:
        check_id(cid)
    
    if not isinstance(e.pbcids, (list, tuple)):
        myerror("e.pbcids is not a list or a tuple.")
    if len(e.pbcids)==0:
        myerror("e.pbcids is an empty list of pbcids.")
    for pbcid in e.pbcids:
        check_id(pbcid)

    if not isinstance(e.rel, dict):
        myerror("e.rel is not a dict.")
    for cid in e.rel:
        if cid not in e.cids:
            mywarning("cid is not in e.cids: {}".format(cid))
        for pbcid in e.rel[cid]:
            if pbcid not in e.pbcids:
                mywarning("pbcid is not in e.pbcids: {}".format(pbcid))
            if e.rel[cid][pbcid]!=True:
                mywarning("e.rel[{}][{}] != True.".format(cid, pbcid, e.rel[cid][pbcid]))

    if not isinstance(e.ivids, dict):
        myerror("e.ivids is not a dict.")
    for cid in e.ivids:
        if cid not in e.cids:
            myerror("e.ivids has a key `{}` not in e.cids.".format(cid))
        if not isinstance(e.ivids[cid], (list, tuple)):
            myerror("e.ivids[{}] is not a list or a tuple.".format(cid))
        for ivid in e.ivids[cid]:
            check_id(ivid)
    for cid in e.cids:
        if cid not in e.ivids:
            mywarning("cid `{}` should a key in e.ivids".format(cid))

    if not isinstance(e.vvids, dict):
        myerror("e.vvids is not a dict.")
    for cid in e.vvids:
        if cid not in e.cids:
            myerror("e.vvids has a key `{}` not in e.cids.".format(cid))
        if not isinstance(e.vvids[cid], (list, tuple)):
            myerror("e.vvids[{}] is not a list or a tuple.".format(cid))
        for vid in e.vvids[cid]:
            check_id(vid)
    for cid in e.cids:
        if cid not in e.vids:
            mywarning("cid `{}` should be key in e.vids".format(cid))

    if not isinstance(e.vids, dict):
        myerror("e.vids is not a dict.")
    for cid in e.vids:
        if cid not in e.cids:
            myerror("e.vids has a key `{}` not in e.cids.".format(cid))
        if not isinstance(e.vids[cid], (list, tuple)):
            myerror("e.vids[{}] is not a list or a tuple.".format(cid))
        for vid in e.vids[cid]:
            check_id(vid)
    for cid in e.cids:
        if cid not in e.vids:
            mywarning("cid `{}` should be key in e.vids".format(cid))

    for cid in e.cids:
        for vvid in e.vvids[cid]:
            for ivid in e.ivids[cid]:
                if vvid == ivid:
                    mywarning("e.vvids[{}] and e.ivids[{}] are not disjoint."
                              .format(cid, cid))

    if not isinstance(e.collection_type, dict):
        myerror("e_collection_type is not a dict.")
    for pbcid in e.collection_type:
        if pbcid not in e.pbcids:
            mywarning("pbcid `{}` is not in e.pbcids".format(pbcid))
        if e.collection_type[pbcid] not in ["CVR", "noCVR"]:
            mywarning("e.collection_type[{}]==`{}` is not CVR or noCVR"
                      .format(pbcid, e.collection_type[pbcid]))
    for pbcid in e.pbcids:
        if pbcid not in e.collection_type:
            mywarning("pbcid `{}` not key in e.collection_type."
                      .format(pbcid))

    if warnings_given>0:
        myerror("Too many errors; terminating.")


def show_election_structure(e):
    myprint("====== Election structure ======")
    myprint("Election type:")
    myprint("    {}".format(e.election_type))
    myprint("Number of contests:")
    myprint("    {}".format(len(e.cids)))
    myprint("e.cids (contest ids):")
    myprint("    ", end='')
    for cid in e.cids:
        myprint(cid, end=' ')
    myprint()
    myprint("Number of paper ballot collections)")
    myprint("    {}".format(len(e.pbcids)))
    myprint("e.pbcids (paper ballot collection ids (e.g. jurisdictions)):")
    myprint("    ", end='')
    for pbcid in e.pbcids:
        myprint(pbcid, end=' ')
    myprint()
    myprint("e.collection_type (either CVR or noCVR) for each pbcid:")
    for pbcid in e.pbcids:
        myprint("    {}:{} ".format(pbcid, e.collection_type[pbcid]))
    myprint("e.rel (valid pbcids for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for pbcid in e.rel[cid]:
            myprint(pbcid, end=' ')
        myprint()
    myprint("e.vvids (valid vote ids for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for vvid in e.vvids[cid]:
            myprint(vvid, end=' ')
        myprint()
    myprint("e.ivids (invalid vote ids for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for ivid in e.ivids[cid]:
            myprint(ivid, end=' ')
        myprint()
    myprint("e.vids (valid or invalid vote ids for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            myprint(vid, end=' ')
        myprint()

##############################################################################
## Election data I/O and validation (stuff that depends on cast votes)
##############################################################################

def finish_election_data(e):
    """ 
    Compute election data attributes of e that are derivative from others. 
    """

    # e.totcid[cid] is total number of votes cast for cid
    for cid in e.cids:
        e.totcid[cid] = sum([e.n[pbcid] for pbcid in e.rel[cid]])

    # e.totvid[cid][vid] is total number cast for vid in cid
    for cid in e.cids:
        e.totvot[cid] = {}
        for vid in e.vids[cid]:
            e.totvot[cid][vid] = \
                sum([e.t[cid][pbcid].get(vid, 0) for pbcid in e.rel[cid]])


def compute_rv(e, cid, pbcid, bid, vid):
    """
    Compute reported vote for e.rv[cid][pbcid][bid]
    based on whether pbcid is CVR or noCVR, and based on
    a prior for errors.  Here vid is the actual vote.
    e.error_rate (default 0.0001) is chance that 
    reported vote != actual vote.  If they differ all 
    other possibilities are equally likely to occur.
    """
    if e.collection_type[pbcid]=="noCVR":
        assert "noCVR" in e.vids[cid], cid   # assume noCVR is legit vid
        return "noCVR"
    # Otherwise, we generate a reported vote
    m = len(e.vids[cid])          # number of vote options for this cid
    if syntheticRandomState.uniform()>e.error_rate or m==1:
        return vid                # no error is typical case
    error_vids = e.vids[cid].copy()
    error_vids.remove(vid)
    # pick an error at random
    return error_vids[int(syntheticRandomState.uniform()*(m-1))]


def compute_synthetic_votes(e):
    """
    Make up actual votes and randomly permute their order.
    Only useful for test elections, not for real elections.
    Form of bid is e.b. PBC1::576
    """
    
    global syntheticRandomState
    syntheticRandomState = np.random.RandomState(e.synthetic_seed)
    # make up bids
    for pbcid in e.pbcids:
        e.bids[pbcid] = list()
        i = 0
        for j in range(i, i+e.n[pbcid]):
            bid = pbcid + "::" + "%d"%j
            e.bids[pbcid].append(bid)
        i += e.n[pbcid]
    # make up votes
    for cid in e.cids:
        e.rv[cid] = {}
        e.av[cid] = {}
        # make up all votes first, so overall tally for cid is right
        votes = []
        for vid in e.vids[cid]:
            votes.extend([vid]*e.totvot[cid][vid])
        syntheticRandomState.shuffle(votes)          # in-place shuffle!
        # break votes up into pieces by pbcid
        i = 0
        for pbcid in e.rel[cid]:
            e.av[cid][pbcid] = {}
            e.rv[cid][pbcid] = {}
            for j in range(e.n[pbcid]):
                bid = e.bids[pbcid][j]
                vid = votes[j]
                e.av[cid][pbcid][bid] = vid
                e.rv[cid][pbcid][bid] = compute_rv(e, cid, pbcid, bid, vid)
            i += e.n[pbcid]


def check_election_data(e):

    assert isinstance(e.t, dict)
    for cid in e.t:
        if cid not in e.cids:
            mywarning("cid `{}` not in e.cids.".format(cid))
        for pbcid in e.t[cid]:
            if pbcid not in e.pbcids:
                mywarning("pbcid `{}` is not in e.pbcids.".format(pbcid))
            for vid in e.t[cid][pbcid]:
                if vid not in e.vids[cid]:
                    mywarning("vid `{}` is not in e.vids[{}].".format(vid, cid))
                if not isinstance(e.t[cid][pbcid][vid], int):
                    mywarning("value `e.t[{}][{}][{}] = `{}` is not an integer."
                              .format(cid, pbcid, vid, e.t[cid][pbcid][vid]))
                if not (0 <= e.t[cid][pbcid][vid] <= e.n[pbcid]):
                    mywarning("value `e.t[{}][{}][{}] = `{}` is out of range 0:{}."
                              .format(cid, pbcid, vid, e.t[cid][pbcid][vid], e.n[pbcid]))
                if e.totvot[cid][vid] != \
                    sum([e.t[cid][pbcid][vid] for pbcid in e.rel[cid]]):
                    mywarning("sum of e.t[{}][*][{}] is not e.totvid[{}][{}]."
                              .format(cid, vid, cid, vid))
    for cid in e.cids:
        if cid not in e.t:
            mywarning("cid `{}` is not a key for e.t".format(cid))
        for pbcid in e.rel[cid]:
            if pbcid not in e.t[cid]:
                mywarning("pbcid {} is not a key for e.t[{}].".format(pbcid, cid))
            # for vid in e.vids[cid]:
            #     assert vid in e.t[cid][pbcid], (cid, pbcid, vid)
            # ## not necessary, since missing vids have assumed t of 0

    if not isinstance(e.totcid, dict):
        myerror("e.totcid is not a dict.")
    for cid in e.totcid:
        if cid not in e.cids:
            mywarning("e.totcid key `{}` is not in e.cids.".format(cid))
        if not isinstance(e.totcid[cid], int):
            mywarning("e.totcid[{}] = {}  is not an integer.".format(cid, e.totcid[cid]))
    for cid in e.cids:
        if cid not in e.totcid:
            mywarning("cid `{}` is not a key for e.totcid".format(cid))

    if not isinstance(e.totvot, dict):
        myerror("e.totvot is not a dict.")
    for cid in e.totvot:
        if cid not in e.cids:
            mywarning("e.totvot key cid `{}` is not in e.cids".format(cid))
        for vid in e.totvot[cid]:
            if vid not in e.vids[cid]:
                mywarning("e.totvot[{}] key `{}` is not in e.vids[{}]"
                          .format(cid, vid, cid))
            if not isinstance(e.totvot[cid][vid], int):
                mywarning("e.totvot[{}][{}] = {} is not an integer."
                          .format(cid, vid, e.totvot[cid][vid]))
    for cid in e.cids:
        if cid not in e.totvot:
            mywarning("cid `{}` is not a key for e.totvot".format(cid))
        for vid in e.vids[cid]:
            if vid not in e.totvot[cid]:
                mywarning("vid `{}` not a key for e.totvot[{}]."
                          .format(vid, cid))

    if not isinstance(e.bids, dict):
        myerror("e.bids is not a dict.")
    for pbcid in e.pbcids:
        if not isinstance(e.bids[pbcid], list):
            myerror("e.bids[{}] is not a list.".format(pbcid))

    if not isinstance(e.av, dict):
        myerror("e.av is not a dict.")
    for cid in e.av:
        if cid not in e.cids:
            mywarning("e.av key {} is not in e.cids.".format(cid))
        for pbcid in e.av[cid]:
            if pbcid not in e.pbcids:
                mywarning("e.av[{}] key `{}` is not in e.pbcids"
                          .format(cid, pbcid))
            if not isinstance(e.av[cid][pbcid], dict):
                myerror("e.av[{}][{}] is not a dict.".format(cid, pbcid))
            bidsset = set(e.bids[pbcid])
            for bid in e.av[cid][pbcid]:
                if bid not in bidsset:
                    mywarning("bid `{}` from e.av[{}][{}] is not in e.bids[{}]."
                              .format(bid, cid, pbcid, pbcid))
                if e.av[cid][pbcid][bid] not in e.vids[cid]:
                    mywarning("vid `{}` from e.av[{}][{}][{}] is not in e.vids[{}]."
                              .format(e.av[cid][pbcid][bid], cid, pbcid, bid, cid))
    for cid in e.cids:
        if cid not in e.av:
            mywarning("cid `{}` is not a key for e.av.".format(cid))
        for pbcid in e.rel[cid]:
            if pbcid not in e.av[cid]:
                mywarning("pbcid `{}` is not in e.av[{}]."
                          .format(pbcid, cid))

    if not isinstance(e.rv, dict):
        myerror("e.rv is not a dict.")
    for cid in e.rv:
        if cid not in e.cids:
            mywarning("e.rv key `{}` is not in e.cids.".format(cid))
        for pbcid in e.rv[cid]:
            if pbcid not in e.pbcids:
                mywarning("e.rv[{}] key `{}` is not in e.pbcids."
                          .format(cid, pbcid))
            if not isinstance(e.rv[cid][pbcid], dict):
                myerror("e.rv[{}][{}] is not a dict.".format(cid, pbcid))
            bidsset = set(e.bids[pbcid])
            for bid in e.rv[cid][pbcid]:
                if bid not in bidsset:
                    mywarning("bid `{}` from e.rv[{}][{}] is not in e.bids[{}]."
                              .format(bid, cid, pbcid, pbcid))
                if e.rv[cid][pbcid][bid] not in e.vids[cid]:
                    mywarning("vid `{}` from e.rv[{}][{}][{}] is not in e.vids[{}]."
                              .format(e.rv[cid][pbcid][bid], cid, pbcid, bid, cid))
    for cid in e.cids:
        if cid not in e.rv:
            mywarning("cid `{}` is not a key in e.rv.".format(cid))
        for pbcid in e.rel[cid]:
            if pbcid not in e.rv[cid]:
                mywarning("pbcid `{}` from e.rel[{}] is not a key for e.rv[{}]."
                          .format(pbcid, cid, cid))
                
    if not isinstance(e.ro, dict):
        myerror("e.ro is not a dict.")
    for cid in e.ro:
        if cid not in e.cids:
            mywarning("cid `{}` from e.rv is not in e.cids".format(cid))
        if e.ro[cid] not in e.vids[cid]:
            mywarning("e.ro[{}] = {} is not in e.vids[{}]."
                      .format(cid, e.ro[cid], cid))
    for cid in e.cids:
        if cid not in e.ro:
            mywarning("cid `{}` is not a key for e.ro.".format(cid))

    if warnings_given>0:
        myerror("Too many errors; terminating.")


def show_election_data(e):

    myprint("====== Reported election data ======")

    myprint("e.t (total votes for each vid by cid and pbcid):")
    for cid in e.cids:
        for pbcid in e.rel[cid]:
            myprint("    {}.{}: ".format(cid, pbcid), end='')
            for vid in e.vids[cid]:
                myprint("{}:{} ".format(vid, e.t[cid][pbcid].get(vid, 0)), end='')
            myprint()

    myprint("e.totcid (total votes cast for each cid):")
    for cid in e.cids:
        myprint("    {}: {}".format(cid, e.totcid[cid]))

    myprint("e.totvot (total cast for each vid for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            myprint("{}:{} ".format(vid, e.totvot[cid][vid]), end='')
        myprint()

    myprint("e.av (first five or so actual votes cast for each cid and pbcid):")
    for cid in e.cids:
        for pbcid in e.rel[cid]:
            myprint("    {}.{}:".format(cid, pbcid), end='')
            for j in range(min(5, len(e.bids[pbcid]))):
                bid = e.bids[pbcid][j]
                myprint(e.av[cid][pbcid][bid], end=' ')
            myprint()

    myprint("e.ro (reported outcome for each cid):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.ro[cid]))

##############################################################################
## Tally and outcome computations
##############################################################################

def compute_tally(vec):
    """
    Here vec is an iterable of elements.
    Return dict giving tally of elements.
    """

    tally = {}
    for x in vec:
        tally[x] = tally.get(x, 0) + 1
    return tally


def compute_tally2(vec):
    """
    Input vec is an iterable of (a, r) pairs. 
    (i.e., (actual vote, reported vote) pairs).
    Return dict giving mapping from r to dict
    giving tally of a's that appear with that r.
    """

    tally2 = {}
    for (a, r) in vec:
        if r not in tally2:
            tally2[r] = compute_tally([aa for (aa, rr) in vec if r==rr])
    return tally2


def plurality(d, vvids):
    """
    Return, for input dict d mapping vids to (real) counts, vid with largest count.
    (Tie-breaking done arbitrarily here.)
    Winning vid must be a valid winner (member of vvids).
    """

    max_cnt = -1e90
    max_vid = None
    for vid in d:
        if d[vid]>max_cnt and vid in vvids:
            max_cnt = d[vid]
            max_vid = vid
    return max_vid

##############################################################################
## Audit I/O and validation
##############################################################################

def check_audit_parameters(e):

    if not isinstance(e.risk_limit, dict):
        myerror("e.risk_limit is not a dict.")
    for cid in e.risk_limit:
        if cid not in e.cids:
            mywarning("e.risk_limit cid key `{}` is not in e.cids."
                      .format(cid))
        if not (0.0 <= e.risk_limit[cid] <= 1.0):
            mywarning("e.risk_limit[{}] not in interval [0,1]".format(cid))

    if not isinstance(e.audit_rate, dict):
        myerror("e.audit_rate is not a dict.")
    for pbcid in e.audit_rate:
        if pbcid not in e.pbcids:
            mywarning("pbcid `{}` is a key for e.audit_rate but not in e.pbcids."
                      .format(pbcid))
        if not 0 <= e.audit_rate[pbcid]:
            mywarning("e.audit_rate[{}] must be nonnegative.".format(pbcid))
        
    if not isinstance(e.contest_status, dict):
        myerror("e.contest_status is not a dict.")
    if "0" not in e.contest_status:
        myerror("e.contest_status must have `0` as a key.")
    for cid in e.contest_status["0"]:
        if cid not in e.cids:
            mywarning("cid `{}` is key in e.contest_status but not in e.cids"
                      .format(cid))
        if e.contest_status["0"][cid] not in ["Auditing", "Just Watching"]:
            mywarning("e.contest_status['0'][{}] must be `Auditing` or `Just Watching`."
                      .format(cid))
    
    if warnings_given>0:
        myerror("Too many errors; terminating.")


def draw_sample(e):
    """ 
    "Draw sample", tally it, save sample tally in e.st[stage][cid][pbcid]. 
    Update e.sr

    Draw sample is in quotes since it just looks at the first
    e.s[stage][pbcid] elements of e.av[cid][pbcid].
    Code sets e.sr[e.stage][cid][pbcid][r] to number in sample with reported vote r.

    Code sets e.s to number of ballots sampled in each pbc (equal to plan).
    Note that in real life actual sampling number might be different than planned;
    here it will be the same.  But code elsewhere allows for such differences.
    """

    e.s[e.stage] = e.plan[e.last_stage]
    e.sr[e.stage] = {}
    for cid in e.cids:
        e.st[e.stage][cid] = {}
        e.sr[e.stage][cid] = {}
        for pbcid in e.rel[cid]:
            e.sr[e.stage][cid][pbcid] = {}
            avotes = [e.av[cid][pbcid][bid] \
                      for bid in e.bids[pbcid][:e.s[e.stage][pbcid]]] # actual
            rvotes = [e.rv[cid][pbcid][bid] \
                      for bid in e.bids[pbcid][:e.s[e.stage][pbcid]]] # reported
            zvotes = list(zip(avotes, rvotes)) # list of (actual, reported) vote pairs
            e.st[e.stage][cid][pbcid] = compute_tally2(zvotes)
            for r in e.vids[cid]:
                e.sr[e.stage][cid][pbcid][r] = len([rr for rr in rvotes if rr==r])

                
def compute_contest_risk(e, cid, st):
    """ 
    Compute Bayesian risk (chance that reported outcome is wrong for cid).
    We take st here as argument rather than e.st so
    we can call compute_contest_risk with modified sample counts.
    (This option not yet used, but might be later.)

    This is the heart of the Bayesian post-election audit method.
    But it could be replaced by a frequentist approach instead, at
    least for those outcome rules and mixes of collection types for
    which a frequentist method is known.

    The comparison and ballot-polling audits are blended here; the
    election data just records an "noCVR" for the reported type of each vote
    in a noCVR paper ballot collection.
    """

    wrong_outcome_count = 0
    for trial in range(e.n_trials):
        test_tally = {vid:0 for vid in e.vids[cid]} 
        for pbcid in e.rel[cid]:
            # draw from posterior for each paper ballot collection, sum them
            # stratify by reported vote
            for r in e.st[e.stage][cid][pbcid]:
                tally = e.st[e.stage][cid][pbcid][r].copy()
                for vid in e.vids[cid]:
                    tally[vid] = tally.get(vid, 0)
                for vid in tally:
                    tally[vid] += e.pseudocount
                dirichlet_dict = dirichlet(tally)
                nonsample_size = e.nr[cid][pbcid][r] - e.sr[e.stage][cid][pbcid][r]
                for vid in tally:
                    # increment actual tally for vid with reported vote r
                    test_tally[vid] += tally[vid]  
                    if e.sr[e.stage][cid][pbcid][r] > 0:
                        test_tally[vid] += dirichlet_dict[vid] * nonsample_size
        if e.ro[cid] != plurality(test_tally, e.vvids[cid]):
            wrong_outcome_count += 1
    e.risk[e.stage][cid] = wrong_outcome_count/e.n_trials


def compute_status(e, st):
    """ 
    compute status of each contest and of election
    """

    for cid in e.cids:
        compute_contest_risk(e, cid, st)
        # The following test could be for !="Just Watching" or for =="Auditing"
        # It may be better to have it so that once a contest has met its
        # risk limit once, it no longer goes back to "Auditing" status, even
        # if its risk drifts back up to be larger than its risk limit.
        # Mathematically, this is OK, although it could conceivably look
        # strange to an observer or an election official to have a contest
        # whose status is "Risk Limit Reached" but whose current risk is
        # more than the risk limit.  If this test compares to "Just Watching",
        # then a contest of status "Risk Limit Reached" could have its status
        # set back to "Auditing" if the risk then rises too much...  Which is better UI?
        # Note that a contest which has reached its risk limit could be set back to
        # Auditing because of any one of its pbc's, even if some of them aren't being
        # audited for a stage.
        e.contest_status[e.stage][cid] = e.contest_status[e.last_stage][cid]
        if e.contest_status[e.stage][cid] != "Just Watching":
            if all([e.n[pbcid]==e.s[e.stage][pbcid] for pbcid in e.rel[cid]]):
                e.contest_status[e.stage][cid] = "All Relevant Ballots Sampled"
            elif e.risk[e.stage][cid] < e.risk_limit[cid]:
                e.contest_status[e.stage][cid] = "Risk Limit Reached"
            elif e.risk[e.stage][cid] > e.recount_threshold:
                e.contest_status[e.stage][cid] = "Full Recount Needed"
            else:
                e.contest_status[e.stage][cid] = "Auditing"
        
    e.election_status[e.stage] = \
        sorted(list(set([e.contest_status[e.stage][cid] for cid in e.cids])))


def show_status(e):
    """ SHow election and contest status info. """

    myprint("    Risk (that reported outcome is wrong) per cid and contest status:")
    for cid in e.cids:
        myprint("     ", cid, e.risk[e.stage][cid], \
              "(limit {})".format(e.risk_limit[cid]), \
              e.contest_status[e.stage][cid])
    myprint("    Election status:", e.election_status[e.stage])
                

def plan_sample(e):
    """ Compute a sampling plan 
        Put in e.plan[e.stage] a dict of target sample sizes by pbcid) 
    """

    # for now, use simple strategy of looking at more ballots
    # only in those paper ballot collections that are still being audited
    e.plan[e.stage] = e.s[e.stage].copy()
    for cid in e.cids:
        for pbcid in e.rel[cid]:
            if e.contest_status[e.stage][cid] == "Auditing":
                # if contest still being audited do as much as you can without
                # exceeding size of paper ballot collection
                e.plan[e.stage][pbcid] = min(e.s[e.stage][pbcid] + e.audit_rate[pbcid], e.n[pbcid])
    return


def show_audit_parameters(e):

    myprint("====== Audit parameters ======")

    myprint("e.contest_status (initial audit status for each contest):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.contest_status["0"][cid]))

    myprint("e.risk_limit (risk limit per contest):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.risk_limit[cid]))

    myprint("e.audit_rate (max number of ballots audited/day per pbcid):")
    for pbcid in e.pbcids:
        myprint("    {}:{}".format(pbcid, e.audit_rate[pbcid]))

    myprint("e.max_stages (max number of audit stages allowed):")
    myprint("    {}".format(e.max_stages))

    myprint("e.n_trials (number of trials used to estimate risk"
            "in compute_contest_risk):")
    myprint("    {}".format(e.n_trials))

    myprint("e.pseudocount (hyperparameter for prior distribution,"
            "e.g. 0.5 for Jeffrey's prior)")
    myprint("    {}".format(e.pseudocount))

    myprint("e.audit_seed (seed for audit pseudorandom number generation)")
    myprint("    {}".format(e.audit_seed))


def show_audit_stage_header(e, last_s):

    myprint("audit stage", e.stage)
    myprint("    New target sample sizes by paper ballot collection:")
    for pbcid in e.pbcids:
        myprint("      {}: {} (+{})"
                .format(pbcid,
                        e.plan[e.last_stage][pbcid],
                        e.plan[e.last_stage][pbcid]-last_s[pbcid]))
            

def show_sample_counts(e):

    myprint("    Total sample counts by Contest.PaperBallotCollection[reported vote]"
            "and actual votes:")
    for cid in e.cids:
        for pbcid in e.rel[cid]:
            tally2 = e.st[e.stage][cid][pbcid]
            for r in sorted(tally2.keys()): # r = reported vote
                myprint("      {}.{}[{}]".format(cid, pbcid, r), end='')
                for v in sorted(tally2[r].keys()):
                    myprint("  {}:{}".format(v, tally2[r][v]), end='')
                myprint("  total:{}".format(e.sr[e.stage][cid][pbcid][r]))


def show_audit_summary(e):

    global myprint_switches

    myprint("=============")
    myprint("Audit completed!")

    myprint("All contests have a status in the following list:",
            e.election_status[e.stage])

    myprint("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        myprint("  {}:{}".format(pbcid, e.s[e.stage][pbcid]))
    myprint_switches = ["std"]
    myprint("Total number of ballots sampled: ", end='')
    myprint(sum([e.s[e.stage][pbcid] for pbcid in e.pbcids]))
    

def audit(e):

    global auditRandomState
    auditRandomState = np.random.RandomState(e.audit_seed)

    show_audit_parameters(e)
    myprint("====== Audit ======")

    e.s["0"] = {}
    for pbcid in e.pbcids:                           
        e.s["0"][pbcid] = 0
    e.last_s = e.s["0"]
    e.plan["0"] = {pbcid:min(e.n[pbcid], e.audit_rate[pbcid]) for pbcid in e.pbcids}
    
    for stage in range(1, e.max_stages):
        e.last_stage = e.stage
        e.stage = "{}".format(stage)      # must be string to be json key
        audit_stage(e)
        if "Auditing" not in e.election_status[e.stage]:
            break
        plan_sample(e)
        e.last_s = e.s[e.stage]
    show_audit_summary(e)


def audit_stage(e):

    e.risk[e.stage] = {}
    e.contest_status[e.stage] = {}
    e.s[e.stage] = {}                      
    e.st[e.stage] = {}

    draw_sample(e)
    compute_status(e, e.st)

    show_audit_stage_header(e, e.last_s)
    show_sample_counts(e)
    show_status(e)

        
def copy_dict_tree(dest, source):
    """
    Copy data from source dict tree to dest dict tree, recursively.
    Omit key/value pairs where key starts with "__".
    """
    if not isinstance(dest, dict) or not isinstance(source, dict):
        myprint("copy_dict_tree: source or dest is not a dict.")
        return
    for source_key in source:
        if not source_key.startswith("__"):   # for comments, etc.
            if isinstance(source[source_key], dict):
                if not source_key in dest:
                    dest_dict = {}
                    dest[source_key] = dest_dict
                else:
                    dest_dict = dest[source_key]
                source_dict = source[source_key]
                copy_dict_tree(dest_dict, source_dict)
            else:
                # Maybe add option to disallow clobbering here??
                dest[source_key] = source[source_key]


def load_part_from_json(e, part_name):
    part_filename = os.path.join(e.elections_dir, e.election_name, part_name)
    part = json.load(open(part_filename, "r"))
    copy_dict_tree(e.__dict__, part)
    myprint("File {} loaded.".format(part_filename))


def main():

    global myprint_switches
    myprint_switches = []       # put this after following line to suppress printing
    myprint_switches = ["std"]

    parser = argparse.ArgumentParser(description=\
            """multi.py: A Bayesian post-election audit program for an
            election with multiple contests and multiple paper ballot 
            collections.""")
    parser.add_argument("election_name", help="""
                        The name of the election.  Same as the name of the 
                        subdirectory within the 'elections' directory 
                        for information about this election.""")
    parser.add_argument("--elections_dir", help=\
                        """The directory where the subdirectory for the
                        election is to be found.  Defaults to "./elections".""",
                        default="./elections")
    parser.add_argument("--audit_seed",
                        help="""Seed for the random number generator used for
                        auditing (32-bit value). (If omitted, uses clock.)""")
    args = parser.parse_args()
                        
    e = Election()
    e.elections_dir = args.elections_dir
    e.election_name = args.election_name

    load_part_from_json(e, "structure.js")
    finish_election_structure(e)
    check_election_structure(e)
    show_election_structure(e)

    load_part_from_json(e, "data.js")
    finish_election_data(e)
    if e.election_type == "Synthetic":
        myprint("Synthetic vote generation seed:", e.synthetic_seed)
        compute_synthetic_votes(e)
    else:
        myerror("For now, data must be synthetic!")

    # set e.nr[cid][pbcid][r] to number in pbcid with reported vote r:
    for cid in e.cids:
        e.nr[cid] = {}
        for pbcid in e.rel[cid]:
            e.nr[cid][pbcid] = {}
            for r in e.vids[cid]:
                e.nr[cid][pbcid][r] = len([bid for bid in e.bids[pbcid] \
                                           if e.rv[cid][pbcid][bid] == r])
    check_election_data(e)
    show_election_data(e)

    load_part_from_json(e, "audit_parameters.js")
    e.audit_seed = args.audit_seed          # (might be None)
    check_audit_parameters(e)
    audit(e)


if __name__=="__main__":
    main()    

