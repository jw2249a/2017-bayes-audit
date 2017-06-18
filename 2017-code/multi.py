# multi.py
# Ronald L. Rivest
# June 15, 2017
# python3

"""
Prototype code for auditing an election having both multiple contests and
multiple paper ballot collections (e.g. multiple jurisdictions).
Relevant to Colorado state-wide post-election audits in 2017.
"""

"""
Assumes each paper ballot collection is 'pure' in the sense that every
ballot in that collection has the same ballot type.  That is, every
ballot in the collection shows the same set of contests.
"""

import logging
import numpy as np                

import nmcb as test_election

##############################################################################
## Gamma distribution
##############################################################################
# https://docs.scipy.org/doc/numpy-1.11.0/reference/generated/numpy.random.gamma.html

from numpy.random import gamma

# To generate random gamma variate with mean k:
# gamma(k)

##############################################################################
## Elections
##############################################################################

class Election(object):

    def __init__(self):

        e = self

        ### election structure
        e.election_type = "Synthetic"  # string, either "Synthetic" or "Real"
        e.synthetic_seed = 7 # seed for synthetic generation of random votes
        e.cids = []          # list of contest ids
        e.pbcids = []        # list of paper ballot collection ids
        e.bids = dict()      # dict mapping pbcids to list of ballot ids
        e.rel = dict()       # dict mapping (cid, pbcid) pairs to True/False (relevance)
        e.vvids = dict()     # dict mapping cid to list of valid (CANDIDATE) votes (vvids)(strings)
        e.ivids = dict()     # dict mapping cid to list of invalid (NONCANDIDATE) votes (ivids) (strings),
                             # must include "Invalid", "Overvote", "Undervote"
        e.vids = dict()      # dict mapping cid to union of e.vvids[cid] and e.ivids[cid]
        e.collection_type = dict()  # dict mapping pbcid to "CVR" or "noCVR"

        ### reported election results
        e.n = dict()         # e.n[pbcid] number ballots cast in collection pbcid
        e.t = dict()         # dict mapping (cid, pbcid, vid) tuples to counts
        e.ro = dict()        # dict mapping cid to reported outcome
        # computed from the above 
        e.totcid = dict()    # dict mapping cid to total # votes cast in contest
        e.totvot = dict()    # dict mapping (cid, vid) pairs to number of votes recd

        ### audit
        e.audit_seed = 0      # seed for pseudo-random number generation for audit
        e.risk_limit = dict() # mapping from cid to risk limit for that contest
        e.risk = dict()       # mapping from cid to risk (that e.ro[cid] is wrong)
        e.audit_rate = dict() # number of ballots that can be audited per day, by pbcid
        e.plan = dict()       # desired size of sample after next draw, by pbcid
        e.contest_status = dict() # maps cid to one of \
                                  # "Auditing", "Just Watching", "Risk Limit Reached", "Full Recount Needed"
                                  # must be one of "Auditing" "Just Watching" initially
        e.recount_threshold = 0.95 # if e.risk[cid] exceeds 0.95, then full recount called for cid
        e.n_trials = 40000    # number of trials used to estimate risk in compute_contest_risk
        # sample info
        e.av = dict()         # dict mapping (cid, pbcid) pairs to 
                              # dict mapping bids to actual votes for that
                              # contest in that paper ballot collection (sampled ballots)
        e.s = dict()          # e.s[pbcid] number ballots sampled in paper ballot collection pbcid
        # computed from the above
        e.st = dict()         # e.st[(cid, pbcid)] gives sample tally dict for that cid pbcid combo

##############################################################################
## Election structure I/O and validation
##############################################################################

def finish_election_structure(e):
    """ Compute attributes of e that are derivative from others. """

    for cid in e.cids:
        e.vids[cid] = (e.vvids[cid]+e.ivids[cid]).copy()
    
def check_id(id):
    assert isinstance(id, str) and id.isprintable()
    for c in id:
        if c.isspace():
            Logger.warning("check_id warning: id should not contain whitespace: {}".format(id))

