# syn2.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# August 3, 2017
# python3

"""
Routines to generate a synthetic test election dataset, 
given the following parameters (defaults in brackets):

    syn_n_cids = # number of contests [2]
    syn_n_cids_wrong = # number of contests with wrong reported outcome [0]
    syn_min_n_selids_per_cid = minimum number of selids per contest [2]
    syn_max_n_selids_per_cid = maximum number of selids per contest [5]
    syn_n_pbcids = # number of pbcids [2]
    syn_n_pbcids_nocvr = # number of collections with no CVRs [0]
    syn_min_n_bids_per_pbcid = minimum number of bids per pbcid [10]
    syn_max_n_bids_per_pbcid = maximum number of bids per pbcid [20]
    syn_box_size = max number of ballots in a box [100]
    syn_min_pbcids_per_cid = minimum number of pbcids per contest [1]
    syn_max_pbcids_per_cid = maximum number of pbcids per contest [1]
    syn_dropoff = rate at which votes drop off with selection (geometric) [0.9]
    syn_error_rate = rate at which reported votes != actual votes [0.005]
    syn_seed = random number seed (for reproducibility) [1]
    syn_RandomState = state for random number generator

    ### following are then computed ###
    cids = list of cids (of length n_cids)
    cids_wrong = list of cids that will have wrong output
    pbcids = list of pbcids (of length syn_n_pbcids)
    cvr_type_p = mapping of pbcid to "CVR" or "noCVR"
    n_bids_p = mapping from pbcid to number of bids in that pbcid
    
The main data structure here, SynElection, is a subclass of 
multi.Election.  We fill in the values of the fields as if they
had been read on, or else we (optionally) output the values as csv files.
"""

import argparse
import numpy as np
import os

import multi
import audit_orders
import election_spec
import ids
import outcomes
import random 
import utils

class Syn_Election(multi.Election):

    def __init__(self, syn_seed=1):

        super(Syn_Election, self).__init__()

        # controllable fields
        self.syn_n_cids = 2
        self.syn_n_cids_wrong = 0
        self.syn_min_n_selids_per_cid = 2
        self.syn_max_n_selids_per_cid = 5
        self.syn_n_pbcids = 2
        self.syn_n_pbcids_nocvr = 0
        self.syn_min_n_bids_per_pbcid = 200
        self.syn_max_n_bids_per_pbcid = 200
        self.syn_box_size = 100
        self.syn_min_pbcids_per_cid = 1
        self.syn_max_pbcids_per_cid = self.syn_n_pbcids
        self.syn_dropoff = 0.9
        self.syn_error_rate = 0.005
        self.syn_seed = syn_seed
        self.syn_RandomState = np.random.RandomState(self.syn_seed)

        # working fields
        # none right now...

default_Syn_Election = Syn_Election()          


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


def geospace_choice(se, start, stop, num=7):
    """ 
    Return a random element from geospace(start, stop, num), 
    based on se.RandomState.
    """

    elts = geospace(start, stop, num)
    return se.syn_RandomState.choice(elts)


def generate_segments(se, low, high):
    """ 
    Generate and return list of  random segments (r, s)  
    where low <= r < s <= high. 
    (Does not return segments of the form (k, k).)

    Intent is that pbcids are integers in range low <= pbcid <= high,
    and each segment is a contest group covering pbcids r..s (inclusive).

    The segments "nest" -- given any two segments, either they
    are disjoint, or they are equal, or one contains the other.
    """

    assert low <= high
    L = []
    if low!=high:
        L.append((low, high))
        mid = se.syn_RandomState.choice(range(low, high))
        L.extend(generate_segments(se, low, mid))
        L.extend(generate_segments(se,  mid+1, high))
    return L


##############################################################################
## election specification

def generate_election_spec(se=default_Syn_Election):
    """
    se has Syn_Election for the parameters noted above;
    add to se values that would be otherwise read in,
    e.g. via election_spec.py (read_election_spec, 
    read_election_spec_contests,
    read_election_spec_contest_groups, 
    read_election_spec_collections)
    """

    print("generate_election_spec")

    # reset syn_RandomState from syn_seed
    se.syn_RandomState = np.random.RandomState(se.syn_seed)

    dts = utils.datetime_string()
    se.election_name = "TestElection-"+dts
    if se.election_dirname=="":
        se.election_dirname = "TestElection-"+dts
    se.election_date = dts                  
    se.election_url = "None"            


