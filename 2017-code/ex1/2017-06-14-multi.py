# multi.py
# Ronald L. Rivest
# June 10, 2017
# python3

"""
Code for multiple contests & multiple jurisdictions.
"""

import random
random.seed(1)     # for reproducibility

##############################################################################
## Gamma distribution
##############################################################################
# https://docs.scipy.org/doc/scipy-0.19.0/reference/generated/scipy.stats.gamma.html

from scipy.stats import gamma

# Generate random variate with mean k
# gamma.rvs(k)

##############################################################################
## Elections
##############################################################################

class Election(object):
    """ so we can hang attributes off of an election """
    pass

def setup():
    e = Election()
    # to be input by user
    e.nj = 0             # number of jurisdictions
    e.jids = []          # list of jurisdiction ids
    e.n = dict()         # e.n[jid] number ballots cast in jurisdiction jid
    e.nc = 0             # number of contests
    e.cids = []          # list of contest ids
    e.w = dict()         # dict mapping (cid, jid) pairs to True/False (relevance)
    e.vids = dict()      # dict mapping cid to list of allowable votes (vids)
    e.t = dict()         # dict mapping (cid, jid, vid) tuples to counts
    e.ro = dict()        # dict mapping cid to reported outcome

    # computed from the above 
    e.totcid = dict()    # dict mapping cid to total # votes cast in contest
    e.totvot = dict()    # dict mapping (cid, vid) pairs to number of votes recd
    e.av = dict()        # dict mapping (cid, jid) pairs to list of actual votes for that
                         # contest in that jurisdiction
    # sample info
    e.s = dict()         # e.s[jid] number ballots sampled in jurisdiction jid
    e.st = dict()        # dict mapping (cid, jid) pairs to tally dicts

    # audit
    e.risk = dict()       # mapping from cid to risk (that e.ro[cid] is wrong)
    e.risk_limit = dict() # mapping from cid to risk limit for that contest
    e.audit_rate = dict() # number of ballots that can be audited per day, by jid

    return e

def nmcb(e):
    """Fill in fields for Neal McBurnett example"""

    # three jurisdictions, 100000 ballots each
    e.jids = ["J1", "J2", "J3"]
    for jid in e.jids:
        e.n[jid] = 100000
        e.s[jid] = 0

    # four contests
    e.nc = 4
    e.cids = ["I", "C1", "C2", "C3", "F23"]

    for cid in e.cids:
        for jid in e.jids:
            e.w[(cid, jid)] = False    # default
    e.w[("I", "J1")] = True            # I is in all counties
    e.w[("I", "J2")] = True          
    e.w[("I", "J3")] = True          
    e.w[("C1", "J1")] = True           # C1 is only in J1
    e.w[("C2", "J2")] = True           # C2 is only in J2
    e.w[("C3", "J3")] = True           # C3 is only in J3
    e.w[("F23", "J2")] = True          # F23 is in both J2 and J3
    e.w[("F23", "J3")] = True

    e.vids["I"] = [0, 1]
    e.vids["C1"] = [0, 1]
    e.vids["C2"] = [0, 1]
    e.vids["C3"] = [0, 1]
    e.vids["F23"] = [0, 1]

    # e.t = vote totals for each cid jid vid combo
    for cid in e.cids:
        for jid in e.jids:
            for vid in e.vids[cid]:
                e.t[(cid, jid, vid)] = 0
    e.t[("I", "J1", 1)] = 50500           # I is in all counties
    e.t[("I", "J1", 0)] = 49500
    e.t[("I", "J2", 1)] = 50500          
    e.t[("I", "J2", 0)] = 49500
    e.t[("I", "J3", 1)] = 50500          
    e.t[("I", "J3", 0)] = 49500
    e.t[("C1", "J1", 1)] = 65000          # C1 is only in J1
    e.t[("C1", "J1", 0)] = 35000
    e.t[("C2", "J2", 1)] = 60000          # C2 is only in J2
    e.t[("C2", "J2", 0)] = 40000
    e.t[("C3", "J3", 1)] = 55000          # C3 is only in J3
    e.t[("C3", "J3", 0)] = 45000
    e.t[("F23", "J2", 1)] = 52500         # F23 is in both J2 and J3
    e.t[("F23", "J2", 0)] = 47500
    e.t[("F23", "J3", 1)] = 52500
    e.t[("F23", "J3", 0)] = 47500
    
    # e.ro = reported outcomes for each cid
    e.ro["I"] = 1                         
    e.ro["C1"] = 1
    e.ro["C2"] = 1
    e.ro["C3"] = 1
    e.ro["F23"] = 1

    e.risk_limit["I"] = 0.05               # risk limit by contest
    e.risk_limit["C1"] = 0.05
    e.risk_limit["C2"] = 0.05
    e.risk_limit["C3"] = 0.05
    e.risk_limit["F23"] = 0.10  

    e.audit_rate["J1"] = 40                 # max rate for auditing ballots
    e.audit_rate["J2"] = 60                 # by jid
    e.audit_rate["J3"] = 80

    return e