def check_election_structure(e):
    
    assert e.election_type in ["Synthetic", "Real"], e.election_type

    assert isinstance(e.cids, (list, tuple))
    assert len(e.cids)>0
    for cid in e.cids:
        assert isinstance(cid, str), cid
        check_id(cid)
    
    assert isinstance(e.pbcids, (list, tuple))
    assert len(e.pbcids)>0, len(e.pbcids)
    for pbcid in e.pbcids:
        assert isinstance(pbcid, str), pbcid
        check_id(pbcid)

    assert isinstance(e.rel, dict)
    for (cid, pbcid) in e.rel:
        assert cid in e.cids, cid
        assert pbcid in e.pbcids, pbcid
        assert isinstance(e.rel[(cid, pbcid)], bool), (cid, pbcid, e.rel[(cid, pbcid)])

    assert isinstance(e.vids, dict)
    for cid in e.vids:
        assert cid in e.cids, cid
        assert isinstance(e.vids[cid], (list, tuple))
        for vid in e.vids[cid]:
            assert isinstance(vid, str), vid
            check_id(vid)
    for cid in e.cids:
        assert cid in e.vids, cid

    assert isinstance(e.ivids, dict)
    for cid in e.ivids:
        assert cid in e.cids, cid
        assert isinstance(e.ivids[cid], (list, tuple))
        for ivid in e.ivids[cid]:
            assert isinstance(ivid, str), ivid
            check_id(ivid)
    for cid in e.cids:
        assert cid in e.ivids, cid

    for cid in e.cids:
        for vvid in e.vvids[cid]:
            for ivid in e.ivids[cid]:
                assert vvid != ivid, (cid, vvid, ivid)

    assert isinstance(e.collection_type, dict)
    for pbcid in e.collection_type:
        assert pbcid in e.pbcids, pbcid
        assert e.collection_type[pbcid] in ["CVR", "noCVR"], \
            e.collection_type[pbcid]
    for pbcid in e.pbcids:
        assert pbcid in e.collection_type, pbcid

