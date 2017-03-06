# bayes.py
# Code for working with Bayes Post-Election Audits
# Ronald L. Rivest and Emily Shen
# 5/31/12
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

"""
Notation:

Even though Python is 0-indexed, we'll use one-indexing here, to
correspond better with our paper.  The 0-th element of lists (arrays)
will be ignored (and is typically set to a dummy(-9)).

m       -- the number of candidates (for plurality elections)

t       -- the number of distinct ballot types possible resulting from
           a machine scan or hand examination of a ballot.
           One may consider "undervote" and "overvote" to be
           ballot types (although they shouldn't win), in
           which case we havve t = m+2 for a plurality election.
           The ballot types are coded as integers: 1, ..., t.

n       -- the number of ballots cast.

r[1..n] -- the list of all the *reported* ballot types.
           This is the "reported profile" for the election.
           That is, r[i] is the ``machine result'' for ballot i.

a[1..n] -- the list of all the corresponding *actual* ballot types.
           This is the "actual profile" for the election.
           That is, a[i] is the ``hand audit result'' for ballot i.
           In practice, these become known only one at a time,
           as audited, instead of all at once, as coded here.

s       -- the size of the current sample (the number of ballots
           audited so far).

epsilon -- the provided ``upset risk limit'' (e.g. 0.05)
"""

######################################################################
# Reminder: this code runs about 7x faster with "pypy" than with     
# the standard python interpreter !  Use pypy!                       
######################################################################

import math
import random
import string
import time

dummy = -9                      # dummy value for array position 0

######################################################################
# TALLY
######################################################################

def tally(P,t):
    """ 
    Return list of counts of each ballot type in profile P.
    Assumes each entry of P[1:] is in 1...t, inclusive.

    P is 0-indexed; dummy value P[0] is ignored.
    returned count[j] is number of votes of type j, 1<=j<=t.
    returned count[0] is a dummy value.
    """
    count = [dummy]+[0]*t
    for i in range(1,len(P)):
        count[P[i]] += 1
    return count

######################################################################
# SOCIAL CHOICE FUNCTION
######################################################################
"""
The social choice function that returns an election outcome for a
given profile with the tally results that are given in count[1..t].
The election outcome is typically an integer
(e.g. the most common ballot type), but can be any arbitrary
Python object that can be compared for equality.

There are many ways this routine could be coded, depending on the
choice of voting system; any (deterministic) voting system could
be used.

For our purposes, it is important that the social choice function f be
well-defined even for non-integer counts, since our Dirichlet
approximations will give non-integral values.  This is OK, since
almost all voting systems are based on comparing vote totals of
various sorts, and integrality of vote totals is not required.

In practice, one may want to disallow "undervote" and "overvote" from
winning, if they are ballot types.  This may be accomplished by 
supplying an extra (optional) argument to f, a dictionary that
supplies additional parameters and information to f (in a way
that may depend on f, of course).  See the example for plurality
below.
"""

def f_plurality(count,params=None):
    """
    A simple example social choice function -- plurality elections.

    Here we assume that the most common ballot type "wins", with 
    ties broken in favor of the lower-numbered outcome.

    If params is supplied to f_plurality, it should be a dict such that
        params['invalid'] is a list of outcomes that are not be allowed to win.
    For example, f(count,{'invalid':[1]}) will not allow outcome 1.
    You can use closures to get the desired binding of params in
    social choice function, e.g.
            g = lambda count: f_plurality(count,{'invalid',[1]})
    defines social choice function g that embeds the desired params
    into f_plurality; g only takes count as an argument (the params
    are now implicit).
    """
    t = len(count)-1
    if params != None:
        invalid_list = params.get('invalid',[])
    else:
        invalid_list = []
    outcome = 1
    while outcome < t and outcome in invalid_list:
        outcome += 1
    for j in xrange(outcome+1,t+1):
        if count[j]>count[outcome] and outcome not in invalid_list:
            outcome = j
    return outcome

def test_f_plurality():
    """ 
    Simple test routine for social choice function f_plurality.
    """
    P = [dummy]+[1, 1, 2, 0, 3, 1, 2]
    t = 3
    print "profile", P[1:]
    count = tally(P,t)
    print "outcome = ", f_plurality(count)
    # ==> 1

    P = [dummy]+[1, 2, 1, 2, 3, 4, 6]
    print P[1:]
    t = 6
    count = tally(P,t)
    print "outcome = ", f_plurality(count,{'invalid':[1]})
    # ==> 2

# test_f_plurality()

######################################################################
# MAKE LIST OF HYPERPARAMETER MATRICES OR VECTORS
######################################################################

