# syn2.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# August 3, 2017
# python3

"""
Routines to generate a synthetic test election dataset, 
given the following parameters (defaults in brackets):

    cids = # number of contests [2]
    n_cids_wrong = # number of contests with wrong reported outcome [0]
    min_n_selids_per_cid = minimum number of selids per contest [2]
    max_n_selids_per_cid = maximum number of selids per contest [5]
    n_pbcids = # number of pbcids [2]
    n_pbcids_nocvr = # number of collections with no CVRs [0]
    min_n_bids_per_pbcid = minimum number of bids per pbcid [10]
    max_n_bids_per_pbcid = maximum number of bids per pbcid [20]
    box_size = max number of ballots in a box [100]
    min_pbcids_per_cid = minimum number of pbcids per contest [1]
    max_pbcids_per_cid = maximum number of pbcids per contest [1]
    dropoff = rate at which votes drop off with selection (geometric) [0.9]
    error_rate = rate at which reported votes != actual votes [0.005]
    seed = random number seed (for reproducibility) [1]
    RandomState = state for random number generator

    ### following are then computed ###
    ### in e:
    cids = list of cids (of length n_cids)
    cids_wrong = list of cids that will have wrong output
    pbcids = list of pbcids (of length syn_n_pbcids)
    cvr_type_p = mapping of pbcid to "CVR" or "noCVR"
    ### in syn:
    n_bids_p = mapping from pbcid to number of bids in that pbcid
    
We fill in the values of the fields of election e as if they
had been read in, or else we (optionally) output the values as csv files.
"""

import argparse
import copy
import numpy as np
import os

import multi
import audit_orders
import election_spec
import ids
import outcomes
import reported
import utils

class Syn_Params(object):
    """ An object we can hang synthesis generation parameters off of. """

    pass


def geospace(start, stop, num=7):
    """
    Return a list of up to num distinct integer values,
    from start, start+1, ..., stop, inclusive, geometrically spread out.

    A bit like numpy.linspace, but geometrically spread
    out rather than linearly spread out, and only integers returned.
    >>> geospace(0,1)
    [0, 1]
    >>> geospace(0,10)
    [0, 1, 2, 3, 5, 7, 10]    
    >>> geospace(20, 10000)
    [20, 56, 159, 447, 1260, 3550, 10000]    
    >>> geospace(1, 64)
    [1, 2, 4, 8, 16, 32, 64]
    """

    answer = {start, stop}
    start = max(start, 1)
    for i in range(1, num-1):
        answer.add(int(np.rint(start*(stop/start)**(i/(num-1)))))
    return sorted(answer)


def geospace_choice(e, syn, start, stop, num=7):
    """ 
    Return a random element from geospace(start, stop, num), 
    based on syn.RandomState.
    """

    elts = geospace(start, stop, num)
    return syn.RandomState.choice(elts)


def generate_segments(e, syn, low, high):
    """ 
    Return list of random segments (r, s) where low <= r < s <= high. 

    Number of segments returned is (high-low).

    Since r<s, does not return segments of the form (k, k).

    Intent is that cids are integers in range low <= cid <= high,
    and each segment yields a contest group covering cids r..s (inclusive).

    The segments "nest" -- given any two segments, either they
    are disjoint, or they are equal, or one contains the other.
    """

    assert low <= high
    L = []
    if low!=high:
        L.append((low, high))
        mid = syn.RandomState.choice(range(low, high))
        L.extend(generate_segments(e, syn, low, mid))
        L.extend(generate_segments(e, syn, mid+1, high))
    return L


##############################################################################
## election specification

def generate_election_spec(e, syn):
    """ 
    e = multi.Election()
    syn = Syn_Params()
    syn supplies additional paramters as noted above;
    add to e values that would be otherwise read in,
    e.g. via election_spec.py 
    (read_election_spec_general, 
     read_election_spec_contests,
     read_election_spec_contest_groups, 
     read_election_spec_collections)
    """

    generate_election_spec_general(e, syn)
    generate_election_spec_contests(e, syn)
    generate_election_spec_contest_groups(e, syn)
    generate_election_spec_collections(e, syn)
    election_spec.finish_election_spec(e)
    election_spec.check_election_spec(e)


