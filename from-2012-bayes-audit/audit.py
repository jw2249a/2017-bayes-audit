# audit.py
# Code to implement Bayes post-election audit
# Ronald L. Rivest and Emily Shen
# June 23, 2012
"""
----------------------------------------------------------------------
This code available under "MIT License" (open source).
Copyright (C) 2012 Ronald L. Rivest and Emily Shen.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
----------------------------------------------------------------------
"""

# See notes.txt for documentation

import hashlib
import json
import string
import os
import random
import sys
import time

import bayes
import sampler

indent = "        "                         

def printstr(s):
    """ Print string s and a following newline.
        (Will be adjusted later to actually save a copy to log file as well.)
    """
    print s

def printvarvalue(varname,value):
    """ Print a variable name and its value. """
    printstr("--- " + varname + ":")
    printstr(indent + str(value))

usage = """
Usage: audit.py command parameters
       command is one of: help set shuffle audit
       try  'audit.py help'  for more help
       'audit.py help command' for help on specific command
"""

def main():
    if len(sys.argv)==1:
        printstr(usage)
        quit()
    printstr("--- Bayes Post-Election Audit Utility (version 2012-06-04 by R.L. Rivest and E. Shen)")
    printstr("--- Start: "+time.asctime())
    printstr("--- Command:")
    printstr(indent+string.join(sys.argv[1:]," "))
    command = sys.argv[1]
    if command=="set":
        set_var()
    elif command=="shuffle":
        shuffle()
    elif command=="audit":
        audit()
    elif command=="help":
        help(sys.argv[2:])
    else:
        print "--- Error: unrecognized command:",sys.argv
    printstr("--- Done: "+time.asctime())

def hash_file(filename):
    """ Return SHA-256 of contents of file with given filename. """
    if not os.path.exists(filename):
        printstr("Error: file does not exist:"+filename)
        return 0
    file = open(filename,"r")
    data = file.read()
    file.close()
    return hashlib.sha256(data).hexdigest()

help_txt = dict()

help_txt[""] = """
--- Available commands for audit.py:
---     help
---     help command
---     set dirname varname value
---     shuffle dirname
---     audit dirname
"""

help_txt["help"] = """
--- Command: help command
---     where command is one of: set shuffle audit
"""

help_txt["set"] = """
--- Command: set dirname varname value
---     where dirname is directory for desired contest
---     where varname is one of  seed  or  audit_type
---     where value is arbitrary string if varname is seed (random number seed)
---     where value is one of  N  or  P  or  NP  if varname is  audit_type
--- File with name varname.js created in the given directory
"""

help_txt["shuffle"] = """
--- Command: shuffle dirname
---     where dirname is directory for desired contest
--- Assumes that directory contains file reported.js
--- Creates new file with name shuffle.js that is shuffle of reported.js
--- Uses given random number seed from seed.js (produced with set)
--- Removes reported choices and replaces them with null string choices
--- shuffle.js can be renamed as actual.js and then filled in with actual choices
--- as auditing proceeds
"""

help_txt["audit"] = """
--- Command: audit dirname
---     where dirname is directory for desired contest
---     assumes directory contest contains reported.js and actual.js
---     file audit_type.js may optionally be present
--- Performs bayes audit of given contest, printing out for
--- each alternative an upper bound on probability that it is winner.
"""

def help(command_list):
    """ Print generic help or help for specific command.

        help           -- print generic help
        help command   -- print help for given command
    """
    if command_list==[]:   # i.e. print generic help
        command = ""
    else:
        command = command_list[0]
    printstr(help_txt[command])

def set_var():
    """ audit.py set dirname varname value
    
    Create a file varname.js in the current directory
    and set contents to be  "value" .
    As of now, only allowed varnames are "seed" and "audit_type"
    """
    allowed_varnames = [ "seed", "audit_type" ]
    if not len(sys.argv)==5:
        printstr("--- Error: incorrect number of arguments for set:"+str(len(sys.argv)-1))
        printstr("--- Usage: audit.py set dirname varname value")
        return
    dirname = os.path.realpath(sys.argv[2])
    varname = sys.argv[3]
    value = sys.argv[4]
    if not os.path.isdir(dirname):
        printstr("--- Error: first parameter not an existing directory:"+dirname)
        printstr("--- Usage: audit.py set dirname varname value")
        return

    contest = os.path.basename(dirname)
    printvarvalue("Contest",contest)
    printvarvalue("Contest directory",dirname)

    if varname not in allowed_varnames:
        printstr("--- Error: only the following varnames may be set: "+str(allowed_varnames))
        return
    printstr("--- Setting value for `%s' for contest `%s'"%(varname,contest))
    if varname=="audit_type" and value not in ["N","P","NP"]:
        printstr("""--- Error: value for audit_type must be one of N, P, or NP """)
        return
    filename = os.path.join(dirname,varname+".js")
    printvarvalue("Writing value to file with name",filename)
    file = open(filename,"w")
    value_data = json.dumps(value)
    file.write(value_data+"\n")
    printvarvalue("New value",value_data)

