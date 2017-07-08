# planner.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 8, 2017
# python3

"""
Routines to work with multi.py on post-election audits.
Specifically, to produce an "audit plan" for the next stage,
given what has been done already, and the results obtained
from the previous stage.
"""


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


