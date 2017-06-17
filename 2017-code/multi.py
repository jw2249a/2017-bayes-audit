# multi.py
# Ronald L. Rivest
# June 15, 2017
# python3

"""
Code for multiple contests & multiple paper ballot collections (jurisdictions)
"""

import random
random.seed(1)     # fix seed for reproducibility

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
    e.npbc = 0           # number of paper ballot collections ("jurisdictions"?)
    e.pbcids = []        # list of paper ballot collection ids
    e.nc = 0             # number of contests
    e.cids = []          # list of contest ids
    e.w = dict()         # dict mapping (cid, pbcid) pairs to True/False (relevance)
    e.vids = dict()      # dict mapping cid to list of allowable votes (vids)

    # reported election results
    e.n = dict()         # e.n[pbcid] number ballots cast in collection pbcid
    e.t = dict()         # dict mapping (cid, pbcid, vid) tuples to counts
    e.ro = dict()        # dict mapping cid to reported outcome

    # computed from the above 
    e.totcid = dict()    # dict mapping cid to total # votes cast in contest
    e.totvot = dict()    # dict mapping (cid, vid) pairs to number of votes recd

    e.av = dict()        # dict mapping (cid, pbcid) pairs to list of actual votes for that
                         # contest in that paper ballot collection

    # sample info
    e.s = dict()         # e.s[pbcid] number ballots sampled in paper ballot collection pbcid
    e.st = dict()        # dict mapping (cid, pbcid) pairs to tally dicts

    # audit
    e.risk = dict()       # mapping from cid to risk (that e.ro[cid] is wrong)
    e.risk_limit = dict() # mapping from cid to risk limit for that contest
    e.audit_rate = dict() # number of ballots that can be audited per day, by pbcid

    return e

def nmcb(e):
    """Fill in fields for Neal McBurnett example"""

    # three paper ballot collections, 100000 ballots each
    e.pbcids = ["PBC1", "PBC2", "PBC3"]
    for pbcid in e.pbcids:
        e.n[pbcid] = 100000
        e.s[pbcid] = 0

    # four contests
    e.nc = 4
    e.cids = ["I", "C1", "C2", "C3", "F23"]

    for cid in e.cids:
        for pbcid in e.pbcids:
            e.w[(cid, pbcid)] = False    # default
    e.w[("I", "PBC1")] = True            # I is in all counties
    e.w[("I", "PBC2")] = True          
    e.w[("I", "PBC3")] = True          
    e.w[("C1", "PBC1")] = True           # C1 is only in PBC1
    e.w[("C2", "PBC2")] = True           # C2 is only in PBC2
    e.w[("C3", "PBC3")] = True           # C3 is only in PBC3
    e.w[("F23", "PBC2")] = True          # F23 is in both PBC2 and PBC3
    e.w[("F23", "PBC3")] = True

    e.vids["I"] = [0, 1]                 # valid votes for each contest
    e.vids["C1"] = [0, 1]
    e.vids["C2"] = [0, 1]
    e.vids["C3"] = [0, 1]
    e.vids["F23"] = [0, 1]

    # e.t = vote totals for each cid pbcid vid combo
    for cid in e.cids:
        for pbcid in e.pbcids:
            for vid in e.vids[cid]:
                e.t[(cid, pbcid, vid)] = 0
    e.t[("I", "PBC1", 1)] = 50500           # I is in all counties (margin 1%)
    e.t[("I", "PBC1", 0)] = 49500
    e.t[("I", "PBC2", 1)] = 50500          
    e.t[("I", "PBC2", 0)] = 49500
    e.t[("I", "PBC3", 1)] = 50500          
    e.t[("I", "PBC3", 0)] = 49500
    e.t[("C1", "PBC1", 1)] = 65000          # C1 is only in PBC1 (margin 30%)
    e.t[("C1", "PBC1", 0)] = 35000
    e.t[("C2", "PBC2", 1)] = 60000          # C2 is only in PBC2 (margin 20%)
    e.t[("C2", "PBC2", 0)] = 40000
    e.t[("C3", "PBC3", 1)] = 55000          # C3 is only in PBC3 (margin 10%)
    e.t[("C3", "PBC3", 0)] = 45000
    e.t[("F23", "PBC2", 1)] = 52500         # F23 is in both PBC2 and PBC3 (margin 5%)
    e.t[("F23", "PBC2", 0)] = 47500
    e.t[("F23", "PBC3", 1)] = 52500
    e.t[("F23", "PBC3", 0)] = 47500
    
    # e.ro = reported outcomes for each cid
    e.ro["I"] = 1                         
    e.ro["C1"] = 1
    e.ro["C2"] = 1
    e.ro["C3"] = 1
    e.ro["F23"] = 1

    # audit parameters
    e.risk_limit["I"] = 0.05               # risk limit by contest
    e.risk_limit["C1"] = 0.05
    e.risk_limit["C2"] = 0.05
    e.risk_limit["C3"] = 0.05
    e.risk_limit["F23"] = 0.10  

    e.audit_rate["PBC1"] = 40              # max rate for auditing ballots by pbcid
    e.audit_rate["PBC2"] = 60 
    e.audit_rate["PBC3"] = 80

    return e

