# co14noncvr
# Ronald L. Rivest, Neal McBurnett

"""
Test election for testing Bayesian post-election audit code (multi.py)
"""

def election_structure(e):

    e.election_type = "Synthetic"

    e.cids = ["STRAT"]

    # three paper ballot collections
    e.pbcids = ["CCVR", "CNONCVR"]

    e.collection_type["CCVR"] = "CVR"
    e.collection_type["CNONCVR"] = "noCVR"

    # Structure
    for cid in e.cids:
        for pbcid in e.pbcids:
            e.rel[(cid, pbcid)] = False    # default
    e.rel[("STRAT", "CCVR")] = True
    e.rel[("STRAT", "CNONCVR")] = True          

    e.vvids["STRAT"] = ["0", "1"]              # valid votes for each contest

    for cid in e.cids:                     # invalid votes for each contest
        e.ivids[cid] = ["Invalid"]
    for cid in e.cids:
        if any([e.collection_type[pbcid]=="noCVR" \
                for pbcid in e.pbcids
                if e.rel[(cid, pbcid)]]):
            e.ivids[cid].append("noCVR")

NONCVR_P = .14
CVR_P = 1 - NONCVR_P

def election_data(e):
    """
    A stratified election with 100000 ballots, where 1 is the winner, with a margin of 2%,
    and 10% are Invalid (undervote/overvote/residual).
    14% noCVR
    """

    e.n["CCVR"] = int(10000 * CVR_P)
    e.n["CNONCVR"] = int(10000 * NONCVR_P)

    # e.t = vote totals for each cid pbcid vid combo
    for cid in e.cids:
        for pbcid in e.pbcids:
            for vid in e.vids[cid]:
                e.t[(cid, pbcid, vid)] = 0
    e.t[("STRAT", "CCVR", "1")] = int(46000 * .1 * CVR_P)
    e.t[("STRAT", "CNONCVR", "1")] = int(46000 * .1 * NONCVR_P)
    e.t[("STRAT", "CCVR", "Invalid")] = int(10000 * .1 * CVR_P)
    e.t[("STRAT", "CCVR", "0")] = int(44000 * .1 * CVR_P)
    e.t[("STRAT", "CNONCVR", "0")] = int(44000 * .1 * NONCVR_P)
    e.t[("STRAT", "CNONCVR", "Invalid")] = int(10000 * .1 * NONCVR_P)
    
    # e.ro = reported outcomes for each cid (all correct here)
    e.ro["STRAT"] = "1"                         

def audit_parameters(e):

    e.risk_limit["STRAT"] = 0.05               # risk limit by contest
    e.audit_rate["CCVR"] = 50    # max rate/stage for auditing ballots by pbcid
    e.audit_rate["CNONCVR"] = 25 

    # Each contest status should be "Auditing" or "Just Watching"
    e.contest_status["STRAT"] = "Auditing"
