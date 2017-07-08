# multi.py
# Ronald L. Rivest
# (with help from Karim Husayn Karimi and Neal McBurnett)
# July 7, 2017

# python3
# clean up with autopep8
#   autopep8 -i multi.py
#   (updates in place; see https://github.com/hhatto/autopep8)

"""
Prototype code for auditing an election having both multiple contests and
multiple paper ballot collections (e.g. multiple jurisdictions).
Possibly relevant to Colorado state-wide post-election audits in Nov 2017.
"""

""" 
This code corresponds to the what Audit Central needs to do, although
it could also be run locally in a county.
"""

# MIT License

import argparse
import datetime
import json
import numpy as np
import os
import sys

import outcomes
import read_structure
import snapshot

##############################################################################
# datetime
##############################################################################


def datetime_string():
    """ Return current datetime as string e.g. '2017-06-26-21-18-30' 
        Year-Month-Day-Hours-Minutes-Seconds
        May be used as a version label in an output filename.
    """
    # https://docs.python.org/3.6/library/datetime.html

    t = datetime.datetime.now()
    return t.strftime("%Y-%m-%d-%H-%M-%S")


##############################################################################
# myprint  (like logging, maybe, but maybe simpler)
##############################################################################

myprint_files = {"stdout": sys.stdout}


def myprint(*args, **kwargs):
    """ variant print statement; prints to all files in myprint_files. """

    for output_file_name in myprint_files:
        kwargs["file"] = myprint_files[output_file_name]
        print(*args, **kwargs)


def close_myprint_files():
    """ Close myprint files other than stdout and stderr. """

    for output_file_name in myprint_files:
        if output_file_name not in ["stdout", "stderr"]:
            myprint_files[output_file_name].close()
            del myprint_files[output_file_name]


# error and warning messages


def myerror(msg):
    """ Print error message and halt immediately """

    print("FATAL ERROR:", msg)
    raise Exception


warnings_given = 0


def mywarning(msg):
    """ Print error message, but keep going.
        Keep track of how many warnings have been given.
    """

    global warnings_given
    warnings_given += 1
    print("WARNING:", msg)


##############################################################################
# Random number generation
##############################################################################

# see numpy.random.RandomState documentation
# Random states used in the program:
# auditRandomState        -- controls random sampling and other audit aspects

# Gamma distribution
# https://docs.scipy.org/doc/numpy-1.11.0/reference/generated/numpy.random.gamma.html
## from numpy.random import gamma
# To generate random gamma variate with mean k:
# gamma(k)  or rs.gamma(k) where rs is a numpy.random.RandomState object


def gamma(k, rs=None):
    """ 
    Return sample from gamma distribution with mean k.
    Differs from standard one that it allows k==0, which returns 0.
    Parameter rs, if present, is a numpy.random.RandomState object.
    """
    global auditRandomState
    if rs == None:
        rs = auditRandomState
    if k <= 0.0:
        return 0.0
    return rs.gamma(k)


# Dirichlet distribution

def dirichlet(tally):
    """ 
    Given tally dict mapping votes (tuples of selids) to nonnegative ints (counts), 
    return dict mapping those votes to elements of Dirichlet distribution sample on
    those votes, where tally values are used as Dirichlet hyperparameters.
    The values produced sum to one.
    """

    dir = {vote: gamma(tally[vote]) for vote in tally}
    total = sum(dir.values())
    dir = {vote: dir[vote] / total for vote in dir}
    return dir


##############################################################################
# Elections
##############################################################################

