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

import random
random.seed(1)     # fix seed for reproducibility (make deterministic)

##############################################################################
## Gamma distribution
##############################################################################
# https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.gamma.html

from scipy.stats import gamma

# To generate random gamma variate with mean k:
# gamma.rvs(k)

##############################################################################
## Elections
##############################################################################

class Election(object):
    """ so we can hang attributes off of an election """
    pass

def setup():
    e = Election()
    # election structure
    e.cids = []          # list of contest ids
    e.nc = 0             # number of contests
    e.pbcids = []        # list of paper ballot collection ids
    e.npbc = 0           # number of paper ballot collections (e.g. jurisdictions)
    e.rel = dict()       # dict mapping (cid, pbcid) pairs to True/False (relevance)
    e.vids = dict()      # dict mapping cid to list of allowable votes (vids)(strings)

    # reported election results
    e.n = dict()         # e.n[pbcid] number ballots cast in collection pbcid
    e.t = dict()         # dict mapping (cid, pbcid, vid) tuples to counts
    e.ro = dict()        # dict mapping cid to reported outcome
    # computed from the above 
    e.totcid = dict()    # dict mapping cid to total # votes cast in contest
    e.totvot = dict()    # dict mapping (cid, vid) pairs to number of votes recd

    # audit
    e.risk_limit = dict() # mapping from cid to risk limit for that contest
    e.risk = dict()       # mapping from cid to risk (that e.ro[cid] is wrong)
    e.audit_rate = dict() # number of ballots that can be audited per day, by pbcid
    e.plan = dict()       # desired size of sample after next draw, by pbcid
    # sample info
    e.av = dict()         # dict mapping (cid, pbcid) pairs to list of actual votes for that
                          # contest in that paper ballot collection (sampled ballots)
    e.s = dict()          # e.s[pbcid] number ballots sampled in paper ballot collection pbcid
    # computed from the above
    e.st = dict()         # e.st[(cid, pbcid)] gives sample tally dict for that cid pbcid combo

    return e

def nmcb(e):
    """Fill in fields for Neal McBurnett example"""

    # four contests
    e.cids = ["I", "C1", "C2", "C3", "F23"]

    # three paper ballot collections
    e.pbcids = ["PBC1", "PBC2", "PBC3"]

    # Structure
    for cid in e.cids:
        for pbcid in e.pbcids:
            e.rel[(cid, pbcid)] = False    # default
    e.rel[("I", "PBC1")] = True            # I is in all counties
    e.rel[("I", "PBC2")] = True          
    e.rel[("I", "PBC3")] = True          
    e.rel[("C1", "PBC1")] = True           # C1 is only in PBC1
    e.rel[("C2", "PBC2")] = True           # C2 is only in PBC2
    e.rel[("C3", "PBC3")] = True           # C3 is only in PBC3
    e.rel[("F23", "PBC2")] = True          # F23 is in both PBC2 and PBC3
    e.rel[("F23", "PBC3")] = True

    e.vids["I"] = ["0", "1"]                 # valid votes for each contest
    e.vids["C1"] = ["0", "1"]
    e.vids["C2"] = ["0", "1"]
    e.vids["C3"] = ["0", "1"]
    e.vids["F23"] = ["0", "1"]

    # Election data
    # 100000 ballots for each paper ballot collection
    for pbcid in e.pbcids:
        e.n[pbcid] = 100000

    # e.t = vote totals for each cid pbcid vid combo
    for cid in e.cids:
        for pbcid in e.pbcids:
            for vid in e.vids[cid]:
                e.t[(cid, pbcid, vid)] = 0
    e.t[("I", "PBC1", "1")] = 50500           # I is in all counties (margin 1%)
    e.t[("I", "PBC1", "0")] = 49500
    e.t[("I", "PBC2", "1")] = 50500          
    e.t[("I", "PBC2", "0")] = 49500
    e.t[("I", "PBC3", "1")] = 50500          
    e.t[("I", "PBC3", "0")] = 49500
    e.t[("C1", "PBC1","1")] = 65000          # C1 is only in PBC1 (margin 30%)
    e.t[("C1", "PBC1", "0")] = 35000
    e.t[("C2", "PBC2", "1")] = 60000          # C2 is only in PBC2 (margin 20%)
    e.t[("C2", "PBC2", "0")] = 40000
    e.t[("C3", "PBC3", "1")] = 55000          # C3 is only in PBC3 (margin 10%)
    e.t[("C3", "PBC3", "0")] = 45000
    e.t[("F23", "PBC2", "1")] = 52500         # F23 is in both PBC2 and PBC3 (margin 5%)
    e.t[("F23", "PBC2", "0")] = 47500
    e.t[("F23", "PBC3", "1")] = 52500
    e.t[("F23", "PBC3", "0")] = 47500
    
    # e.ro = reported outcomes for each cid (all correct here)
    e.ro["I"] = "1"                         
    e.ro["C1"] = "1"
    e.ro["C2"] = "1"
    e.ro["C3"] = "1"
    e.ro["F23"] = "1"

    # Audit parameters
    e.risk_limit["I"] = 0.05               # risk limit by contest
    e.risk_limit["C1"] = 0.05
    e.risk_limit["C2"] = 0.05
    e.risk_limit["C3"] = 0.05
    e.risk_limit["F23"] = 0.10  

    e.audit_rate["PBC1"] = 40    # max rate/stage for auditing ballots by pbcid
    e.audit_rate["PBC2"] = 60 
    e.audit_rate["PBC3"] = 80

    return e

