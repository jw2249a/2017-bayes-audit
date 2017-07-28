# reported.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 24, 2017
# python3

"""
Code that works with multi.py for post-election audit support.
This code reads and checks the "reported" results: votes
and reported outcomes.

The directory format is illustrated by this example from
README.md:

    2-election
       21-ballot-manifests
          manifest-DEN-A01-2017-11-07.csv
          manifest-DEN-A01-2017-11-07.csv
          manifest-LOG-B13-2017-11-07.csv
       22-reported-votes
          reported-cvrs-DEN-A01-2017-11-07.csv
          reported-cvrs-DEN-A02-2017-11-07.csv
          reported-cvrs-LOG-B13-2017-11-07.csv
       23-reported-outcomes-2017-11-07.csv

The 2-election directory is a subdirectory of the main
directory for the election.

There are three file types here:
   ballot-manifests
   reported-cvrs
   reported-outcomes

Here is an example of a ballot-manifests file, from the README.md file:

Collection id , Original index , Ballot id , Location       
LOG-B13       , 1              , B-0001    , Box 001 no 0001
LOG-B13       , 2              , B-0002    , Box 001 no 0002
LOG-B13       , 3              , B-0003    , Box 001 no 0003
LOG-B13       , 4              , B-0004    , Box 001 no 0004
LOG-B13       , 5              , C-0001    , Box 002 no 0001

Here is an example of a reported-cvrs file, from
the README.md file:

Collection id   , Source , Ballot id   , Contest     , Selections
DEN-A01         , L      , B-231       , DEN-prop-1  , Yes       
DEN-A01         , L      , B-231       , DEN-prop-2  
DEN-A01         , L      , B-231       , US-Senate-1 , Rhee Pub       , Sarah Day
DEN-A01         , L      , B-777       , DEN-prop-1  , No            
DEN-A01         , L      , B-777       , DEN-prop-2  , Yes           
DEN-A01         , L      , B-777       , US-Senate-1 , +Tom Cruz     
DEN-A01         , L      , B-888       , US-Senate-1 , -Invalid      

If the collection is noCVR, then the format is slightly different:

Collection id   , Source , Tally       , Contest     , Selections 
LOG-B13         , L      , 2034        , LOG-mayor   , Susan Hat  
LOG-B13         , L      , 1156        , LOG-mayor   , Barry Su   
LOG-B13         , L      , 987         , LOG-mayor   , Benton Liu 
LOG-B13         , L      , 3           , LOG-mayor   , -Invalid   
LOG-B13         , L      , 1           , LOG-mayor   , +Lizard People
LOG-B13         , L      , 3314        , US-Senate-1 , Rhee Pub      
LOG-B13         , L      , 542         , US-Senate-1 , Deb O'Crat    
LOG-B13         , L      , 216         , US-Senate-1 , Val Green     
LOG-B13         , L      , 99          , US-Senate-1 , Sarah Day     
LOG-B13         , L      , 9           , US-Senate-1 , +Tom Cruz     
LOG-B13         , L      , 1           , US-Senate-1 , -Invalid      


Here is an example of a reported outcomes file, from the README.md file:

Contest id      , Winner(s)
DEN-prop-1      , Yes      
DEN-mayor       , John Smith 
Boulder-council , Dave Diddle, Ben Borg   , Sue Mee   , Jill Snead

"""


import os


import multi
import csv_readers
import ids
import utils



##############################################################################
# Election data I/O and validation (stuff that depends on cast votes)
##############################################################################


def get_election_data(e):

    # next line needs to be replaced!
    # load_part_from_json(e, "data.js")

    read_ballot_manifests(e)
    read_reported_votes(e)
    read_reported_outcomes(e)
    
    for cid in e.rn_cpr:
        unpack_json_keys(e.syn_rn_cr[cid])
        for pbcid in e.rn_cpr[cid]:
            unpack_json_keys(e.rn_cpr[cid][pbcid])

    finish_election_data(e)
    check_election_data(e)
    show_election_data(e)


