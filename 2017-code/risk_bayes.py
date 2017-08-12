# risk_bayes.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# August 11, 2017
# python3

"""
Routines to compute Bayes risk for a contest, or for a set of contests.

Called by audit.py
"""

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

def compute_risk(e, mid, st):
    """ 
    Compute Bayesian risk (chance that reported outcome is wrong 
    for contest e.cid_m[mid]).
    We take st here as argument rather than e.sn_tcpra so
    we can call compute_contest_risk with modified sample counts.
    (This option not yet used, but might be later, when optimizing
    workload.)

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
            for rv in sorted(e.sn_tcpra[e.stage_time][cid][pbcid]):
                tally = e.sn_tcpra[e.stage_time][cid][pbcid][rv].copy()
                for av in e.votes_c[cid]:
                    if av not in tally:
                        tally[av] = 0
                    tally[av] += (e.pseudocount_match if av==rv
                                  else e.pseudocount_base)
                dirichlet_dict = dirichlet(tally)
                nonsample_size = e.rn_cpr[cid][pbcid][rv] - \
                                 e.sn_tcpr[e.stage_time][cid][pbcid][rv]
                for av in sorted(tally):
                    test_tally[av] += tally[av]
                    if e.sn_tcpr[e.stage_time][cid][pbcid][rv] > 0:
                        test_tally[av] += dirichlet_dict[av] * nonsample_size
        if e.ro_c[cid] != outcomes.compute_outcome(e, cid, test_tally):  
            wrong_outcome_count += 1
    risk = wrong_outcome_count / e.n_trials
    e.risk_tm[e.stage_time][mid] = risk
    return risk


def compute_risks(e, st):

    for mid in e.mids:
        compute_risk(e, mid, st)


if __name__ == "__main__":

    pass


