# syn2.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 22, 2017
# python3

"""
Routines to generate a synthetic test election dataset, 
given the following parameters (defaults in brackets):

    n_cids = # number of contests [2]
    n_cids_wrong = # number of contests with wrong reported outcome [0]
    min_n_selids_per_cid = minimum number of selids per contest [2]
    max_n_selids_per_cid = maximum number of selids per contest [5]
    n_pbcids = # number of pbcids [2]
    n_pbcids_nocvr = # number of collections with no CVRs [0]
    min_n_bids_per_pbcid = minimum number of bids per pbcid [10]
    max_n_bids_per_pbcidp = maximum number of bids per pbcid [20]
    box_size = max number of ballots in a box [100]
    min_pbcids_per_cid = minimum number of pbcids per contest [1]
    max_pbcids_per_cid = maximum number of pbcids per contest [1]
    dropoff = rate at which votes drop off with selection (geometric) [0.9]
    errorrate = rate at which reported votes != actual votes [0.005]
    synseed = random number seed (for reproducibility) [1]
    RandomState = state for random number generator

    ### following are then computed ###
    cids = list of cids (of length n_cids)
    cids_wrong = list of cids that will have wrong output
    pbcids = list of pbcids (of length n_pbcids)
    cvr_type_p = mapping of pbcid to "CVR" or "noCVR"
    n_bids_p = mapping from pbcid to number of bids in that pbcid
    
The main data structure here, SynElection, is a subclass of 
multi.Election.  We fill in the values of the fields as if they
had been read on, or else we (optionally) output the values as csv files.
"""

import numpy as np
import os

import multi
import ids
import outcomes
import random 
import structure
import utils

class SynElection(multi.Election):

    def __init__(self, synseed=1):

        super(SynElection, self).__init__()

        # controllable fields
        self.n_cids = 2
        self.n_cids_wrong = 0
        self.min_n_selids_per_cid = 2
        self.max_n_selids_per_cid = 5
        self.n_pbcids = 2
        self.n_pbcids_nocvr = 0
        self.min_n_bids_per_pbcid = 10
        self.max_n_bids_per_pbcid = 20
        self.box_size = 100
        self.min_pbcids_per_cid = 1
        self.max_pbcids_per_cid = self.n_pbcids
        self.dropoff = 0.9
        self.error_rate = 0.005
        self.synseed = synseed
        self.SynRandomState = np.random.RandomState(self.synseed)

        # working fields
        # none right now...

default_SynElection = SynElection()          


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
    return se.SynRandomState.choice(elts)


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
        mid = se.SynRandomState.choice(range(low, high))
        L.extend(generate_segments(se, low, mid))
        L.extend(generate_segments(se,  mid+1, high))
    return L


##############################################################################
## election structure

def generate_election_structure(se=default_SynElection):
    """
    se has SynElection for the parameters noted above;
    add to se values that would be otherwise read in,
    e.g. via structure.py (read_election_structure, read_contests,
    read_contest_groups, read_collections)
    """

    # reset SynRandomState from synseed
    se.SynRandomState = np.random.RandomState(se.synseed)

    dts = utils.datetime_string()
    se.election_name = "TestElection-"+dts
    se.election_dirname = "TestElection-"+dts
    se.election_date = dts                     # FIX ??
    se.election_url = "None"            


def generate_contests(se):

    # check number of contests
    assert isinstance(se.n_cids, int) and se.n_cids >= 1
    # make cid for each contest
    se.cids = set("con{}".format(i+1) for i in range(se.n_cids))

    # generate contest types as plurality and number winners = 1
    # no write-ins
    for cid in se.cids:
        se.contest_type_c[cid] = "plurality"
        se.winners_c[cid] = 1
        se.write_ins_c[cid] = "no"

    # check number of cids with wrong reported outcome
    assert isinstance(se.n_cids_wrong, int) and 0 <= se.n_cids_wrong <= se.n_cids
    # determine which cids have wrong reported outcome
    se.cids_wrong = []
    while len(se.cids_wrong) < se.n_cids_wrong:
        se.cids_wrong.append(se.SynRandomState.choice(se.cids))

    # generate selids for each cid
    se.n_selids_c = {}
    se.selids_c = {}
    for cid in se.cids:
        se.n_selids_c[cid] = geospace_choice(se,
                                             se.min_n_selids_per_cid,
                                             se.max_n_selids_per_cid)

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
    for (low, high) in generate_segments(se, 1, se.n_cids):
        gid = "gid{}-{}".format(low, high)
        se.cgids_g[gid] = cids_list[low:high+1] 


