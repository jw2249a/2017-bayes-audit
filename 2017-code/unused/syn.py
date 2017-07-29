# syn.py
# Ronald L. Rivest
# July 7, 2017

"""
Code to generate synthetic (test) data for use by multi.py
All test data is written out to CSV files.
"""

import numpy as np

import multi              # to get Election spec


# syntheticRandomState    -- controls generation of synthetic data
synthetic_seed = 1
syntheticRandomState = np.random.RandomState(synthetic_seed)


def compute_rv(e, cid, pbcid, bid, vote):
    """
    Compute synthetic reported vote for e.rv_cpb[cid][pbcid][bid]
    based on whether pbcid is CVR or noCVR, and based on
    a prior for errors.  Input vote is the actual vote.
    e.error_rate (default 0.0001) is chance that 
    reported vote differs from actual vote.  If they differ, 
    then all possibilities (including original vote)
    are equally likely to occur.
    Only generates votes with a single selid.
    TODO: ensure that we get "-Invalids" etc. too
    """

    if e.collection_type_p[pbcid] == "noCVR":
        return ("-noCVR",)
    # Otherwise, we generate a reported vote
    # m = number of selection options for this cid
    m = len(e.selids_c[cid])
    if syntheticRandomState.uniform() > e.error_rate or m <= 1:
        # no error is typical case
        return vote
    else:
        # generate "error" (may be the same as original vote)
        selids = list(e.selids_c[cid])
        return (syntheticRandomState.choice(selids),)


def compute_synthetic_selections(e):
    """
    Make up reported and actual votes and randomly permute their order.
    Only useful for test elections, not for real elections.
    Form of bid is e.g. PBC1-00576
    """

    global syntheticRandomState

    # make up bids
    for pbcid in e.pbcids:
        e.bids_p[pbcid] = list()
        i = 0
        for j in range(i, i + e.rn_p[pbcid]):
            bid = pbcid + "-" + "%05d" % j
            e.bids_p[pbcid].append(bid)
        i += e.rn_p[pbcid]

    # get rn_cr from syn_rn_cr
    # (needs to be computed early, in order to make up votes)
    for cid in e.cids:
        e.rn_cr[cid] = {}
        for vote in e.syn_rn_cr[cid]:
            e.rn_cr[cid][vote] = e.syn_rn_cr[cid][vote]

    # make up votes
    for cid in e.cids:
        e.rv_cpb[cid] = {}
        e.av_cpb[cid] = {}
        # make up all votes first, so overall tally for cid is right
        votes = []
        for vote in e.rn_cr[cid]:
            votes.extend([vote] * e.rn_cr[cid][vote])
        syntheticRandomState.shuffle(votes)          # in-place shuffle
        # break list of votes up into pieces by pbcid
        i = 0
        for pbcid in e.rel_cp[cid]:
            e.av_cpb[cid][pbcid] = {}
            e.rv_cpb[cid][pbcid] = {}
            for j in range(e.rn_p[pbcid]):
                bid = e.bids_p[pbcid][j]
                vote = votes[j]
                av = vote
                e.av_cpb[cid][pbcid][bid] = av
                rv = compute_rv(e, cid, pbcid, bid, vote)
                e.rv_cpb[cid][pbcid][bid] = rv
            i += e.rn_p[pbcid]

if __name__=="__main__":
    pass

