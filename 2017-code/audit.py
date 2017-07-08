# audit.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 8, 2017
# python3

"""
Routines to work with multi.py on post-election audits.
"""

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

    myprint("    Total sample counts by Contest.PaperBallotCollection[reported selection]"
            "and actual selection:")
    for cid in e.cids:
        for pbcid in sorted(e.rel_cp[cid]):
            tally2 = e.sn_tcpra[e.stage][cid][pbcid]
            for r in sorted(tally2.keys()):  # r = reported vote
                myprint("      {}.{}[{}]".format(cid, pbcid, r), end='')
                for a in sorted(tally2[r].keys()):
                    myprint("  {}:{}".format(a, tally2[r][a]), end='')
                myprint("  total:{}".format(e.sn_tcpr[e.stage][cid][pbcid][r]))


##############################################################################
# Risk measurement

def compute_contest_risk(e, cid, st):
    """ 
    Compute Bayesian risk (chance that reported outcome is wrong for cid).
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
                    tally[a] += e.pseudocount
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
    e.risk_tc[e.stage][cid] = wrong_outcome_count / e.n_trials


def compute_contest_risks(e, st):

    for cid in e.cids:
        compute_contest_risk(e, cid, st)


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

    myprint("    Risk (that reported outcome is wrong) and contest status per cid:")
    for cid in e.cids:
        myprint("     ", cid, e.risk_tc[e.stage][cid],
                "(limit {})".format(e.risk_limit_c[cid]),
                e.contest_status_tc[e.stage][cid])
    myprint("    Election status:", e.election_status_t[e.stage])


##############################################################################
# Audit parameters

def get_audit_seed(e, args):

    global auditRandomState

    e.audit_seed = args.audit_seed
    # audit_seed might be None if no command-line argument given

    auditRandomState = np.random.RandomState(e.audit_seed)


def get_audit_parameters(e, args):

    load_part_from_json(e, "audit_parameters.js")
    # command line can override .js file CHECK THIS
    get_audit_seed(e, args)
    check_audit_parameters(e)


def check_audit_parameters(e):

    if not isinstance(e.risk_limit_c, dict):
        myerror("e.risk_limit_c is not a dict.")
    for cid in e.risk_limit_c:
        if cid not in e.cids:
            mywarning("e.risk_limit_c cid key `{}` is not in e.cids."
                      .format(cid))
        if not (0.0 <= e.risk_limit_c[cid] <= 1.0):
            mywarning("e.risk_limit_c[{}] not in interval [0,1]".format(cid))

    if not isinstance(e.audit_rate_p, dict):
        myerror("e.audit_rate_p is not a dict.")
    for pbcid in e.audit_rate_p:
        if pbcid not in e.pbcids:
            mywarning("pbcid `{}` is a key for e.audit_rate_p but not in e.pbcids."
                      .format(pbcid))
        if not 0 <= e.audit_rate_p[pbcid]:
            mywarning("e.audit_rate_p[{}] must be nonnegative.".format(pbcid))

    if not isinstance(e.contest_status_tc, dict):
        myerror("e.contest_status_tc is not a dict.")
    if "0" not in e.contest_status_tc:
        myerror("e.contest_status_tc must have `0` as a key.")
    for cid in e.contest_status_tc["0"]:
        if cid not in e.cids:
            mywarning("cid `{}` is key in e.contest_status_tc but not in e.cids"
                      .format(cid))
        if e.contest_status_tc["0"][cid] not in ["Auditing", "Just Watching"]:
            mywarning("e.contest_status_tc['0'][{}] must be `Auditing` or `Just Watching`."
                      .format(cid))

    if warnings_given > 0:
        myerror("Too many errors; terminating.")


def show_audit_parameters(e):

    myprint("====== Audit parameters ======")

    myprint("e.contest_status_tc (initial audit status for each contest):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.contest_status_tc["0"][cid]))

    myprint("e.risk_limit_c (risk limit per contest):")
    for cid in e.cids:
        myprint("    {}:{}".format(cid, e.risk_limit_c[cid]))

    myprint("e.audit_rate_p (max number of ballots audited/day per pbcid):")
    for pbcid in sorted(e.pbcids):
        myprint("    {}:{}".format(pbcid, e.audit_rate_p[pbcid]))

    myprint("e.max_stages (max number of audit stages allowed):")
    myprint("    {}".format(e.max_stages))

    myprint("e.n_trials (number of trials used to estimate risk "
            "in compute_contest_risk):")
    myprint("    {}".format(e.n_trials))

    myprint("e.pseudocount (hyperparameter for prior distribution,")
    myprint("    {}".format(e.pseudocount))

    myprint("e.audit_seed (seed for audit pseudorandom number generation)")
    myprint("    {}".format(e.audit_seed))


def initialize_audit(e):

    e.sn_tp["0"] = {}
    for pbcid in e.pbcids:
        e.sn_tp["0"][pbcid] = 0
    # Initial plan size is just audit rate, for each pbcid.
    e.plan_tp["0"] = {pbcid: min(
        e.rn_p[pbcid], e.audit_rate_p[pbcid]) for pbcid in e.pbcids}


def show_audit_stage_header(e):

    myprint("audit stage", e.stage)
    myprint("    New target sample sizes by paper ballot collection:")
    for pbcid in e.pbcids:
        last_s = e.sn_tp[e.last_stage]
        myprint("      {}: {} (+{})"
                .format(pbcid,
                        e.plan_tp[e.last_stage][pbcid],
                        e.plan_tp[e.last_stage][pbcid] - last_s[pbcid]))


def audit_stage(e, stage):

    e.last_stage = "{}".format(stage - 1)   # json keys must be strings
    e.stage = "{}".format(stage)
    e.risk_tc[e.stage] = {}
    e.contest_status_tc[e.stage] = {}
    e.sn_tp[e.stage] = {}
    e.sn_tcpra[e.stage] = {}

    draw_sample(e)
    compute_contest_risks(e, e.sn_tcpra)
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

    myprint("====== Audit ======")

    for stage in range(1, e.max_stages + 1):
        audit_stage(e, stage)
        if stop_audit(e):
            break
        compute_plan(e)
    show_audit_summary(e)


def show_audit_summary(e):

    global myprint_switches

    myprint("=============")
    myprint("Audit completed!")

    myprint("All contests have a status in the following list:",
            e.election_status_t[e.stage])
    if "Auditing" not in e.election_status_t[e.stage]:
        myprint("No contest still has `Auditing' status.")
    if "Full Recount Needed" in e.election_status_t[e.stage]:
        myprint("At least one contest needs a full recount.")
    if int(e.stage) == e.max_stages:
        myprint("Maximum number of audit stages ({}) reached."
                .format(e.max_stages))

    myprint("Number of ballots sampled, by paper ballot collection:")
    for pbcid in e.pbcids:
        myprint("  {}:{}".format(pbcid, e.sn_tp[e.stage][pbcid]))
    myprint_switches = ["std"]
    myprint("Total number of ballots sampled: ", end='')
    myprint(sum([e.sn_tp[e.stage][pbcid] for pbcid in e.pbcids]))


