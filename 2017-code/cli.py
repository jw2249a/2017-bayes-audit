# cli.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 22, 2017
# python3

"""
Command-line parser and dispatch
"""


import argparse


import audit
import multi
import reported
import structure


##############################################################################
# Command-line arguments

def parse_args():

    parser = argparse.ArgumentParser(description="""multi.py: A Bayesian post-election audit program for an
            election with multiple contests and multiple paper ballot 
            collections.""")

    #v1 and v2:
    # Mandatory argument is dirname
    parser.add_argument("election_dirname", help="""
                        The name for this election of the subdirectory within the elections root directory.""")
    # All others are optional
    # First group sets parameters: election_name, elections_root, audit_seed
    parser.add_argument("--election_name", help="""
                        Human-readable name of the election.""",
                        default="TestElection")
    parser.add_argument("--elections_root", help="""The directory where the subdirectory for the
                        election is to be found.  Defaults to "./elections".""",
                        default="./elections")
    parser.add_argument("--audit_seed",
                        help="""Seed for the random number generator used for
                        auditing (arbitrary nonnegative integer). (If omitted, uses clock.)""")
    ## v2:
    parser.add_argument("--read_structure", action="store_true", help="""
                        Read and check election structure.""")
    parser.add_argument("--read_reported", action="store_true", help="""
                        Read and check reported election data and results.""")
    parser.add_argument("--read_seed", action="store_true", help="""
                        Read audit seed.""")
    parser.add_argument("--make_orders", action="store_true", help="""
                        Make audit orders files.""")
    parser.add_argument("--read_audited", action="store_true", help="""
                        Read and check audited votes.""")
    parser.add_argument("--stage",
                        help="""Run stage STAGE of the audit (may specify "ALL").""")
    args = parser.parse_args()
    # print("Command line arguments:", args)
    return args


def process_args(e, args):

    e.election_dirname = args.election_dirname
    e.election_name = args.election_name
    ELECTIONS_ROOT = args.elections_root
    audit.set_audit_seed(e, args.audit_seed)

    if args.read_structure:
        # print("read_structure")
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