def make_prior_list(audit_type,t,ballot_polling):
    """
    return list of  t x t  prior matrices if comparison audit
    return list of  t      prior vectors if ballot-polling audit
    audit_type is one of (where c is an integer):
        "N"                -- non partisan (uniform) all hyperparameters = 1 (same as N1)
        "Nc"               -- non partisan (uniform) all hyperparameters = c
        "P"                -- partisan: list of t matrices each all zeros except one column = to 1 (same as P1)
        "Pc"               -- partisan: list of t matrices each all zeros except one column = to c
        "NP"               -- N union P
        "NPc"              -- Nc union Pc
    Each matrix is t x t with integer entries (with dummy entries to account for 0-indexing of lists).
    """
    prior_list = [ ]
    c_digits = [ d for d in audit_type if d in string.digits ]
    if c_digits != [ ] :
        c = int(string.join(c_digits,sep=""))
    else:
        c = 1
    if not ballot_polling:
        if "N" in audit_type:
            prior_list += [ [dummy] + 
                            [ [dummy]+[c]*t for j in xrange(1,t+1) ]      # just one matrix, c's everywhere
                          ]
        if "P" in audit_type:
            prior_list +=  [ [dummy] + [ [dummy]+[0]*(k-1) + [c] + [0]*(t-k) for j in xrange(1,t+1) ]    # one for each type k
                             for k in xrange(1,t+1)                   
                             ] 
    else: # ballot polling
        if "N" in audit_type:
            prior_list +=  [ [dummy] + [c]*t ]                            # just one vector of all c's
        if "P" in audit_type:
            prior_list += [ [dummy]+[0]*(k-1) + [c] + [0]*(t-k)          # one for each type k
                            for k in xrange(1,t+1)                   
                            ]
    return prior_list

# print make_prior_list("N2",3,True)
#   --> [[-9, 2, 2, 2]]
# print make_prior_list("P2",3,True)
#   --> [[-9, 2, 0, 0], [-9, 0, 2, 0], [-9, 0, 0, 2]]
# print make_prior_list("N2",3,False)
#   --> [ [-9, [-9, 2, 2, 2], [-9, 2, 2, 2], [-9, 2, 2, 2]] ]
# print make_prior_list("P2",3,False)
#   --> [ [-9, [-9, 2, 0, 0], [-9, 2, 0, 0], [-9, 2, 0, 0]], 
#         [-9, [-9, 0, 2, 0], [-9, 0, 2, 0], [-9, 0, 2, 0]], 
#         [-9, [-9, 0, 0, 2], [-9, 0, 0, 2], [-9, 0, 0, 2]]]

######################################################################
# MAKE AUDITING SCHEDULE
######################################################################

def make_schedule(n,pattern):
    """
    Make up an auditing schedule (a list of sample size s values to use)
    start with 0
    do pattern, then pattern repeated by multipied by last/first, etc.
    end with n
    note that last/first does not need to be an integer.
    make_schedule(1000,[1,2])         # --> 0,1,2,4,8,16,32,64,128,256,512,1000
    make_schedule(1000,[1,2,5,10])    # --> 0,1,2,5,10,20,50,100,200,500,1000
    make_schedule(1000,[5,6])         # --> 0,5,6,7,8,10,12,14,17,21,25,30,37,44,53,64,77,...
    """
    schedule = [ 0 ]
    multiplier = 1
    next_s = 1
    while schedule[-1] < n:
        for x in pattern:
            next_s = int(x*multiplier)
            next_s = min(n,next_s)
            if next_s > schedule[-1]:
                schedule.append(next_s)
        multiplier *= float(pattern[-1])/float(pattern[0])
    return schedule

######################################################################
# AUDIT (top-level dispatch function)
######################################################################

audit_method = "dirichlet"        # switch to control dispatch
                                  # alternative is "polya"

def audit(r,a,t,epsilon,schedule,printing_wanted=True,ballot_polling=False,f=f_plurality,audit_type="N"):
    """
    Audit the election, given reported ballot types (r), actual
    ballot types (a), and an upset probability limit (epsilon).
    Each ballot type should be an integer in the range 1 to t (incl.)    

    ballot_polling=True if we want a ballot-polling audit.

    f is the social choice function (defaults to plurality among ballot types)

    Assumes the ballots already in some "random order"                   
  
    r[0] and a[0] are ignored; only r[1..n] and a[1..n] are considered.

    t = number of ballot types possible (numbered 1...t, inclusive)

    audit_type is one of (where c is an integer) (default is "N"):
        "N"                -- non partisan (uniform) all hyperparameters = 1 (same as N1)
        "Nc"               -- non partisan (uniform) all hyperparameters = c
        "P"                -- partisan: list of t matrices each all zeros except one column = to 1 (same as P1)
        "Pc"               -- partisan: list of t matrices each all zeros except one column = to c
        "NP"               -- N union P
        "NPc"              -- Nc union Pc

    The audit stops when upset probability is at most epsilon for *all* priors in list.

    returns (result, s)
        where result=="OK" if the reported outcome seems OK, else result=="NOT OK"
        and where s == number of ballots examined.
    """

    n = len(r)-1                      # number of ballots in r
    assert len(r) == len(a)           # should have the same length
    assert min(r[1:]) >= 1
    assert max(r[1:]) <= t
    assert min(a[1:]) >= 1
    assert max(a[1:]) <= t

    if audit_method == "dirichlet":
        return audit_dirichlet(r,a,t,epsilon,schedule,printing_wanted,ballot_polling,f,audit_type)
    elif audit_method == "polya":
        import polya
        return polya.audit_polya(r,a,t,epsilon,schedule,printing_wanted,ballot_polling,f,audit_type)
    else:
        print "In audit(): illegal audit_method specification:",audit_method
        quit()

