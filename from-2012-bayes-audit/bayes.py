# bayes.py
# Code for working with Bayes Post-Election Audits
# Ronald L. Rivest and Emily Shen
# 5/31/12
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

######################################################################
# Reminder: this code runs about 7x faster with "pypy" than with     
# the standard python interpreter !  Use pypy!                       
######################################################################
import copy
import math
import random
import string
import time
import operator
import itertools
import logging

dummy = -9                      # dummy value for array position 0
STRATUM_S_INDEX = 3

def setup_csv_logger(name):
    "Configure a logger for producing csv files to /tmp/<name>.csv"

    logger = logging.getLogger(name)
    fh = logging.FileHandler('/tmp/%s.csv' % name)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.setLevel(logging.INFO)


def log_csv(name, fields, level=logging.INFO):
    "Log comma-separated fields to the named logger"

    logger = logging.getLogger(name)
    logger.log(level, ','.join([str(f) for f in fields]))


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

def audit(r,a,t,epsilon,schedule,printing_wanted=True,ballot_polling=False,f=f_plurality,audit_type="N",max_trials=10000):
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
        return audit_dirichlet(r,a,t,epsilon,schedule,printing_wanted,ballot_polling,f,audit_type,max_trials=max_trials)
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

def audit_dirichlet(r,a,t,epsilon,schedule,printing_wanted=True,ballot_polling=False,f=f_plurality,audit_type="N",max_trials=10000):
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
        # FIXME: Note: this count format is different from the one returned by tally().  Make sense?
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
        for prior in prior_list:
            # Determine probability of each outcome (dictionary "wins")
            # Determine u the probability of an election upset
            # Determine z the number of simulated profiles examined within upset_prob_dirichlet routine
            wins,u,z = win_probs(r,a,t,s,n,count,ballot_polling,f,prior,max_trials=max_trials)
            if printing_wanted:
                print "After %6d ballots audited, probability of an upset is %7.4f"%(s,u),"(z = %4d simulated profiles)"%z,
                print "(winning probabilities are:",wins,")"
            max_upset_prob = max(u,max_upset_prob)
            breakout = True
            if breakout and  max_upset_prob > epsilon:                  # don't bother with other priors
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
    max_trials determines accuracy of u (upset probability)
    return dictionary mapping outcomes to frequency of winning, upset probability, and max_trials
    """
    R = tally(r,t)                               # tally of reported votes
    if not ballot_polling:                       # only have reported votes if not ballot polling
        reported_outcome = f(R)
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

        #log_csv('tallies', prefix + [new_outcome == reported_outcome, new_outcome] + tallytot[1:] +
        #    list(itertools.chain.from_iterable([t[1:] for t in tallies])))

    for outcome in wins.keys():
        wins[outcome] = float(wins[outcome])/float(max_trials)
    u = float(upsets) / float(max_trials)

    #log_csv('win_probs', prefix + [u] + wins.values())

    return wins,u,max_trials


def aggregateTallies(*tallies):
    """Return aggregated totals for each ballot type across the tallies.
    Each tally is of the form [dummy, c0, c1, c2, ... ct] where the entries are floats.
    NB this is the type of tally array used in dirichlet(), not the type used in win_probs

    >>> tallies = [[-9, 25800, 114810, 117390], [-9, 4200, 18690, 19110]]
    >>> aggregateTallies(*tallies)
    [-9, 30000, 133500, 136500]
    """

    total = [sum(x) for x in zip(*tallies)]
    total[0] = dummy
    return total


# also need a refactored audit_dirichlet?
# Yes

# "NAH...."
# do this differently?  Split into setup, returning necessary parts,
#  then in to loop part via yield
# and then write new wrapper
#    bayes.stratified_win_probs(strata,t,reported_outcome,prior=None):

# sequence of actions now:
#  audit_dirichlet setup: checks and printing and calculate priors and count
#  loop 0 of audit_dirichlet, thru schedule
#   setup, simulate auditing
#   loops of priors
#     run win_probs for each.
#     => Could instead yield the arguments to be used when calling stratified_win_probs
#

def stratified_audit_dirichlet(strata0,t,epsilon,schedule,printing_wanted=True,f=f_plurality,audit_type="N", max_trials=10000):
    """
    Stratified audit of election, given reported ballot types (r) and actual ballot types (a).

    strata0 is list containing [r, a, ballot_polling] for each stratum.

    Each ballot type should be an integer in the range 1 to t (incl.)

    epsilon is the upset probability limit.

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

    # Do this for each stratum
    Rtallies = []
    Atallies = []
    for stratum in strata0:
        r, a, ballot_polling = stratum

        n = len(r)-1                      # number of ballots in r
        assert len(r) == len(a)           # should have the same length
        assert min(r[1:]) >= 1
        assert max(r[1:]) <= t
        assert min(a[1:]) >= 1
        assert max(a[1:]) <= t

        Rtallies.append(tally(r,t))
        Atallies.append(tally(a,t))

    R = aggregateTallies(*Rtallies)
    reported_outcome = f(R)
    A = aggregateTallies(*Atallies)
    actual_outcome = f(A)

    # Make both prior lists up, then later select the one that matches ballot_polling setting

    prior_list_ballot_polling = make_prior_list(audit_type,t,True)
    prior_list_ballot_comparison = make_prior_list(audit_type,t,False)
    prior_lists = [prior_list_ballot_comparison, prior_list_ballot_polling]

    if printing_wanted:
        print "%8d = number of ballot types"%t
        print "%8d = number of total ballots"%n
        print "%8.4f = epsilon (upset probabilitylimit)"%epsilon
        print "audit_type = ",audit_type
        print "%8d = number of priors"%len(prior_lists[0])
        print prior_lists
        print "= prior_lists"
        for x in R[1:]:
            print "%8d "%x,
        print "= counts of reported ballots (reported outcome is %4d )"%reported_outcome
        for x in A[1:]:
            print "%8d "%x,
        print "= counts of actual ballots   (actual outcome is   %4d )"%actual_outcome
        print "Ballot-polling audit:",ballot_polling

    # main loop  -- do samples of given sizes from schedule
    s = 0

    # build augmented strata, of lists containing [r, a, ballot_polling, s, n, count]
    # Two items are modified after being set initially.
    # FIXME: make this a class. But for now...
    # The "count" member is an array which is updated in place.
    # s needs to be updated via index:
    strata = []
    for stratum in strata0:
        r, a, ballot_polling = stratum

        s = 0
        n = len(r) - 1

        # initialize counts to zero
        if not ballot_polling:
            count = [dummy] + [ [dummy]+[0]*t for j in xrange(1,t+1) ]  # allocate this only once
        else: # ballot-polling
            count = [dummy]+[0]*t                                       # allocate this only once

        strata.append([r, a, ballot_polling, s, n, count, prior_lists[ballot_polling][0]]) # FIXME: not always [0]?

    MARGIN = 0.5
    print("prob of incrementing CVR sample size: %.3f" % MARGIN)

    alls = 0

    for next_s in schedule:
        # audit enough ballots so that s = next_s   FIXME for stratified, by doing some sort of dynamic optimization.
        # For now, alls is just a rough progress indicator

        while alls < next_s:

            for stratum in strata:
                r, a, ballot_polling, s, n, count, prior = stratum

                # For now, since ballot_polling is a factor of 1/margin less efficient, 
                #  just look at fraction MARGIN of all ballot comparison ballots
                if not ballot_polling  or  random.random() < MARGIN:
                    alls += 1
                    s += 1
                    # In practice you'd be looking at a paper ballot in the next line;
                    # in this code, we assume actual ballot types already available in array a.
                    pass   # <-- audit ballot number s here; that is, determine a[s]

                    if not ballot_polling:
                        count[r[s]][a[s]] += 1
                    else:
                        count[a[s]] += 1

                # now number of ballots audited in this stratum is s
                stratum[STRATUM_S_INDEX] = s
                # Note that the "count" list updates in place

        max_upset_prob = -1.0

        # for each stratum? no - that happens in stratified_win_probs
        s = sum(stratum[STRATUM_S_INDEX] for stratum in strata)

        for prior in ["dummy"]: # FIXME prior_lists[]:
            # Determine probability of each outcome (dictionary "wins")
            # Determine u the probability of an election upset
            # Determine z the number of simulated profiles examined within upset_prob_dirichlet routine

            wins,u,z = stratified_win_probs(strata,t,reported_outcome,f, max_trials)

            if printing_wanted:
                print "After %6d ballots (%s) audited, probability of an upset is %7.4f" % ( s, [stratum[STRATUM_S_INDEX] for stratum in strata], u), "(z = %4d simulated profiles)" % z,
                print "(winning probabilities are:",wins,")"

            max_upset_prob = max(u,max_upset_prob)
            # FIXME figure out some new way to deal with multiple priors
            # breakout = True
            # if breakout and  max_upset_prob > epsilon:                  # don't bother with other priors
            #     break

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


