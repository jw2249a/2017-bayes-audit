# audit.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 8, 2017
# python3

"""
Routines to work with multi.py on post-election audits.
"""


import numpy as np

import utils

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

    utils.myprint("    Total sample counts by Contest.PaperBallotCollection[reported selection]"
            "and actual selection:")
    for cid in e.cids:
        for pbcid in sorted(e.rel_cp[cid]):
            tally2 = e.sn_tcpra[e.stage][cid][pbcid]
            for r in sorted(tally2.keys()):  # r = reported vote
                utils.myprint("      {}.{}[{}]".format(cid, pbcid, r), end='')
                for a in sorted(tally2[r].keys()):
                    utils.myprint("  {}:{}".format(a, tally2[r][a]), end='')
                utils.myprint("  total:{}".format(e.sn_tcpr[e.stage][cid][pbcid][r]))


##############################################################################
# Risk measurement

def compute_risk(e, mid, st):
    """ 
    Compute Bayesian risk (chance that reported outcome is wrong 
    for e.cid_m[mid]).
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

    cid = e.cid_m[mid]
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
                    if r!=a:
                        tally[a] += e.pseudocount_base
                    else:
                        tally[a] += e.pseudocount_match
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
    e.risk_tm[e.stage][mid] = wrong_outcome_count / e.n_trials


def compute_risks(e, st):

    for mid in e.mids:
        compute_risk(e, mid, st)


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

    utils.myprint("    Risk (that reported outcome is wrong) and contest status per cid:")
    for cid in e.cids:
        utils.myprint("     ", cid, e.risk_tc[e.stage][cid],
                "(limit {})".format(e.risk_limit_c[cid]),
                e.contest_status_tc[e.stage][cid])
    utils.myprint("    Election status:", e.election_status_t[e.stage])


##############################################################################
# Audit parameters


def set_audit_seed(e, new_audit_seed):
    """ 
    Set e.audit_seed to new value (but only if not already set). 

    The idea is that the command line may set the audit seed to a non-None
    value first, in which case it is "sticky" and thus overrides any 
    setting that might be in the audit seed file.

    This routine also sets the global auditRandomState.
    """

    global auditRandomState

    e.audit_seed = new_audit_seed
    # audit_seed might be None if no command-line argument given

    auditRandomState = utils.RandomState(e.audit_seed)
    # if seed is None (which happens if no command line value is given),
    # utils.RandomState uses clock or other variable process-state
    # parameters (via np.random.RandomState)


def get_audit_parameters(e, args):

    # this should NOT overwrite e.audit_seed if it was non-None
    # because it was already set from the command line

    # now obsolete:
    # load_part_from_json(e, "audit_parameters.js")

    check_audit_parameters(e)


def check_audit_parameters(e):

    if not isinstance(e.risk_limit_c, dict):
        utils.myerror("e.risk_limit_c is not a dict.")
    for cid in e.risk_limit_c:
        if cid not in e.cids:
            utils.mywarning("e.risk_limit_c cid key `{}` is not in e.cids."
                      .format(cid))
        if not (0.0 <= e.risk_limit_c[cid] <= 1.0):
            utils.mywarning("e.risk_limit_c[{}] not in interval [0,1]".format(cid))

    if not isinstance(e.audit_rate_p, dict):
        utils.myerror("e.audit_rate_p is not a dict.")
    for pbcid in e.audit_rate_p:
        if pbcid not in e.pbcids:
            utils.mywarning("pbcid `{}` is a key for e.audit_rate_p but not in e.pbcids."
                      .format(pbcid))
        if not 0 <= e.audit_rate_p[pbcid]:
            utils.mywarning("e.audit_rate_p[{}] must be nonnegative.".format(pbcid))

    if not isinstance(e.contest_status_tc, dict):
        utils.myerror("e.contest_status_tc is not a dict.")
    if "0" not in e.contest_status_tc:
        utils.myerror("e.contest_status_tc must have `0` as a key.")
    for cid in e.contest_status_tc["0"]:
        if cid not in e.cids:
            utils.mywarning("cid `{}` is key in e.contest_status_tc but not in e.cids"
                      .format(cid))
        if e.contest_status_tc["0"][cid] not in ["Auditing", "Just Watching"]:
            utils.mywarning("e.contest_status_tc['0'][{}] must be `Auditing` or `Just Watching`."
                      .format(cid))

    if utils.warnings_given > 0:
        utils.myerror("Too many errors; terminating.")


def show_audit_parameters(e):

    utils.myprint("====== Audit parameters ======")

    utils.myprint("Seed for audit pseudorandom number generation (e.audit_seed):")
    utils.myprint("    {}".format(e.audit_seed))

    utils.myprint("Risk Measurement ids (e.mids) with contest, method, risk limit, and risk upset threshold:")
    for mid in e.mids:
        utils.myprint("    {}: ({}, {}, {}, {})"
                      .format(e.cid_m[mid], e.risk_method_m[mid], e.risk_limit_m[mid],
                              e.risk_upset_m[mid], e.sampling_mode_m[mid]))

    utils.myprint("e.audit_rate_p (max number of ballots audited/day per pbcid):")
    for pbcid in sorted(e.pbcids):
        utils.myprint("    {}:{}".format(pbcid, e.audit_rate_p[pbcid]))

    utils.myprint("e.max_stages (max number of audit stages allowed):")
    utils.myprint("    {}".format(e.max_stages))

    utils.myprint("e.n_trials (number of trials used to estimate risk "
            "in compute_contest_risk):")
    utils.myprint("    {}".format(e.n_trials))

    utils.myprint("Dirichlet hyperparameter for base case or non-matching reported/actual votes")
    utils.myprint("(e.pseudocount_base):")
    utils.myprint("    {}".format(e.pseudocount_base))
    utils.myprint("Dirichlet hyperparameter for matching reported/actual votes")
    utils.myprint("(e.pseudocount_match):")
    utils.myprint("    {}".format(e.pseudocount_match))


def initialize_audit(e):

    e.sn_tp["0"] = {}
    for pbcid in e.pbcids:
        e.sn_tp["0"][pbcid] = 0
    # Initial plan size is just audit rate, for each pbcid.
    e.plan_tp["0"] = {pbcid: min(
        e.rn_p[pbcid], e.audit_rate_p[pbcid]) for pbcid in e.pbcids}


def show_audit_stage_header(e):

    utils.myprint("audit stage", e.stage)
    utils.myprint("    New target sample sizes by paper ballot collection:")
    for pbcid in e.pbcids:
        last_s = e.sn_tp[e.last_stage]
        utils.myprint("      {}: {} (+{})"
                .format(pbcid,
                        e.plan_tp[e.last_stage][pbcid],
                        e.plan_tp[e.last_stage][pbcid] - last_s[pbcid]))


def audit_stage(e, stage):

    e.last_stage = "{}".format(stage - 1)   # json keys must be strings
    e.stage = "{}".format(stage)
    e.risk_tm[e.stage] = {}
    e.status_tm[e.stage] = {}
    e.sn_tp[e.stage] = {}
    e.sn_tcpra[e.stage] = {}

    draw_sample(e)
    compute_risks(e, e.sn_tcpra)
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

    utils.myprint("====== Audit ======")

    for stage in range(1, e.max_stages + 1):
        audit_stage(e, stage)
        if stop_audit(e):
            break
        compute_plan(e)
    show_audit_summary(e)


def show_audit_summary(e):

    utils.myprint("=============")
    utils.myprint("Audit completed!")

    utils.myprint("All contests have a status in the following list:",
            e.election_status_t[e.stage])
    if "Auditing" not in e.election_status_t[e.stage]:
        utils.myprint("No contest still has `Auditing' status.")
    if "Full Recount Needed" in e.election_status_t[e.stage]:
        utils.myprint("At least one contest needs a full recount.")
    if int(e.stage) == e.max_stages:
        utils.myprint("Maximum number of audit stages ({}) reached."
                .format(e.max_stages))

    utils.myprint("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        utils.myprint("  {}:{}".format(pbcid, e.sn_tp[e.stage][pbcid]))
    utils.myprint_switches = ["std"]
    utils.myprint("Total number of ballots sampled: ", end='')
    utils.myprint(sum([e.sn_tp[e.stage][pbcid] for pbcid in e.pbcids]))