def generate_election_spec_general(e, syn):

    # reset syn.RandomState from syn.seed
    syn.RandomState = np.random.RandomState(syn.seed)

    dts = utils.datetime_string()
    e.election_name = "TestElection-"+dts
    if e.election_dirname=="":
        e.election_dirname = "TestElection-"+dts
    e.election_date = dts                  
    e.election_url = "None"            


def generate_election_spec_contests(e, syn):

    # check number of contests
    assert isinstance(syn.n_cids, int) and syn.n_cids >= 1
    # make cid for each contest
    e.cids = set("con{}".format(i+1) for i in range(syn.n_cids))

    # generate contest types as plurality and number winners = 1
    # no write-ins
    for cid in e.cids:
        e.contest_type_c[cid] = "plurality"
        e.winners_c[cid] = 1
        e.write_ins_c[cid] = "no"

    # check number of cids with wrong reported outcome
    assert isinstance(syn.n_cids_wrong, int)
    assert 0 <= syn.n_cids_wrong <= syn.n_cids
    # determine which, if any, cids have wrong reported outcome
    cids_list = list(e.cids)
    syn.RandomState.shuffle(cids_list)    # in-place
    syn.cids_wrong = cids_list[:syn.n_cids_wrong]

    # generate selids for each cid
    e.n_selids_c = {}
    e.selids_c = {}
    for cid in e.cids:
        e.n_selids_c[cid] = geospace_choice(e,
                                            syn,
                                            syn.min_n_selids_per_cid,
                                            syn.max_n_selids_per_cid)

        e.selids_c[cid] = {"sel{}".format(i):True for i in range(1, e.n_selids_c[cid]+1)}

    # generate possible votes for each cid
    for cid in e.cids:
        if e.contest_type_c[cid] == "plurality":
            for selid in e.selids_c[cid]:
                utils.nested_set(e.votes_c, [cid, (selid,)], True)
        else:
            utils.myerror(("Contest {} is not plurality---"
                           "Can't generate votes for it.")
                          .format(cid))


def generate_election_spec_contest_groups(e, syn):
    """ 
    Greate syn.n_cids-1 'random' contest groups. 

    They get ids like 'gid2-6' meaning they cover cids 2 to 6 inclusive.
    """

    e.gids = []
    cids_list = sorted(list(e.cids))
    for (low, high) in generate_segments(e, syn, 1, syn.n_cids):
        gid = "gid{}-{}".format(low, high)
        e.cgids_g[gid] = cids_list[low:high+1] 


def generate_election_spec_collections(e, syn):

    # generate list of pbcids
    assert isinstance(syn.n_pbcids, int) and syn.n_pbcids >= 1
    e.pbcids = ["pbc{}".format(i) for i in range(1, syn.n_pbcids+1)]

    # add managers
    for pbcid in e.pbcids:
        e.manager_p[pbcid] = "Nobody"

    # number of pbcids with no CVR
    assert isinstance(syn.n_pbcids_nocvr, int) and \
        0 <= syn.n_pbcids_nocvr <= syn.n_pbcids

    # identify which pbcids have types CVR or noCVR
    e.cvr_type_p = {}
    while len(e.cvr_type_p) < syn.n_pbcids_nocvr:
        e.cvr_type_p[syn.RandomState.choice[e.pbcids]] = "noCVR"
    for pbcid in e.pbcids:
        if pbcid not in e.cvr_type_p:
            e.cvr_type_p[pbcid] = "CVR"

    # record randomly chosen required and possible contest groups for each pbcid
    for pbcid in e.pbcids:
        if len(e.gids)>0:
            e.required_gid_p[pbcid] = syn.RandomState.choice(e.gids)
            e.possible_gid_p[pbcid] = syn.RandomState.choice(e.gids)
        else:
            e.required_gid_p[pbcid] = ""
            e.possible_gid_p[pbcid] = ""

    election_spec.finish_election_spec_contest_groups(e, syn)
    