def generate_contests(se):

    # check number of contests
    assert isinstance(se.syn_n_cids, int) and se.syn_n_cids >= 1
    # make cid for each contest
    se.cids = set("con{}".format(i+1) for i in range(se.syn_n_cids))

    # generate contest types as plurality and number winners = 1
    # no write-ins
    for cid in se.cids:
        se.contest_type_c[cid] = "plurality"
        se.winners_c[cid] = 1
        se.write_ins_c[cid] = "no"

    # check number of cids with wrong reported outcome
    assert isinstance(se.syn_n_cids_wrong, int)
    assert 0 <= se.syn_n_cids_wrong <= se.syn_n_cids
    # determine which, if any, cids have wrong reported outcome
    cids_list = list(se.cids)
    se.syn_RandomState.shuffle(cids_list)    # in-place
    se.cids_wrong = cids_list[:se.syn_n_cids_wrong]

    # generate selids for each cid
    se.n_selids_c = {}
    se.selids_c = {}
    for cid in se.cids:
        se.n_selids_c[cid] = geospace_choice(se,
                                             se.syn_min_n_selids_per_cid,
                                             se.syn_max_n_selids_per_cid)

        se.selids_c[cid] = {"sel{}".format(i):True for i in range(1, se.n_selids_c[cid]+1)}

    # generate possible votes for each cid
    for cid in se.cids:
        if se.contest_type_c[cid] == "plurality":
            for selid in se.selids_c[cid]:
                utils.nested_set(se.votes_c, [cid, (selid,)], True)
        else:
            utils.myerror("Contest {} is not plurality---can't generate votes for it."
                          .format(cid))


def generate_contest_groups(se):

    se.gids = []
    cids_list = sorted(list(se.cids))
    for (low, high) in generate_segments(se, 1, se.syn_n_cids):
        gid = "gid{}-{}".format(low, high)
        se.cgids_g[gid] = cids_list[low:high+1] 


def generate_collections(se):

    # generate list of pbcids
    assert isinstance(se.syn_n_pbcids, int) and se.syn_n_pbcids >= 1
    se.pbcids = ["pbc{}".format(i) for i in range(1, se.syn_n_pbcids+1)]

    # add managers
    for pbcid in se.pbcids:
        se.manager_p[pbcid] = "Nobody"

    # number of pbcids with no CVR
    assert isinstance(se.syn_n_pbcids_nocvr, int) and \
        0 <= se.syn_n_pbcids_nocvr <= se.syn_n_pbcids

    # identify which pbcids have types CVR or noCVR
    se.cvr_type_p = {}
    while len(se.cvr_type_p) < se.syn_n_pbcids_nocvr:
        se.cvr_type_p[se.syn_RandomState.choice[se.pbcids]] = "noCVR"
    for pbcid in se.pbcids:
        if pbcid not in se.cvr_type_p:
            se.cvr_type_p[pbcid] = "CVR"

    # record randomly chosen required and possible contest groups for each pbcid
    for pbcid in se.pbcids:
        if len(se.gids)>0:
            se.required_gid_p[pbcid] = se.syn_RandomState.choice(se.gids)
            se.possible_gid_p[pbcid] = se.syn_RandomState.choice(se.gids)
        else:
            se.required_gid_p[pbcid] = ""
            se.possible_gid_p[pbcid] = ""

    election_spec.finish_election_spec_contest_groups(se)
    


def write_election_spec_csv(se):

    write_election_spec_general_csv(se)
    write_election_spec_contests_csv(se)
    write_election_spec_contest_groups_csv(se)
    write_election_spec_collections_csv(se)


def write_election_spec_general_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "election-spec-general.csv")

    with open(filename, "w") as file:
        file.write("Attribute,Value\n")
        file.write("Election name,"+se.election_name+"\n")
        file.write("Election dirname,"+se.election_dirname+"\n")
        file.write("Election date,"+se.election_date+"\n")
        file.write("Election URL,"+se.election_url+"\n")


