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
    seed = random number seed (for reproducibility) [1]
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
import structure
import utils
import random 

class SynElection(multi.Election):

    def __init__(self, synseed=1):

        super(SynElection, self).__init__()
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


##############################################################################
## nested_set -- convenient utility to assign into a tree of nested dicts

def nested_set(dic, keys, value):
    """ 
    Here 
       dic = existing dict
       keys = nonempty list of keys
       value = an arbitrary value
    Function by example:
       If keys = ["A", "B", "C"], then set dic["A"]["B"]["C"] = value,
       ensuring all intermediate dicts exit
    """

    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


##############################################################################
## election structure

def generate_election_structure(se=default_SynElection):
    """
    se has SynElection for the parameters noted above;
    add to se values that would be otherwise read in,
    e.g. via structure.py (read_election, read_contests,
    read_collections)
    """

    # reset SynRandomState from seed
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
    se.cids = ["c{}".format(i+1) for i in range(se.n_cids)]

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

        se.selids_c[cid] = {"s{}".format(i):True for i in range(1, se.n_selids_c[cid]+1)}


def generate_collections(se):

    # generate list of pbcids
    assert isinstance(se.n_pbcids, int) and se.n_pbcids >= 1
    se.pbcids = ["p{}".format(i) for i in range(1, se.n_pbcids+1)]

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
    
    # determine range of pbcids for each cid
    # (always a range of consecutive pbcids, looking at them as integers)
    m = se.min_pbcids_per_cid
    M = se.max_pbcids_per_cid
    assert m >= 1
    assert M <= se.n_pbcids
    se.firstpbcidx_c = {}
    se.lastpbcidx_c = {}
    se.rel_cp = {}
    for cid in se.cids:
        s = geospace_choice(se, m, M)
        se.firstpbcidx_c[cid] = se.SynRandomState.randint(0, se.n_pbcids - s + 1)
        se.lastpbcidx_c[cid] = se.firstpbcidx_c[cid] + s - 1
        se.rel_cp[cid] = {}
        for pbcidx in range(se.firstpbcidx_c[cid], se.lastpbcidx_c[cid]+1):
            pbcid = se.pbcids[pbcidx]
            se.rel_cp[cid][pbcid] = True


def write_structure_csvs(se):

    write_11_election_csv(se)
    write_12_contests_csv(se)
    write_13_collections_csv(se)
    write_14_contest_groups_csv(se)


def write_11_election_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-structure")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "11_election.csv")

    with open(filename, "w") as file:
        file.write("Attribute,Value\n")
        file.write("Election name,"+se.election_name+"\n")
        file.write("Elections dirname,"+se.election_dirname+"\n")
        file.write("Election date,"+se.election_date+"\n")
        file.write("Election URL,"+se.election_url+"\n")


def write_12_contests_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-structure")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "12_contests.csv")

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
        

def write_13_collections_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "1-structure")
    os.makedirs(dirpath, exist_ok=True)
    filename = os.path.join(dirpath, "13_collections.csv")

    with open(filename, "w") as file:
        fieldnames = ["Collection id", "Manager", "CVR type", "Contests"]
        file.write(",".join(fieldnames))
        file.write("\n")
        for pbcid in se.pbcids:
            file.write("{},".format(pbcid))
            file.write("{},".format(se.manager_p[pbcid]))
            file.write("{},".format(se.cvr_type_p[pbcid]))
            cids = [cid for cid in se.cids if pbcid in se.rel_cp[cid]]
            file.write(",".join(cids))
            file.write("\n")

