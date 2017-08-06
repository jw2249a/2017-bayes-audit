# syn.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# August 3, 2017
# python3

"""
Routines to generate a synthetic test election dataset, 
given the following parameters (defaults in brackets):

    cids = # number of contests [2]
    n_cids_wrong = # number of contests with wrong reported outcome [0]
    min_n_selids_per_cid = minimum number of selids per contest [2]
    max_n_selids_per_cid = maximum number of selids per contest [5]
    n_pbcids = # number of pbcids [2]
    n_pbcids_nocvr = # number of collections with no CVRs [0]
    min_n_bids_per_pbcid = minimum number of bids per pbcid [10]
    max_n_bids_per_pbcid = maximum number of bids per pbcid [20]
    box_size = max number of ballots in a box [100]
    min_pbcids_per_cid = minimum number of pbcids per contest [1]
    max_pbcids_per_cid = maximum number of pbcids per contest [1]
    dropoff = rate at which votes drop off with selection (geometric) [0.9]
    error_rate = rate at which reported votes != actual votes [0.005]
    seed = random number seed (for reproducibility) [1]
    RandomState = state for random number generator

    ### following are then computed ###
    ### in e:
    cids = list of cids (of length n_cids)
    cids_wrong = list of cids that will have wrong output
    pbcids = list of pbcids (of length syn_n_pbcids)
    cvr_type_p = mapping of pbcid to "CVR" or "noCVR"
    ### in syn:
    n_bids_p = mapping from pbcid to number of bids in that pbcid
    
We fill in the values of the fields of election e as if they
had been read in, or else we (optionally) output the values as csv files.
"""

import argparse
import copy
import numpy as np
import os

import multi
import audit_orders
import election_spec
import ids
import outcomes
import reported
import syn1
import syn2
import utils
import write_csv

class Syn_Params(object):
    """ An object we can hang synthesis generation parameters off of. """

    pass


##############################################################################
## random choices

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


def geospace_choice(e, syn, start, stop, num=7):
    """ 
    Return a random element from geospace(start, stop, num), 
    based on syn.RandomState.
    """

    elts = geospace(start, stop, num)
    return syn.RandomState.choice(elts)


def generate_segments(e, syn, low, high):
    """ 
    Return list of random segments (r, s) where low <= r < s <= high. 

    Number of segments returned is (high-low).

    Since r<s, does not return segments of the form (k, k).

    Intent is that cids are integers in range low <= cid <= high,
    and each segment yields a contest group covering cids r..s (inclusive).

    The segments "nest" -- given any two segments, either they
    are disjoint, or they are equal, or one contains the other.
    """

    assert low <= high
    L = []
    if low!=high:
        L.append((low, high))
        mid = syn.RandomState.choice(range(low, high))
        L.extend(generate_segments(e, syn, low, mid))
        L.extend(generate_segments(e, syn, mid+1, high))
    return L


##############################################################################
# Command-line arguments

def parse_args():

    parser = argparse.ArgumentParser(description=\
                                     ("syn.py: "
                                      "Synthetic election generation for "
                                      "multi.py (a Bayesian post-election "
                                      "audit program for an election with "
                                      "multiple contests and multiple paper "
                                      "ballot collections)."))

    # Mandatory argument: dirname

    parser.add_argument("election_dirname",
                        help=('The name for this election of the '
                              'subdirectory within the elections root '
                              'directory. Enter "" to get default '
                              'of TestElection followed by datetime.'))

    # All others are optional

    parser.add_argument("--syn_type",
                        help="Type of synthetic election.",
                        default='1')

    args = parser.parse_args()
    return args




def process_args(e, args):

    e.election_dirname = ids.filename_safe(args.election_dirname)
    e.election_name = e.election_dirname

    print(args)
    if args.syn_type == '1':                        
        syn1.generate_syn_type_1(e, args)
    elif args.syn_type == '2':
        syn2.generate_syn_type_2(e, args)
    else:
        print("Illegal syn_type:", args.syn_type)


if __name__=="__main__":

    e = multi.Election()

    args = parse_args()
    process_args(e, args)

    filepath = os.path.join(multi.ELECTIONS_ROOT, e.election_dirname)
    print("  Done. Synthetic election written to:", filepath)