class Election(object):

    """
    All relevant attributes of an election are stored within an Election 
    object.

    For compatibility with json, an Election object should be viewed as 
    the root of a tree of dicts, where all keys are strings, and the leaves are
    strings or numbers, or lists of strings or numbers.

    In comments: 
       dicts: an object of type "cids->int" is a dict mapping cids to ints,
                and an object of type "cids->pcbids->selids->int" is a nested 
                set of dicts, the top level keyed by a cid, and so on.
       lists: an object of type [bids] is a list of ballot ids.

    Glossary:

        cid    a contest id (e.g. "Den-Mayor")

        pbcid  a paper-ballot collection id (e.g. "Den-P24")

        bid    a ballot id (e.g. "Den-12-234")

        selid  a selection id (e.g. "Yes" or "JohnSmith"). A string.
               If it begins with a "+", it denotes a write-in (e.g. "+BobJones")
               If it begins with a "-", it denotes an error (e.g. "-Invalid" or
               "-Missing" or "-noCVR").  Errors for overvotes and undervotes
               are indicated in another way.  Each selid naively corresponds to
               one bubble filled in on an optical scan ballot.

        vote   a tuple of selids, e.g. ("AliceJones", "BobSmith", "+LizardPeople").
               An empty vote (e.g. () ) is an undervote (for plurality).
               A vote with more than one selid is an overvote (for plurality).
               The order may matter; for preferential voting a vote of the form
               ("AliceJones", "BobSmith", "+LizardPeople") indicates that Alice
               is the voter's first choice, Bob the second, etc.               

    It is recommended (but not required) that ids not contain anything but
             A-Z   a-z   0-9  -   _   .   +
    and perhaps whitespace.
    """

    def __init__(self):

        e = self

        # Note: we use nested dictionaries extensively.
        # variables may be named e.de_wxyz
        # where w, x, y, z give argument type:
        # c = contest id (cid)
        # p = paper ballot collection id (pbcid)
        # r = reported vote
        # a = actual vote
        # b = ballot id (bid)
        # t = audit stage number
        # and where de may be something like:
        # rn = reported number (from initial scan)
        # sn = sample number (from given sample stage)
        # but may be something else.
        #
        # Example:
        # e.rn_cr = reported number of votes by contest
        # and reported vote r, e.g.
        # e.rn_cr[cid][r]  gives such a count.

        # election structure

        e.elections_dirname = ""
        # where the elections data is e.g. "./elections",
        # so e.g. election data for CO-Nov-2017
        # is all in "./elections/CO-Nov-2017"

        e.election_name = ""
        # Name of election (e.g. "CO-Nov-2017")
        # Used as a directory name within elections_dir

        e.election_date = ""
        # In ISO8601 format, e.g. "2017-11-07"

        e.election_url = ""
        # URL to find more information about the election

        e.cids = []
        # list of contest ids (cids)

        e.contest_type = {}
        # cid->contest type  (e.g. "plurality" or "irv")

        e.winners = {}
        # cid->int
        # number of winners in contest 

        e.write_ins = {}
        # cid->str  (e.g. "no" or "qualified" or "arbitrary")

        e.selids_c = {}
        # cid->selids->True
        # dict of some possible selection ids (selids) for each cid 
        # note that e.selids_c is used for both reported selections
        # (from votes in e.rv) and for actual selections (from votes in e.av)
        # it also increases when new selids starting with "+" or "-" are seen.

        e.pbcids = []
        # list of paper ballot collection ids (pbcids)


        e.manager_p = {}
        # pbcid->manager
        # Gives name and/or contact information for collection manager

        e.cvr_type_p = {}
        # pbcid-> "CVR" or "noCVR"

        e.rel_cp = {}
        # cid->pbcid->"True"
        # relevance; only relevant pbcids in e.rel_cp[cid]
        # True means the pbcid *might* contains ballots relevant to cid

        e.bids_p = {}
        # pbcid->[bids]
        # list of ballot ids (bids) for each pcbid

        # election data (reported election results)

        e.rn_p = {}
        # pbcid -> count
        # e.rn_p[pbcid] number ballots reported cast in collection pbcid

        e.votes_c = {}
        # cid->votes
        # e.votes_c[cid] gives all votes seen for cid, reported or actual
        # (These are the votes, not the count.  So e.votes_c is the domain
        # for tallies of contest cid.)

        e.rn_cpr = {}
        # cid->pbcid->rvote->count
        # reported number of votes by contest, paper ballot collection,
        # and reported vote.

        e.ro_c = {}
        # cid->outcome
        # reported outcome by contest

        # computed from the above

        e.rn_c = {}
        # cid->int
        # reported number of votes cast in contest

        e.rn_cr = {}
        # cid->votes->int
        # reported number of votes for each reported vote in cid

        e.rv_cpb = {}
        # cid->pbcid->bid->vote
        # vote in given contest, paper ballot collection, and ballot id
        # e.rv_cpb is like e.av, but reported votes instead of actual votes

        e.synthetic_seed = 2
        # seed for generation of synthetic random votes

        e.syn_rn_cr = {}
        # synthetic reported number cid->vote->count

        e.error_rate = 0.0001
        # error rate used in model for generating synthetic reported votes

        # audit

        e.audit_seed = None
        # seed for pseudo-random number generation for audit

        e.risk_limit_c = {}
        # cid->reals
        # risk limit for each contest

        e.audit_rate_p = {}
        # pbcid->int
        # number of ballots that can be audited per stage in a pcb

        e.stage = "0"
        # current audit stage number (in progress) or last stage completed

        e.last_stage = "-1"
        # previous stage (just one less, in string form)

        e.max_stages = 20
        # maximum number of stages allowed in audit

        e.pseudocount = 0.5
        # hyperparameter for prior distribution
        # (e.g. 0.5 for Jeffrey's distribution)

        e.recount_threshold = 0.95
        # if e.risk[e.stage][cid] exceeds 0.95, then full recount called for
        # cid

        e.n_trials = 100000
        # number of trials used to estimate risk in compute_contest_risk

        # stage-dependent items
        # stage number input is stage when computed
        # stage is denoted t here

        e.plan_tp = {}
        # stage->pbcid->reals
        # sample size wanted after next draw

        e.risk_tc = {}
        # stage->cid->reals
        # risk = probability that e.ro_c[cid] is wrong

        e.contest_status_tc = {}
        # stage->cid-> one of the following:
        #     "Auditing",
        #     "Just Watching",
        #     "Risk Limit Reached",
        #     "Full Recount Needed"
        # initially must be "Auditing" or "Just Watching"

        e.election_status_t = {}
        # stage->list of contest statuses, at most once each

        # sample info

        e.sn_tp = {}
        # stage->pbcid->ints
        # number of ballots sampled so far

        e.av_cpb = {}
        # cid->pbcid->bid->vote
        # (actual votes from sampled ballots)

        # computed from the above sample data

        e.sn_tcpra = {}
        # sampled number: stage->cid->pbcid->rvote->avote->count
        # first vote r is reported vote, second vote a is actual vote

        e.sn_tcpr = {}
        # sampled number stage->cid->pbcid->vote->count
        # sampled number by stage, contest, pbcid, and reported vote


##############################################################################
# Low level i/o for reading election data structure

