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
   13-collections-2017-09-08.csv
with structures represented by csv files of the form:

11-election.csv:
Attribute     , Value                                   
Election name , Colorado general election               
Election dirname , CO-2017-11-07,
Election date , 2017-11-07                              
Election URL  , https://sos.co.gov/election/2017-11-07/ 

12-contests.csv
Contest id      , Contest type , Winners   ,Write-ins  , Selections 
DEN-prop-1      , Plurality    , 1         , No        , Yes        , No
DEN-prop-2      , Plurality    , 1         , No        , Yes        , No
DEN-mayor       , Plurality    , 1         , Qualified , John Smith , Bob Cat   , Mary Mee   ,+Jack Frost
LOG-mayor       , Plurality    , 1         , Arbitrary , Susan Hat  , Barry Su  , Benton Liu 
US-Senate-1     , Plurality    , 1         , Qualified , Deb O'Crat , Rhee Pub  , Val Green  , Sarah Day   , +Tom Cruz
Boulder-clerk   , IRV          , 1         , Arbitrary , Rock Ohn   , Peh Bull  , Roll Stone
Boulder-council , Plurality    , 4         , No        , Dave Diddle, Ben Borg  , Sue Mee    , Fan Tacy    , Jill Snead

13-collections.csv
Collection id , Manager          , CVR type  , Contests 
DEN-A01       , abe@co.gov       , CVR       , DEN-prop-1 , DEN-prop-2 , US-Senate-1
DEN-A02       , bob@co.gov       , CVR       , DEN-prop-1 , DEN-prop-2 , US-Senate-1
LOG-B13       , carol@co.gov     , noCVR     , LOG-mayor  , US-Senate-1

The values are sanity checked, and put into the Election data structure (e)
from multi.py
"""

import os

import multi
import csv_readers
import utils


def read_election(e, election_dirname):
    """ 
    Read file 1-structure/11-election.csv, put results into Election e.
    election_dirname is the name of the directory for the election 
        (e.g. "./elections/CO-2017-11")
    """
    
    structure_dirname = os.path.join(election_dirname, "1-structure")
    filename = utils.greatest_name(structure_dirname, "11-election", ".csv")
    full_filename = os.path.join(structure_dirname, filename)
    rows = csv_readers.read_csv_file(full_filename)
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


def test_read_election(e):        

    print("test_read_election")
    read_election(e, "./elections/v2-ex1")


def read_contests(e):
    """
    Read file 12-contests.csv, put results into Election e.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname, "1-structure")
    filename = utils.greatest_name(structure_pathname, "12-contests", ".csv")
    file_pathname = os.path.join(structure_pathname, filename)
    rows = csv_readers.read_csv_file(file_pathname, varlen=True)
    for row in rows:

        cid = row["Contest id"]
        
        e.cids.append(cid)
        
        e.contest_type_c[cid] = row["Contest type"].lower()
        
        e.winners_c[cid] = int(row["Winners"])
        
        e.write_ins_c[cid] = row["Write-ins"].lower()

        e.selids_c[cid] = {}
        for selid in row["Selections"]:
            e.selids_c[cid][selid] = True

        e.rel_cp[cid] = {}


def test_read_contests(e):

    print("test_read_contests")
    read_election(e, "./elections/v2-ex1/")
    read_contests(e)


def read_collections(e):
    """
    Read file 13-collections.csv, put results into Election e.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname, "1-structure")
    filename = utils.greatest_name(structure_pathname, "13-collections", ".csv")
    file_pathname = os.path.join(structure_pathname, filename)
    rows = csv_readers.read_csv_file(file_pathname, varlen=True)
    for row in rows:

        pbcid = row["Collection id"]
        e.pbcids.append(pbcid)
        e.manager_p[pbcid] = row["Manager"]
        e.cvr_type_p[pbcid] = row["CVR type"]
        for cid in row["Contests"]:
            if cid not in e.rel_cp:
                e.rel_cp[cid] = {}
            e.rel_cp[cid][pbcid] = True
    

def test_read_collections(e):

    print("test_read_collections")
    read_collections(e)


def get_election_structure(e):

    # load_part_from_json(e, "structure.js")
    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    read_election(e, election_pathname)
    read_contests(e)
    read_collections(e)
    finish_election_structure(e)
    check_election_structure(e)
    show_election_structure(e)


def finish_election_structure(e):

    noCVRvote = ("-noCVR",)

    for cid in e.cids:
        e.votes_c[cid] = {}
        for selid in e.selids_c[cid]:
            e.votes_c[cid][(selid,)] = True
        for pbcid in e.rel_cp[cid]:
            if e.cvr_type_p[pbcid] == "noCVR":
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

    if not isinstance(e.cids, (list, tuple)):
        utils.myerror("e.cids is not a list or a tuple.")
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

    if not isinstance(e.rel_cp, dict):
        utils.myerror("e.rel_cp is not a dict.")
    for cid in e.rel_cp:
        if cid not in e.cids:
            utils.mywarning("cid is not in e.cids: {}".format(cid))
        for pbcid in e.rel_cp[cid]:
            if pbcid not in e.pbcids:
                utils.mywarning("pbcid is not in e.pbcids: {}".format(pbcid))
            if e.rel_cp[cid][pbcid] != True:
                utils.mywarning("e.rel_cp[{}][{}] != True.".format(
                    cid, pbcid, e.rel_cp[cid][pbcid]))

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
        utils.myerror("Too many errors; terminating.")


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
    utils.myprint("Contest ids with contest type, number of winners, and write-ins mode (e.cids, e.contest_type_c, e.winners_c, e.write_ins_c):")
    for cid in e.cids:
        utils.myprint("   {} ({}, {} winner(s), write-ins: {})"
                      .format(cid, e.contest_type_c[cid], e.winners_c[cid], e.write_ins_c[cid]))
    utils.myprint("Number of paper ballot collections:")
    utils.myprint("    {}".format(len(e.pbcids)))
    utils.myprint("Paper ballot collection ids (e.pbcids):")
    for pbcid in sorted(e.pbcids):
        utils.myprint("   ", pbcid)
    utils.myprint("CVR type (either CVR or noCVR) for each pbcid (e.cvr_type_p):")
    for pbcid in sorted(e.pbcids):
        utils.myprint("    {}: {} ".format(pbcid, e.cvr_type_p[pbcid]))
    utils.myprint("Possible pbcids for each cid (e.rel_cp):")
    for cid in e.cids:
        utils.myprint("    {}: ".format(cid), end='')
        for pbcid in sorted(e.rel_cp[cid]):
            utils.myprint(pbcid, end=', ')
        utils.myprint()
    utils.myprint("Valid selection ids for each cid (e.selids_c):")
    for cid in e.cids:
        utils.myprint("    {}: ".format(cid), end='')
        for selid in sorted(e.selids_c[cid]):
            utils.myprint(selid, end=', ')
        utils.myprint()


if __name__=="__main__":
    e = multi.Election()
    test_read_election(e)
    test_read_contests(e)
    test_read_collections(e)