def write_election_spec_csv(e):

    write_election_spec_general_csv(e)
    write_election_spec_contests_csv(e)
    write_election_spec_contest_groups_csv(e)
    write_election_spec_collections_csv(e)


def write_election_spec_general_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "election-spec-general.csv")
    with open(filename, "w") as file:
        file.write("Attribute,Value\n")
        file.write("Election name,"+e.election_name+"\n")
        file.write("Election dirname,"+e.election_dirname+"\n")
        file.write("Election date,"+e.election_date+"\n")
        file.write("Election URL,"+e.election_url+"\n")


def write_election_spec_contests_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "election-spec-contests.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest", "Contest type", "Winners", "Write-ins", "Selections"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for cid in e.cids:
            file.write(cid+",")
            file.write("{},".format(e.contest_type_c[cid].title()))
            file.write("{},".format(e.winners_c[cid]))
            file.write("{},".format(e.write_ins_c[cid].title()))
            file.write(",".join(e.selids_c[cid]))
            file.write("\n")
        

def write_election_spec_contest_groups_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "election-spec-contest-groups.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest group", "Contest(s) or group(s)"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for gid in e.gids:
            file.write(gid+",")
            file.write(",".join(sorted(e.cgids_g[gid])))
            file.write("\n")


def write_election_spec_collections_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "election-spec-collections.csv")

    with open(filename, "w") as file:
        fieldnames = ["Collection", "Manager", "CVR type",
                      "Required Contests", "Possible Contests"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for pbcid in e.pbcids:
            file.write("{},".format(pbcid))
            file.write("{},".format(e.manager_p[pbcid]))
            file.write("{},".format(e.cvr_type_p[pbcid]))
            file.write("{},".format(e.required_gid_p[pbcid]))
            file.write("{}".format(e.possible_gid_p[pbcid]))
            file.write("\n")



##############################################################################
## reported results


def generate_reported(e, syn):

    generate_n_bids_p(e, syn)
    generate_bids_p(e, syn)
    generate_cids_b(e, syn)
    generate_rv_cpb(e, syn)
    generate_reported_ballot_manifests(e, syn)
    compute_reported_stats(e, syn)


def generate_n_bids_p(e, syn):
    """ Generate number of bids for each pbcid. """
    
    syn.n_bids_p = {}
    for pbcid in e.pbcids:
        syn.n_bids_p[pbcid] = geospace_choice(e,
                                              syn,
                                              syn.min_n_bids_per_pbcid,
                                              syn.max_n_bids_per_pbcid)


def generate_bids_p(e, syn):
    """ 
    Generate list of ballot ids for each pbcid: bid1, bid2, ...  .

    Note that these need only be unique within a pbcid, not globally.
    """

    syn.n_bids = 0
    e.bids_p = {}
    for pbcid in e.pbcids:
        e.bids_p[pbcid] = []
        for i in range(syn.n_bids_p[pbcid]):
            syn.n_bids += 1
            bid = "bid{}".format(syn.n_bids)
            e.bids_p[pbcid].append(bid)


def generate_cids_b(e, syn):
    """
    Determine what contest(s) are on the ballot for each bid and pbcid 
    Determine if contest is CVR or not 
    draw from selection 

    Also sets: syn.required_gid_b 
               syn.possible_gid_b 

    Assumes we already have the bids that correspond to the given paper ballot 
    collections.  What we want to do is assign contests to those ballot 
    ids based on what contests are in the given pbcids as well as assign 
    selections based on the possible selections for each contest.
    """

    # syn.cids_b
    syn.cids_b = {}
    for pbcid in e.pbcids:
        syn.required_gid_b = {}
        syn.possible_gid_b = {}
        for bid in e.bids_p[pbcid]:
            if len(e.gids) > 0:
                syn.required_gid_b[bid] = syn.RandomState.choice(e.gids)
                syn.possible_gid_b[bid] = syn.RandomState.choice(e.gids)
                required_cids_b = set(e.cids_g[e.required_gid_b[bid]])
                possible_cids_b = set(e.cids_g[e.possible_gid_b[bid]])
            else:
                syn.required_gid_b[bid] = ""     # means no contests required
                syn.possible_gid_b[bid] = ""     # means any contest is possible
                required_cids_b = set()
                possible_cids_b = set(e.cids)

            # now determine cids for this ballot, i.e. syn.cids_b[bid]
            syn.cids_b[bid] = set()
            required_cids_p = set(e.required_cid_p[pbcid])
            required_cids = required_cids_p.union(required_cids_b)
            for cid in required_cids:
                syn.cids_b[bid].add(cid)

            possible_cids_p = set(e.possible_cid_p[pbcid])
            possible_cids = possible_cids_p.intersection(possible_cids_b)
            for cid in possible_cids:
                if syn.RandomState.choice([True, False]):
                    syn.cids_b[bid].add(cid)

            syn.cids_b[bid] = list(syn.cids_b[bid])


def generate_rv_cpb(e, syn):
    """ Generate the reported selection for each contest and ballot.

        That is, populate rv_cpb, by drawing from selids_c[cid] for each cid.
    """

    e.rv_cpb = {}
    for pbcid in e.pbcids:
        for bid in e.bids_p[pbcid]:
            for cid in syn.cids_b[bid]:
                selids = list(e.selids_c[cid])
                if e.contest_type_c[cid] == 'plurality':
                    # give min(selids) an "edge" (expected margin) for winning
                    if syn.RandomState.uniform() <= syn.margin:
                        selection = min(selids)
                    else:
                        selection = syn.RandomState.choice(selids)
                    rv = (selection,)
                    utils.nested_set(e.rv_cpb, [cid, pbcid, bid], rv)
                else:
                    # assume otherwise that vote is permutation of selids
                    # (This will need refinement later presumably.)
                    rv = list(selids)
                    syn.RandomState.shuffle(rv)
                    utils.nested_set(e.rv_cpb, [cid, pbcid, bid], rv)
                    

def compute_reported_stats(e, syn):

    reported.compute_rn_cpr(e)
    reported.compute_rn_c(e)
    reported.compute_rn_p(e)
    reported.compute_rn_cr(e)
    outcomes.compute_ro_c(e, syn)


def generate_reported_ballot_manifests(e, syn):
    """
    Generate synthetic ballot manifest data.

    This procedure must be run *after* generate_reported.
    """

    for pbcid in e.pbcids:
        for i, bid in enumerate(e.bids_p[pbcid]):
            boxid = 1+((i+1)//syn.box_size)
            position = 1+(i%syn.box_size)
            stamp = "stmp"+"{:06d}".format((i+1)*17)
            utils.nested_set(e.boxid_pb, [pbcid, bid], "box{}".format(boxid))
            utils.nested_set(e.position_pb, [pbcid, bid], position)
            utils.nested_set(e.stamp_pb, [pbcid, bid], stamp)
            utils.nested_set(e.required_gid_pb, [pbcid, bid], "")
            utils.nested_set(e.possible_gid_pb, [pbcid, bid], "")
            utils.nested_set(e.comments_pb, [pbcid, bid], "")


def write_reported_csv(e):

    write_21_ballot_manifests_csv(e)
    write_22_reported_cvrs_csv(e)
    write_23_reported_outcomes_csv(e)


def write_21_ballot_manifests_csv(e):
                           
    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "2-reported",
                           "21-reported-ballot-manifests")
    os.makedirs(dirpath, exist_ok=True)

    for pbcid in e.pbcids:
        safe_pbcid = ids.filename_safe(pbcid)
        filename = os.path.join(dirpath, "manifest-"+safe_pbcid+".csv")
        with open(filename, "w") as file:
            fieldnames = ["Collection", "Box", "Position",
                          "Stamp", "Ballot id", "Number of ballots",
                          "Required Contests", "Possible Contests",
                          "Comments"]
            file.write(",".join(fieldnames))
            file.write("\n")
            for bid in e.bids_p[pbcid]:
                file.write("{},".format(pbcid))
                file.write("{},".format(e.boxid_pb[pbcid][bid]))
                file.write("{},".format(e.position_pb[pbcid][bid]))
                file.write("{},".format(e.stamp_pb[pbcid][bid]))
                file.write("{},".format(bid))
                file.write("1") # number of ballots
                file.write("{},".format(""))
                file.write("{},".format(""))
                # no comments
                file.write("\n")


def write_22_reported_cvrs_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "2-reported",
                           "22-reported-cvrs")
    os.makedirs(dirpath, exist_ok=True)

    scanner = "scanner1"
    for pbcid in e.pbcids:
        # handle cvr pbcids
        if e.cvr_type_p[pbcid]=="CVR": 
            safe_pbcid = ids.filename_safe(pbcid)
            filename = os.path.join(dirpath,
                                    "reported-cvrs-" + safe_pbcid+".csv")
            with open(filename, "w") as file:
                fieldnames = ["Collection", "Scanner", "Ballot id",
                              "Contest", "Selections"]
                file.write(",".join(fieldnames))
                file.write("\n")
                for bid in e.bids_p[pbcid]:
                    for cid in e.cids:
                        if cid in e.rv_cpb:
                            if bid in e.rv_cpb[cid][pbcid]:
                                vote = e.rv_cpb[cid][pbcid][bid]
                                file.write("{},".format(pbcid))
                                file.write("{},".format(scanner))
                                file.write("{},".format(bid))
                                file.write("{},".format(cid))
                                file.write(",".join(vote))
                                file.write("\n")
        # handle noCVR pbcids
        else:
            assert False, "FIX: add write-out of noCVR reported cvrs."


