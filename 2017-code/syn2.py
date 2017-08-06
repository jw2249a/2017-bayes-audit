# syn22.py
# Ronald L. Rivest
# August 5, 2017
# python3

"""
Routines to generate synthetic elections of "type 2".
Called from syn.py.
"""

import copy

import write_csv


##############################################################################
##

def generate_syn_type_2(e, args):

    syn = copy.copy(args)
    default_parameters(syn)

    generate_election_spec(e, syn)
    generate_reported(e, syn)
    generate_audit(e, syn)

    debug = False
    if debug:
        for key in sorted(vars(e)):
            print(key)
            print("    ", vars(e)[key])

    write_csv.write_csv(e)