def finish_setup(e):
    """ Compute attributes of e that are derivative from others. """
    # e.totcid[cid] is total number of votes cast for cid
    for cid in e.cids:
        e.totcid[cid] = sum([e.n[jid] for jid in e.jids if e.w[(cid, jid)]])

    # e.totvid[(cid, vid)] is total number cast for vid in cid
    for cid in e.cids:
        for vid in e.vids[cid]:
            e.totvot[(cid, vid)] = sum([e.t[(cid, jid, vid)] for jid in e.jids])

    # make up votes and randomly permute their order
    for cid in e.cids:
        votes = [0]*e.totvot[(cid, 0)] + [1]*e.totvot[(cid,1)]
        random.shuffle(votes)
        i = 0
        for jid in e.jids:
            e.av[(cid, jid)] = []
            if e.w[(cid, jid)]:
                e.av[(cid, jid)] = votes[i:i+e.n[jid]]
                i = i + e.n[jid]

def print_election_structure(e):
    print("====== Election structure ======")
    print("e.cids (contest ids):")
    print("    ", end='')
    for cid in e.cids:
        print(cid, end=' ')
    print()
    print("e.jids (jurisdiction ids) (aka paper ballot collection ids):")
    print("    ", end='')
    for jid in e.jids:
        print(jid, end=' ')
    print()
    print("e.w (valid jids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for jid in e.jids:
            if e.w[(cid, jid)]:
                print(jid, end=' ')
        print()
    print("e.vids (allowable vote ids for each cid):")
    for cid in e.cids:
        print("    {}: ".format(cid), end='')
        for vid in e.vids[cid]:
            print(vid, end=' ')
        print()

def print_reported_results(e):
    print("====== Reported election results ======")
    print("e.t (total votes for each vid by cid and jid):")
    for cid in e.cids:
        for jid in e.jids:
            if e.w[(cid, jid)]:
                print("    {}.{}: ".format(cid, jid), end='')
                for vid in e.vids[cid]:
                    print("{}:{} ".format(vid, e.t[(cid, jid, vid)]), end='')
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
    print("e.av (first five actual votes cast for each cid and jid):")
    for cid in e.cids:
        for jid in e.jids:
            if e.w[(cid, jid)]:
                print("    {}.{}:".format(cid, jid), e.av[(cid, jid)][:5])
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
    "Draw sample", tally it, print out tally, save it in e.st[(cid, jid)].

    Draw sample is in quotes since it just looks at the first
    e.s[jid] elements of e.av[(cid, jid)].
    """
    print("    Total sample counts by contest, jurisdiction, and vote:")
    for cid in e.cids:
        for jid in e.jids:
            if e.w[(cid, jid)]:
                tally = make_tally(e.av[(cid, jid)][:e.s[jid]])
                e.st[(cid, jid)] = tally
                print("      {}.{}".format(cid, jid), end='')
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
        for jid in e.jids:
            if e.w[(cid, jid)]:
                # draw from posterior for each jurisdiction, sum them
                tally = st[(cid, jid)]  # tally from actual sample
                for vid in tally:
                    test_tally[vid] += tally[vid]
                    assert e.s[jid] > 0               # sample sizes should always be positive
                    test_tally[vid] += gamma.rvs(tally[vid]) * (e.n[jid] - e.s[jid]) / e.s[jid]
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
    # only in those jurisdictions that still have contests
    # that haven't finished yet.
    s = e.s.copy()
    for jid in e.jids:
        for cid in e.cids:
            if e.w[(cid, jid)] and e.risk[cid]>e.risk_limit[cid]:
                s[jid] = min(e.s[jid] + e.audit_rate[jid], e.n[jid])
                break
    return s

def print_audit_summary(e):
    print("Number of ballots sampled, by jurisdiction:")
    for jid in e.jids:
        print("  {}:{}".format(jid, e.s[jid]))
    print("Total number of ballots sampled: ", end='')
    print(sum([e.s[jid] for jid in e.jids]))
    
def audit(e):
    print("====== Audit setup ======")
    print("e.risk_limit (risk limit per contest):")
    for cid in e.cids:
        print("    {}:{}".format(cid, e.risk_limit[cid]))
    print("e.audit_rate (max number of ballots audited/day):")
    for jid in e.jids:
        print("    {}:{}".format(jid, e.audit_rate[jid]))
    for jid in e.jids:
        e.s[jid] = e.audit_rate[jid]
    print("====== Audit ======")
    last_s = {jid: 0 for jid in e.jids}
    for stage in range(1, 1000):
        print("audit stage", stage)
        print("    New sample sizes by jurisdiction:")
        for jid in e.jids:
            print("      {}: {} (+{})".format(jid, e.s[jid], e.s[jid]-last_s[jid]))
        draw_sample(e)
        excess_risk = measure_excess_risk(e, e.st)
        if excess_risk == 0.0:
            print("============")
            print("Audit done (all risk limits reached)!")
            print_audit_summary(e)
            break
        s = plan_sample(e)
        if 0 == max([s[jid]-e.s[jid] for jid in e.jids]):
            print("============")
            print("Audit done (no more ballots to sample)!")
            print_audit_summary(e)
            break
        last_s = e.s
        e.s = s
        
e = setup()
nmcb(e)
finish_setup(e)
print_election_structure(e)
print_reported_results(e)
audit(e)