def shuffle():
    """
    audit.py shuffle dirname
    Produce an audit order for this audit.
    
    Assumes that seed.js has been set, e.g. by a command
    of the form "set seed 3544523"
    """
    if not len(sys.argv)==3:
        printstr("--- Error: incorrect number of arguments for shuffle:"+str(len(sys.argv)-1))
        printstr("--- Usage: audit.py set dirname varname value")
        return
    dirname = os.path.realpath(sys.argv[2])
    if not os.path.isdir(dirname):
        printstr("--- Error: not an existing directory:"+dirname)
        printstr("--- Usage: audit.py shuffle dirname")
        return

    contest = os.path.basename(dirname)
    printvarvalue("Contest",contest)
    printvarvalue("Contest directory",dirname)

    seed_filename = os.path.join(dirname,"seed.js")
    seed_file = open(seed_filename,"r")
    seed = json.load(seed_file)
    printvarvalue("Seed",seed)

    reported_filename = os.path.join(dirname,"reported.js")
    reported_file = open(reported_filename,"r")
    reported = json.load(reported_file)
    n = len(reported)
    printvarvalue("Number of reported ballots",n)
    skip, sample = sampler.generate_outputs(n,False,0,n-1,seed,0)
    shuffled_filename = os.path.join(dirname,"shuffled.js")
    shuffled_file = open(shuffled_filename,"w")
    ids = sorted(reported.keys())
    shuffled_ids = [ ids[sample[i]] for i in xrange(len(sample)) ]
    shuffled_file.write("{\n")
    for i,id in enumerate(shuffled_ids):
        shuffled_file.write('   "' + str(id) + '": ""')
        if i+1<len(shuffled_ids):
            shuffled_file.write(",")
        shuffled_file.write("\n")
    shuffled_file.write("}\n")
    shuffled_file.close()
    printvarvalue("Filename for shuffled file written, and hash of shuffled file",shuffled_filename)
    printstr(indent+"hash:"+hash_file(shuffled_filename))

