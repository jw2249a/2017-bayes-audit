# polya.py
# Ronald L. Rivest and Emily Shen
# 5/29/12
# Code for working with ``Bayesian Election Audits''
#      Specifically: for running experiments
# The auditing code itself in in bayes.py

# This code is OUT OF DATE and no longer part of the main code base, and is now unused.
# It is less efficient than the method to compute posterior probabilities
# using the Dirichlet approximation.

# For efficiency reasons, it is recommended to run this code with
# "pypy" instead of the standard python interpreter.  It runs about
# 7x faster...

"""
----------------------------------------------------------------------
This code available under "MIT License" (open source).
Copyright (C) 2012 Ronald L. Rivest.

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

import bayes
import random

dummy = -9

def audit_polya(r,a,t,epsilon,schedule,printing_wanted=True,ballot_polling=False,f=bayes.f_plurality,audit_type="N"):
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
    R = tally(r,t)
    reported_outcome = f(R,t)
    A = tally(a,t)
    actual_outcome = f(A,t)

    prior_list = make_prior_list(audit_type,t,ballot_polling)

    if printing_wanted:
        print "%8d = number of ballot types"%t
        print "%8d = number of total ballots"%n
        print "audit_type = ",audit_type
        print "%8d = number of priors"%len(prior_list)
        print "%8.4f = epsilon (upset probability limit)"%epsilon
        for x in R[1:]:
            print "%8d "%x,
        print "Counts of reported ballots (reported outcome is %4d )"%reported_outcome
        for x in A[1:]:
            print "%8d "%x,
        print "Counts of actual ballots   (actual outcome is   %4d )"%actual_outcome
        print "Ballot-polling audit:",ballot_polling
   
    # main loop  -- do samples of given sizes 
    s = 0
    for next_s in schedule:
        # audit enough ballots so that s = next_s
        while s < next_s:
            s = s + 1
            # In practice you'd be looking at a paper ballot in the next line;
            # in this code, we assume actual ballot types already available in array a.
            pass   # <-- audit ballot s here; determine a[s]
        # now number of ballots audited is s

        # Determine u the probability of an election upset
        # Determine z the number of simulated profiles examined within upset_prob routine
        max_upset_prob = -1.0
        for prior in prior_list:
            (u,z) = upset_prob(r,a,t,s,n,ballot_polling,f,prior)
            if printing_wanted:
                print "After %6d ballots audited, probability of an upset is %7.4f"%(s,u),"(z = %4d simulated profiles)"%z
            max_upset_prob = max(u,max_upset_prob)
            breakout = True
            if breakout and max_upset_prob > epsilon:                     # don't bother with other priors
                break

        # decide to quit if upset probability is at most epsilon
        if max_upset_prob<=epsilon:
            if printing_wanted:
                print "Reported election outcome is OK"
            return ("OK",s)
    else:
        if printing_wanted:
            print "Reported election outcome was NOT OK !!! (All %d ballots audited)"%n
        return ("NOT OK",s)
        
def upset_prob(r,a,t,s,n,ballot_polling=False,f=bayes.f_plurality,prior=None):
    """
    Use simulation (via Polya Urn) to determine u, the probability of an upset.
    s is sample size (so far), 0 <= s <= n
    prior is matrix of prior hyperparameters (alphas) prior[j][k] if comparison audit,
         else matrix of prior hyperparameters prior[k] if ballot-polling audit
    return (u,z), where z = number of simulated profiles examined.
    """

    R = tally(r,t)
    reported_outcome = f(R,t)
    max_trials = 250
    upsets = 0

    count = [dummy]+[1]*t               # allocate this only once
    b = [dummy]+[0]*n                   # allocate this only once
    urn = [dummy]+[0]*(n+t)             # allocate this only once
                                        # may need to adjust size if prior changes

    for z in xrange(1,max_trials+1):
        polya(b,r,a,s,t,n,urn,ballot_polling,prior)    # create simulated ballot profile b
        B = tally(b,t)
        new_outcome = f(B,t)
        if new_outcome != reported_outcome:
            upsets += 1
    u = float(upsets) / float(max_trials)
    return (u,z)
    
def polya(b,r,a,s,t,n,urn,ballot_polling=False,prior=None):
    """
    Use Polya's urn to create a simulated ballot profile b 
    Input:
    r,a = arrays of length n for reported and actual ballot types
    s = number of ballots audited so far (so a[1..s] are known)
    t = number of ballot types
    n = number of ballots
    urn = array to use for urn (saves re-allocation and gc time)
    Output:
    b = array to place output
    b[1..s] are correct (copied from actual a[1..s])
    b[s+1..n] are only as reported (copied from reported r[s+1..n]),
              but then are subjected to error model (polya's urn)
    if ballot_polling==True then reported ballot types are ignored            
    """
    for i in xrange(1,s+1):
        b[i] = a[i]
    for i in xrange(s+1,n+1):
        b[i] = r[i]
    # in simulated profile for b[s+1..n]:
    # apply error model to each reported ballot type separately
    # unless we are doing ballot_polling, in which case treat all r[i]'s as 1.        
    if not ballot_polling:        
        if prior == None:   # use uniform prior
            prior = [dummy] + [ [dummy]+[1]*t for i in xrange(1,t+1) ]
        for j in xrange(1,t+1):
            urnsize = 0
            # initialize urn to have prior[j][k] balls of each type k.
            for k in xrange(1,t+1):
                for z in xrange(prior[j][k]):
                    urnsize += 1                              
                    urn[urnsize] = k
            # add in ball for each ballot in sample of reported type j and error type (j,k)
            for i in xrange(1,s+1):
                if r[i] == j:
                    urnsize += 1
                    urn[urnsize] = a[i]
            # remaining positions of reported type j subject to error model (polya urn)
            for i in xrange(s+1,n+1):
                if r[i] == j:
                    b[i] = urn[1+random.randrange(urnsize)]
                    urnsize += 1
                    urn[urnsize] = b[i]
    else: # ballot_polling
        if prior == None:  # use uniform prior (no dependence on j)
            prior = [dummy] + [1]*t 
        urnsize = 0
        # initialize counts for each actual type k to prior[k] 
        for k in xrange(1,t+1):
            for z in xrange(prior[k]):
                urnsize += 1                              
                urn[urnsize] = k
        # add in counts for ballots in sample of each actual type
        for i in xrange(1,s+1):
            urnsize += 1
            urn[urnsize] = a[i]
        # remaining positions subject to error model
        for i in xrange(s+1,n+1):
            b[i] = urn[1+random.randrange(urnsize)]
            urnsize += 1
            urn[urnsize] = b[i]
    # print "   b = ", b[1:]