def read_ballot_manifests(e):
    """
    Read ballot manifest file 21-ballot-manifests and expand rows if needed.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname,
                                      "2-election","21-ballot-manifests")
    fieldnames = ["Collection id", "Box id", "Position", "Stamp", 
                  "Ballot id", "Number of ballots",
                  "Required Contests", "Possible Contests", "Comments"]
    for pbcid in e.pbcids:
        safe_pbcid = ids.filename_safe(pbcid)
        filename = utils.greatest_name(structure_pathname,
                                       "manifest-" + safe_pbcid,
                                       ".csv")
        file_pathname = os.path.join(structure_pathname, filename)
        rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=False)
        for row in rows:
            pbcid = row["Collection id"]
            boxid = row["Box id"]
            position = row["Position"]
            stamp = row["Stamp"]
            bid = row["Ballot id"]
            try:
                num = int(row["Number of ballots"])
            except ValueError:
                utils.myerror("Number {} of ballots not an integer.".format(num))
            if num<=0:
                utils.mywarning("Number {} of ballots not positive.".format(num))
            req = row["Required Contests"]
            poss = row["Possible Contests"]
            comments = row["Comments"]

            bids = utils.count_on(bid, num)
            stamps = utils.count_on(stamp, num)
            positions = utils.count_on(position, num)

            for i in range(num):
                utils.nested_set(e.bids_p, [pbcid, bids[i]], True)
                utils.nested_set(e.boxid_pb, [pbcid, bids[i]], boxid)
                utils.nested_set(e.position_pb, [pbcid, bids[i]], position[i])
                utils.nested_set(e.stamp_pb, [pbcid, bids[i]], stamp[i])
                utils.nested_set(e.required_gid_pb, [pbcid, bids[i]], req)
                utils.nested_set(e.possible_gid_pb, [pbcid, bids[i]], poss)
                utils.nested_set(e.comments_pb, [pbcid, bids[i]], comments)
                          

def read_reported_votes(e):
    """
    Read reported votes 22-reported-votes/reported-cvrs-PBCID.csv.
    """

    election_pathname = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    structure_pathname = os.path.join(election_pathname,
                                      "2-election","22-reported-votes")
    fieldnames = ["Collection id", "Scanner", "Ballot id",
                  "Contest", "Selections"]
    for pbcid in e.pbcids:
        safe_pbcid = ids.filename_safe(pbcid)
        filename = utils.greatest_name(structure_pathname,
                                       "reported-cvrs-" + safe_pbcid,
                                       ".csv")
        file_pathname = os.path.join(structure_pathname, filename)
        rows = csv_readers.read_csv_file(file_pathname, fieldnames, varlen=True)
        for row in rows:
            pbcid = row["Collection id"]
            scanner = row["Scanner"]
            bid = row["Ballot id"]
            cid = row["Contest"]
            vote = row["Selections"]
            utils.nested_set(e.rv_cpb, [cid, pbcid, bid], vote)
            utils.nested_set(e.votes_c, [cid, vote], True)


def read_reported_outcomes(e):

    pass


def finish_election_data(e):
    """ 
    Compute election data attributes that are derivative from others. 
    or that need conversion (e.g. strings-->tuples from json keys).
    """

    # make sure e.selids_c[cid] contains all +/- selids seen in reported votes
    # and that e.votes_c[cid] contains all reported votes
    for cid in e.cids:
        for pbcid in e.possible_pbcid_c[cid]:
            print("***", cid, e.possible_pbcid_c[cid])
            for bid in e.bids_p[pbcid]:
                print(cid, pbcid, bid, e.rv_cpb)
                if bid in e.rv_cpb[cid][pbcid]:
                    rv = e.rv_cpb[cid][pbcid][bid]
                else:
                    rv = ("-NoSuchContest",)
                utils.nested_set(e.votes_c, [cid, rv], True)
                for selid in rv:
                    if ids.is_writein(selid) or ids.is_error_selid(selid):
                        e.selids_c[cid][selid] = True

    # set e.rn_cpr[cid][pbcid][r] to number in pbcid with reported vote rv:
    for cid in e.cids:
        e.rn_cpr[cid] = {}
        for pbcid in e.possible_pbcid_c[cid]:
            e.rn_cpr[cid][pbcid] = {}
            for rv in e.votes_c[cid]:
                e.rn_cpr[cid][pbcid][rv] = len([bid for bid in e.bids_p[pbcid]
                                                if bid in e.rv_cpb[cid][pbcid] and \
                                                e.rv_cpb[cid][pbcid][bid] == rv])

    # e.rn_c[cid] is number of reported votes cast in contest cid
    for cid in e.cids:
        e.rn_c[cid] = sum([e.rn_cpr[cid][pbcid][vote]
                           for pbcid in e.rn_cpr[cid]
                           for vote in e.votes_c[cid]])

    # e.rn_p[pbcid] is number of reported votes cast in collection pbcid
    for pbcid in e.pbcids:
        e.rn_p[pbcid] = sum([e.rn_cpr[cid][pbcid][rv]
                             for cid in e.rn_cpr
                             for rv in e.votes_c[cid]])        

    # e.rn_cr[cid][vote] is reported number cast for vote in cid
    for cid in e.cids:
        e.rn_cr[cid] = {}
        for pbcid in e.rn_cpr[cid]:
            for vote in e.votes_c[cid]:
                if rv not in e.rn_cr[cid]:
                    e.rn_cr[cid][rv] = 0
                if vote not in e.rn_cpr[cid][pbcid]:
                    e.rn_cpr[cid][pbcid][rv] = 0
                e.rn_cr[cid][rv] += e.rn_cpr[cid][pbcid][rv]


def check_election_data(e):

    if not isinstance(e.rn_cpr, dict):
        utils.myerror("e.rn_cpr is not a dict.")
    for cid in e.rn_cpr:
        if cid not in e.cids:
            utils.mywarning("cid `{}` not in e.cids.".format(cid))
        for pbcid in e.rn_cpr[cid]:
            if pbcid not in e.pbcids:
                utils.mywarning("pbcid `{}` is not in e.pbcids.".format(pbcid))
            for rv in e.rn_cpr[cid][pbcid]:
                for selid in rv:
                    if selid not in e.selids_c[cid] and selid[0].isalnum():
                        utils.mywarning(
                            "selid `{}` is not in e.selids_c[{}]."
                            .format(selid, cid))
                if not isinstance(e.rn_cpr[cid][pbcid][rv], int):
                    utils.mywarning("value `e.rn_cpr[{}][{}][{}] = `{}` is not an integer."
                              .format(cid, pbcid, rv, e.rn_cpr[cid][pbcid][rv]))
                if not (0 <= e.rn_cpr[cid][pbcid][rv] <= e.rn_p[pbcid]):
                    utils.mywarning("value `e.rn_cpr[{}][{}][{}] = `{}` is out of range 0:{}."
                              .format(cid, pbcid, rv, e.rn_cpr[cid][pbcid][vote],
                                      e.rn_p[pbcid]))
                if e.rn_cr[cid][rv] != \
                        sum([e.rn_cpr[cid][pbcid][rv]]):
                    for pbcid in e.possible_pbcid_c[cid]:
                        utils.mywarning("sum of e.rn_cpr[{}][*][{}] is not e.rn_cr[{}][{}]."
                              .format(cid, rv, cid, rv))
    for cid in e.cids:
        if cid not in e.rn_cpr:
            utils.mywarning("cid `{}` is not a key for e.rn_cpr".format(cid))
        for pbcid in e.possible_pbcid_c[cid]:
            if pbcid not in e.rn_cpr[cid]:
                utils.mywarning(
                    "pbcid {} is not a key for e.rn_cpr[{}].".format(pbcid, cid))
            # for selid in e.selids_c[cid]:
            #     assert selid in e.rn_cpr[cid][pbcid], (cid, pbcid, selid)
            # ## not necessary, since missing selids have assumed count of 0

    if not isinstance(e.rn_c, dict):
        utils.myerror("e.rn_c is not a dict.")
    for cid in e.rn_c:
        if cid not in e.cids:
            utils.mywarning("e.rn_c key `{}` is not in e.cids.".format(cid))
        if not isinstance(e.rn_c[cid], int):
            utils.mywarning("e.rn_c[{}] = {}  is not an integer.".format(
                cid, e.rn_c[cid]))
    for cid in e.cids:
        if cid not in e.rn_c:
            utils.mywarning("cid `{}` is not a key for e.rn_c".format(cid))

    if not isinstance(e.rn_cr, dict):
        utils.myerror("e.rn_cr is not a dict.")
    for cid in e.rn_cr:
        if cid not in e.cids:
            utils.mywarning("e.rn_cr key cid `{}` is not in e.cids".format(cid))
        for vote in e.rn_cr[cid]:
            for selid in vote:
                if (not ids.is_writein(selid) and not ids.is_error_selid(selid)) \
                   and not selid in e.selids_c[cid]:
                    utils.mywarning("e.rn_cr[{}] key `{}` is not in e.selids_c[{}]"
                              .format(cid, selid, cid))
            if not isinstance(e.rn_cr[cid][vote], int):
                utils.mywarning("e.rn_cr[{}][{}] = {} is not an integer."
                          .format(cid, vote, e.rn_cr[cid][vote]))
    for cid in e.cids:
        if cid not in e.rn_cr:
            utils.mywarning("cid `{}` is not a key for e.rn_cr".format(cid))

    if not isinstance(e.bids_p, dict):
        utils.myerror("e.bids_p is not a dict.")
    for pbcid in e.pbcids:
        if not isinstance(e.bids_p[pbcid], list):
            utils.myerror("e.bids_p[{}] is not a list.".format(pbcid))

    if not isinstance(e.av_cpb, dict):
        utils.myerror("e.av_cpb is not a dict.")
    for cid in e.av_cpb:
        if cid not in e.cids:
            utils.mywarning("e.av_cpb key {} is not in e.cids.".format(cid))
        for pbcid in e.av_cpb[cid]:
            if pbcid not in e.pbcids:
                utils.mywarning("e.av_cpb[{}] key `{}` is not in e.pbcids"
                          .format(cid, pbcid))
            if not isinstance(e.av_cpb[cid][pbcid], dict):
                utils.myerror("e.av_cpb[{}][{}] is not a dict.".format(cid, pbcid))
            bidsset = set(e.bids_p[pbcid])
            for bid in e.av_cpb[cid][pbcid]:
                if bid not in bidsset:
                    utils.mywarning("bid `{}` from e.av_cpb[{}][{}] is not in e.bids_p[{}]."
                              .format(bid, cid, pbcid, pbcid))

    for cid in e.cids:
        if cid not in e.av_cpb:
            utils.mywarning("cid `{}` is not a key for e.av_cpb.".format(cid))
        for pbcid in e.possible_pbcid_c[cid]:
            if pbcid not in e.av_cpb[cid]:
                utils.mywarning("pbcid `{}` is not in e.av_cpb[{}]."
                          .format(pbcid, cid))

    if not isinstance(e.rv_cpb, dict):
        utils.myerror("e.rv_cpb is not a dict.")
    for cid in e.rv_cpb:
        if cid not in e.cids:
            utils.mywarning("e.rv_cpb key `{}` is not in e.cids.".format(cid))
        for pbcid in e.rv_cpb[cid]:
            if pbcid not in e.pbcids:
                utils.mywarning("e.rv_cpb[{}] key `{}` is not in e.pbcids."
                          .format(cid, pbcid))
            if not isinstance(e.rv_cpb[cid][pbcid], dict):
                utils.myerror("e.rv_cpb[{}][{}] is not a dict.".format(cid, pbcid))
            bidsset = set(e.bids_p[pbcid])
            for bid in e.rv_cpb[cid][pbcid]:
                if bid not in bidsset:
                    utils.mywarning("bid `{}` from e.rv_cpb[{}][{}] is not in e.bids_p[{}]."
                              .format(bid, cid, pbcid, pbcid))
    for cid in e.cids:
        if cid not in e.rv_cpb:
            utils.mywarning("cid `{}` is not a key in e.rv_cpb.".format(cid))
        for pbcid in e.possible_pbcid_c[cid]:
            if pbcid not in e.rv_cpb[cid]:
                utils.mywarning("pbcid `{}` from e.possible_pbcid_c[{}] is not a key for e.rv_cpb[{}]."
                          .format(pbcid, cid, cid))

    if not isinstance(e.ro_c, dict):
        utils.myerror("e.ro_c is not a dict.")
    for cid in e.ro_c:
        if cid not in e.cids:
            utils.mywarning("cid `{}` from e.rv_cpb is not in e.cids".format(cid))
    for cid in e.cids:
        if cid not in e.ro_c:
            utils.mywarning("cid `{}` is not a key for e.ro_c.".format(cid))

    if utils.warnings_given > 0:
        utils.myerror("Too many errors; terminating.")


def show_election_data(e):

    utils.myprint("====== Reported election data ======")

    utils.myprint("Total reported votes for each vote by cid and pbcid (e.rn_cpr):")
    for cid in e.cids:
        for pbcid in sorted(e.possible_pbcid_c[cid]):
            utils.myprint("    {}.{}: ".format(cid, pbcid), end='')
            for vote in sorted(e.rn_cpr[cid][pbcid]):
                utils.myprint("{}:{} ".format(
                    vote, e.rn_cpr[cid][pbcid][vote]), end='')
            utils.myprint()

    utils.myprint("Total votes cast for each cid (e.rn_c):")
    for cid in e.cids:
        utils.myprint("    {}: {}".format(cid, e.rn_c[cid]))

    utils.myprint("Total cast for each vote for each cid (e.rn_cr):")
    for cid in e.cids:
        utils.myprint("    {}: ".format(cid), end='')
        for vote in sorted(e.rn_cr[cid]):
            utils.myprint("{}:{} ".format(vote, e.rn_cr[cid][vote]), end='')
        utils.myprint()

    utils.myprint("Reported outcome for each cid (e.ro_c):")
    for cid in e.cids:
        utils.myprint("    {}:{}".format(cid, e.ro_c[cid]))