# Split win_probs up into two pieces to allow for stratified auditing.
# The inner part is pulled out into tallysim.
# This outer part calls the 

def stratified_win_probs(strata,t,reported_outcome,f=f_plurality,max_trials=10000):
    """
    Use simulation to determine the probability of each outcome.
    strata is list containing [r, a, ballot_polling, s, n, count, prior]
     s is sample size (so far), 0 <= s <= n
    reported_outcome is the reported winner (between 1 and t??)
    for comparison audit:
        count[j][k] is number of ballots of reported type j and actual type k (plus hyperparameter prior[j][k]) in ballots 1..s
    for ballot-polling audit
        count[k] is number of ballots of actual type k (plus hyperparameter prior[k]) in ballots 1..s
    ballot_polling is True iff we want a ballot-polling audit
    f is social choice function
    return dictionary mapping outcomes to frequency of winning, upset probability, and max_trials
    """

    upsets = 0
    wins = dict()                                # keep track of number of wins for each outcome
    for j in xrange(1,t+1):
        wins[j] = 0

    # Make a list of generators, each of which uses tallysim to generate a stream of tallies for a single stratum
    tallyGens = []
    alls = sum(stratum[STRATUM_S_INDEX] for stratum in strata)
    alln = sum(stratum[STRATUM_S_INDEX+1] for stratum in strata)
    prefix = [t, len(strata), alln, alls]
    for stratum in strata:
        r, a, ballot_polling, s, n, count, prior = stratum

        tallyGens.append(tallysim(r,a,t,s,n,count,ballot_polling,f,prior,max_trials))
        prefix += [n, s, ballot_polling]

    # Iterate down the generators for each stratum in parallel
    tallyGenUnion = itertools.izip(*tallyGens)

    #prefix = (["tallies", t, list(itertools.chain.from_iterable([n, s, bp]
    #                        for r, a, bp, s, n, count, prior in strata]))])

    for tallies in tallyGenUnion:
        # zip tallies from the strata together, process outcome
        tallytot = aggregateTallies(*tallies)

        new_outcome = f(tallytot)
        wins[new_outcome] = wins.get(new_outcome,0)+1
        if new_outcome != reported_outcome:
            upsets += 1

        log_csv('tallies', prefix + [new_outcome==reported_outcome, new_outcome] + tallytot[1:] + list(itertools.chain.from_iterable([t[1:] for t in tallies])))

    for outcome in wins.keys():
        wins[outcome] = float(wins[outcome])/float(max_trials)
    u = float(upsets) / float(max_trials)

    log_csv('win_probs', prefix + [u] + wins.values())

    return wins,u,max_trials