def finish_setup(e):
    """ Compute attributes of e that are derivative from others. """

    ###### Structure of election
    e.nc = len(e.cids)                     # number of contests
    e.npbc = len(e.pbcids)                 # number of paper ballot collections
    
    ###### Election data
    # e.totcid[cid] is total number of votes cast for cid
    for cid in e.cids:
        e.totcid[cid] = sum([e.n[pbcid] for pbcid in e.pbcids if e.rel[(cid, pbcid)]])

    # e.totvid[(cid, vid)] is total number cast for vid in cid
    for cid in e.cids:
        for vid in e.vids[cid]:
            e.totvot[(cid, vid)] = sum([e.t[(cid, pbcid, vid)] for pbcid in e.pbcids])

    # make up actual votes and randomly permute their order
    for cid in e.cids:
        # make up all votes first, so overall tally for cid is right
        votes = []
        for vid in e.vids[cid]:
            votes.extend([vid]*e.totvot[(cid, vid)])
        random.shuffle(votes)
        # break votes up into pieces by pbc
        i = 0
        for pbcid in e.pbcids:
            e.av[(cid, pbcid)] = []
            if e.rel[(cid, pbcid)]:
                e.av[(cid, pbcid)] = votes[i:i+e.n[pbcid]]
                i = i + e.n[pbcid]

def check_election_structure(e):
    
    assert isinstance(e.cids, (list, tuple))
    assert len(e.cids)>0
    for cid in e.cids:
        assert isinstance(cid, str), cid
    assert e.nc == len(e.cids)
    
    assert isinstance(e.pbcids, (list, tuple))
    assert len(e.pbcids)>0, len(e.pbcids)
    assert e.npbc == len(e.pbcids), e.npbc

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