def finish_setup(e):
    """ Compute attributes of e that are derivative from others. """
    # e.totcid[cid] is total number of votes cast for cid
    for cid in e.cids:
        e.totcid[cid] = sum([e.n[pbcid] for pbcid in e.pbcids if e.w[(cid, pbcid)]])

    # e.totvid[(cid, vid)] is total number cast for vid in cid
    for cid in e.cids:
        for vid in e.vids[cid]:
            e.totvot[(cid, vid)] = sum([e.t[(cid, pbcid, vid)] for pbcid in e.pbcids])

    # make up votes and randomly permute their order
    for cid in e.cids:
        votes = [0]*e.totvot[(cid, 0)] + [1]*e.totvot[(cid,1)]
        random.shuffle(votes)
        i = 0
        for pbcid in e.pbcids:
            e.av[(cid, pbcid)] = []
            if e.w[(cid, pbcid)]:
                e.av[(cid, pbcid)] = votes[i:i+e.n[pbcid]]
                i = i + e.n[pbcid]

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
    print("e.w (valid pbcids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for pbcid in e.pbcids:
            if e.w[(cid, pbcid)]:
                print(pbcid, end=' ')
        print()
    print("e.vids (allowable vote ids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            print(vid, end=' ')
        print()

def print_reported_results(e):
    print("====== Reported election results ======")
    print("e.t (total votes for each vid by cid and pbcid):")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.w[(cid, pbcid)]:
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
            if e.w[(cid, pbcid)]:
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
    "Draw sample", tally it, print out tally, save it in e.st[(cid, pbcid)].

    Draw sample is in quotes since it just looks at the first
    e.s[pbcid] elements of e.av[(cid, pbcid)].
    """
    print("    Total sample counts by contest, paper ballot collection, and vote:")
    for cid in e.cids:
        for pbcid in e.pbcids:
            if e.w[(cid, pbcid)]:
                tally = make_tally(e.av[(cid, pbcid)][:e.s[pbcid]])
                e.st[(cid, pbcid)] = tally
                print("      {}.{}".format(cid, pbcid), end='')
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
        test_tally = { vid:0 for vid in e.vids[cid] }
        for pbcid in e.pbcids:
            if e.w[(cid, pbcid)]:
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
    """ Return a new value for e.s (new sample sizes) """
    # for now, just simple strategy of looking at more ballots
    # only in those paper ballot collections that still have contests
    # that haven't finished yet.
    s = e.s.copy()
    for pbcid in e.pbcids:
        for cid in e.cids:
            if e.w[(cid, pbcid)] and e.risk[cid]>e.risk_limit[cid]:
                s[pbcid] = min(e.s[pbcid] + e.audit_rate[pbcid], e.n[pbcid])
                break
    return s

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
    for pbcid in e.pbcids:
        e.s[pbcid] = e.audit_rate[pbcid]
    print("====== Audit ======")
    last_s = {pbcid: 0 for pbcid in e.pbcids}
    for stage in range(1, 1000):
        print("audit stage", stage)
        print("    New sample sizes by paper ballot collection:")
        for pbcid in e.pbcids:
            print("      {}: {} (+{})".format(pbcid, e.s[pbcid], e.s[pbcid]-last_s[pbcid]))
        draw_sample(e)
        excess_risk = measure_excess_risk(e, e.st)
        if excess_risk == 0.0:
            print("============")
            print("Audit done (all risk limits reached)!")
            print_audit_summary(e)
            break
        s = plan_sample(e)
        if 0 == max([s[pbcid]-e.s[pbcid] for pbcid in e.pbcids]):
            print("============")
            print("Audit done (no more ballots to sample)!")
            print_audit_summary(e)
            break
        last_s = e.s
        e.s = s
        
def main():
    e = setup()
    nmcb(e)
    finish_setup(e)
    print_election_structure(e)
    print_reported_results(e)
    audit(e)

main()    