def audit():
    """ 
    audit.py audit dirname 
    """
    dirname = os.path.realpath(sys.argv[2])
    if not os.path.isdir(dirname):
        printstr("--- Error: not an existing directory:"+dirname)
        printstr("--- Usage: audit.py audit dirname")
        return

    contest = os.path.basename(dirname)
    printvarvalue("Contest",contest)
    printvarvalue("Contest directory",dirname)

    actual_filename = "actual.js"
    full_actual_filename = os.path.join(dirname,actual_filename)

    printvarvalue("Filename for Actual Ballots and Hash of Actual Ballots File",actual_filename)
    printstr(indent+"hash:"+hash_file(full_actual_filename))
    actual_file = open(full_actual_filename,"r")
    actual = json.load(actual_file)
    printvarvalue("Number of actual ballots",len(actual))

    distinct_actual_choices = sorted(set(actual.values()))
    printstr("--- Distinct actual choices (alphabetical order):")
    for choice in distinct_actual_choices:
        if choice == "":
            printstr(indent+'"" (no choice given)')
        else:
            printstr(indent+choice)

    reported_filename = "reported.js"
    full_reported_filename = os.path.join(dirname,reported_filename)

    if os.path.exists(full_reported_filename):
        printvarvalue("Filename for Reported Ballots and Hash of Reported Ballots File",reported_filename)
        printstr(indent+"hash:"+hash_file(full_reported_filename))
        reported_file = open(full_reported_filename,"r")
        reported = json.load(reported_file)
        printvarvalue("Number of reported ballots",len(reported))
        printstr("--- Both actual and reported ballot types available, so audit will be a `comparison' audit.")
        ballot_polling = False
        distinct_reported_choices = sorted(set(reported.values()))
        printstr("--- Distinct reported choices (alphabetical order):")
        for choice in distinct_reported_choices:
            printstr(indent+choice)
        all_choices = sorted(set(distinct_actual_choices).union(set(distinct_reported_choices)))
        # check that actual choices are also reported choices?
        for choice in distinct_actual_choices:
            if choice != "" and choice not in distinct_reported_choices:
                printstr("--- Warning:")
                printstr('        actual choice "%s" not in reported choices; possible typo?'%choice)
                printstr("        (no need to do anything if this is not a typo...)")
        # check that no ballots are added in actual
        for id in actual.keys():
            if not id in reported:
                if id == '':
                    id = '""'
                printstr("--- Warning:")
                printstr('        Actual ballot id "%s" not in reported ballot ids!'%id)
                printstr("        (This ballot will be ignored in this audit.)")
    else:
        printstr( "--- No file of reported ballots (%s) given."%reported_filename)
        printstr("--- Audit will therefore be a `ballot-polling' audit.")
        ballot_polling = True
        all_choices = distinct_actual_choices

    # printstr("--- All choices (alphabetical order):")
    # for choice in all_choices:
    #     printstr(indent+choice)

    # set seed for package random from seed.js
    seed_filename = os.path.join(dirname,"seed.js")
    if not os.path.exists(seed_filename):
        printstr("Error: seed file doesn't exist at filename:"+seed_filename)
    seed_file = open(seed_filename,"r")
    seed = json.load(seed_file)
    random.seed(seed)

    if not ballot_polling:
        audited_ids = set([ id for id in actual if id in reported and actual[id] != "" ])
        unaudited_ids = set([ id for id in reported if id not in audited_ids ])
    else:
        audited_ids = set([ id for id in actual if actual[id] != "" ])
        unaudited_ids = set([ id for id in actual if id not in audited_ids ])

    printvarvalue("Number of audited ballots",len(audited_ids))
    printvarvalue("Number of unaudited ballots",len(unaudited_ids))

    # give indices to all bids in audit
    i_to_id = dict()
    id_to_i = dict()
    i = 1
    for id in sorted(audited_ids):
        i_to_id[i] = id
        id_to_i[id] = i
        i += 1
    for id in sorted(unaudited_ids):
        i_to_id[i] = id
        id_to_i[id] = i
        i += 1

    # give indices to all choices
    j_to_choice = dict()
    choice_to_j = dict()
    j = 1
    for choice in all_choices:
        j_to_choice[j] = choice
        choice_to_j[choice] = j
        j = j + 1

    # now create r and a arrays
    dummy = -9
    t = len(all_choices)
    s = len(audited_ids)
    n = len(audited_ids)+len(unaudited_ids)
    # printvarvalue("n",n)
    # printvarvalue("s",s)
    # printvarvalue("t",t)
    r = [ dummy ]        
    a = [ dummy ]
    if not ballot_polling:
        count = [dummy]+[[dummy] + [0]*t for k in range(t+1)]
        for i in range(1,s+1):
            j = choice_to_j[reported[i_to_id[i]]]
            k = choice_to_j[actual[i_to_id[i]]]
            r.append(j)
            a.append(k)
            count[j][k] += 1
        for i in range(s+1,n+1):
            j = choice_to_j[reported[i_to_id[i]]]
            k = 1 # doesn't matter
            r.append(j)
            a.append(k)
        # printvarvalue("r",r)
        # printvarvalue("a",a)
    else: # ballot_polling
        count = [dummy] + [0]*t
        for i in range(1,s+1):
            k = choice_to_j[actual[i_to_id[i]]]
            r.append(1)  # fixed value
            a.append(k)
            count[k] += 1
        for i in range(s+1,n+1):
            j = choice_to_j[actual[i_to_id[i]]]
            k = 1 # doesn't matter
            r.append(j)
            a.append(k)
        
    f = bayes.f_plurality
    
    audit_type = "NP"
    audit_type_filename = os.path.join(dirname,"audit_type.js")
    if os.path.exists(audit_type_filename):
        audit_type_file=open(audit_type_filename,"r")
        audit_type=json.load(audit_type_file)
        if audit_type not in ["P","NP","N"]:
            printstr("Error: audit_type.js contains illegal audit.type,"+audit_type)
            printstr('       (assumed to be "NP")')
            audit_type = "NP"

    print "--- Audit type:"
    if ballot_polling:
        printstr("        ballot-polling audit")
    else:
        printstr("        comparison audit")
    printstr("        %s-type"%audit_type)

    if audit_type == "P":
        printstr("        "+"(Partisan priors)")
    elif audit_type == "N":
        printstr(indent+"(Nonpartisan prior)")
    else:
        printstr(indent+ "(Nonpartisan prior and also Partisan priors)")

    prior_list = bayes.make_prior_list(audit_type,t,ballot_polling)
    # print prior

    if not ballot_polling:
        # print out reported winner
        reported_winner = j_to_choice[f(bayes.tally(r,t))]
        printvarvalue("Reported winner",reported_winner)

    # print out win probabilities (assumes plurality voting)
    max_wins = dict()
    max_u = 0
    for prior in prior_list:
        wins,u,z =  bayes.win_probs(r,a,t,s,n,count,ballot_polling,f,prior)
        for j in wins.keys():
            max_wins[j] = max(wins[j],max_wins.get(j,0))
            max_u = max(max_u,u)
    L = sorted([(max_wins[j],j_to_choice[j]) for j in max_wins.keys()],reverse=True)
    print "--- Estimated maximum winning probabilities:"
    for (maxp,c) in L:
        printstr(indent+"%6.4f"%maxp+" "+str(c))
    if ballot_polling:
        printstr("--- Estimated maximum probability that actual winner is not "+str(L[0][1])+":")
    else:
        printstr("--- Estimated maximum probability that actual winner is not "+str(reported_winner)+":")
    printstr(indent+str(max_u))
        
def status():
    """
    audit.py status dirname

    Give a status report on the named contest
    Include a note of any discrepancies between actual and reported.
    """
    # TBD
    pass

# import cProfile
# cProfile.run("main()")
main()
    