def copy_dict_tree(dest, source):
    """
    Copy data from source dict tree to dest dict tree, recursively.
    Omit key/value pairs where key starts with "__".
    TODO?? Filter so only desired attributes are copied, for security. 
    OBSOLETE--WAS USED FOR LOADING FROM JSON FILES.
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


##############################################################################
# Election structure I/O and validation
##############################################################################

def get_election_structure(e):

    # load_part_from_json(e, "structure.js")
    election_dirname = os.path.join(e.elections_dirname, e.election_name)
    read_structure.read_election(e, election_dirname)
    read_structure.read_contests(e)
    read_structure.read_collections(e)
    finish_election_structure(e)
    check_election_structure(e)
    show_election_structure(e)


def finish_election_structure(e):

    noCVRvote = ("-noCVR",)

    for cid in e.cids:
        e.votes_c[cid] = {}
        for selid in e.selids_c[cid]:
            e.votes_c[cid][(selid,)] = True
        for pbcid in e.rel_cp[cid]:
            if e.cvr_type_p[pbcid] == "noCVR":
                e.votes_c[cid][noCVRvote] = True


def check_id(id, check_for_whitespace=False):

    if not isinstance(id, str) or not id.isprintable():
        mywarning("id is not string or is not printable: {}".format(id))
    if check_for_whitespace:
        for c in id:
            if c.isspace():
                mywarning("id `id` contains whitespace.")
                break


def check_election_structure(e):

    if not isinstance(e.cids, (list, tuple)):
        myerror("e.cids is not a list or a tuple.")
    if len(e.cids) == 0:
        myerror("e.cids is an empty list of contests.")
    for cid in e.cids:
        check_id(cid)

    if not isinstance(e.pbcids, (list, tuple)):
        myerror("e.pbcids is not a list or a tuple.")
    if len(e.pbcids) == 0:
        myerror("e.pbcids is an empty list of pbcids.")
    for pbcid in e.pbcids:
        check_id(pbcid)

    if not isinstance(e.rel_cp, dict):
        myerror("e.rel_cp is not a dict.")
    for cid in e.rel_cp:
        if cid not in e.cids:
            mywarning("cid is not in e.cids: {}".format(cid))
        for pbcid in e.rel_cp[cid]:
            if pbcid not in e.pbcids:
                mywarning("pbcid is not in e.pbcids: {}".format(pbcid))
            if e.rel_cp[cid][pbcid] != True:
                mywarning("e.rel_cp[{}][{}] != True.".format(
                    cid, pbcid, e.rel_cp[cid][pbcid]))

    for cid in e.selids_c:
        if cid not in e.cids:
            myerror("e.selids_c has a key `{}` not in e.cids.".format(cid))
        for selid in e.selids_c[cid]:
            check_id(selid)
    for cid in e.cids:
        if cid not in e.selids_c:
            mywarning("cid `{}` should be key in e.selids_c".format(cid))

    if not isinstance(e.cvr_type_p, dict):
        myerror("e_cvr_type is not a dict.")
    for pbcid in e.cvr_type_p:
        if pbcid not in e.pbcids:
            mywarning("pbcid `{}` is not in e.pbcids".format(pbcid))
        if e.cvr_type_p[pbcid] not in ["CVR", "noCVR"]:
            mywarning("e.cvr_type_p[{}]==`{}` is not CVR or noCVR"
                      .format(pbcid, e.cvr_type_p[pbcid]))
    for pbcid in e.pbcids:
        if pbcid not in e.cvr_type_p:
            mywarning("pbcid `{}` not key in e.cvr_type_p."
                      .format(pbcid))

    if warnings_given > 0:
        myerror("Too many errors; terminating.")


def show_election_structure(e):
    myprint("====== Election structure ======")
    myprint("Number of contests:")
    myprint("    {}".format(len(e.cids)))
    myprint("e.cids (contest ids):")
    for cid in e.cids:
        myprint("   ", cid)
    myprint("Number of paper ballot collections)")
    myprint("    {}".format(len(e.pbcids)))
    myprint("e.pbcids (paper ballot collection ids (e.g. jurisdictions)):")
    for pbcid in sorted(e.pbcids):
        myprint("   ", pbcid)
    myprint("e.cvr_type_p (either CVR or noCVR) for each pbcid:")
    for pbcid in sorted(e.pbcids):
        myprint("    {}: {} ".format(pbcid, e.cvr_type_p[pbcid]))
    myprint("e.rel_cp (possible pbcids for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for pbcid in sorted(e.rel_cp[cid]):
            myprint(pbcid, end=', ')
        myprint()
    myprint("e.selids_c (valid selection ids for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for selid in sorted(e.selids_c[cid]):
            myprint(selid, end=', ')
        myprint()


##############################################################################
# Election data I/O and validation (stuff that depends on cast votes)
##############################################################################


def is_writein(selid):

    return len(selid) > 0 and selid[0] == "+"


def is_error_selid(selid):

    return len(selid) > 0 and selid[0] == "-"


def get_election_data(e):

    load_part_from_json(e, "data.js")
    # fix up json vote encodings for votes in
    #   e.rn_cpr[cid][pbcid]
    #   e.syn_rn_cr[cid]
    # need to do latter before synthetic data generated
    for cid in e.rn_cpr:
        unpack_json_keys(e.syn_rn_cr[cid])
        for pbcid in e.rn_cpr[cid]:
            unpack_json_keys(e.rn_cpr[cid][pbcid])

    finish_election_data(e)
    check_election_data(e)
    show_election_data(e)


def finish_election_data(e):
    """ 
    Compute election data attributes that are derivative from others. 
    or that need conversion (e.g. strings-->tuples from json keys).
    """

    # make sure e.selids_c contains all +/- selids seen in reported votes
    # and that e.votes_c[cid] contains all reported votes
    for cid in e.cids:
        for pbcid in e.rel_cp[cid]:
            for bid in e.bids_p[pbcid]:
                r = e.rv_cpb[cid][pbcid][bid]
                e.votes_c[r] = True
                for selid in r:
                    if is_writein(selid) or is_error_selid(selid):
                        e.selids_c[cid][selid] = True

    # set e.rn_cpr[cid][pbcid][r] to number in pbcid with reported vote r:
    for cid in e.cids:
        e.rn_cpr[cid] = {}
        for pbcid in e.rel_cp[cid]:
            e.rn_cpr[cid][pbcid] = {}
            for r in e.votes_c[cid]:
                e.rn_cpr[cid][pbcid][r] = len([bid for bid in e.bids_p[pbcid]
                                               if e.rv_cpb[cid][pbcid][bid] == r])

    # e.rn_c[cid] is reported number of votes cast in contest cid
    for cid in e.cids:
        e.rn_c[cid] = sum([e.rn_cpr[cid][pbcid][vote]
                           for pbcid in e.rn_cpr[cid]
                           for vote in e.votes_c[cid]])

    # e.rn_cr[cid][vote] is reported number cast for vote in cid
    for cid in e.cids:
        e.rn_cr[cid] = {}
        for pbcid in e.rn_cpr[cid]:
            for vote in e.votes_c[cid]:
                if vote not in e.rn_cr[cid]:
                    e.rn_cr[cid][vote] = 0
                if vote not in e.rn_cpr[cid][pbcid]:
                    e.rn_cpr[cid][pbcid][vote] = 0
                e.rn_cr[cid][vote] += e.rn_cpr[cid][pbcid][vote]


def check_election_data(e):

    if not isinstance(e.rn_cpr, dict):
        myerror("e.rn_cpr is not a dict.")
    for cid in e.rn_cpr:
        if cid not in e.cids:
            mywarning("cid `{}` not in e.cids.".format(cid))
        for pbcid in e.rn_cpr[cid]:
            if pbcid not in e.pbcids:
                mywarning("pbcid `{}` is not in e.pbcids.".format(pbcid))
            for vote in e.rn_cpr[cid][pbcid]:
                for selid in vote:
                    if selid not in e.selids_c[cid] and selid[0].isalnum():
                        mywarning(
                            "selid `{}` is not in e.selids_c[{}]."
                            .format(selid, cid))
                if not isinstance(e.rn_cpr[cid][pbcid][vote], int):
                    mywarning("value `e.rn_cpr[{}][{}][{}] = `{}` is not an integer."
                              .format(cid, pbcid, vote, e.rn_cpr[cid][pbcid][vote]))
                if not (0 <= e.rn_cpr[cid][pbcid][vote] <= e.rn_p[pbcid]):
                    mywarning("value `e.rn_cpr[{}][{}][{}] = `{}` is out of range 0:{}."
                              .format(cid, pbcid, vote, e.rn_cpr[cid][pbcid][vote],
                                      e.rn_p[pbcid]))
                if e.rn_cr[cid][vote] != \
                        sum([e.rn_cpr[cid][pbcid][vote]
                             for pbcid in e.rel_cp[cid]]):
                    mywarning("sum of e.rn_cpr[{}][*][{}] is not e.rn_cr[{}][{}]."
                              .format(cid, vote, cid, vote))
    for cid in e.cids:
        if cid not in e.rn_cpr:
            mywarning("cid `{}` is not a key for e.rn_cpr".format(cid))
        for pbcid in e.rel_cp[cid]:
            if pbcid not in e.rn_cpr[cid]:
                mywarning(
                    "pbcid {} is not a key for e.rn_cpr[{}].".format(pbcid, cid))
            # for selid in e.selids_c[cid]:
            #     assert selid in e.rn_cpr[cid][pbcid], (cid, pbcid, selid)
            # ## not necessary, since missing selids have assumed count of 0

    if not isinstance(e.rn_c, dict):
        myerror("e.rn_c is not a dict.")
    for cid in e.rn_c:
        if cid not in e.cids:
            mywarning("e.rn_c key `{}` is not in e.cids.".format(cid))
        if not isinstance(e.rn_c[cid], int):
            mywarning("e.rn_c[{}] = {}  is not an integer.".format(
                cid, e.rn_c[cid]))
    for cid in e.cids:
        if cid not in e.rn_c:
            mywarning("cid `{}` is not a key for e.rn_c".format(cid))

    if not isinstance(e.rn_cr, dict):
        myerror("e.rn_cr is not a dict.")
    for cid in e.rn_cr:
        if cid not in e.cids:
            mywarning("e.rn_cr key cid `{}` is not in e.cids".format(cid))
        for vote in e.rn_cr[cid]:
            for selid in vote:
                if (not is_writein(selid) and not is_error_selid(selid)) \
                   and not selid in e.selids_c[cid]:
                    mywarning("e.rn_cr[{}] key `{}` is not in e.selids_c[{}]"
                              .format(cid, selid, cid))
            if not isinstance(e.rn_cr[cid][vote], int):
                mywarning("e.rn_cr[{}][{}] = {} is not an integer."
                          .format(cid, vote, e.rn_cr[cid][vote]))
    for cid in e.cids:
        if cid not in e.rn_cr:
            mywarning("cid `{}` is not a key for e.rn_cr".format(cid))

    if not isinstance(e.bids_p, dict):
        myerror("e.bids_p is not a dict.")
    for pbcid in e.pbcids:
        if not isinstance(e.bids_p[pbcid], list):
            myerror("e.bids_p[{}] is not a list.".format(pbcid))

    if not isinstance(e.av_cpb, dict):
        myerror("e.av_cpb is not a dict.")
    for cid in e.av_cpb:
        if cid not in e.cids:
            mywarning("e.av_cpb key {} is not in e.cids.".format(cid))
        for pbcid in e.av_cpb[cid]:
            if pbcid not in e.pbcids:
                mywarning("e.av_cpb[{}] key `{}` is not in e.pbcids"
                          .format(cid, pbcid))
            if not isinstance(e.av_cpb[cid][pbcid], dict):
                myerror("e.av_cpb[{}][{}] is not a dict.".format(cid, pbcid))
            bidsset = set(e.bids_p[pbcid])
            for bid in e.av_cpb[cid][pbcid]:
                if bid not in bidsset:
                    mywarning("bid `{}` from e.av_cpb[{}][{}] is not in e.bids_p[{}]."
                              .format(bid, cid, pbcid, pbcid))

    for cid in e.cids:
        if cid not in e.av_cpb:
            mywarning("cid `{}` is not a key for e.av_cpb.".format(cid))
        for pbcid in e.rel_cp[cid]:
            if pbcid not in e.av_cpb[cid]:
                mywarning("pbcid `{}` is not in e.av_cpb[{}]."
                          .format(pbcid, cid))

    if not isinstance(e.rv_cpb, dict):
        myerror("e.rv_cpb is not a dict.")
    for cid in e.rv_cpb:
        if cid not in e.cids:
            mywarning("e.rv_cpb key `{}` is not in e.cids.".format(cid))
        for pbcid in e.rv_cpb[cid]:
            if pbcid not in e.pbcids:
                mywarning("e.rv_cpb[{}] key `{}` is not in e.pbcids."
                          .format(cid, pbcid))
            if not isinstance(e.rv_cpb[cid][pbcid], dict):
                myerror("e.rv_cpb[{}][{}] is not a dict.".format(cid, pbcid))
            bidsset = set(e.bids_p[pbcid])
            for bid in e.rv_cpb[cid][pbcid]:
                if bid not in bidsset:
                    mywarning("bid `{}` from e.rv_cpb[{}][{}] is not in e.bids_p[{}]."
                              .format(bid, cid, pbcid, pbcid))
    for cid in e.cids:
        if cid not in e.rv_cpb:
            mywarning("cid `{}` is not a key in e.rv_cpb.".format(cid))
        for pbcid in e.rel_cp[cid]:
            if pbcid not in e.rv_cpb[cid]:
                mywarning("pbcid `{}` from e.rel_cp[{}] is not a key for e.rv_cpb[{}]."
                          .format(pbcid, cid, cid))

    if not isinstance(e.ro_c, dict):
        myerror("e.ro_c is not a dict.")
    for cid in e.ro_c:
        if cid not in e.cids:
            mywarning("cid `{}` from e.rv_cpb is not in e.cids".format(cid))
    for cid in e.cids:
        if cid not in e.ro_c:
            mywarning("cid `{}` is not a key for e.ro_c.".format(cid))

    if warnings_given > 0:
        myerror("Too many errors; terminating.")


def show_election_data(e):

    myprint("====== Reported election data ======")

    myprint("e.rn_cpr (total reported votes for each vote by cid and pbcid):")
    for cid in e.cids:
        for pbcid in sorted(e.rel_cp[cid]):
            myprint("    {}.{}: ".format(cid, pbcid), end='')
            for vote in sorted(e.rn_cpr[cid][pbcid]):
                myprint("{}:{} ".format(
                    vote, e.rn_cpr[cid][pbcid][vote]), end='')
            myprint()

    myprint("e.rn_c (total votes cast for each cid):")
    for cid in e.cids:
        myprint("    {}: {}".format(cid, e.rn_c[cid]))

    myprint("e.rn_cr (total cast for each vote for each cid):")
    for cid in e.cids:
        myprint("    {}: ".format(cid), end='')
        for vote in sorted(e.rn_cr[cid]):
            myprint("{}:{} ".format(vote, e.rn_cr[cid][vote]), end='')
        myprint()

    myprint("e.av_cpb (first five or so actual votes cast for each cid and pbcid):")
    for cid in e.cids:
        for pbcid in sorted(e.rel_cp[cid]):
            myprint("    {}.{}:".format(cid, pbcid), end='')
            for j in range(min(5, len(e.bids_p[pbcid]))):
                bid = e.bids_p[pbcid][j]
                myprint(e.av_cpb[cid][pbcid][bid], end=' ')
            myprint()

    myprint("e.ro_c (reported outcome for each cid):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.ro_c[cid]))

##############################################################################
# Audit I/O and validation
##############################################################################


def draw_sample(e):
    """ 
    "Draw sample", tally it, save sample tally in e.sn_tcpra[stage][cid][pbcid]. 
    Update e.sn_tcpr

    Draw sample is in quotes since it just looks at the first
    e.sn_tp[stage][pbcid] elements of e.av_cpb[cid][pbcid].
    Code sets e.sn_tcpr[e.stage][cid][pbcid][r] to number in sample with reported vote r.

    Code sets e.sn_tp to number of ballots sampled in each pbc (equal to plan).
    Note that in real life actual sampling number might be different than planned;
    here it will be the same.  But code elsewhere allows for such differences.
    """

    e.sn_tp[e.stage] = e.plan_tp[e.last_stage]
    e.sn_tcpr[e.stage] = {}
    for cid in e.cids:
        e.sn_tcpra[e.stage][cid] = {}
        e.sn_tcpr[e.stage][cid] = {}
        for pbcid in e.rel_cp[cid]:
            e.sn_tcpr[e.stage][cid][pbcid] = {}
            avs = [e.av_cpb[cid][pbcid][bid]
                   for bid in e.bids_p[pbcid][:e.sn_tp[e.stage][pbcid]]]  # actual
            rvs = [e.rv_cpb[cid][pbcid][bid]
                   for bid in e.bids_p[pbcid][:e.sn_tp[e.stage][pbcid]]]  # reported
            arvs = list(zip(avs, rvs))  # list of (actual, reported) vote pairs
            e.sn_tcpra[e.stage][cid][pbcid] = outcomes.compute_tally2(arvs)
            for r in e.rn_cpr[cid][pbcid]:
                e.sn_tcpr[e.stage][cid][pbcid][r] = len(
                    [rr for rr in rvs if rr == r])


def show_sample_counts(e):

    myprint("    Total sample counts by Contest.PaperBallotCollection[reported selection]"
            "and actual selection:")
    for cid in e.cids:
        for pbcid in sorted(e.rel_cp[cid]):
            tally2 = e.sn_tcpra[e.stage][cid][pbcid]
            for r in sorted(tally2.keys()):  # r = reported vote
                myprint("      {}.{}[{}]".format(cid, pbcid, r), end='')
                for a in sorted(tally2[r].keys()):
                    myprint("  {}:{}".format(a, tally2[r][a]), end='')
                myprint("  total:{}".format(e.sn_tcpr[e.stage][cid][pbcid][r]))


##############################################################################
# Risk measurement

def compute_contest_risk(e, cid, st):
    """ 
    Compute Bayesian risk (chance that reported outcome is wrong for cid).
    We take st here as argument rather than e.sn_tcpra so
    we can call compute_contest_risk with modified sample counts.
    (This option not yet used, but might be later, when optimizing
    workload.)

    This is the heart of the Bayesian post-election audit method.
    But it could be replaced by a frequentist approach instead, at
    least for those outcome rules and mixes of collection types for
    which a frequentist method is known.

    The comparison and ballot-polling audits are blended here; the
    election data just records an ("-noCVR",) vote for the reported vote
    in a noCVR paper ballot collection.
    """

    wrong_outcome_count = 0
    for trial in range(e.n_trials):
        test_tally = {vote: 0 for vote in e.rn_cr[cid]}
        for pbcid in e.rel_cp[cid]:
            # draw from posterior for each paper ballot collection, sum them
            # stratify by reported selection
            for r in e.sn_tcpra[e.stage][cid][pbcid]:
                tally = e.sn_tcpra[e.stage][cid][pbcid][r].copy()
                # for a in tally:
                #    tally[a] = tally.get(a, 0)
                for a in tally:
                    tally[a] += e.pseudocount
                dirichlet_dict = dirichlet(tally)
                nonsample_size = e.rn_cpr[cid][pbcid][r] - \
                    e.sn_tcpr[e.stage][cid][pbcid][r]
                for a in tally:
                    # increment actual tally for (actual vote a with reported
                    # vote r)
                    test_tally[a] += tally[a]
                    if e.sn_tcpr[e.stage][cid][pbcid][r] > 0:
                        test_tally[a] += dirichlet_dict[a] * nonsample_size
        if e.ro_c[cid] != outcomes.compute_outcome(e, cid, test_tally):  
            wrong_outcome_count += 1
    e.risk_tc[e.stage][cid] = wrong_outcome_count / e.n_trials


def compute_contest_risks(e, st):

    for cid in e.cids:
        compute_contest_risk(e, cid, st)


##############################################################################
# Compute status of each contest and of election


def compute_contest_and_election_statuses(e):
    """ 
    compute status of each contest and of election, from 
    already-computed contest risks.
    """

    for cid in e.cids:
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
        e.contest_status_tc[e.stage][cid] = e.contest_status_tc[e.last_stage][cid]
        if e.contest_status_tc[e.stage][cid] != "Just Watching":
            if all([e.rn_p[pbcid] == e.sn_tp[e.stage][pbcid] for pbcid in e.rel_cp[cid]]):
                e.contest_status_tc[e.stage][cid] = "All Relevant Ballots Sampled"
            elif e.risk_tc[e.stage][cid] < e.risk_limit_c[cid]:
                e.contest_status_tc[e.stage][cid] = "Risk Limit Reached"
            elif e.risk_tc[e.stage][cid] > e.recount_threshold:
                e.contest_status_tc[e.stage][cid] = "Full Recount Needed"
            else:
                e.contest_status_tc[e.stage][cid] = "Auditing"

    e.election_status_t[e.stage] = \
        sorted(list(set([e.contest_status_tc[e.stage][cid]
                         for cid in e.cids])))


def show_risks_and_statuses(e):
    """ 
    Show election and contest statuses for current stage. 
    """

    myprint("    Risk (that reported outcome is wrong) and contest status per cid:")
    for cid in e.cids:
        myprint("     ", cid, e.risk_tc[e.stage][cid],
                "(limit {})".format(e.risk_limit_c[cid]),
                e.contest_status_tc[e.stage][cid])
    myprint("    Election status:", e.election_status_t[e.stage])


##############################################################################
# Audit parameters

def get_audit_seed(e, args):

    global auditRandomState

    e.audit_seed = args.audit_seed
    # audit_seed might be None if no command-line argument given

    auditRandomState = np.random.RandomState(e.audit_seed)


def get_audit_parameters(e, args):

    load_part_from_json(e, "audit_parameters.js")
    # command line can override .js file CHECK THIS
    get_audit_seed(e, args)
    check_audit_parameters(e)


def check_audit_parameters(e):

    if not isinstance(e.risk_limit_c, dict):
        myerror("e.risk_limit_c is not a dict.")
    for cid in e.risk_limit_c:
        if cid not in e.cids:
            mywarning("e.risk_limit_c cid key `{}` is not in e.cids."
                      .format(cid))
        if not (0.0 <= e.risk_limit_c[cid] <= 1.0):
            mywarning("e.risk_limit_c[{}] not in interval [0,1]".format(cid))

    if not isinstance(e.audit_rate_p, dict):
        myerror("e.audit_rate_p is not a dict.")
    for pbcid in e.audit_rate_p:
        if pbcid not in e.pbcids:
            mywarning("pbcid `{}` is a key for e.audit_rate_p but not in e.pbcids."
                      .format(pbcid))
        if not 0 <= e.audit_rate_p[pbcid]:
            mywarning("e.audit_rate_p[{}] must be nonnegative.".format(pbcid))

    if not isinstance(e.contest_status_tc, dict):
        myerror("e.contest_status_tc is not a dict.")
    if "0" not in e.contest_status_tc:
        myerror("e.contest_status_tc must have `0` as a key.")
    for cid in e.contest_status_tc["0"]:
        if cid not in e.cids:
            mywarning("cid `{}` is key in e.contest_status_tc but not in e.cids"
                      .format(cid))
        if e.contest_status_tc["0"][cid] not in ["Auditing", "Just Watching"]:
            mywarning("e.contest_status_tc['0'][{}] must be `Auditing` or `Just Watching`."
                      .format(cid))

    if warnings_given > 0:
        myerror("Too many errors; terminating.")


def show_audit_parameters(e):

    myprint("====== Audit parameters ======")

    myprint("e.contest_status_tc (initial audit status for each contest):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.contest_status_tc["0"][cid]))

    myprint("e.risk_limit_c (risk limit per contest):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.risk_limit_c[cid]))

    myprint("e.audit_rate_p (max number of ballots audited/day per pbcid):")
    for pbcid in sorted(e.pbcids):
        myprint("    {}:{}".format(pbcid, e.audit_rate_p[pbcid]))

    myprint("e.max_stages (max number of audit stages allowed):")
    myprint("    {}".format(e.max_stages))

    myprint("e.n_trials (number of trials used to estimate risk "
            "in compute_contest_risk):")
    myprint("    {}".format(e.n_trials))

    myprint("e.pseudocount (hyperparameter for prior distribution,")
    myprint("    {}".format(e.pseudocount))

    myprint("e.audit_seed (seed for audit pseudorandom number generation)")
    myprint("    {}".format(e.audit_seed))


def initialize_audit(e):

    e.sn_tp["0"] = {}
    for pbcid in e.pbcids:
        e.sn_tp["0"][pbcid] = 0
    # Initial plan size is just audit rate, for each pbcid.
    e.plan_tp["0"] = {pbcid: min(
        e.rn_p[pbcid], e.audit_rate_p[pbcid]) for pbcid in e.pbcids}


def show_audit_stage_header(e):

    myprint("audit stage", e.stage)
    myprint("    New target sample sizes by paper ballot collection:")
    for pbcid in e.pbcids:
        last_s = e.sn_tp[e.last_stage]
        myprint("      {}: {} (+{})"
                .format(pbcid,
                        e.plan_tp[e.last_stage][pbcid],
                        e.plan_tp[e.last_stage][pbcid] - last_s[pbcid]))


def audit_stage(e, stage):

    e.last_stage = "{}".format(stage - 1)   # json keys must be strings
    e.stage = "{}".format(stage)
    e.risk_tc[e.stage] = {}
    e.contest_status_tc[e.stage] = {}
    e.sn_tp[e.stage] = {}
    e.sn_tcpra[e.stage] = {}

    draw_sample(e)
    compute_contest_risks(e, e.sn_tcpra)
    compute_contest_and_election_statuses(e)

    show_audit_stage_header(e)
    show_sample_counts(e)
    show_risks_and_statuses(e)


def stop_audit(e):

    return "Auditing" not in e.election_status_t[e.stage]


def audit(e, args):

    get_audit_seed(e, args)
    initialize_audit(e)
    show_audit_parameters(e)

    myprint("====== Audit ======")

    for stage in range(1, e.max_stages + 1):
        audit_stage(e, stage)
        if stop_audit(e):
            break
        compute_plan(e)
    show_audit_summary(e)


def show_audit_summary(e):

    global myprint_switches

    myprint("=============")
    myprint("Audit completed!")

    myprint("All contests have a status in the following list:",
            e.election_status_t[e.stage])
    if "Auditing" not in e.election_status_t[e.stage]:
        myprint("No contest still has `Auditing' status.")
    if "Full Recount Needed" in e.election_status_t[e.stage]:
        myprint("At least one contest needs a full recount.")
    if int(e.stage) == e.max_stages:
        myprint("Maximum number of audit stages ({}) reached."
                .format(e.max_stages))

    myprint("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        myprint("  {}:{}".format(pbcid, e.sn_tp[e.stage][pbcid]))
    myprint_switches = ["std"]
    myprint("Total number of ballots sampled: ", end='')
    myprint(sum([e.sn_tp[e.stage][pbcid] for pbcid in e.pbcids]))


##############################################################################
# Compute audit plan for next stage

def compute_plan(e):
    """ Compute a sampling plan for the next stage.
        Put in e.plan_tp[e.stage] a dict of target sample sizes keyed by pbcid. 
        Only input is contest statuses, pbcid audit rates, pbcid current
        sample size, and pcbid size.
    """

    # for now, use simple strategy of looking at more ballots
    # only in those paper ballot collections that are still being audited
    e.plan_tp[e.stage] = e.sn_tp[e.stage].copy()
    for cid in e.cids:
        for pbcid in e.rel_cp[cid]:
            if e.contest_status_tc[e.stage][cid] == "Auditing":
                # if contest still being audited do as much as you can without
                # exceeding size of paper ballot collection
                e.plan_tp[e.stage][pbcid] = \
                    min(e.sn_tp[e.stage][pbcid] +
                        e.audit_rate_p[pbcid], e.rn_p[pbcid])
    return


##############################################################################
# Input/output at the file-handling level

def greatest_name(dirpath, startswith, endswith, dir_wanted=False):
    """ 
    Return the filename (or, optionally, directory name) in the given directory 
    that begins and ends with strings startswith and endswith, respectively.
    If there is more than one such file, return the greatest (lexicographically)
    such filename.  Raise an error if there are no such files.
    The portion between the prefix startswith and the suffix endswith is called
    the version label in the documentation.
    If switch "dir_wanted" is True, then return greatest directory name, not filename.
    Example:  greatest_name(".", "foo", ".csv")
    will return "foo-11-09.csv" from a directory containing files
    with names  "foo-11-09.csv", "foo-11-08.csv", and "zeb-12-12.csv".
    """

    selected_filename = ""
    for filename in os.listdir(dirpath):
        full_filename = os.path.join(dirpath,filename)
        if (dir_wanted == False and os.path.isfile(full_filename) or \
            dir_wanted == True and not os.path.isfile(full_filename)) and\
           filename.startswith(startswith) and \
           filename.endswith(endswith) and \
           filename > selected_filename:
            selected_filename = filename
    if selected_filename == "":
        if dir_wanted == False:
            myerror("No files in `{}` have a name starting with `{}` and ending with `{}`."
                    .format(dirpath, startswith, endswith))
        else:
            myerror("No directories in `{}` have a name starting with `{}` and ending with `{}`."
                    .format(dirpath, startswith, endswith))
    return selected_filename


##############################################################################
# Command-line arguments

def parse_args():

    parser = argparse.ArgumentParser(description="""multi.py: A Bayesian post-election audit program for an
            election with multiple contests and multiple paper ballot 
            collections.""")

    #v1 and v2:
    parser.add_argument("election_name", help="""
                        The name of the election.  Same as the name of the 
                        subdirectory within the 'elections' directory 
                        for information about this election.""")
    parser.add_argument("--elections_dir", help="""The directory where the subdirectory for the
                        election is to be found.  Defaults to "./elections".""",
                        default="./elections")
    parser.add_argument("--audit_seed",
                        help="""Seed for the random number generator used for
                        auditing (32-bit value). (If omitted, uses clock.)""")
    ## v2:
    parser.add_argument("--read_structure", action="store_true", help="""
                        Read and check election structure.""")
    parser.add_argument("--read_reported", action="store_true", help="""
                        Read and check reported election data and results.""")
    parser.add_argument("--read_seed", action="store_true", help="""
                        Read audit seed.""")
    parser.add_argument("--make_orders", action="store_true", help="""
                        Make sampling orders files.""")
    parser.add_argument("--read_audited", action="store_true", help="""
                        Read and check audited votes.""")
    parser.add_argument("--stage",
                        help="""Run stage STAGE of the audit (may specify "ALL").""")
    args = parser.parse_args()
    print("Command line arguments:", args)
    return args


def process_args(e, args):

    e.elections_dirname = args.elections_dir
    e.election_name = args.election_name

    if args.read_structure:
        print("read_structure")
        get_election_structure(e)
    elif args.read_reported:
        print("read_reported")
        get_election_structure(e)
        get_election_data(e)
    elif args.read_seed:
        print("read_seed")
        get_election_structure(e)
        get_election_data(e)
        get_audit_parameters(e, args)
    elif args.make_orders:
        print("make_orders")
    elif args.read_audited:
        print("read_audited")
    elif args.stage:
        print("stage", args.stage)
        get_election_structure(e)
        get_election_data(e)
        get_audit_parameters(e, args)
        audit(e, args)


def main():

    global myprint_switches
    myprint_switches = []       # put this after following line to suppress printing
    myprint_switches = ["std"]

    print("multi.py -- Bayesian audit support program.")

    global start_datetime_string
    start_datetime_string = datetime_string()
    print("Starting data/time:", start_datetime_string)

    args = parse_args()
    e = Election()
    try:
        process_args(e, args)
    finally:
        close_myprint_files()


if __name__ == "__main__":
    main()