def tallysim(r,a,t,s,n,count,ballot_polling=False,f=f_plurality,prior=None,max_trials=10000):
    """generate a stream of max_trials simulated tallies
    >>> random.seed(1)
    >>> Testtallysim()
    vote schedule: [-9, 3, 1, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
    ballots: 22.  tally matrix: [-9, [-9, 4, 0, 0], [-9, 0, 3, 0], [-9, 0, 0, 1]]
    3
    [-9.0, 9.705459245838918, 7.573060990468178, 4.721479763692905]
    [-9, 9.40976301599895, 9.020196080127581, 3.5700409038734686]
    [-9, 10.259647392797337, 6.456717862735404, 5.283634744467258]
    [-9, 9.446967328720465, 7.242269028541547, 5.310763642737989]
    [-9, 9.40976301599895, 9.020196080127581, 3.5700409038734686]
    [-9, 10.259647392797337, 6.456717862735404, 5.283634744467258]
    [-9, 9.446967328720465, 7.242269028541547, 5.310763642737989]
    [[-9, 17.632265147698376, 20.95811624431672, 5.409618607984903], [-9, 20.754257006240735, 17.76187791432313, 5.483865079436132], [-9, 21.509173834010426, 17.399345116233796, 5.091481049755775]]
    2
    1
    1
    """

    R = tally(r,t)                               # tally of reported votes
    B = [dummy] + [0]*t                          # allocate this only once (tally for simulated profile)
    alphas = [dummy] + [0]*t                     # allocate only once (alphas for Dirichlet)
    wins = dict()                                # keep track of number of wins for each outcome
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

            B[0] = z
            # print("tallysim iteration %d" % z)
            yield B[:]  # yield a copy, for combining with other strata and final tabulation

    else: # ballot-polling audit
        for k in xrange(1,t+1):
            alphas[k] = prior[k] + count[k]
        for z in xrange(1,max_trials+1):
            ds = dirichlet(alphas,n-s)           # n-s = number of unaudited ballots
            for k in xrange(1,t+1):
                ds[k] += count[k]                # add counts to dirichlet for simulated ballot tally

            yield ds[:] # yield a copy, for combining with other strata and final tabulation