def write_23_reported_outcomes_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "2-reported")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "23-reported-outcomes.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest", "Winner(s)"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for cid in e.cids:
            file.write("{},".format(cid))
            file.write(",".join(e.ro_c[cid]))
            file.write("\n")


##############################################################################
## audit

##############################################################################
## Generate audit data

def generate_audit(e, syn):

    generate_audit_spec(e, syn)
    generate_audit_orders(e, syn)
    generate_audited_votes(e, syn)

    # (audit stages will be generated by audit itself)


def generate_audit_spec(e, syn):

    generate_audit_spec_global(e, syn)
    generate_audit_spec_contest(e, syn)
    generate_audit_spec_collection(e, syn)
    generate_audit_spec_seed(e, syn)


def generate_audit_spec_global(e, syn):

    e.max_stage_time = "9999-12-31-23-59-59"


def generate_audit_spec_contest(e, syn):

    # Generate one measurement per contest
    # Audit all contests

    for i, cid in enumerate(e.cids):
        mid = "mid{}".format(i)
        e.mids.append(mid)
        e.cid_m[mid] = cid
        e.risk_method_m[mid] = "Bayes"
        e.risk_limit_m[mid] = 0.05
        e.risk_upset_m[mid] = 0.98
        e.sampling_mode_m[mid] = "Active"
        e.initial_status_m[mid] = "Open"
        e.risk_measurement_parameters_m[mid] = ()


