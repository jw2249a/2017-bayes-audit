# audit.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 18, 2017
# python3

"""
Routines to work with multi.py on post-election audits.
"""


import numpy as np
import os

import multi
import csv_readers
import outcomes
import utils


##############################################################################
# Random number generation
##############################################################################

# see numpy.random.RandomState documentation and utils.RandomState
# Random states used in this program:
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
        for pbcid in e.possible_pbcid_c[cid]:
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
        for pbcid in sorted(e.possible_pbcid_c[cid]):
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
        for pbcid in e.possible_pbcid_c[cid]:
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


def compute_measurement_and_election_statuses(e):
    """ 
    Compute status of each measurement and of election, from 
    already-computed measurement risks.
    """

    for mid in e.mids:
        # Measurement transition from Open to any of Exhausted, Passed, or Upset,
        # but not vice versa.
        e.status_tm[e.stage][mid] = e.status_tm[e.last_stage][mid]
        if e.status_tm[e.stage][mid] == "Open":
            if all([e.rn_p[pbcid] == e.sn_tp[e.stage][pbcid]
                    for pbcid in e.possible_pbcid_c[cid]]):
                e.status_tm[e.stage][mid] = "Exhausted"
            elif e.risk_tm[e.stage][mid] < e.risk_limit_m[mid]:
                e.status_tm[e.stage][mid] = "Passed"
            elif e.risk_tm[e.stage][mid] > e.risk_upset_m[mid]:
                e.status_tm[e.stage][mid] = "Upset"

    e.election_status_t[e.stage] = \
        sorted(list(set([e.status_tm[e.stage][mid]
                         for mid in e.mids])))


def show_risks_and_statuses(e):
    """ 
    Show election and contest statuses for current stage. 
    """

    utils.myprint("    Risk (that reported outcome is wrong) and measurement status per mid:")
    for mid in e.mids:
        utils.myprint("     ",
                      mid,
                      e.cid_m[mid],
                      e.risk_method_m[mid],
                      e.sampling_mode_m[mid],
                      e.risk_tm[e.stage][mid],
                      "(limits {},{})".format(e.risk_limit_m[mid], e.risk_upset_m[mid]),
                      e.status_tm[e.stage][mid])
    utils.myprint("    Election status:", e.election_status_t[e.stage])


##############################################################################
# Audit spec


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


def read_audit_spec(e, args):


    read_audit_spec_global(e, args)
    read_audit_spec_seed(e, args)
    read_audit_spec_contest(e, args)
    read_audit_spec_collection(e, args)

    check_audit_spec(e)


def read_audit_spec_global(e, args):

    pass


def read_audit_spec_contest(e, args):

    election_pathname = os.path.join(multi.ELECTIONS_ROOT,
                                     e.election_dirname)
    audit_spec_pathname = os.path.join(election_pathname,
                                       "3-audit",
                                       "31-audit-spec")
    filename = utils.greatest_name(audit_spec_pathname,
                                   "audit-spec-contest",
                                   ".csv")
    file_pathname = os.path.join(audit_spec_pathname, filename)
    fieldnames = ["Measurement id",
                  "Contest",
                  "Risk Measurement Method",
                  "Risk Limit",
                  "Risk Upset Threshold",
                  "Sampling Mode",
                  "Initial Status",
                  "Param 1",
                  "Param 2"]          
    rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=False)
    for row in rows:
        mid = row["Measurement id"]
        e.mids.append(mid)
        e.cid_m[mid] = row["Contest"]
        e.risk_method_m[mid] = row["Risk Measurement Method"]
        e.risk_limit_m[mid] = row["Risk Limit"]
        e.risk_upset_m[mid] = row["Risk Upset Threshold"]
        e.sampling_mode_m[mid] = row["Sampling Mode"]
        e.initial_status_m[mid] = row["Initial Status"]
        e.risk_measurement_parameters[mid] = (row["Param 1"], row["Param 2"])


def read_audit_spec_collection(e, args):

    election_pathname = os.path.join(multi.ELECTIONS_ROOT,
                                     e.election_dirname)
    audit_spec_pathname = os.path.join(election_pathname,
                                       "3-audit",
                                       "31-audit-spec")
    filename = utils.greatest_name(audit_spec_pathname,
                                   "audit-spec-collection",
                                   ".csv")
    file_pathname = os.path.join(audit_spec_pathname, filename)
    fieldnames = ["Collection",
                  "Max audit rate"]
    rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=False)
    for row in rows:
        pbcid = row["Collection"]
        e.max_audit_rate_p[pbcid] = row["Max audit rate"]