def write_14_contest_groups_csv(se):
    """ Experimental feature not yet implemented """

    pass


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
            bid = "b{}".format(se.n_bids)
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
    se.cids_b = {}

    # change rel_cp to rel_pc 
    rel_pc = {}
    for cid in se.cids:
        pbcids = se.rel_cp[cid]
        for pbcid in pbcids:
            if pbcid not in rel_pc:
                rel_pc[pbcid]=[cid]
            else:
                rel_pc[pbcid].append(cid)

    for pbcid in se.pbcids:
        if se.cvr_type_p[pbcid] == 'CVR':
            bids_pi = se.bids_p[pbcid]
            available_contests = rel_pc[pbcid]
            for i in range(len(bids_pi)):
                num_contests =  int(se.SynRandomState.uniform(1,len(available_contests)+1,1))
                # random.randint(1,len(available_contests))
                # change to int(se.SynRandomState.uniform(low, high, size))
                contest_set = set()
                for j in range(num_contests):
                    contest = int(se.SynRandomState.uniform(0,len(available_contests),1))
                    # random.randint(0, len(available_contests)-1)
                    if contest not in contest_set:
                        contest_set.add(contest)
                        se.cids_b[bids_pi[i]] = available_contests[contest]
        else:
            # not sure what to do here if cvr_type_p[pbcid] == noCVR 
            pass 

    # Generate the selection for each contest (populate rv_cpb).
    # Draw from selids_c. 
    # Also keep track of ro_c.
    se.rv_cpb = dict()
    for cid in se.rel_cp:
        for pbcid in se.rel_cp[cid]:
            for bid in se.bids_p[pbcid]:
                selids = list(se.selids_c[cid])

                if se.contest_type_c[cid] == 'plurality':
                    # vote is a tuple of length 1 here
                    selection = se.SynRandomState.choice(selids)
                    vote = (selection,)
                    nested_set(se.rv_cpb, [cid, pbcid, bid], vote)

                else: # we can handle this later when its not hardcoded 
                    pass
                    

    # sum over ballot ids and pbcids to get se.ro_c
    rn_cv = dict() 
    for cid in se.cids:
        for pbcid in se.rel_cp[cid]:
            for bid in se.bids_p[pbcid]:
                vote = se.rv_cpb[cid][pbcid][bid]
                if cid not in rn_cv:
                    nested_set(rn_cv, [cid, vote], 1)
                else:
                    if vote not in rn_cv[cid]:
                        nested_set(rn_cv, [cid, vote], 1)
                    else:
                        rn_cv[cid][vote]+=1

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
        for vote in rn_cv[cid]:
            if cid not in se.rn_c:
                se.rn_c[cid]=rn_cv[cid][vote]
            else:
                se.rn_c[cid]+=rn_cv[cid][vote]

    # get rn_cpr
    se.rn_cpr = dict()
    for cid in se.rv_cpb:
        for pbcid in se.rv_cpb[cid]:
            for bid in se.rv_cpb[cid][pbcid]:
                vote = se.rv_cpb[cid][pbcid][bid]
                if cid in se.rn_cpr:
                    if pbcid in se.rn_cpr[cid]:
                        if vote in se.rn_cpr[cid][pbcid]:
                            se.rn_cpr[cid][pbcid][vote]+=1
                        else:
                            nested_set(se.rn_cpr,[cid,pbcid,vote], 1)
                    else:
                        nested_set(se.rn_cpr,[cid,pbcid,vote], 1)
                else:
                    nested_set(se.rn_cpr,[cid,pbcid,vote], 1)

    # sum over pbcids to get rn_cr
    se.rn_cr = dict()
    for cid in se.rn_cpr:
        for pbcid in se.rn_cpr[cid]:
            for vote in se.rn_cpr[cid][pbcid]:
                if cid in se.rn_cr:
                    if vote in se.rn_cr[cid]:
                        se.rn_cr[cid][vote]+=se.rn_cpr[cid][pbcid][vote]
                    else:
                        nested_set(se.rn_cr, [cid, vote], se.rn_cpr[cid][pbcid][vote])
                else:
                    nested_set(se.rn_cr, [cid, vote], se.rn_cpr[cid][pbcid][vote])

    se.ro_c = dict()
    for cid in rn_cv:
        outcome = max(rn_cv[cid], key=rn_cv[cid].get)
        se.ro_c[cid] = outcome

    # dropoff
    assert 0 < se.dropoff <= 1

    # error_rate
    assert 0 <= se.error_rate <= 1

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
    # se.comments_pb = {}
    for pbcid in se.pbcids:
        print(pbcid, se.bids_p[pbcid])
        for i, bid in enumerate(se.bids_p[pbcid]):
            nested_set(se.boxid_pb, [pbcid, bid], "box{}".format(1+((i+1)//se.box_size)))
            nested_set(se.position_pb, [pbcid, bid], 1+(i%se.box_size))
            nested_set(se.stamp_pb, [pbcid, bid], "{:06d}".format((i+1)*17))
            nested_set(se.comments_pb, [pbcid, bid], "")


def write_reported(se):

    write_21_reported_csv(se)
    write_22_ballot_manifests(se)
    write_23_reported_outcomes(se)


def write_21_reported_csv(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname,
                           "2-election", "21-reported-votes")
    os.makedirs(dirpath, exist_ok=True)

    scanner = "scanner1"
    for pbcid in se.pbcids:
        # handle cvr pbcids
        if se.cvr_type_p[pbcid]=="CVR": 
            filename = os.path.join(dirpath,
                                    "reported-cvrs-" + pbcid+".csv")
            with open(filename, "w") as file:
                fieldnames = ["Collection id", "Scanner", "Ballot id",
                              "Contest", "Selections"]
                file.write(",".join(fieldnames))
                file.write("\n")
                for bid in se.bids_p[pbcid]:
                    for cid in se.cids:
                        if pbcid in se.rel_cp[cid]:
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


def write_22_ballot_manifests(se):
                           
    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname,
                           "2-election", "22-ballot-manifests")
    os.makedirs(dirpath, exist_ok=True)

    for pbcid in se.pbcids:
        filename = os.path.join(dirpath, "manifest-"+pbcid+".csv")
        with open(filename, "w") as file:
            fieldnames = ["Collection id", "Box id", "Position",
                          "Stamp", "Ballot id", "Number of ballots",
                          "Comments"]
            file.write(",".join(fieldnames))
            file.write("\n")
            print(se.bids_p[pbcid])
            for bid in se.bids_p[pbcid]:
                file.write("{},".format(pbcid))
                file.write("{},".format(se.boxid_pb[pbcid][bid]))
                file.write("{},".format(se.position_pb[pbcid][bid]))
                file.write("{},".format(se.stamp_pb[pbcid][bid]))
                file.write("{},".format(bid))
                file.write("1") # number of ballots
                # no comments
                file.write("\n")


def write_23_reported_outcomes(se):

    pass

##############################################################################
## audit

##############################################################################
## Generate audit data

def generate_audit(se):

    # setup
    # generate 3/audit/31-setup/311-audit-seed.csv

    # 32-audit_orders
    # generate 3/audit/32-audit-orders

    # 33-audited_votes
    # generate 3/audit/33-audited-votes
    #   audited-votes-PBCID.csv

    # (audit stages will be generated by audit itself)

    pass


def generate_actual(se):
    se.av_cpb = dict()
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
                    nested_set(se.av_cpb, [cid, pbcid, bid], selection)

def write_audit(se):

    write_311_audit_seed(se)
    write_32_audit_orders(se)
    write_33_audited_votes(se)


def write_311_audit_seed(se):

    pass


def write_32_audit_orders(se):

    pass

def write_33_audited_votes(se):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "3-audit")
    os.makedirs(dirpath, exist_ok=True)
    for cid in se.av_cpb:
        for pbcid in se.av_cpb[cid]:
            filename = os.path.join(dirpath, "audited-votes-" + pbcid+".csv")
            with open(filename, "w") as file:
                fieldnames = ["Collection id", "Ballot id", "Contest", "Selections"]
                file.write(",".join(fieldnames))
                file.write("\n")
                for cid in se.av_cpb:
                    for pbcid_inner in se.av_cpb[cid]:
                        if pbcid_inner == pbcid:
                            for bid in se.av_cpb[cid][pbcid]:
                                selid = se.av_cpb[cid][pbcid][bid]
                                file.write("{},".format(pbcid))
                                file.write("{},".format(bid))
                                file.write("{},".format(cid))
                                file.write("{},".format(selid))
                                file.write("\n")



def test():

    se = SynElection()
    se.seed = 9
    generate_election_structure(se)
    generate_contests(se)
    generate_collections(se)
    generate_reported(se)
    generate_actual(se)
    generate_ballot_manifest(se)
    structure.finish_election_structure(se)

    for key in sorted(vars(se)):
        print(key)
        print("    ", vars(se)[key])

    print("Checking structure:", structure.check_election_structure(se))
    
    write_structure_csvs(se)
    write_reported(se)
    write_audit(se)

    # audit stages
    pass # TBD


if __name__=="__main__":

    test()