def generate_collections(se):

    # generate list of pbcids
    assert isinstance(se.n_pbcids, int) and se.n_pbcids >= 1
    se.pbcids = ["pbc{}".format(i) for i in range(1, se.n_pbcids+1)]

    # add managers
    for pbcid in se.pbcids:
        se.manager_p[pbcid] = "Nobody"

    # number of pbcids with no CVR
    assert isinstance(se.n_pbcids_nocvr, int) and \
        0 <= se.n_pbcids_nocvr <= se.n_pbcids

    # identify which pbcids have types CVR or noCVR
    se.cvr_type_p = {}
    while len(se.cvr_type_p) < se.n_pbcids_nocvr:
        se.cvr_type_p[se.SynRandomState.choice[se.pbcids]] = "noCVR"
    for pbcid in se.pbcids:
        if pbcid not in se.cvr_type_p:
            se.cvr_type_p[pbcid] = "CVR"

    # record randomly chosen required and possible contest groups for each pbcid
    for pbcid in se.pbcids:
        if len(se.gids)>0:
            se.required_gid_p[pbcid] = se.SynRandomState.choice(se.gids)
            se.possible_gid_p[pbcid] = se.SynRandomState.choice(se.gids)
        else:
            se.required_gid_p[pbcid] = ""
            se.possible_gid_p[pbcid] = ""

    structure.finish_election_structure_groups(se)
    


def write_election_specification_csv(se):

    write_11_general_csv(se)
    write_12_contests_csv(se)
    write_13_contest_groups_csv(se)
    write_14_collections_csv(se)


def write_11_general_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-election-specification")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "11-general.csv")

    with open(filename, "w") as file:
        file.write("Attribute,Value\n")
        file.write("Election name,"+se.election_name+"\n")
        file.write("Elections dirname,"+se.election_dirname+"\n")
        file.write("Election date,"+se.election_date+"\n")
        file.write("Election URL,"+se.election_url+"\n")


def write_12_contests_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-election-specification")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "12-contests.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest id", "Contest type", "Winners", "Write-ins", "Selections"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for cid in se.cids:
            file.write(cid+",")
            file.write("{},".format(se.contest_type_c[cid].title()))
            file.write("{},".format(se.winners_c[cid]))
            file.write("{},".format(se.write_ins_c[cid].title()))
            file.write(",".join(se.selids_c[cid]))
            file.write("\n")
        

