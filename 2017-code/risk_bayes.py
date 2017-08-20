# risk_bayes.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# August 11, 2017
# python3

"""
Routines to compute Bayes risk for a contest, or for a set of contests.

Called by audit.py

This is designed to be compatible only with sampling by pbcid;
more elaborate sampling regimes, such as sampling by card number
or by reported vote, are yet to be implemented, and may require
a significant change to the code base.  (Some thoughts, albeit
primitive, are sketched in risk_bayes_2.py.)
"""

import copy
import numpy as np

import multi
import audit
import outcomes

##############################################################################
# Gamma distribution
# https://docs.scipy.org/doc/numpy-1.11.0/reference/generated/numpy.random.gamma.html
# from numpy.random import gamma
# To generate random gamma variate with mean k:
# gamma(k)  or rs.gamma(k) where rs is a numpy.random.RandomState object


def gamma(k, rs=None):
    """ 
    Return sample from gamma distribution with mean k.
    Differs from standard one that it allows k==0, which returns 0.
    Parameter rs, if present, is a numpy.random.RandomState object.
    """
    if rs == None:
        rs = audit.auditRandomState
    if k <= 0.0:
        ans = 0.0
    else:
        ans = rs.gamma(k)
    return ans


# Dirichlet distribution

def dirichlet(tally):
    """ 
    Given tally dict mapping votes (tuples of selids) to nonnegative ints (counts), 
    return dict mapping those votes to elements of Dirichlet distribution sample on
    those votes, where tally values are used as Dirichlet hyperparameters.
    The values produced sum to one.
    """

    # make sure order of applying gamma is deterministic, for reproducibility
    dir = {vote: gamma(tally[vote]) for vote in sorted(tally)}
    total = sum(dir.values())
    dir = {vote: dir[vote] / total for vote in dir}
    return dir


##############################################################################
# Risk measurement (Bayes risk)

def compute_risk(e, mid, sn_tcpra):
    """ 
    Compute Bayesian risk (chance that reported outcome is wrong 
    for contest e.cid_m[mid]).
    We take sn_tcpra here as argument rather than just use e.sn_tcpra so
    we can call compute_contest_risk with modified sample counts.
    (This option not yet used, but might be later, when optimizing
    workload.)
    Here sn_tcpra is identical in structure to (and may in fact be
    identical to) e.sn_tcpra.

    This method is the heart of the Bayesian post-election audit method.
    But it could be replaced by a frequentist approach instead, at
    least for those outcome rules and mixes of collection types for
    which a frequentist method is known.

    The comparison and ballot-polling audits are blended here; the
    reported election data just records a ("-noCVR",) vote for the 
    reported vote in a noCVR paper ballot collection.
    """

    cid = e.cid_m[mid]
    wrong_outcome_count = 0
    for trial in range(e.n_trials):
        test_tally = {vote: 0 for vote in e.votes_c[cid]}
        for pbcid in sorted(e.possible_pbcid_c[cid]):
            # Draw from posterior for each paper ballot collection, sum them.
            # Stratify by reported vote.
            for rv in sorted(sn_tcpra[e.stage_time][cid][pbcid]):
                tally = sn_tcpra[e.stage_time][cid][pbcid][rv].copy()
                for av in e.votes_c[cid]:
                    if av not in tally:
                        tally[av] = 0
                    tally[av] += (e.pseudocount_match if av==rv
                                  else e.pseudocount_base)
                dirichlet_dict = dirichlet(tally)
                stratum_size = e.rn_cpr[cid][pbcid][rv]
                # sample_size = sn_tcpr[e.stage_time][cid][pbcid][rv]  
                sample_size = sum([sn_tcpra[e.stage_time][cid][pbcid][rv][av]
                                   for av in sn_tcpra[e.stage_time][cid][pbcid][rv]])
                nonsample_size = stratum_size - sample_size
                for av in sorted(tally):
                    test_tally[av] += tally[av]
                    test_tally[av] += dirichlet_dict[av] * nonsample_size
        if e.ro_c[cid] != outcomes.compute_outcome(e, cid, test_tally):  
            wrong_outcome_count += 1
    risk = wrong_outcome_count / e.n_trials
    e.risk_tm[e.stage_time][mid] = risk
    return risk


def compute_risks(e, st):

    for mid in e.mids:
        compute_risk(e, mid, st)


def compute_slack_p(e):
    """
    Return dictionary showing amount by which sample in each
    pbcid can be increased.
    """

    mid = e.mids[0]         # sampling is same so far for all mids
    cid = e.cid_m[mid]
    slack_p = {}
    for pbcid in e.pbcids:
        slack_p[pbcid] = 0
        for rv in e.rn_cpr[cid][pbcid]:
            slack_p[pbcid] += e.rn_cpr[cid][pbcid][rv]
            slack_p[pbcid] -= e.sn_tcpr[e.stage_time][cid][pbcid][rv]
    return slack_p

def compute_risk_with_tweak(e, mid, slack_p, tweak):
    """
    Return computed risk if sample sizes were tweaked.

    Here tweak is a dict mapping pbcids to how much
    to increase sample size by in each pbcid.  We must have
        slack[pbcid] >= tweak[pbcid] >= 0
    for all pbcids.
    """

    cid = e.cid_m[mid]
    sn_tcpra = copy.deepcopy(e.sn_tcpra)
    sn_tcp = {}
    sn_tcp[e.stage_time] = {}
    sn_tcp[e.stage_time][cid] = {}
    for pbcid in e.pbcids:
        assert slack[pbcid] >= tweak[pbcid] >= 0
        sn_tcp[e.stage_time][cid][pbcid] = 0
        sn_tcpra = copy.deepcopy(e.sn_tcpra)
    return compute_risk(e, mid, sn_tcpra)

def tweak_all(e, mid):
    """
    Test routine to try all tweaks.
    """

    return

    # FIXME in below sn_tcp is not defined.
    risk = compute_risk(e, mid, e.sn_tcpra)
    print("Risk (no change):", risk)
    slack_p = compute_slack_p(e)
    cid = e.cid_m[mid]
    for pbcid in e.pbcids:
        for rv in e.sn_tcpra[e.stage_time][cid][pbcid]:
            for av in e.sn_tcpra[e.stage_time][cid][pbcid][rv]:
                if sn_tcp[e.stage_time][cid][pbcid] > 0:
                    sn_tcpra[e.stage_time][cid][pbcid][rv][av] += \
                        min(100,                                                               
                            slack_p[pbcid] *\
                            sn_tcpra[e.stage_time][cid][pbcid][rv][av] / \
                            sn_tcp[e.stage_time][cid][pbcid])
        risk = compute_risk_with_tweak(e, mid, slack_p, tweak)
        print("Risk (change {}):".format(pbcid),
              risk)
                                                                                    

if __name__ == "__main__":

    pass


