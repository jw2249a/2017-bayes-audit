# multi.py
# Ronald L. Rivest
# (with help from Karim Husayn Karimi and Neal McBurnett)
# July 7, 2017

# python3
# clean up with autopep8
#   autopep8 -i multi.py
#   (updates in place; see https://github.com/hhatto/autopep8)

"""
Prototype code for auditing an election having both multiple contests and
multiple paper ballot collections (e.g. multiple jurisdictions).
Possibly relevant to Colorado state-wide post-election audits in Nov 2017.
"""

""" 
This code corresponds to the what Audit Central needs to do, although
it could also be run locally in a county.
"""

# MIT License

import argparse
import datetime
import json
import numpy as np
import os
import sys

import outcomes
import snapshot

import structure
import reported
import audit
import planner

##############################################################################
# datetime
##############################################################################


def datetime_string():
    """ Return current datetime as string e.g. '2017-06-26-21-18-30' 
        Year-Month-Day-Hours-Minutes-Seconds
        May be used as a version label in an output filename.
    """
    # https://docs.python.org/3.6/library/datetime.html

    t = datetime.datetime.now()
    return t.strftime("%Y-%m-%d-%H-%M-%S")


##############################################################################
# myprint  (like logging, maybe, but maybe simpler)
##############################################################################

myprint_files = {"stdout": sys.stdout}


def myprint(*args, **kwargs):
    """ variant print statement; prints to all files in myprint_files. """

    for output_file_name in myprint_files:
        kwargs["file"] = myprint_files[output_file_name]
        print(*args, **kwargs)


def close_myprint_files():
    """ Close myprint files other than stdout and stderr. """

    for output_file_name in myprint_files:
        if output_file_name not in ["stdout", "stderr"]:
            myprint_files[output_file_name].close()
            del myprint_files[output_file_name]


# error and warning messages


def myerror(msg):
    """ Print error message and halt immediately """

    print("FATAL ERROR:", msg)
    raise Exception


warnings_given = 0


def mywarning(msg):
    """ Print error message, but keep going.
        Keep track of how many warnings have been given.
    """

    global warnings_given
    warnings_given += 1
    print("WARNING:", msg)


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
# Elections
##############################################################################

