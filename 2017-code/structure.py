# structure.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 7, 2017
# python3

"""
Routines to work with multi.py, to read in the
CSV files containing information about the "structure"
of an election:
   11-election-2017-09-08.csv
   12-contests-2017-09-08.csv
   14-collections-2017-09-08.csv
with structures represented by csv files of the form:

11-election.csv:
Attribute     , Value                                   
Election name , Colorado general election               
Election dirname , CO-2017-11-07,
Election date , 2017-11-07                              
Election URL  , https://sos.co.gov/election/2017-11-07/ 

12-contests.csv
Contest id      , Contest type , Winners   ,Write-ins  , Selections 
Denver Prop 1   , Plurality    , 1         , No        , Yes        , No  
Denver Prop 2   , Plurality    , 1         , No        , Yes        , No   
Denver Mayor    , Plurality    , 1         , Qualified , John Smith , Bob Cat   , Mary Mee   ,+Jack Frost 
Denver Clerk    , Plurality    , 1         , No        , Yet Again  , New Guy
Logan Mayor     , Plurality    , 1         , Arbitrary , Susan Hat  , Barry Su  , Benton Liu 
Logan Water     , Plurality    , 1         , No        , Yes        , No
U.S. President  , Plurality    , 1         , Arbitrary , Don Brown  , Larry Pew
U.S. Senate 1   , Plurality    , 1         , Qualified , Deb O'Crat , Rhee Pub  , Val Green  , Sarah Day   , +Tom Cruz 
U.S. Senate 2   , Plurality    , 1         , Qualified , Term Three , Old Guy   , +Hot Stuff
CO Prop A       , Plurality    , 1         , No        , Yes        , No

13-contest-groups.csv
Contest group id ,Contest or group id(s)
FEDERAL          ,U.S. President   ,U.S. Senate 1        ,U.S. Senate 2
STATE            ,CO Prop A
FED STATE        ,FEDERAL          ,STATE
DENVER LOCAL     ,Denver Mayor     ,Denver Clerk, Denver Prop 1, Denver Prop 2
DENVER           ,FED STATE        ,DENVER LOCAL
LOGAN REQ        ,FED STATE        ,Logan Mayor 
LOGAN POSS       ,Logan Water

14-collections.csv
Collection id , Manager          , CVR type  , Required Contests, Possible Contests
DEN-A01       , abe@co.gov       , CVR       , DENVER,            DENVER
DEN-A02       , bob@co.gov       , CVR       , DENVER,            DENVER
LOG-B13       , carol@co.gov     , noCVR     , LOGAN REQ,         LOGAN POSS

The values are sanity checked, and put into the Election data structure (e)
from multi.py
"""

import os

import multi
import csv_readers
import groups
import utils


def read_election_structure(e, election_dirname):
    """ 
    Read file 1-structure/11-election.csv, put results into Election e.
    election_dirname is the name of the directory for the election 
        (e.g. "CO-2017-11") with ELECTIONS_ROOT
    """
    
    election_pathname = os.path.join(multi.ELECTIONS_ROOT, election_dirname)
    structure_pathname = os.path.join(election_pathname, "1-structure")
    filename = utils.greatest_name(structure_pathname, "11-election", ".csv")
    file_pathname = os.path.join(structure_pathname, filename)
    fieldnames = ["Attribute", "Value"]
    rows = csv_readers.read_csv_file(file_pathname, fieldnames)
    for row in rows:
        if "Election name" == row["Attribute"]:
            e.election_name = row["Value"]
        elif "Election dirname" == row["Attribute"]:
            e.election_dirname = row["Value"]
        elif "Election date" == row["Attribute"]:
            e.election_date = row["Value"]
        elif "Election URL" == row["Attribute"]:
            e.election_url = row["Value"]
    for attribute in ["election_name", "election_dirname",
                      "election_date", "election_url"]:
        if attribute not in vars(e):
            utils.mywarning("Attribute {} not present in 11-election.csv."
                            .format(attribute))
    if utils.warnings_given > 0:
        utils.myerror("Too many errors; terminating.")


def test_read_election_structure(e):        

    print("test_read_election_structure")
    read_election_structure(e, "ex1")