def Testtallysim(max_trials=3):
    """Test tallysim with a close contest with three candidates, 11 for candidate 1, 10 for 2 and 1 for 3.
    One miscount in second ballot, interpreted as vote for 2.
    """
    a = [-9] + [3] + [1] + [1, 2] * 10
    print("actual vote schedule:   %s" % a)
    r = copy.copy(a)
    r[2] = 2
    print("reported vote schedule: %s" % r)
    t = 3
    s = 8
    n = 22

    ballot_polling = False

    # initialize counts to zero
    if ballot_polling:
        count = [dummy]+[0]*t                                       # allocate this only once
    else: # ballot-polling
        count = [dummy] + [ [dummy]+[0]*t for j in xrange(1,t+1) ]  # allocate this only once

    for si in range(1, s+1):
        if not ballot_polling:
            count[r[si]][a[si]] += 1
        else:
            count[a[si]] += 1

    print("ballots: %d.  sampling %s. sample tally matrix: %s" % (len(r)-1, s, count))

    if ballot_polling:
        prior = [-9, 1, 1, 1]
    else:
        prior = [-9, [-9, 1, 1, 1], [-9, 1, 1, 1], [-9, 1, 1, 1]]

    wins, u, max_trials = stratified_win_probs([[r,a,ballot_polling,s,n,count,prior]],t,1,max_trials=max_trials)
    print("stratified_win_probs: wins = %s, u = %f" % (wins, u))

    wins, u, max_trials = win_probs(r,a,t,s,n,count,ballot_polling,prior=prior,max_trials=max_trials)
    print("win_probs:            wins = %s, u = %f" % (wins, u))

    gen = tallysim(r,a,t,s,n,count,ballot_polling=ballot_polling,prior=prior, max_trials=max_trials)

    tallies = list(gen)

    print("Generated %d tallies" % len(tallies))

    avg = [float(sum(col))/len(col) for col in zip(*tallies)]
    print("Average of tallies: %s" % avg)

    for tally in tallies[:3] + tallies[-3:]:
        print("test tally: %s" % tally)

    print("Run two tallies in parallel")
    tallyGens = ([tallysim(r,a,t,s,n,count,ballot_polling=ballot_polling,prior=prior, max_trials=max_trials),
                  tallysim(r,a,t,s,n,count,ballot_polling=ballot_polling,prior=prior, max_trials=max_trials)])
    tallyGenUnion = itertools.izip(*tallyGens)
    res = []
    for tallyGenSet in tallyGenUnion:
      tallies = [tallyStratum for tallyStratum in tallyGenSet]
      totalTally = aggregateTallies(*tallies)
      res.append(totalTally)

    for tally in res[:3]:
        print("test tally: %s" % tally)

    for totalTally in res[:3]:
        print("test winner: %d" % f_plurality(totalTally))