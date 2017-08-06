# syn22.py
# Ronald L. Rivest
# August 5, 2017
# python3

"""
Routines to generate synthetic elections of "type 2".
Called from syn.py.
In support of multi.py audit support program.
"""

import copy

import syn
import syn1
import write_csv


def process_spec(e, synpar, L):
    """
    Initialize Election e according to spec in list L.

    Here e is of type multi.Election

    Here synpar is of type syn.Syn_Parameters

    Each item in L has the form:
        (cid, pbcid, rv, av, num)
    where 
        cid = contest id
        pbcid = paper ballot collection id
        rv = reported vote
             (may be ("-noCVR",) if pbcid is noCVR type
        av = actual vote
        num = number of ballots of this type
    Either or both of rv and av may be
        ("-NoSuchContest",)
        ("-Invalid",)
        or other such votes with selection ids starting with "-",
        signifying that they can't win the contest.
    The votes rv and av are arbitrary tuples, and may contain
    0, 1, 2, or more selection ids.
    """

    for (cid, pbcid, rv, av, num) in L:

        e.cids.append(cid)

        e.pbcids.append(pbcid)

        for bidx in range(1, num+1):
            bid = "bid{}".format(bidx)
            utils.nested_set(e.rv_cpb, [cid, pbcid, bid], rv)
            utils.nested_set(e.av_cpb, [cid, pbcid, bid], av)
            

##############################################################################
##

def generate_syn_type_2(e, args):

    synpar = copy.copy(args)
    # syn1.default_parameters(synpar)

    generate_election_spec(e, synpar)
    generate_reported(e, synpar)
    generate_audit(e, synpar)

    debug = False
    if debug:
        for key in sorted(vars(e)):
            print(key)
            print("    ", vars(e)[key])

    write_csv.write_csv(e)


