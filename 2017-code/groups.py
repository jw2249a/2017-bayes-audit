# groups.py
# Ronald L. Rivest
# July 25, 2017
# python3

"""
This module implements "contest groups" for the post-election audit program
"multi.py".  
"""

import multi


def expand_contest_group_defs(e):
    """
    Expand contest group definitions so that we have a definition
    for each contest group purely in terms of its contests.

    The input definitions are in e.cgids_g, which gives definition
    of each contest group as list of cids and gids, for each gid.

    The output goes into e.cids_g, which gives just the cids in 
    each group.

    This is a simple reachability computation in a directed graph.
    """

    e.cids_g = {}

    for gid in e.gids:
        expand_dfs(e, gid)


def expand_dfs(e, gid):
    """
    Expand contest group definitions.
    
    This works even if the graph contains cycles.
    """

    if gid in e.cids_g:
        return

    e.cids_g[gid] = set()

    for cgid in e.cgids_g[gid]:
        if cgid in e.cids:
            e.cids_g[gid].add(cgid)
        else:
            expand_dfs(e, cgid)
            for cid in e.cids_g[cgid]:
                e.cids_g[gid].add(cid)
    

def test_expand():

    e = multi.Election()

    e.gids = [1, 2, 3, 4, 5, 6, 7]

    e.cids = [11, 22, 33, 44, 55, 66, 77]

    e.cgids_g[1] = [11, 2]
    e.cgids_g[2] = [22, 3, 4]
    e.cgids_g[3] = [33]
    e.cgids_g[4] = [44, 5]
    e.cgids_g[5] = [55, 4]
    e.cgids_g[6] = [66, 1, 7]
    e.cgids_g[7] = [77, 3]

    print("Input:")
    print("  cids:", e.cids)
    print("  gids:", e.gids)
    for gid in e.gids:
        print("    {}->{}".format(gid, e.cgids_g[gid]))

    expand_contest_group_defs(e)

    print("Output:")
    for gid in e.gids:
        print("    {}->{}".format(gid, e.cids_g[gid]))

if __name__ == "__main__":

    test_expand()