def read_audit_spec_seed(e, args):
    """
    Read audit seed from 3-audit/31-audit-spec/audit-spec-seed.csv

    But does not overwrite e.audit_seed if it was non-None
    because this means it was already set from the command line.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT,
                                     e.election_dirname)
    audit_spec_pathname = os.path.join(election_pathname,
                                       "3-audit",
                                       "31-audit-spec")
    filename = utils.greatest_name(audit_spec_pathname,
                                   "audit-spec-seed",
                                   ".csv")
    file_pathname = os.path.join(audit_spec_pathname, filename)
    fieldnames = ["Audit seed"]
    rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=False)
    for row in rows:
        new_audit_seed = row["Audit seed"]
        if e.audit_seed == None:
            set_audit_seed(e, new_audit_seed)


def check_audit_spec(e):

    if not isinstance(e.risk_limit_m, dict):
        utils.myerror("e.risk_limit_m is not a dict.")
    for mid in e.risk_limit_m:
        if mid not in e.mids:
            utils.mywarning("e.risk_limit_m mid key `{}` is not in e.mids."
                      .format(mid))
        if not (0.0 <= e.risk_limit_m[mid] <= 1.0):
            utils.mywarning("e.risk_limit_m[{}] not in interval [0,1]".format(mid))

    if not isinstance(e.max_audit_rate_p, dict):
        utils.myerror("e.max_audit_rate_p is not a dict.")
    for pbcid in e.max_audit_rate_p:
        if pbcid not in e.pbcids:
            utils.mywarning("pbcid `{}` is a key for e.max_audit_rate_p but not in e.pbcids."
                      .format(pbcid))
        if not 0 <= int(e.max_audit_rate_p[pbcid]):
            utils.mywarning("e.max_audit_rate_p[{}] must be nonnegative.".format(pbcid))

    if utils.warnings_given > 0:
        utils.myerror("Too many errors; terminating.")


def show_audit_spec(e):

    utils.myprint("====== Audit spec ======")

    utils.myprint("Seed for audit pseudorandom number generation (e.audit_seed):")
    utils.myprint("    {}".format(e.audit_seed))

    utils.myprint(("Risk Measurement ids (e.mids) with contest,"
                   "method, risk limit, and risk upset threshold:"))
    for mid in e.mids:
        utils.myprint("    {}: ({}, {}, {}, {})"
                      .format(e.cid_m[mid],
                              e.risk_method_m[mid],
                              e.risk_limit_m[mid],
                              e.risk_upset_m[mid],
                              e.sampling_mode_m[mid]))

    utils.myprint("e.max_audit_rate_p (max number of ballots audited/day per pbcid):")
    for pbcid in sorted(e.pbcids):
        utils.myprint("    {}:{}".format(pbcid, e.max_audit_rate_p[pbcid]))

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
        e.rn_p[pbcid], int(e.max_audit_rate_p[pbcid])) for pbcid in e.pbcids}


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

    # we represent stage number with a string, as json requires
    # keys to be strings.  We aren't using json now, but we might again later.
    e.last_stage = "{}".format(stage - 1)
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
    """Return True if we should stop audit (some measurement is Open and Active)."""

    for m in e.mids:
        if e.status_m[mid]=="Open" and e.sampling_mode=="Active":
            return False
    return True


def audit(e, args):

    read_audit_spec(e, args)
    initialize_audit(e)
    show_audit_spec(e)

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

    utils.myprint("All measurements have a status in the following list:",
            e.election_status_t[e.stage])
    if all([e.sampling_mode_m[mid]!="Active" or e.status_m[mid]!="Open" \
            for mid in e.mids]):
        utils.myprint("No `Active' measurement still has `Open' status.")
    if ("Active", "Upset") in \
       [(e.sampling_mode_m[mid], e.status_m[mid]) for mid in e.mids]:
        utils.myprint("At least one `Active' measurement signals `Upset' (full recount needed).")
    if int(e.stage) == e.max_stages:
        utils.myprint("Maximum number of audit stages ({}) reached."
                .format(e.max_stages))

    utils.myprint("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        utils.myprint("  {}:{}".format(pbcid, e.sn_tp[e.stage][pbcid]))
    utils.myprint_switches = ["std"]
    utils.myprint("Total number of ballots sampled: ", end='')
    utils.myprint(sum([e.sn_tp[e.stage][pbcid] for pbcid in e.pbcids]))