######################################################################
# DIRICHLET DISTRIBUTION
######################################################################

def dirichlet(alphas,n):
    """ 
    Sample from a Dirichlet distribution.
    return n times a Dirichlet random variable generated according to the given alphas.
    note that alphas[0] is dummy to be ignored.
    ignores alphas that are 0 (i.e. generates a zero component here)
    returns vector x of same length as alphas
    """
    # print "alphas",alphas
    t = len(alphas)-1
    x = [dummy] + [0.0]*t
    sumx = 0.0
    for k in xrange(1,t+1):
        if alphas[k]>0.0:
            x[k] = random.gammavariate(alphas[k],1)
            sumx += x[k]
    assert sumx > 0.0
    for k in xrange(1,t+1):
        x[k] = n * x[k] / sumx
    return x

######################################################################
# AUDIT USING DIRICHLET DISTRIBUTION
######################################################################

simcsv = open("/srv/tmp/simlog.csv", "a", 0)
simlog = open("/srv/tmp/simlog.json", "a", 0)
simlog.write("\n")  # add timestamp, argv

def audit_dirichlet(r,a,t,epsilon,schedule,printing_wanted=True,ballot_polling=False,f=f_plurality,audit_type="N"):
    """
    Audit the election, given reported ballot types (r), actual
    ballot types (a), and an upset probability limit (epsilon)
    Each ballot type should be an integer in the range 1 to t (incl.)    

    Assumes the ballots already in some "random order"                   
  
    r[0] and a[0] are ignored; only r[1..n] and a[1..n] are considered.

    t = number of ballot types possible (numbered 1...t, inclusive)

    ballot_polling=True if we want a ballot_polling audit (then r is ignored)

    f is the social choice function (defaults to plurality among ballot types)

    audit_type is one of (where c is an integer):
        "N"                -- non partisan (uniform) all hyperparameters = 1 (same as N1)
        "Nc"               -- non partisan (uniform) all hyperparameters = c
        "P"                -- partisan: list of t matrices each all zeros except one column = to 1 (same as P1)
        "Pc"               -- partisan: list of t matrices each all zeros except one column = to c
        "NP"               -- N union P
        "NPc"              -- Nc union Pc
    returns ("OK",s) if the reported outcome seems OK
    Otherwise it returns ("NOT OK",s)
    where s is the number of ballots examined.
    """

    n = len(r)-1                      # number of ballots in r
    assert len(r) == len(a)           # should have the same length
    assert min(r[1:]) >= 1
    assert max(r[1:]) <= t
    assert min(a[1:]) >= 1
    assert max(a[1:]) <= t

    R = tally(r,t)
    reported_outcome = f(R)
    A = tally(a,t)
    actual_outcome = f(A)

    prior_list = make_prior_list(audit_type,t,ballot_polling)

    if printing_wanted:
        print "%8d = number of ballot types"%t
        print "%8d = number of total ballots"%n
        print "%8.4f = epsilon (upset probabilitylimit)"%epsilon
        print "audit_type = ",audit_type
        print "%8d = number of priors"%len(prior_list)
        for x in R[1:]:
            print "%8d "%x,
        print "= counts of reported ballots (reported outcome is %4d )"%reported_outcome
        for x in A[1:]:
            print "%8d "%x,
        print "= counts of actual ballots   (actual outcome is   %4d )"%actual_outcome
        print "Ballot-polling audit:",ballot_polling
   
    # main loop  -- do samples of given sizes from schedule
    s = 0
    # initialize counts to zero
    if not ballot_polling:
        count = [dummy] + [ [dummy]+[0]*t for j in xrange(1,t+1) ]  # allocate this only once
    else: # ballot-polling
        count = [dummy]+[0]*t                                       # allocate this only once
    for next_s in schedule:
        # audit enough ballots so that s = next_s
        while s < next_s:
            s = s + 1
            # In practice you'd be looking at a paper ballot in the next line;
            # in this code, we assume actual ballot types already available in array a.
            pass   # <-- audit ballot number s here; that is, determine a[s]
            if not ballot_polling:
                count[r[s]][a[s]] += 1
            else:
                count[a[s]] += 1
        # now number of ballots audited is s

        max_upset_prob = -1.0                
        for prior_index, prior in enumerate(prior_list):
            # Determine probability of each outcome (dictionary "wins")
            # Determine u the probability of an election upset
            # Determine z the number of simulated profiles examined within upset_prob_dirichlet routine
            wins,u,z = win_probs(r,a,t,s,n,count,ballot_polling,f,prior)

            import json
            global simlog
            global simcsv
            # want experiment_name, margin, or L, discrepancy_freq, s, trials, upset_prob, prior!
            name = "test"
            simlog.write(json.dumps(dict(name=name, s=s, trials=10000, audit_type=audit_type, upset_prob=u)))
            simcsv.write("{name},{s},{u},10000,{audit_type},{prior_index}\n".format(**locals()))

            if printing_wanted:
                print "After %6d ballots audited, probability of an upset is %7.4f"%(s,u),"(z = %4d simulated profiles)"%z,
                print "(winning probabilities are:",wins,")"
            max_upset_prob = max(u,max_upset_prob)
            breakout = False #True                         # Should we stop early? (Or evaluate other priors?)
            if breakout and  max_upset_prob > epsilon:
                break

        # decide to quit if max_upset prob is at most epsilon
        if max_upset_prob<=epsilon:
            if printing_wanted:
                print "Reported election outcome is OK (%d ballots audited)"%s
                # print "count:",count
            return ("OK",s)
    else:
        if printing_wanted:
            print "Reported election outcome was NOT OK !!! (All %d ballots audited)"%n
        return ("NOT OK",s)
        