def read_contests(e):
    """
    Read file 12-contests.csv, put results into Election e.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname, "1-structure")
    filename = utils.greatest_name(structure_pathname, "12-contests", ".csv")
    file_pathname = os.path.join(structure_pathname, filename)
    fieldnames = ["Contest id", "Contest type", "Winners", "Write-ins",
                  "Selections"]
    rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=True)
    for row in rows:

        cid = row["Contest id"]
        
        e.cids.append(cid)
        
        e.contest_type_c[cid] = row["Contest type"].lower()
        
        e.winners_c[cid] = int(row["Winners"])
        
        e.write_ins_c[cid] = row["Write-ins"].lower()

        e.selids_c[cid] = {}
        for selid in row["Selections"]:
            e.selids_c[cid][selid] = True


def test_read_contests(e):

    print("test_read_contests")
    read_election_structure(e, "ex1/")
    read_contests(e)


def read_contest_groups(e):
    """
    Read file 13-contest-groups.csv, put results into Election e.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname, "1-structure")
    filename = utils.greatest_name(structure_pathname, "13-contest-groups", ".csv")
    file_pathname = os.path.join(structure_pathname, filename)
    fieldnames = ["Contest group id", "Contest or group id(s)"]
    rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=True)
    for row in rows:

        gid = row["Contest group id"]
        e.gids.append(gid)
        
        e.cgids_g[gid] = row["Contest or group id(s)"]


def test_read_contest_groups(e):    

    print("test_read_contest_groups")
    read_contest_groups(e)
    pass