def generate_audit_spec_collection(e, syn):

    DEFAULT_MAX_AUDIT_RATE = 40
    for pbcid in e.pbcids:
        e.max_audit_rate_p[pbcid] = DEFAULT_MAX_AUDIT_RATE


def generate_audit_spec_seed(e, syn):
    """ 
    Generate a pseudo-random audit_seed.

    Here audit_seed has limited range (2**32 possible values)
    but this is only for synthetic elections, so 
    this isn't so important.
    """

    e.audit_seed = syn.RandomState.randint(0, 2**32-1)


def generate_audit_orders(e, syn):

    audit_orders.compute_audit_orders(e)


def generate_audited_votes(e, syn):

    e.av_cpb = {}
    for cid in e.rv_cpb:
        for pbcid in e.rv_cpb[cid]:
            for bid in e.rv_cpb[cid][pbcid]:
                rv = e.rv_cpb[cid][pbcid][bid]
                av = e.rv_cpb[cid][pbcid][bid]  # default no error
                if (syn.RandomState.uniform() <= syn.error_rate):
                    selids = list(e.selids_c[cid])     
                    if rv in selids and len(selids)>1:    
                        selids.remove(rv)
                    av = (syn.RandomState.choice(selids),)
                utils.nested_set(e.av_cpb, [cid, pbcid, bid], av)


