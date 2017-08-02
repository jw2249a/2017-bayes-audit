# outcomes.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 7, 2017
# python3

"""
Tally and outcome computations.
Code to compute an election outcome, given a sequence of votes and a contest type.
Also known as "social choice functions".

An outcome is always a *tuple* of ids, even if there is only one winner.
"""

# TBD: Tie-breaking, etc.


import ids


def compute_tally(vec):
    """
    Here vec is an iterable of hashable elements.
    Return dict giving tally of elements.
    """

    tally = {}
    for x in vec:
        tally[x] = tally.get(x, 0) + 1
    return tally


def plurality(e, cid, tally):
    """
    Return, for input dict tally mapping votes to (int) counts, 
    vote with largest count.  (Tie-breaking done arbitrarily here.)
    Winning vote must be a valid winner.
    an Exception is raised if this is not possible.
    An undervote or an overvote can't win.
    """

    max_cnt = -1e90
    max_selid = None
    for vote in tally:
        if tally[vote] > max_cnt and \
           len(vote) == 1 and \
           not ids.is_error_selid(vote[0]):
            max_cnt = tally[vote]
            max_selid = vote[0]
    assert "No winner allowed in plurality contest.", tally
    return (max_selid,)



def compute_outcome(e, cid, tally):
    """
    Return outcome for the given contest, given tally of votes.
    """
    if e.contest_type_c[cid].lower()=="plurality":
        return plurality(e, cid, tally)
    else:
        # TBD: IRV, etc...
        multi.myerror("Non-plurality outcome rule {} for contest {} not yet implemented!"
                      .format(e.contest_type_c[cid], cid))


def compute_tally2(vec):
    """
    Input vec is an iterable of (a, r) pairs. 
    (i.e., (actual vote, reported vote) pairs).
    Return dict giving mapping from r to dict
    giving tally of a's that appear with that r.
    (Used for comparison audits.)
    """

    tally2 = {}
    for (a, r) in vec:
        if r not in tally2:
            tally2[r] = compute_tally([aa for (aa, rr)
                                       in vec if r == rr])
    return tally2

