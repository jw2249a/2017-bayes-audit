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
import utils
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

        if cid not in e.cids:
            e.cids.append(cid)
            e.contest_type_c[cid] = "plurality"
            e.winners_c[cid] = 1
            e.write_ins_c[cid] = "no"
            e.selids_c[cid] = {}
            for selid in rv:
                if selid not in e.selids_c[cid]:
                    e.selids_c[cid][selid] = True
            for selid in av:
                if selid not in e.selids_c[cid]:
                    e.selids_c[cid][selid] = True
            e.ro_c[cid] = "FIX_ME"

        if pbcid not in e.pbcids:
            e.pbcids.append(pbcid)
            e.manager_p[pbcid] = "Nobody"
            e.cvr_type_p[pbcid] = "CVR"
            e.required_gid_p[pbcid] = ""
            e.possible_gid_p[pbcid] = ""
            e.bids_p[pbcid] = []
            e.boxid_pb[pbcid] = {}
            e.position_pb[pbcid] = {}
            e.stamp_pb[pbcid] = {}
            e.max_audit_rate_p[pbcid] = 40
            e.shuffled_indices_p[pbcid] = "FIXME"
            e.shuffled_bids_p[pbcid] = "FIXME"

        for pos in range(1, num+1):
            bid = "bid{}".format(pos)
            utils.nested_set(e.rv_cpb, [cid, pbcid, bid], rv)
            utils.nested_set(e.av_cpb, [cid, pbcid, bid], av)
            e.bids_p[pbcid].append(bid)
            e.boxid_pb[pbcid][bid] = "box1"
            e.position_pb[pbcid][bid] = pos
            e.stamp_pb[pbcid][bid] = ""

##############################################################################
##

def generate_syn_type_2(e, args):

    synpar = copy.copy(args)
    # syn1.default_parameters(synpar)

    L = [ ("cid1", "pbcid1", ("Alice",), ("Bob,"), 3) ]

    process_spec(e, synpar, L)

    # generate_election_spec(e, synpar)
    # generate_reported(e, synpar)
    # generate_audit(e, synpar)

    debug = False
    if debug:
        for key in sorted(vars(e)):
            print(key)
            print("    ", vars(e)[key])

    write_csv.write_csv(e)