class Election(object):

    """
    All relevant attributes of an election are stored within an Election 
    object.

    For compatibility with json, an Election object should be viewed as 
    the root of a tree of dicts, where all keys are strings, and the leaves are
    strings or numbers, or lists of strings or numbers.

    In comments: 
       dicts: an object of type "cids->int" is a dict mapping cids to ints,
                and an object of type "cids->pcbids->selids->int" is a nested 
                set of dicts, the top level keyed by a cid, and so on.
       lists: an object of type [bids] is a list of ballot ids.

    Glossary:

        cid    a contest id (e.g. "Den-Mayor")

        pbcid  a paper-ballot collection id (e.g. "Den-P24")

        bid    a ballot id (e.g. "Den-12-234")

        selid  a selection id (e.g. "Yes" or "JohnSmith"). A string.
               If it begins with a "+", it denotes a write-in (e.g. "+BobJones")
               If it begins with a "-", it denotes an error (e.g. "-Invalid" or
               "-Missing" or "-noCVR").  Errors for overvotes and undervotes
               are indicated in another way.  Each selid naively corresponds to
               one bubble filled in on an optical scan ballot.

        vote   a tuple of selids, e.g. ("AliceJones", "BobSmith", "+LizardPeople").
               An empty vote (e.g. () ) is an undervote (for plurality).
               A vote with more than one selid is an overvote (for plurality).
               The order may matter; for preferential voting a vote of the form
               ("AliceJones", "BobSmith", "+LizardPeople") indicates that Alice
               is the voter's first choice, Bob the second, etc.               

    It is recommended (but not required) that ids not contain anything but
             A-Z   a-z   0-9  -   _   .   +
    and perhaps whitespace.
    """

    def __init__(self):

        e = self

        # Note: we use nested dictionaries extensively.
        # variables may be named e.de_wxyz
        # where w, x, y, z give argument type:
        # c = contest id (cid)
        # p = paper ballot collection id (pbcid)
        # r = reported vote
        # a = actual vote
        # b = ballot id (bid)
        # t = audit stage number
        # and where de may be something like:
        # rn = reported number (from initial scan)
        # sn = sample number (from given sample stage)
        # but may be something else.
        #
        # Example:
        # e.rn_cr = reported number of votes by contest
        # and reported vote r, e.g.
        # e.rn_cr[cid][r]  gives such a count.

        # election structure

        e.elections_dirname = ""
        # where the elections data is e.g. "./elections",
        # so e.g. election data for CO-Nov-2017
        # is all in "./elections/CO-Nov-2017"

        e.election_name = ""
        # Name of election (e.g. "CO-Nov-2017")
        # Used as a directory name within elections_dir

        e.election_date = ""
        # In ISO8601 format, e.g. "2017-11-07"

        e.election_url = ""
        # URL to find more information about the election

        e.cids = []
        # list of contest ids (cids)

        e.contest_type = {}
        # cid->contest type  (e.g. "plurality" or "irv")

        e.winners = {}
        # cid->int
        # number of winners in contest 

        e.write_ins = {}
        # cid->str  (e.g. "no" or "qualified" or "arbitrary")

        e.selids_c = {}
        # cid->selids->True
        # dict of some possible selection ids (selids) for each cid 
        # note that e.selids_c is used for both reported selections
        # (from votes in e.rv) and for actual selections (from votes in e.av)
        # it also increases when new selids starting with "+" or "-" are seen.

        e.pbcids = []
        # list of paper ballot collection ids (pbcids)


        e.manager_p = {}
        # pbcid->manager
        # Gives name and/or contact information for collection manager

        e.cvr_type_p = {}
        # pbcid-> "CVR" or "noCVR"

        e.rel_cp = {}
        # cid->pbcid->"True"
        # relevance; only relevant pbcids in e.rel_cp[cid]
        # True means the pbcid *might* contains ballots relevant to cid

        e.bids_p = {}
        # pbcid->[bids]
        # list of ballot ids (bids) for each pcbid

        # election data (reported election results)

        e.rn_p = {}
        # pbcid -> count
        # e.rn_p[pbcid] number ballots reported cast in collection pbcid

        e.votes_c = {}
        # cid->votes
        # e.votes_c[cid] gives all votes seen for cid, reported or actual
        # (These are the votes, not the count.  So e.votes_c is the domain
        # for tallies of contest cid.)

        e.rn_cpr = {}
        # cid->pbcid->rvote->count
        # reported number of votes by contest, paper ballot collection,
        # and reported vote.

        e.ro_c = {}
        # cid->outcome
        # reported outcome by contest

        # computed from the above

        e.rn_c = {}
        # cid->int
        # reported number of votes cast in contest

        e.rn_cr = {}
        # cid->votes->int
        # reported number of votes for each reported vote in cid

        e.rv_cpb = {}
        # cid->pbcid->bid->vote
        # vote in given contest, paper ballot collection, and ballot id
        # e.rv_cpb is like e.av, but reported votes instead of actual votes

        e.synthetic_seed = 2
        # seed for generation of synthetic random votes

        e.syn_rn_cr = {}
        # synthetic reported number cid->vote->count

        e.error_rate = 0.0001
        # error rate used in model for generating synthetic reported votes

        # audit

        e.audit_seed = None
        # seed for pseudo-random number generation for audit

        e.risk_limit_c = {}
        # cid->reals
        # risk limit for each contest

        e.audit_rate_p = {}
        # pbcid->int
        # number of ballots that can be audited per stage in a pcb

        e.stage = "0"
        # current audit stage number (in progress) or last stage completed

        e.last_stage = "-1"
        # previous stage (just one less, in string form)

        e.max_stages = 20
        # maximum number of stages allowed in audit

        e.pseudocount = 0.5
        # hyperparameter for prior distribution
        # (e.g. 0.5 for Jeffrey's distribution)

        e.recount_threshold = 0.95
        # if e.risk[e.stage][cid] exceeds 0.95, then full recount called for
        # cid

        e.n_trials = 100000
        # number of trials used to estimate risk in compute_contest_risk

        # stage-dependent items
        # stage number input is stage when computed
        # stage is denoted t here

        e.plan_tp = {}
        # stage->pbcid->reals
        # sample size wanted after next draw

        e.risk_tc = {}
        # stage->cid->reals
        # risk = probability that e.ro_c[cid] is wrong

        e.contest_status_tc = {}
        # stage->cid-> one of the following:
        #     "Auditing",
        #     "Just Watching",
        #     "Risk Limit Reached",
        #     "Full Recount Needed"
        # initially must be "Auditing" or "Just Watching"

        e.election_status_t = {}
        # stage->list of contest statuses, at most once each

        # sample info

        e.sn_tp = {}
        # stage->pbcid->ints
        # number of ballots sampled so far

        e.av_cpb = {}
        # cid->pbcid->bid->vote
        # (actual votes from sampled ballots)

        # computed from the above sample data

        e.sn_tcpra = {}
        # sampled number: stage->cid->pbcid->rvote->avote->count
        # first vote r is reported vote, second vote a is actual vote

        e.sn_tcpr = {}
        # sampled number stage->cid->pbcid->vote->count
        # sampled number by stage, contest, pbcid, and reported vote


##############################################################################
# Low level i/o for reading election data structure

