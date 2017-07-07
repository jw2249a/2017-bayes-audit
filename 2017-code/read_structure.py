# read-structure.py
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
with structures of the form:

11-election.csv:
Attribute     , Value                                   
Election name , Colorado general election               
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


def read_election(e, election_dirname):
    """ 
    Read file 1-structure/11-election.csv, put results into Election e.
    election_dirname is the name of the directory for the election 
        (e.g. "./elections/CO-2017-11")
    """
    
    structure_dirname = os.path.join(election_dirname, "1-structure")
    filename = multi.greatest_name(structure_dirname, "11-election", ".csv")
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
            multi.mywarning("Attribute {} not present in 11-election.csv."
                            .format(attribute))
    if multi.warnings_given > 0:
        multi.myerror("Too many errors; terminating.")


def test_read_election(e):        

    print("test_read_election")
    read_election(e, "./elections/v2-ex1")


def read_contests(e):
    """
    Read file 12-contests.csv, put results into Election e.
    """

    election_dirname = e.election_dirname
    structure_dirname = os.path.join(election_dirname, "1-structure")
    filename = multi.greatest_name(structure_dirname, "12-contests", ".csv")
    full_filename = os.path.join(structure_dirname, filename)
    rows = csv_readers.read_csv_file(full_filename, varlen=True)
    for row in rows:

        cid = row["Contest id"]
        
        e.cids.append(cid)
        
        e.contest_type[cid] = row["Contest type"].lower()
        
        e.winners[cid] = int(row["Winners"])
        
        e.write_ins = row["Write-ins"]

        e.selids_c[cid] = row["Selections"]

        print(row)

def test_read_contests(e):

    print("test_read_contests")
    read_election(e, "./elections/v2-ex1/")
    read_contests(e)


def read_collections(e):
    """
    Read file 13-collections.csv, put results into Election e.
    """

    election_dirname = e.election_dirname
    structure_dirname = os.path.join(election_dirname, "1-structure")
    filename = multi.greatest_name(structure_dirname, "13-collections", ".csv")
    full_filename = os.path.join(structure_dirname, filename)
    rows = csv_readers.read_csv_file(full_filename, varlen=True)
    for row in rows:

        pbcid = row["Collection id"]
        e.pbcids.append(pbcid)
        e.manager_p[pbcid] = row["Manager"]
        e.cvr_type_p[pbcid] = row["CVR type"]
        for cid in row["Contests"]:
            if cid not in e.rel_cp:
                e.rel_cp[cid] = {}
            e.rel_cp[cid][pbcid] = True
        print(row)
    

def test_read_collections(e):

    print("test_read_collections")
    read_collections(e)


if __name__=="__main__":
    e = multi.Election()
    test_read_election(e)
    test_read_contests(e)
    test_read_collections(e)