def print_election_structure(e):
    print("====== Election structure ======")
    print("Election type:")
    print("    {}".format(e.election_type))
    print("Number of contests:")
    print("    {}".format(len(e.cids)))
    print("e.cids (contest ids):")
    print("    ", end='')
    for cid in e.cids:
        print(cid, end=' ')
    print()
    print("Number of paper ballot collections)")
    print("    {}".format(len(e.pbcids)))
    print("e.pbcids (paper ballot collection ids (e.g. jurisdictions)):")
    print("    ", end='')
    for pbcid in e.pbcids:
        print(pbcid, end=' ')
    print()
    print("e.rel (valid pbcids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                print(pbcid, end=' ')
        print()
    print("e.vvids (valid vote ids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for vvid in e.vvids[cid]:
            print(vvid, end=' ')
        print()
    print("e.ivids (invalid vote ids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for ivid in e.ivids[cid]:
            print(ivid, end=' ')
        print()
    print("e.vids (valid or invalid vote ids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            print(vid, end=' ')
        print()

##############################################################################
## Election data I/O and validation (stuff that depends on cast votes)
##############################################################################

def finish_election_data(e):
    """ 
    Compute election data attributes of e that are derivative from others. 
    """

    # e.totcid[cid] is total number of votes cast for cid
    for cid in e.cids:
        e.totcid[cid] = sum([e.n[pbcid] for pbcid in e.pbcids if e.rel[(cid, pbcid)]])

    # e.totvid[(cid, vid)] is total number cast for vid in cid
    for cid in e.cids:
        for vid in e.vids[cid]:
            e.totvot[(cid, vid)] = sum([e.t[(cid, pbcid, vid)] for pbcid in e.pbcids])


def compute_synthetic_votes(e):
    """
    Make up actual votes and randomly permute their order.
    Only useful for test elections, not for real elections.
    Form of bid is e.b. PBC1::576
    """
    
    np.random.seed(e.synthetic_seed)
    # make up bids
    for pbcid in e.pbcids:
        e.bids[pbcid] = list()
        i = 0
        for j in range(i, i+e.n[pbcid]):
            bid = pbcid + "::" + "%d"%j
            e.bids[pbcid].append(bid)
        i += e.n[pbcid]
    print(e.n)
    # make up votes
    for cid in e.cids:
        # make up all votes first, so overall tally for cid is right
        votes = []
        for vid in e.vids[cid]:
            votes.extend([vid]*e.totvot[(cid, vid)])
        np.random.shuffle(votes)                     # in-place shuffle!
        # break votes up into pieces by pbcid
        i = 0
        for pbcid in e.pbcids:
            e.av[(cid, pbcid)] = dict()
            if e.rel[(cid, pbcid)]:
                for j in range(e.n[pbcid]):
                    bid = e.bids[pbcid][j]
                    vid = votes[j]
                    e.av[(cid, pbcid)][bid] = vid
                i += e.n[pbcid]

def check_election_data(e):

    assert isinstance(e.t, dict)
    for (cid, pbcid, vid) in e.t:
        assert cid in e.cids, cid
        assert pbcid in e.pbcids, pbcid
        assert vid in e.vids[cid], vid
        assert isinstance(e.t[(cid, pbcid, vid)], int), (cid, pbcid, vid, e.t[(cid, pbcid, vid)])
        assert 0 <= e.t[(cid, pbcid, vid)] <= e.n[pbcid], (cid, pbcid, vid, e.t[(cid, pbcid, vid)], "e.t out of range")
        assert e.totvot[(cid, vid)] == sum([e.t[(cid, pbcid, vid)] for pbcid in e.pbcids])
    for cid in e.cids:
        for pbcid in e.pbcids:
            for vid in e.vids[cid]:
                assert (cid, pbcid, vid) in e.t, (cid, pbcid, vid)

    assert isinstance(e.totcid, dict)
    for cid in e.totcid:
        assert cid in e.cids, cid
        assert isinstance(e.totcid[cid], int), (cid, e.totcid[cid])
    for cid in e.cids:
        assert cid in e.totcid, cid

    assert isinstance(e.totvot, dict)
    for (cid, vid) in e.totvot:
        assert cid in e.cids, cid
        assert vid in e.vids[cid], (cid, vid)
        assert isinstance(e.totvot[(cid, vid)], int)
    for cid in e.cids:
        for vid in e.vids[cid]:
            assert (cid, vid) in e.totvot, (cid, vid)

    assert isinstance(e.bids, dict)
    for pbcid in e.pbcids:
        assert isinstance(e.bids[pbcid], list), pbcid

    assert isinstance(e.av, dict)
    for (cid, pbcid) in e.av:
        assert cid in e.cids, cid
        assert pbcid in e.pbcids, pbcid
        assert isinstance(e.av[(cid, pbcid)], dict), (cid, pbcid)
        bidsset = set(e.bids[pbcid])
        for bid in e.av[(cid, pbcid)]:
            assert bid in bidsset, bid
            assert e.av[(cid, pbcid)][bid] in e.vids[cid]
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                assert (cid, pbcid) in e.av

    assert isinstance(e.ro, dict)
    for cid in e.ro:
        assert cid in e.cids, cid
        assert e.ro[cid] in e.vids[cid], (cid, e.ro[cid])
    for cid in e.cids:
        assert cid in e.ro, cid

def print_election_data(e):

    print("====== Reported election data ======")

    print("e.t (total votes for each vid by cid and pbcid):")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                print("    {}.{}: ".format(cid, pbcid), end='')
                for vid in e.vids[cid]:
                    print("{}:{} ".format(vid, e.t[(cid, pbcid, vid)]), end='')
                print()

    print("e.totcid (total votes cast for each cid):")
    for cid in e.cids:
        print("    {}: {}".format(cid, e.totcid[cid]))

    print("e.totvot (total cast for each vid for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            print("{}:{} ".format(vid, e.totvot[(cid, vid)]), end='')
        print()

    print("e.av (first five or so actual votes cast for each cid and pbcid):")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                print("    {}.{}:".format(cid, pbcid), end='')
                for j in range(min(5, len(e.bids[pbcid]))):
                    bid = e.bids[pbcid][j]
                    print(e.av[(cid, pbcid)][bid], end=' ')
                print()

    print("e.ro (reported outcome for each cid):")
    for cid in e.cids:
        print("    {}:{}".format(cid, e.ro[cid]))

##############################################################################
## Tally and outcome computations
##############################################################################

def compute_tally(vec):
    """
    Return dict giving tally of elements in iterable vec.
    """

    tally = dict()
    for x in vec:
        tally[x] = tally.get(x, 0) + 1

    return tally

def plurality(d):
    """
    Return, for input dict d mapping vids to (real) counts, vid with largest count.
    (Tie-breaking done arbitrarily here.)
    """

    max_cnt = -1e90
    max_vid = None
    for vid in d:
        if d[vid]>max_cnt:
            max_cnt = d[vid]
            max_vid = vid

    return max_vid

##############################################################################
## Audit I/O and validation
##############################################################################

def check_audit_parameters(e):

    assert isinstance(e.risk_limit, dict)
    for cid in e.risk_limit:
        assert cid in e.cids, cid
        assert 0.0 <= e.risk_limit[cid] <= 1.0

    assert isinstance(e.audit_rate, dict)
    for pbcid in e.audit_rate:
        assert pbcid in e.pbcids, pbcid
        assert 0 <= e.audit_rate[pbcid]
        
    assert isinstance(e.contest_status, dict)
    for cid in e.contest_status:
        assert cid in e.cids, cid
        assert e.contest_status[cid] in ["Auditing", "Just Watching"], \
            e.contest_status[cid]

def draw_sample(e):
    """ 
    "Draw sample", tally it, save sample tally in e.st[(cid, pbcid)].

    Draw sample is in quotes since it just looks at the first
    e.s[pbcid] elements of e.av[(cid, pbcid)].

    Note that in real life actual sampling might be different than planned;
    here it will be the same.  But code elsewhere allows for such differences.
    Code sets e.s to number of ballots sampled in each pbc.
    """

    e.s = e.plan
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                votes = [e.av[(cid, pbcid)][bid] for bid in e.bids[pbcid][:e.s[pbcid]]]
                e.st[(cid, pbcid)] = compute_tally(votes)
                
def compute_contest_risk(e, cid, st):
    """ 
    Return Bayesian risk (chance that reported outcome is wrong for cid).
    We take st here as argument rather than e.st so
    we can call compute_contest_risk with modified sample counts.
    (This option not yet used.)

    This is the heart of the Bayesian post-election audit method.
    But it could be replaced by a frequentist approach instead, at
    least for those outcome rules and mixes of collection types for
    which a frequentist method is known.
    """

    wrong_outcome_count = 0
    for trial in range(e.n_trials):
        test_tally = {vid:0 for vid in e.vids[cid]}
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                # draw from posterior for each paper ballot collection, sum them
                tally = st[(cid, pbcid)]  # tally from actual sample
                for vid in tally:
                    test_tally[vid] += tally[vid]     
                    assert e.s[pbcid] > 0               # sample sizes should always be positive
                    test_tally[vid] += gamma(tally[vid]) * (e.n[pbcid] - e.s[pbcid]) / e.s[pbcid]
        if e.ro[cid] != plurality(test_tally):
            wrong_outcome_count += 1
    e.risk[cid] = wrong_outcome_count/e.n_trials

def compute_status(e, st):
    """ 
    compute status of each contest and of election
    """

    for cid in e.cids:
        compute_contest_risk(e, cid, st)
        # The following test was could be for !="Just Watching" or for =="Auditing"
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
        if e.contest_status[cid] != "Just Watching":
            if all([e.n[pbcid]==e.s[pbcid] for pbcid in e.pbcids if e.rel[(cid, pbcid)]]):
                e.contest_status[cid] = "All Relevant Ballots Sampled"
            elif e.risk[cid] < e.risk_limit[cid]:
                e.contest_status[cid] = "Risk Limit Reached"
            elif e.risk[cid] > e.recount_threshold:
                e.contest_status[cid] = "Full Recount Needed"
            else:
                e.contest_status[cid] = "Auditing"
        
    e.election_status = set([e.contest_status[cid] for cid in e.cids])

def print_status(e):
    """ 
    Print election and contest status info.
    """

    print("    Risk (that reported outcome is wrong) per cid and contest status:")
    for cid in e.cids:
        print("      ", cid, e.risk[cid], \
              "(limit {})".format(e.risk_limit[cid]), \
              e.contest_status[cid])
    print("    Election status:", e.election_status)
                
def plan_sample(e):
    """ 
    Return a sampling plan (dict of target sample sizes by pbcid) 
    """

    # for now, just simple strategy of looking at more ballots
    # only in those paper ballot collections that are still being audited
    plan = e.s.copy()
    for pbcid in e.pbcids:
        for cid in e.cids:
            if e.rel[(cid, pbcid)] and e.contest_status[cid] == "Auditing":
                # if contest still being audited do as much as you can without
                # exceeding size of paper ballot collection
                plan[pbcid] = min(e.s[pbcid] + e.audit_rate[pbcid], e.n[pbcid])
                break
    return plan

def print_audit_parameters(e):

    print("====== Audit parameters ======")

    print("e.contest_status (initial audit status for each contest):")
    for cid in e.cids:
        print("    {}:{}".format(cid, e.contest_status[cid]))

    print("e.risk_limit (risk limit per contest):")
    for cid in e.cids:
        print("    {}:{}".format(cid, e.risk_limit[cid]))

    print("e.audit_rate (max number of ballots audited/day per pbcid):")
    for pbcid in e.pbcids:
        print("    {}:{}".format(pbcid, e.audit_rate[pbcid]))

    print("e.n_trials (number of trials used to estimate risk in compute_contest_risk):")
    print("    {}".format(e.n_trials))

def print_audit_stage_header(e, stage, last_s):

    print("audit stage", stage)
    print("    New target sample sizes by paper ballot collection:")
    for pbcid in e.pbcids:
        print("      {}: {} (+{})".format(pbcid, e.plan[pbcid], e.plan[pbcid]-last_s[pbcid]))
            
def print_sample_counts(e):

    print("    Total sample counts by contest, paper ballot collection, and vote:")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                print("      {}.{}".format(cid, pbcid), end='')
                tally = e.st[(cid, pbcid)]
                for v in tally:
                    print("  {}:{}".format(v, tally[v]), end='')
                print("  total:{}".format(sum([tally[v] for v in tally])))

def print_audit_summary(e):

    print("=============")
    print("Audit completed!")
    print("All contests have a status in the following set:", e.election_status)
    print("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        print("  {}:{}".format(pbcid, e.s[pbcid]))
    print("Total number of ballots sampled: ", end='')
    print(sum([e.s[pbcid] for pbcid in e.pbcids]))
    
def audit(e):

    e.audit_seed = 11                      # TBD: generate randomly with dice!
    np.random.seed(e.audit_seed)

    print_audit_parameters(e)
    print("====== Audit ======")

    for pbcid in e.pbcids:                           
        e.s[pbcid] = 0
    last_s = e.s
    e.plan = {pbcid:min(e.n[pbcid], e.audit_rate[pbcid]) for pbcid in e.pbcids}
    for stage in range(1, 1000):
        draw_sample(e)
        compute_status(e, e.st)

        print_audit_stage_header(e, stage, last_s)
        print_sample_counts(e)
        print_status(e)

        if "Auditing" not in e.election_status:
            print_audit_summary(e)
            break

        e.plan = plan_sample(e)
        last_s = e.s
        
def main():

    e = Election()

    test_election.election_structure(e)
    finish_election_structure(e)
    check_election_structure(e)
    print_election_structure(e)

    test_election.election_data(e)
    finish_election_data(e)
    if e.election_type == "Synthetic":
        print("Synthetic vote generation seed:", e.synthetic_seed)
        compute_synthetic_votes(e)
    check_election_data(e)
    print_election_data(e)

    test_election.audit_parameters(e)
    audit(e)

Logger = logging.getLogger()
main()    