def write_election_spec_contests_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "election-spec-contests.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest", "Contest type", "Winners", "Write-ins", "Selections"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for cid in se.cids:
            file.write(cid+",")
            file.write("{},".format(se.contest_type_c[cid].title()))
            file.write("{},".format(se.winners_c[cid]))
            file.write("{},".format(se.write_ins_c[cid].title()))
            file.write(",".join(se.selids_c[cid]))
            file.write("\n")
        

def write_election_spec_contest_groups_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "election-spec-contest-groups.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest group", "Contest(s) or group(s)"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for gid in se.gids:
            file.write(gid+",")
            file.write(",".join(sorted(se.cgids_g[gid])))
            file.write("\n")


def write_election_spec_collections_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "1-election-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "election-spec-collections.csv")

    with open(filename, "w") as file:
        fieldnames = ["Collection", "Manager", "CVR type",
                      "Required Contests", "Possible Contests"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for pbcid in se.pbcids:
            file.write("{},".format(pbcid))
            file.write("{},".format(se.manager_p[pbcid]))
            file.write("{},".format(se.cvr_type_p[pbcid]))
            file.write("{},".format(se.required_gid_p[pbcid]))
            file.write("{}".format(se.possible_gid_p[pbcid]))
            file.write("\n")



##############################################################################
## election


def generate_reported(se):

    # generate number of bids for each pbcid
    se.n_bids_p = {}
    for pbcid in se.pbcids:
        se.n_bids_p[pbcid] = geospace_choice(se,
                                             se.syn_min_n_bids_per_pbcid,
                                             se.syn_max_n_bids_per_pbcid)

    # generate list of ballot ids for each pbcid
    # note that these are only unique within a pbcid, not globally
    se.n_bids = 0
    se.bids_p = {}
    for pbcid in se.pbcids:
        se.bids_p[pbcid] = []
        for i in range(se.n_bids_p[pbcid]):
            se.n_bids += 1
            bid = "bid{}".format(se.n_bids)
            se.bids_p[pbcid].append(bid)

    """
    figure out what contest(s) are on the ballot for given bid and pbcid 
    figure out if contest is CVR or not 
    draw from selection 
    """

    """
    Above we have the bids that correspond to the given paper ballot 
    collections.  What we want to do is assign contests to those ballot 
    ids based on what contests are in the given pbcids as well as assign 
    selections based on the possible selections for each contest.
    """

    # se.cids_b
    se.cids_b = {}
    for pbcid in se.pbcids:
        se.required_gid_b = {}
        se.possible_gid_b = {}
        for bid in se.bids_p[pbcid]:
            se.cids_b[bid] = set()

            if len(se.gids) > 0:
                se.required_gid_b[bid] = se.syn_RandomState.choice(se.gids)
                se.possible_gid_b[bid] = se.syn_RandomState.choice(se.gids)
            else:
                se.required_gid_b[bid] = ""
                se.possible_gid_b[bid] = ""

            required_cids_p = set(se.required_cid_p[pbcid])
            if se.required_gid_b[bid] != "":
                required_cids_b = set(se.cids_g[se.required_gid_b[bid]])
            else:
                required_cids_b = set()
            required_cids = required_cids_p.union(required_cids_b)
            for cid in required_cids:
                se.cids_b[bid].add(cid)

            possible_cids_p = set(se.possible_cid_p[pbcid])
            if se.possible_gid_b[bid] != "":
                possible_cids_b = set(se.cids_g[se.possible_gid_b[bid]])
            else:
                possible_cids_b = set(se.cids)
            possible_cids = possible_cids_p.intersection(possible_cids_b)
            for cid in possible_cids:
                if se.syn_RandomState.choice([True, False]):
                    se.cids_b[bid].add(cid)

            se.cids_b[bid] = list(se.cids_b[bid])

    # Generate the reported selection for each contest and ballot
    # (populate rv_cpb).
    # Draw from selids_c[cid] for each cid.
    se.rv_cpb = {}

    for pbcid in se.pbcids:
        for bid in se.bids_p[pbcid]:
            for cid in se.cids_b[bid]:
                selids = list(se.selids_c[cid])
                if se.contest_type_c[cid] == 'plurality':
                    selection = se.syn_RandomState.choice(selids)
                    rv = (selection,)
                    utils.nested_set(se.rv_cpb, [cid, pbcid, bid], rv)
                else:
                    # we can handle this later...
                    # need to distinguish preferential voting, etc...
                    pass
                    

    # sum over ballot ids and pbcids to get se.rn_cv
    rn_cv = {}
    for pbcid in se.pbcids:
        for bid in se.bids_p[pbcid]:
            for cid in se.cids_b[bid]:
                rvote = se.rv_cpb[cid][pbcid][bid]
                if cid not in rn_cv:
                    utils.nested_set(rn_cv, [cid, rvote], 1)
                else:
                    if rvote not in rn_cv[cid]:
                        utils.nested_set(rn_cv, [cid, rvote], 1)
                    else:
                        rn_cv[cid][rvote]+=1

    # get rn_p from se.rv_cpb
    se.rn_p = dict()
    for cid in se.rv_cpb:
        for pbcid in se.rv_cpb[cid]:
            for bid in se.rv_cpb[cid][pbcid]:
                if pbcid not in se.rn_p:
                    se.rn_p[pbcid]=1
                else:
                    se.rn_p[pbcid]+=1

    # sum over selection ids to get rn_c
    se.rn_c = {}
    for cid in rn_cv:
        for rvote in rn_cv[cid]:
            if cid not in se.rn_c:
                se.rn_c[cid]=rn_cv[cid][rvote]
            else:
                se.rn_c[cid]+=rn_cv[cid][rvote]

    # get rn_cpr
    se.rn_cpr = dict()
    for cid in se.cids:
        for pbcid in se.rv_cpb[cid]:
            for bid in se.rv_cpb[cid][pbcid]:
                rvote = se.rv_cpb[cid][pbcid][bid]
                if cid in se.rn_cpr:
                    if pbcid in se.rn_cpr[cid]:
                        if rvote in se.rn_cpr[cid][pbcid]:
                            se.rn_cpr[cid][pbcid][rvote]+=1
                        else:
                            utils.nested_set(se.rn_cpr,[cid, pbcid, rvote], 1)
                    else:
                        utils.nested_set(se.rn_cpr,[cid, pbcid, rvote], 1)
                else:
                    utils.nested_set(se.rn_cpr,[cid, pbcid, rvote], 1)

    # sum over pbcids to get rn_cr
    se.rn_cr = dict()
    for cid in se.cids:
        for pbcid in se.rn_cpr[cid]:
            for rvote in se.rn_cpr[cid][pbcid]:
                if cid in se.rn_cr:
                    if rvote in se.rn_cr[cid]:
                        se.rn_cr[cid][rvote] += se.rn_cpr[cid][pbcid][rvote]
                    else:
                        utils.nested_set(se.rn_cr, [cid, rvote], se.rn_cpr[cid][pbcid][rvote])
                else:
                    utils.nested_set(se.rn_cr, [cid, rvote], se.rn_cpr[cid][pbcid][rvote])

    se.ro_c = dict()
    for cid in rn_cv:
        tally = rn_cv[cid]
        se.ro_c[cid] = outcomes.compute_outcome(se, cid, tally)
        print(">>> se.ro_c[{}] = {}".format(cid, se.ro_c[cid]))

    return se


def generate_ballot_manifest(se):
    """
    Generate synthetic ballot manifest data.

    This procedure must be run *after* generate_reported.
    """
    # se.bids_p = {}
    # This dict is generated by generate_reported(se).

    # se.boxid_pb = {}
    # se.position_pb = {}
    # se.stamp_pb = {}
    #   for stamps: just use consecutive multiples of 17;
    #               this protects against digit substitution
    #               and transposition errors.
    # se.number_of_ballots_pb not used, since they are all 1.
    # se.required_gid_pb = {}
    # se.possible_gid_pb = {}
    # se.comments_pb = {}
    for pbcid in se.pbcids:
        for i, bid in enumerate(se.bids_p[pbcid]):
            utils.nested_set(se.boxid_pb, [pbcid, bid], "box{}"
                             .format(1+((i+1)//se.syn_box_size)))
            utils.nested_set(se.position_pb, [pbcid, bid], 1+(i%se.syn_box_size))
            utils.nested_set(se.stamp_pb, [pbcid, bid], "stmp"+"{:06d}".format((i+1)*17))
            utils.nested_set(se.required_gid_pb, [pbcid, bid], "")
            utils.nested_set(se.possible_gid_pb, [pbcid, bid], "")
            utils.nested_set(se.comments_pb, [pbcid, bid], "")


def write_reported_csv(se):

    write_21_ballot_manifests_csv(se)
    write_22_reported_cvrs_csv(se)
    write_23_reported_outcomes_csv(se)


def write_21_ballot_manifests_csv(se):
                           
    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "2-reported",
                           "21-reported-ballot-manifests")
    os.makedirs(dirpath, exist_ok=True)

    for pbcid in se.pbcids:
        safe_pbcid = ids.filename_safe(pbcid)
        filename = os.path.join(dirpath, "manifest-"+safe_pbcid+".csv")
        with open(filename, "w") as file:
            fieldnames = ["Collection", "Box", "Position",
                          "Stamp", "Ballot id", "Number of ballots",
                          "Required Contests", "Possible Contests",
                          "Comments"]
            file.write(",".join(fieldnames))
            file.write("\n")
            for bid in se.bids_p[pbcid]:
                file.write("{},".format(pbcid))
                file.write("{},".format(se.boxid_pb[pbcid][bid]))
                file.write("{},".format(se.position_pb[pbcid][bid]))
                file.write("{},".format(se.stamp_pb[pbcid][bid]))
                file.write("{},".format(bid))
                file.write("1") # number of ballots
                file.write("{},".format(""))
                file.write("{},".format(""))
                # no comments
                file.write("\n")


def write_22_reported_cvrs_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "2-reported",
                           "22-reported-cvrs")
    os.makedirs(dirpath, exist_ok=True)

    scanner = "scanner1"
    for pbcid in se.pbcids:
        # handle cvr pbcids
        if se.cvr_type_p[pbcid]=="CVR": 
            safe_pbcid = ids.filename_safe(pbcid)
            filename = os.path.join(dirpath,
                                    "reported-cvrs-" + safe_pbcid+".csv")
            with open(filename, "w") as file:
                fieldnames = ["Collection", "Scanner", "Ballot id",
                              "Contest", "Selections"]
                file.write(",".join(fieldnames))
                file.write("\n")
                for bid in se.bids_p[pbcid]:
                    for cid in se.cids:
                        if cid in se.cids_b[bid]:
                            vote = se.rv_cpb[cid][pbcid][bid]
                            file.write("{},".format(pbcid))
                            file.write("{},".format(scanner))
                            file.write("{},".format(bid))
                            file.write("{},".format(cid))
                            file.write(",".join(vote))
                            file.write("\n")
        # handle noCVR pbcids
        else:
            pass


def write_23_reported_outcomes_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "2-reported")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "23-reported-outcomes.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest", "Winner(s)"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for cid in se.cids:
            file.write("{},".format(cid))
            file.write(",".join(se.ro_c[cid]))
            file.write("\n")


##############################################################################
## audit

##############################################################################
## Generate audit data

def generate_audit(se):

    generate_audit_spec(se)
    generate_audit_orders(se)
    generate_audited_votes(se)

    # (audit stages will be generated by audit itself)


def generate_audit_spec(se):

    generate_audit_spec_global(se)
    generate_audit_spec_contest(se)
    generate_audit_spec_collection(se)
    generate_audit_spec_seed(se)


def generate_audit_spec_global(se):

    se.max_stage_time = "9999-12-31-23-59-59"


def generate_audit_spec_contest(se):

    # Generate one measurement per contest
    # Audit all contests

    for i, cid in enumerate(se.cids):
        mid = "mid{}".format(i)
        se.mids.append(mid)
        se.cid_m[mid] = cid
        se.risk_method_m[mid] = "Bayes"
        se.risk_limit_m[mid] = 0.05
        se.risk_upset_m[mid] = 0.98
        se.sampling_mode_m[mid] = "Active"
        se.initial_status_m[mid] = "Open"
        se.risk_measurement_parameters_m[mid] = ()


def generate_audit_spec_collection(se):

    pass #TBD


def generate_audit_spec_seed(se):

    se.audit_seed = se.syn_RandomState.randint(0, 2**32-1)


def generate_audit_orders(se):

    audit_orders.compute_audit_orders(se)


def generate_audited_votes(se):

    se.av_cpb = {}
    for cid in se.rv_cpb:
        for pbcid in se.rv_cpb[cid]:
            for bid in se.rv_cpb[cid][pbcid]:
                rv = se.rv_cpb[cid][pbcid][bid]
                av = se.rv_cpb[cid][pbcid][bid]  # default no error
                if (se.syn_RandomState.uniform() <= se.syn_error_rate):
                    selids = list(se.selids_c[cid])     
                    if rv in selids:    
                        selids.remove(rv)
                    av = (se.syn_RandomState.choice(selids),)
                utils.nested_set(se.av_cpb, [cid, pbcid, bid], av)


def write_audit_csv(se):

    write_31_audit_spec_csv(se)
    write_32_audit_orders_csv(se)
    write_33_audited_votes_csv(se)


def write_31_audit_spec_csv(se):

    write_audit_spec_global_csv(se)
    write_audit_spec_contest_csv(se)
    write_audit_spec_collection_csv(se)
    write_audit_spec_seed_csv(se)
    

def write_audit_spec_global_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
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
        file.write(se.max_stage_time)
        file.write("\n")


def write_audit_spec_contest_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
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
        for mid in se.mids:
            file.write("{},".format(mid))
            file.write("{},".format(se.cid_m[mid]))
            file.write("{},".format(se.risk_method_m[mid]))
            file.write("{},".format(se.risk_limit_m[mid]))
            file.write("{},".format(se.risk_upset_m[mid]))
            file.write("{},".format(se.sampling_mode_m[mid]))
            file.write("{},".format(se.initial_status_m[mid]))
            params = ",".join(se.risk_measurement_parameters_m[mid])
            file.write("{}".format(params))
            file.write("\n")


def write_audit_spec_collection_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
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
        for pbcid in se.pbcids:
            file.write("{},".format(pbcid))
            file.write("{},".format(40))
            file.write("\n")


def write_audit_spec_seed_csv(se):
    """ Write 3-audit/31-audit-spec/audit-spec-seed.csv """

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "3-audit",
                           "31-audit-spec")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath,
                            "audit-spec-seed-"+utils.start_datetime_string+".csv")
    with open(filename, "w") as file:
        file.write("Audit seed\n")
        file.write("{}\n".format(se.audit_seed))