def print_election_structure(e):
    print("====== Election structure ======")
    print("e.cids (contest ids):")
    print("    ", end='')
    for cid in e.cids:
        print(cid, end=' ')
    print()
    print("e.pbcids (paper ballot collection ids aka jurisdictions):")
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
    print("e.vids (allowable vote ids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            print(vid, end=' ')
        print()

def check_election_data(e):

    assert isinstance(e.t, dict)
    for (cid, pbcid, vid) in e.t:
        assert cid in e.cids, cid
        assert pbcid in e.pbcids, pbcid
        assert vid in e.vids[cid], vid
        assert isinstance(e.t[(cid, pbcid, vid)], int), (cid, pbcid, vid, e.t[(cid, pbcid, vid)])

    assert isinstance(e.totcid, dict)
    for cid in e.totcid:
        assert cid in e.cids, cid
        assert isinstance(e.totcid[cid], int), (cid, e.totcid[cid])

    assert isinstance(e.totvot, dict)
    for (cid, vid) in e.totvot:
        assert cid in e.cids, cid
        assert vid in e.vids[cid], (cid, vid)
        assert isinstance(e.totvot[(cid, vid)], int)

    assert isinstance(e.av, dict)
    for (cid, pbcid) in e.av:
        assert cid in e.cids, cid
        assert pbcid in e.pbcids, pbcid
        assert isinstance(e.av[(cid, pbcid)], (list, tuple)), (cid, pbcid, e.av[(cid, pbcid)])
        for vid in e.av[(cid, pbcid)]:
            assert vid in e.vids[cid], vid

    assert isinstance(e.ro, dict)
    for cid in e.ro:
        assert cid in e.cids, cid
        assert e.ro[cid] in e.vids[cid], (cid, e.ro[cid])

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
    print("e.av (first five actual votes cast for each cid and pbcid):")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                print("    {}.{}:".format(cid, pbcid), e.av[(cid, pbcid)][:5])
    print("e.ro (reported outcome for each cid):")
    for cid in e.cids:
        print("    {}:{}".format(cid, e.ro[cid]))

def make_tally(vec):
    """
    Return dict giving tally of elements in iterable vec.
    """
    tally = dict()
    for x in vec:
        tally[x] = tally.get(x, 0) + 1
    return tally

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
                e.st[(cid, pbcid)] = make_tally(e.av[(cid, pbcid)][:e.s[pbcid]])
                
def print_sample(e):
    print("    Total sample counts by contest, paper ballot collection, and vote:")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                print("      {}.{}".format(cid, pbcid), end='')
                tally = e.st[(cid, pbcid)]
                for v in tally:
                    print("  {}:{}".format(v, tally[v]), end='')
                print("  total:{}".format(sum([tally[v] for v in tally])))

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

def measure_contest_risk(e, cid, st):
    """ 
    Return risk that reported outcome is wrong for cid.
    We take st here as argument rather than e.st so
    we can call measure contest risk with modified sample counts.
    """
    n_trials = 40000
    wrong_outcome_count = 0
    for trial in range(n_trials):
        test_tally = {vid:0 for vid in e.vids[cid]}
        for pbcid in e.pbcids:
            if e.rel[(cid, pbcid)]:
                # draw from posterior for each paper ballot collection, sum them
                tally = st[(cid, pbcid)]  # tally from actual sample
                for vid in tally:
                    test_tally[vid] += tally[vid]     
                    assert e.s[pbcid] > 0               # sample sizes should always be positive
                    test_tally[vid] += gamma.rvs(tally[vid]) * (e.n[pbcid] - e.s[pbcid]) / e.s[pbcid]
        if e.ro[cid] != plurality(test_tally):
            wrong_outcome_count += 1
    e.risk[cid] = wrong_outcome_count/n_trials

def measure_excess_risk(e, st):
    """ 
    Measure excess risk according to current sample. 
    Excess risk is sum of excess of risk over limits (when positive).
    We take st here as argument rather than e.st so
    we can call measure contest risk with modified sample counts.
    """
    print("    Risks per cid:")
    excess_risk = 0.0
    for cid in e.cids:
        measure_contest_risk(e, cid, st)
        print("      risk that reported outcome is wrong", cid, e.risk[cid], "(limit {})".format(e.risk_limit[cid]))
        excess_risk += max(0, e.risk[cid] - e.risk_limit[cid])
    print("    Excess risk: sum over cids of amt risk exceeds limit =", excess_risk)
    return excess_risk
                
def plan_sample(e):
    """ Return a sampling plan (dict of target sample sizes) """
    # for now, just simple strategy of looking at more ballots
    # only in those paper ballot collections that still have contests
    # that haven't finished yet.
    plan = e.s.copy()
    for pbcid in e.pbcids:
        for cid in e.cids:
            if e.rel[(cid, pbcid)] and e.risk[cid]>e.risk_limit[cid]:
                # if contest still active do as much as you can without
                # exceeding size of paper ballot collection
                plan[pbcid] = min(e.s[pbcid] + e.audit_rate[pbcid], e.n[pbcid])
                break
    return plan

def print_audit_summary(e):
    print("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        print("  {}:{}".format(pbcid, e.s[pbcid]))
    print("Total number of ballots sampled: ", end='')
    print(sum([e.s[pbcid] for pbcid in e.pbcids]))
    
def audit(e):
    print("====== Audit setup ======")
    print("e.risk_limit (risk limit per contest):")
    for cid in e.cids:
        print("    {}:{}".format(cid, e.risk_limit[cid]))
    print("e.audit_rate (max number of ballots audited/day):")
    for pbcid in e.pbcids:
        print("    {}:{}".format(pbcid, e.audit_rate[pbcid]))
    print("====== Audit ======")
    for pbcid in e.pbcids:                           
        e.s[pbcid] = 0
    last_s = e.s
    e.plan = {pbcid:min(e.n[pbcid], e.audit_rate[pbcid]) for pbcid in e.pbcids}
    for stage in range(1, 1000):
        print("audit stage", stage)
        print("    New target sample sizes by paper ballot collection:")
        for pbcid in e.pbcids:
            print("      {}: {} (+{})".format(pbcid, e.plan[pbcid], e.plan[pbcid]-last_s[pbcid]))
        draw_sample(e)
        print_sample(e)
        excess_risk = measure_excess_risk(e, e.st)
        if excess_risk == 0.0:
            print("============")
            print("Audit done (all risk limits reached)!")
            print_audit_summary(e)
            break
        e.plan = plan_sample(e)
        if 0 == max([e.plan[pbcid]-e.s[pbcid] for pbcid in e.pbcids]):
            print("============")
            print("Audit done (no more ballots to sample)!")
            print_audit_summary(e)
            break
        last_s = e.s
        
def main():
    e = setup()
    nmcb(e)
    finish_setup(e)
    check_election_structure(e)
    print_election_structure(e)
    check_election_data(e)
    print_election_data(e)
    audit(e)

main()    


