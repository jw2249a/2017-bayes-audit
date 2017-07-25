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
        expand_dfs(gid)


def expand_dfs(gid):
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
            expand_dfs(cgid)
            for cid in e.cids_g[cgid]:
                e.cids_g[gid].add(cgid)
    