def write_32_audit_orders_csv(se):
    """ Write 3-audit/32-audit-orders/audit_orders-PBCID.csv """

    audit_orders.write_audit_orders(se)


def write_33_audited_votes_csv(se):
    """ Write 3-audit/33-audited-votes/audited-votes-PBCID.csv """

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "3-audit",
                           "33-audited-votes")
    os.makedirs(dirpath, exist_ok=True)

    pbcids = [pbcid for cid in se.av_cpb for pbcid in se.av_cpb[cid]]
    for pbcid in pbcids:
        safe_pbcid = ids.filename_safe(pbcid)
        filename = os.path.join(dirpath, "audited-votes-" + safe_pbcid+".csv")
        with open(filename, "w") as file:
            fieldnames = ["Collection", "Ballot id", "Contest", "Selections"]
            file.write(",".join(fieldnames))
            file.write("\n")
            for cid in se.av_cpb:
                if pbcid in se.av_cpb[cid]:
                    for bid in se.av_cpb[cid][pbcid]:
                        vote = se.av_cpb[cid][pbcid][bid]
                        file.write("{},".format(pbcid))
                        file.write("{},".format(bid))
                        file.write("{},".format(cid))
                        selections = ",".join(vote)
                        file.write("{}".format(selections))
                        file.write("\n")


def test(se):

    generate_election_spec(se)
    election_spec.finish_election_spec(se)

    generate_contests(se)
    generate_contest_groups(se)
    generate_collections(se)

    generate_reported(se)
    generate_ballot_manifest(se)

    generate_audit_spec(se)
    generate_audit_orders(se)
    generate_audited_votes(se)

    for key in sorted(vars(se)):
        print(key)
        print("    ", vars(se)[key])

    print("Checking specification: ", end='')
    election_spec.check_election_spec(se)
    print("OK.")
    
    write_election_spec_csv(se)
    write_reported_csv(se)
    write_audit_csv(se)


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

    args = parser.parse_args()
    return args


def process_args(se, args):

    se.election_dirname = ids.filename_safe(args.election_dirname)
    se.election_name = se.election_dirname

    test(se)


if __name__=="__main__":

    se = Syn_Election()

    args = parse_args()
    process_args(se, args)

    