def write_13_contest_groups_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-election-specification")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "13-contest-groups.csv")

    with open(filename, "w") as file:
        fieldnames = ["Contest group id", "Contest or group id(s)"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for gid in se.gids:
            file.write(gid+",")
            file.write(",".join(sorted(se.cgids_g[gid])))
            file.write("\n")


def write_14_collections_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-election-specification")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "14-collections.csv")

    with open(filename, "w") as file:
        fieldnames = ["Collection id", "Manager", "CVR type", "Required Contests", "Possible Contests"]
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
                                             se.min_n_bids_per_pbcid,
                                             se.max_n_bids_per_pbcid)

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
                se.required_gid_b[bid] = se.SynRandomState.choice(se.gids)
                se.possible_gid_b[bid] = se.SynRandomState.choice(se.gids)
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
                if se.SynRandomState.choice([True, False]):
                    se.cids_b[bid].add(cid)

            se.cids_b[bid] = list(se.cids_b[bid])

    # Generate the reported selection for each contest and ballot (populate rv_cpb).
    # Draw from selids_c[cid] for each cid.
    se.rv_cpb = {}

    for pbcid in se.pbcids:
        for bid in se.bids_p[pbcid]:
            for cid in se.cids_b[bid]:
                selids = list(se.selids_c[cid])
                if se.contest_type_c[cid] == 'plurality':
                    selection = se.SynRandomState.choice(selids)
                    rv = (selection,)
                    utils.nested_set(se.rv_cpb, [cid, pbcid, bid], rv)
                else: # we can handle this later when its not hardcoded 
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
        outcome = max(rn_cv[cid], key=rn_cv[cid].get)
        se.ro_c[cid] = outcome
        tally = rn_cv[cid]
        se.ro_c[cid] = outcomes.compute_outcome(se, cid, tally)

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
            utils.nested_set(se.boxid_pb, [pbcid, bid], "box{}".format(1+((i+1)//se.box_size)))
            utils.nested_set(se.position_pb, [pbcid, bid], 1+(i%se.box_size))
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
            fieldnames = ["Collection id", "Box id", "Position",
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
                fieldnames = ["Collection id", "Scanner", "Ballot id",
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

    generate_audit_seed(se)
    generate_audit_orders(se)
    generate_audited_votes(se)

    # (audit stages will be generated by audit itself)



def generate_audit_seed(se):

    se.audit_seed = se.SynRandomState.randint(0, 2**32-1)


def generate_audit_orders(se):

    # see audit_orders.py

    pass


def generate_audited_votes(se):

    se.av_cpb = {}
    for cid in se.rv_cpb:
        for pbcid in se.rv_cpb[cid]:
            for bid in se.rv_cpb[cid][pbcid]:
                for vote in se.rv_cpb[cid][pbcid][bid]:
                    if (se.SynRandomState.uniform() <= se.error_rate):
                        #then choose a different selection other than the one on reported
                        selids = list(se.selids_c[cid].keys())
                        # selids.remove(se.rv_cpb[contest][pbcid][bid])
                    else:
                        selids = list(se.selids_c[cid].keys())
                    selection = se.SynRandomState.choice(selids)
                    # FIX: this should be a vote, not just a selection
                    utils.nested_set(se.av_cpb, [cid, pbcid, bid], selection)


def write_audit_csv(se):

    write_311_audit_seed_csv(se)
    write_32_audit_orders_csv(se)
    write_33_audited_votes_csv(se)


def write_311_audit_seed_csv(se):
    """ Write 3-audit/31-audit-setup/311-audit-seed.csv """

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "3-audit",
                           "31-audit-setup")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "311-audit-seed.csv")
    with open(filename, "w") as file:
        file.write("Audit seed\n")
        file.write("{}\n".format(se.audit_seed))


def write_32_audit_orders_csv(se):
    """ Write 3-audit/32-audit-orders/audit_orders-PBCID.csv """

    pass


def write_33_audited_votes_csv(se):
    """ Write 3-audit/33-audited-votes/audited-votes-PBCID.csv """

    dirpath = os.path.join(multi.ELECTIONS_ROOT,
                           se.election_dirname,
                           "3-audit",
                           "33-audited-votes")
    os.makedirs(dirpath, exist_ok=True)
    for cid in se.av_cpb:
        for pbcid in se.av_cpb[cid]:
            safe_pbcid = ids.filename_safe(pbcid)
            filename = os.path.join(dirpath, "audited-votes-" + safe_pbcid+".csv")
            with open(filename, "w") as file:
                fieldnames = ["Collection id", "Ballot id", "Contest", "Selections"]
                file.write(",".join(fieldnames))
                file.write("\n")
                for cid in se.av_cpb:
                    for pbcid_inner in se.av_cpb[cid]:
                        if pbcid_inner == pbcid:
                            for bid in se.av_cpb[cid][pbcid]:
                                vote = se.av_cpb[cid][pbcid][bid]
                                file.write("{},".format(pbcid))
                                file.write("{},".format(bid))
                                file.write("{},".format(cid))
                                file.write("{}".format(vote))
                                file.write("\n")



def test():

    se = SynElection()
    se.seed = 9

    generate_election_structure(se)
    structure.finish_election_structure(se)
    generate_contests(se)
    generate_contest_groups(se)
    generate_collections(se)

    generate_reported(se)
    generate_ballot_manifest(se)

    generate_audit_seed(se)
    generate_audited_votes(se)

    for key in sorted(vars(se)):
        print(key)
        print("    ", vars(se)[key])

    print("Checking structure: ", end='')
    structure.check_election_structure(se)
    print("OK.")
    
    write_election_specification_csv(se)
    write_reported_csv(se)
    write_audit_csv(se)

    # audit stages
    pass # TBD


if __name__=="__main__":

    test()