def write_audit_csv(e):

    write_31_audit_spec_csv(e)
    write_32_audit_orders_csv(e)
    write_33_audited_votes_csv(e)


def write_31_audit_spec_csv(e):

    write_audit_spec_global_csv(e)
    write_audit_spec_contest_csv(e)
    write_audit_spec_collection_csv(e)
    write_audit_spec_seed_csv(e)
    

def write_audit_spec_global_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "3-audit",
                           "31-audit-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "audit-spec-global-"+utils.start_datetime_string+".csv")
    with open(filename, "w") as file:
        fieldnames = ["Global Audit Parameter",
                      "Value"]
        file.write(",".join(fieldnames))
        file.write("\n")
        file.write("Max audit stage time,")
        file.write(e.max_stage_time)
        file.write("\n")


def write_audit_spec_contest_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "3-audit",
                           "31-audit-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "audit-spec-contest-"+utils.start_datetime_string+".csv")
    with open(filename, "w") as file:
        fieldnames = ["Measurement id",
                      "Contest",
                      "Risk Measurement Method",
                      "Risk Limit",
                      "Risk Upset Threshold",
                      "Sampling Mode",
                      "Initial Status",
                      "Param 1",
                      "Param 2"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for mid in e.mids:
            file.write("{},".format(mid))
            file.write("{},".format(e.cid_m[mid]))
            file.write("{},".format(e.risk_method_m[mid]))
            file.write("{},".format(e.risk_limit_m[mid]))
            file.write("{},".format(e.risk_upset_m[mid]))
            file.write("{},".format(e.sampling_mode_m[mid]))
            file.write("{},".format(e.initial_status_m[mid]))
            params = ",".join(e.risk_measurement_parameters_m[mid])
            file.write("{}".format(params))
            file.write("\n")


def write_audit_spec_collection_csv(e):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "3-audit",
                           "31-audit-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "audit-spec-collection-"+utils.start_datetime_string+".csv")
    with open(filename, "w") as file:
        fieldnames = ["Collection",
                      "Max audit rate"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for pbcid in e.pbcids:
            file.write("{},".format(pbcid))
            file.write("{},".format(e.max_audit_rate_p[pbcid]))
            file.write("\n")


def write_audit_spec_seed_csv(e):
    """ Write 3-audit/31-audit-spec/audit-spec-seed.csv """

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "3-audit",
                           "31-audit-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "audit-spec-seed-"+utils.start_datetime_string+".csv")
    with open(filename, "w") as file:
        file.write("Audit seed\n")
        file.write("{}\n".format(e.audit_seed))


def write_32_audit_orders_csv(e):
    """ Write 3-audit/32-audit-orders/audit_orders-PBCID.csv """

    audit_orders.write_audit_orders(e)


def write_33_audited_votes_csv(e):
    """ Write 3-audit/33-audited-votes/audited-votes-PBCID.csv """

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           e.election_dirname,
                           "3-audit",
                           "33-audited-votes")
    os.makedirs(dirpath, exist_ok=True)

    pbcids = [pbcid for cid in e.av_cpb for pbcid in e.av_cpb[cid]]
    for pbcid in pbcids:
        safe_pbcid = ids.filename_safe(pbcid)
        filename = os.path.join(dirpath, "audited-votes-" + safe_pbcid+".csv")
        with open(filename, "w") as file:
            fieldnames = ["Collection", "Ballot id", "Contest", "Selections"]
            file.write(",".join(fieldnames))
            file.write("\n")
            for cid in e.av_cpb:
                if pbcid in e.av_cpb[cid]:
                    for bid in e.av_cpb[cid][pbcid]:
                        vote = e.av_cpb[cid][pbcid][bid]
                        file.write("{},".format(pbcid))
                        file.write("{},".format(bid))
                        file.write("{},".format(cid))
                        selections = ",".join(vote)
                        file.write("{}".format(selections))
                        file.write("\n")


def generate_syn_type_1(e, args):

    syn = copy.copy(args)
    default_parameters(syn)

    generate_election_spec(e, syn)
    generate_reported(e, syn)
    generate_audit(e, syn)

    debug = False
    if debug:
        for key in sorted(vars(e)):
            print(key)
            print("    ", vars(e)[key])

    
    write_election_spec_csv(e)
    write_reported_csv(e)
    write_audit_csv(e)



def generate_syn_type_2(e, args):

    syn = copy.copy(args)
    default_parameters(syn)

    generate_election_spec(e, syn)
    generate_reported(e, syn)
    generate_audit(e, syn)

    debug = False
    if debug:
        for key in sorted(vars(e)):
            print(key)
            print("    ", vars(e)[key])

    write_election_spec_csv(e)
    write_reported_csv(e)
    write_audit_csv(e)

    


##############################################################################
# Command-line arguments

def parse_args():

    parser = argparse.ArgumentParser(description=\
                                     ("syn2.py: "
                                      "Synthetic election generation for "
                                      "multi.py (a Bayesian post-election "
                                      "audit program for an election with "
                                      "multiple contests and multiple paper "
                                      "ballot collections)."))

    # Mandatory argument: dirname

    parser.add_argument("election_dirname",
                        help=('The name for this election of the '
                              'subdirectory within the elections root '
                              'directory. Enter "" to get default '
                              'of TestElection followed by datetime.'))

    # All others are optional

    parser.add_argument("--syn_type",
                        help="Type of synthetic election.",
                        default='1')

    args = parser.parse_args()
    return args


def default_parameters(syn):

    syn.n_cids = 2
    syn.n_cids_wrong = 0
    syn.min_n_selids_per_cid = 2
    syn.max_n_selids_per_cid = 5
    syn.n_pbcids = 2
    syn.n_pbcids_nocvr = 0
    syn.min_n_bids_per_pbcid = 200
    syn.max_n_bids_per_pbcid = 200
    syn.box_size = 100
    syn.min_pbcids_per_cid = 1
    syn.max_pbcids_per_cid = syn.n_pbcids
    syn.dropoff = 0.9
    syn.error_rate = 0.005
    syn.seed = 1
    syn.andomState = np.random.RandomState(syn.seed)
    syn.margin = 0.05



def process_args(e, args):

    e.election_dirname = ids.filename_safe(args.election_dirname)
    e.election_name = e.election_dirname

    print(args)
    if args.syn_type == '1':                        
        generate_syn_type_1(e, args)
    elif args.syn_type == '2':
        generate_syn_type_2(e, args)
    else:
        print("Illegal syn_type:", args.syn_type)


if __name__=="__main__":

    e = multi.Election()

    args = parse_args()
    process_args(e, args)

    filepath = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    print("  Done. Synthetic election written to:", filepath)