def read_collections(e):
    """
    Read file 14-collections.csv, put results into Election e.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname, "1-structure")
    filename = utils.greatest_name(structure_pathname, "14-collections", ".csv")
    file_pathname = os.path.join(structure_pathname, filename)
    fieldnames = ["Collection id", "Manager", "CVR type",
                  "Required Contests", "Possible Contests"]
    rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=False)
    for row in rows:

        pbcid = row["Collection id"]
        e.pbcids.append(pbcid)
        e.manager_p[pbcid] = row["Manager"]
        e.cvr_type_p[pbcid] = row["CVR type"]
        e.required_gid_p[pbcid] = row["Required Contests"]
        e.possible_gid_p[pbcid] = row["Possible Contests"]


def test_read_collections(e):

    print("test_read_collections")
    read_collections(e)


def get_election_structure(e):

    read_election_structure(e, e.election_dirname)
    read_contests(e)
    read_contest_groups(e)
    read_collections(e)
    finish_election_structure(e)
    check_election_structure(e)
    show_election_structure(e)


def finish_election_structure(e):

    finish_election_structure_groups(e)
    finish_election_structure_votes(e)

    
def finish_election_structure_groups(e):

    groups.expand_contest_group_defs(e)

    for pbcid in e.pbcids:
        e.possible_cid_p[pbcid] = {}
        e.required_cid_p[pbcid] = {}
    for cid in e.cids:
        e.possible_pbcid_c[cid] = {}
        e.required_pbcid_c[cid] = {}

    for pbcid in e.pbcids:
        req_gid = e.required_gid_p[pbcid]
        poss_gid = e.possible_gid_p[pbcid]
        for cid in e.cids:
            # "" req_gid means nothing is required.
            if req_gid!="" and cid in e.cids_g[req_gid]:
                utils.nested_set(e.required_cid_p, [pbcid, cid], "True")
                utils.nested_set(e.required_pbcid_c, [cid, pbcid], "True")
            # enforce that possible contests includes all contests
            # "" poss_gid means everything is possible
            if poss_gid=="" or cid in e.cids_g[poss_gid] or cid in e.cids_g[req_gid]:
                utils.nested_set(e.possible_cid_p, [pbcid, cid], "True")
                utils.nested_set(e.possible_pbcid_c, [cid, pbcid], "True")


def finish_election_structure_votes(e):

    noCVRvote = ("-noCVR",)
    for cid in e.cids:
        e.votes_c[cid] = {}
        for selid in e.selids_c[cid]:
            e.votes_c[cid][(selid,)] = True
    for pbcid in e.pbcids:
        if e.cvr_type_p[pbcid] == "noCVR":
            for cid in e.required_cid_p[pbcid]:
                e.votes_c[cid][noCVRvote] = True            


def check_id(id, check_for_whitespace=False):

    if not isinstance(id, str) or not id.isprintable():
        utils.mywarning("id is not string or is not printable: {}".format(id))
    if check_for_whitespace:
        for c in id:
            if c.isspace():
                utils.mywarning("id `id` contains whitespace.")
                break


def check_election_structure(e):

    if not isinstance(e.cids, (list, tuple, set)):
        utils.myerror("e.cids is not a set.")
    if len(e.cids) == 0:
        utils.myerror("e.cids is an empty list of contests.")
    for cid in e.cids:
        check_id(cid)

    if not isinstance(e.pbcids, (list, tuple)):
        utils.myerror("e.pbcids is not a list or a tuple.")
    if len(e.pbcids) == 0:
        utils.myerror("e.pbcids is an empty list of pbcids.")
    for pbcid in e.pbcids:
        check_id(pbcid)

    for cid in e.selids_c:
        if cid not in e.cids:
            utils.myerror("e.selids_c has a key `{}` not in e.cids.".format(cid))
        for selid in e.selids_c[cid]:
            check_id(selid)
    for cid in e.cids:
        if cid not in e.selids_c:
            utils.mywarning("cid `{}` should be key in e.selids_c".format(cid))

    if not isinstance(e.cvr_type_p, dict):
        utils.myerror("e_cvr_type is not a dict.")
    for pbcid in e.cvr_type_p:
        if pbcid not in e.pbcids:
            utils.mywarning("pbcid `{}` is not in e.pbcids".format(pbcid))
        if e.cvr_type_p[pbcid] not in ["CVR", "noCVR"]:
            utils.mywarning("e.cvr_type_p[{}]==`{}` is not CVR or noCVR"
                      .format(pbcid, e.cvr_type_p[pbcid]))
    for pbcid in e.pbcids:
        if pbcid not in e.cvr_type_p:
            utils.mywarning("pbcid `{}` not key in e.cvr_type_p."
                      .format(pbcid))

    if utils.warnings_given > 0:
        utils.myerror("structure.check_election_structure: Too many errors or warnings; terminating.")


def show_election_structure(e):
    utils.myprint("====== Election structure ======")
    utils.myprint("Election name: (e.election_name):")
    utils.myprint("    {}".format(e.election_name))
    utils.myprint("Election dirname (e.election_dirname):")
    utils.myprint("    {}".format(e.election_dirname))
    utils.myprint("Election date (e.election date):")
    utils.myprint("    {}".format(e.election_date))
    utils.myprint("Election URL (e.election_url):")
    utils.myprint("    {}".format(e.election_url))
    utils.myprint("Number of contests:")
    utils.myprint("    {}".format(len(e.cids)))
    utils.myprint("Contest ids with contest type, number of winners, and write-ins mode")
    utils.myprint("(e.cids, e.contest_type_c, e.winners_c, e.write_ins_c):")
    for cid in e.cids:
        utils.myprint("    {} ({}, {} winner(s), {} write-ins)"
                      .format(cid, e.contest_type_c[cid], e.winners_c[cid], e.write_ins_c[cid]))
    utils.myprint("Valid selection ids for each cid (e.selids_c):")
    for cid in e.cids:
        utils.myprint("    {}: ".format(cid), end='')
        utils.myprint(", ".join(sorted(e.selids_c[cid])))
    utils.myprint("Number of paper ballot collections:")
    utils.myprint("    {}".format(len(e.pbcids)))
    utils.myprint("Paper ballot collection ids (e.pbcids), CVR types (e.cvr_type_p), and managers (e.manager_p):")
    for pbcid in sorted(e.pbcids):
        utils.myprint("    {} ({}, Manager:{})"
                      .format(pbcid, e.cvr_type_p[pbcid], e.manager_p[pbcid]))
    utils.myprint("Required pbcids for each cid (e.required_pbcid_c):")
    for cid in e.cids:
        utils.myprint("    {}: ".format(cid), end='')
        utils.myprint(", ".join(sorted(e.required_pbcid_c[cid])))
    utils.myprint("Possible pbcids for each cid (e.possible_pbcid_c):")
    for cid in e.cids:
        utils.myprint("    {}: ".format(cid), end='')
        utils.myprint(", ".join(sorted(e.possible_pbcid_c[cid])))



def test():
    
    e = multi.Election()
    test_read_election_structure(e)
    test_read_contests(e)
    test_read_contest_groups(e)
    test_read_collections(e)    


if __name__=="__main__":

    test()