def win_probs(r,a,t,s,n,count,ballot_polling=False,f=f_plurality,prior=None,max_trials=10000):
    """
    Use simulation to determine the probability of each outcome.
    s is sample size (so far), 0 <= s <= n
    for comparison audit:
        count[j][k] is number of ballots of reported type j and actual type k (plus hyperparameter prior[j][k]) in ballots 1..s
    for ballot-polling audit
        count[k] is number of ballots of actual type k (plus hyperparameter prior[k]) in ballots 1..s
    ballot_polling is True iff we want a ballot-polling audit
    f is social choice function
    return dictionary mapping outcomes to frequency of winning, upset probability, and max_trials
    """
    R = tally(r,t)                               # tally of reported votes
    if not ballot_polling:                       # only have reported votes if not ballot polling
        reported_outcome = f(R)
    max_trials = 10000                           # determines accuracy of u (upset probability)
    upsets = 0
    B = [dummy] + [0]*t                          # allocate this only once (tally for simulated profile)
    alphas = [dummy] + [0]*t                     # allocate only once (alphas for Dirichlet)
    wins = dict()                                # keep track of number of wins for each outcome
    for j in xrange(1,t+1):
        wins[j] = 0
    if not ballot_polling:                       # comparison audit
        Rrem = [dummy] + [0]*t                   # Rrem[j] is number remaining unaudited of reported type j
        for j in xrange(1,t+1):
            Rrem[j] = R[j]                       # number remaining unaudited of reported type j
        for j in xrange(1,t+1):
            for k in xrange(1,t+1):
                Rrem[j] -= count[j][k]
        for z in xrange(1,max_trials+1):
            for k in xrange(1,t+1):             
                B[k] = 0                         # initialize tally for profile b to zero.
            for j in xrange(1,t+1):              # add in actual counts for ballots audited so far
                for k in xrange(1,t+1):
                    B[k] += count[j][k]
            for j in xrange(1,t+1):              # for each reported type
                for k in xrange(1,t+1):
                    alphas[k] = prior[j][k] + count[j][k]
                ds = dirichlet(alphas,Rrem[j])   # note: Rrem[j] is remaining size of profile of reported type j after sample
                for k in xrange(1,t+1):
                    B[k] += ds[k]                # add to counts for sample
            new_outcome = f(B)
            wins[new_outcome] = wins.get(new_outcome,0)+1
            if new_outcome != reported_outcome:
                upsets += 1
    else: # ballot-polling audit
        for k in xrange(1,t+1):
            alphas[k] = prior[k] + count[k]
        for z in xrange(1,max_trials+1):
            ds = dirichlet(alphas,n-s)           # n-s = number of unaudited ballots
            for k in xrange(1,t+1):
                ds[k] += count[k]                # add counts to dirichlet for simulated ballot tally
            new_outcome = f(ds)
            wins[new_outcome] = wins.get(new_outcome,0)+1
        # for ballot-polling audit, "upset prob" is 1 - max winning prob
        upsets = max_trials - max(wins.values())
    for outcome in wins.keys():
        wins[outcome] = float(wins[outcome])/float(max_trials)
    u = float(upsets) / float(max_trials)
    return wins,u,max_trials
    