def copy_dict_tree(dest, source):
    """
    Copy data from source dict tree to dest dict tree, recursively.
    Omit key/value pairs where key starts with "__".
    TODO?? Filter so only desired attributes are copied, for security. 
    OBSOLETE--WAS USED FOR LOADING FROM JSON FILES.
    """

    if not isinstance(dest, dict) or not isinstance(source, dict):
        myprint("copy_dict_tree: source or dest is not a dict.")
        return
    for source_key in source:
        if not source_key.startswith("__"):   # for comments, etc.
            if isinstance(source[source_key], dict):
                if not source_key in dest:
                    dest_dict = {}
                    dest[source_key] = dest_dict
                else:
                    dest_dict = dest[source_key]
                source_dict = source[source_key]
                copy_dict_tree(dest_dict, source_dict)
            else:
                # Maybe add option to disallow clobbering here??
                dest[source_key] = source[source_key]


##############################################################################
# Input/output at the file-handling level

def greatest_name(dirpath, startswith, endswith, dir_wanted=False):
    """ 
    Return the filename (or, optionally, directory name) in the given directory 
    that begins and ends with strings startswith and endswith, respectively.
    If there is more than one such file, return the greatest (lexicographically)
    such filename.  Raise an error if there are no such files.
    The portion between the prefix startswith and the suffix endswith is called
    the version label in the documentation.
    If switch "dir_wanted" is True, then return greatest directory name, not filename.
    Example:  greatest_name(".", "foo", ".csv")
    will return "foo-11-09.csv" from a directory containing files
    with names  "foo-11-09.csv", "foo-11-08.csv", and "zeb-12-12.csv".
    """

    selected_filename = ""
    for filename in os.listdir(dirpath):
        full_filename = os.path.join(dirpath,filename)
        if (dir_wanted == False and os.path.isfile(full_filename) or \
            dir_wanted == True and not os.path.isfile(full_filename)) and\
           filename.startswith(startswith) and \
           filename.endswith(endswith) and \
           filename > selected_filename:
            selected_filename = filename
    if selected_filename == "":
        if dir_wanted == False:
            myerror("No files in `{}` have a name starting with `{}` and ending with `{}`."
                    .format(dirpath, startswith, endswith))
        else:
            myerror("No directories in `{}` have a name starting with `{}` and ending with `{}`."
                    .format(dirpath, startswith, endswith))
    return selected_filename


##############################################################################
# Command-line arguments

def parse_args():

    parser = argparse.ArgumentParser(description="""multi.py: A Bayesian post-election audit program for an
            election with multiple contests and multiple paper ballot 
            collections.""")

    #v1 and v2:
    parser.add_argument("election_name", help="""
                        The name of the election.  Same as the name of the 
                        subdirectory within the 'elections' directory 
                        for information about this election.""")
    parser.add_argument("--elections_dir", help="""The directory where the subdirectory for the
                        election is to be found.  Defaults to "./elections".""",
                        default="./elections")
    parser.add_argument("--audit_seed",
                        help="""Seed for the random number generator used for
                        auditing (32-bit value). (If omitted, uses clock.)""")
    ## v2:
    parser.add_argument("--read_structure", action="store_true", help="""
                        Read and check election structure.""")
    parser.add_argument("--read_reported", action="store_true", help="""
                        Read and check reported election data and results.""")
    parser.add_argument("--read_seed", action="store_true", help="""
                        Read audit seed.""")
    parser.add_argument("--make_orders", action="store_true", help="""
                        Make sampling orders files.""")
    parser.add_argument("--read_audited", action="store_true", help="""
                        Read and check audited votes.""")
    parser.add_argument("--stage",
                        help="""Run stage STAGE of the audit (may specify "ALL").""")
    args = parser.parse_args()
    print("Command line arguments:", args)
    return args


def process_args(e, args):

    e.elections_dirname = args.elections_dir
    e.election_name = args.election_name

    if args.read_structure:
        print("read_structure")
        structure.get_election_structure(e)
    elif args.read_reported:
        print("read_reported")
        structure.get_election_structure(e)
        reported.get_election_data(e)
    elif args.read_seed:
        print("read_seed")
        structure.get_election_structure(e)
        reported.get_election_data(e)
        audit.get_audit_parameters(e, args)
    elif args.make_orders:
        print("make_orders")
    elif args.read_audited:
        print("read_audited")
    elif args.stage:
        print("stage", args.stage)
        structure.get_election_structure(e)
        reported.get_election_data(e)
        audit.get_audit_parameters(e, args)
        audit.audit(e, args)


def main():

    global myprint_switches
    myprint_switches = []       # put this after following line to suppress printing
    myprint_switches = ["std"]

    print("multi.py -- Bayesian audit support program.")

    global start_datetime_string
    start_datetime_string = datetime_string()
    print("Starting data/time:", start_datetime_string)

    args = parse_args()
    e = Election()
    try:
        process_args(e, args)
    finally:
        close_myprint_files()


if __name__ == "__main__":
    main()
