# sampling_orders.py
# Ronald L. Rivest
# July 10, 2017
# python3

"""
Routine to work with multi.py program for election audits.
Generates random sampling orders from a ballot manifest 
and an audit seed, for each paper ballot collection.

The overall algorithm is the "Fisher-Yates shuffle":
     https://en.wikipedia.org/wiki/FisherYates_shuffle

The method used uses SHA256 in counter mode, as in
the program:
     https://people.csail.mit.edu/rivest/sampler.py

"""

import hashlib

import multi


def sha256(hash_input):
    """ 
    Return value of SHA256 hash of input 
    bytearray hash_input, as a nonnegative integer.
    """

    assert isinstance(hash_input, bytearray)
    return int(hashlib.sha256(hash_input).hexdigest(), 16)


def shuffle(L, seed):
    """ Return shuffled copy of list L, based on seed. """

    L = list(L).copy()
    for i in range(len(L)):
        hash_input = bytearray(str(seed)+","+str(i),'utf-8')
        hash_value = sha256(hash_input)
        j = hash_value % (i+1)             # random modulo (i+1)
        L[i], L[j] = L[j], L[i]            # swap
    return L


def test_shuffle(seed=1234567890):

    for i in range(3):
        L = range(20)
        print(shuffle(L, seed+i))
    """
    [12, 13, 2, 18, 3, 8, 9, 7, 17, 6, 16, 5, 11, 19, 1, 14, 10, 0, 4, 15]
    [4, 2, 9, 8, 14, 6, 3, 5, 7, 15, 18, 10, 19, 1, 13, 11, 17, 12, 0, 16]
    [13, 12, 1, 0, 3, 4, 19, 10, 11, 5, 7, 2, 17, 16, 18, 14, 8, 6, 9, 15]
    """
    

def compute_sampling_orders(e):

    for pbcid in e.pbcids:
        compute_sampling_order(e, pbcid)


def compute_sampling_order(e, pbcid):

    L = shuffle(e.bids_p[pbcid], e.audit_seed)


def write_sampling_order(e, pbcid):

    pass


if __name__=="__main__":

    test_shuffle()

    
    
