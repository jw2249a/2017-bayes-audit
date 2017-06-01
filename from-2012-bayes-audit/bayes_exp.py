# bayes_exp.py
# Ronald L. Rivest and Emily Shen
# 5/31/12
# Code for working with ``Bayes Post-Election Audits''
#      Specifically: for running experiments
# The auditing code itself in in bayes.py

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

import random
import sys
import time

import bayes  # our auditing code

dummy = -9                            # marker for position 0 in lists

def make_profiles(L,printing_wanted=True):
    """
    Return two ballot profiles (reported and actual, r and a), 
    given a specification.  r and a are shuffled (in same way).
    Also return t and n.

    L is specification: a list of (j,k,freq) tuples
    where j = reported type and k = actual type
    """
    r = [dummy]
    a = [dummy]
    t = 1
    for (j,k,c) in L:
        if printing_wanted:
            print "%8d ballots of reported/actual type (%d,%d)"%(c,j,k)
        r.extend([j]*c)
        a.extend([k]*c)
        t = max(t,j,k)
    n = len(r)-1
    r,a = myshuffle(r,a)
    return r,a,t,n

def myshuffle(r,a):
    """
    Return r and a, after they have been shuffled (in same way).
    r and a must be lists of the same length
    """
    n = len(r)-1
    assert n == len(a)-1
    L = [(random.random(),r[i],a[i]) for i in range(1,n+1)]
    L = sorted(L)           
    r = [dummy]+[x[1] for x in L]
    a = [dummy]+[x[2] for x in L]
    return r,a

def experiment_1(printing_wanted=True):
    if printing_wanted:
        print "Experiment 1. Small error data set."
    L = [ (1,1,600), (1,2,100), (2,2,200) ]
    r,a,t,n = make_profiles(L,printing_wanted)
    schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
    epsilon = 0.05
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)

def experiment_2(printing_wanted=True):
    if printing_wanted:
        print "Experiment 2. Small data set with small error (not sufficient to upset)."
    L = [ (1, 1, 600), (2, 2, 500), (1, 2, 20), (2, 1, 20) ]
    r,a,t,n = make_profiles(L,printing_wanted)
    schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
    epsilon = 0.05
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)
    return result

def experiment_3(printing_wanted=True):
    if printing_wanted:
        print "Experiment 3. No error data set from Checkoway/Sarwate/Shacham (eqn 49, page 11 m=1000)"
    L = [ (1,1,10000), (2,2,40000), (3,3,50000) ]
    r,a,t,n = make_profiles(L,printing_wanted)
    # schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
    # epsilon = 0.01
    schedule = bayes.make_schedule(n,[10,11])
    epsilon = 0.01
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)

def experiment_4(printing_wanted=True):
    if printing_wanted:
        print "Experiment 4. Data set from Checkoway/Sarwate/Shacham (section 3.4, page 9)"
    # ---> Note that their matrix is transpose of ours!!
    # ---> Ballot type 1 corresponds to "None", whereas 2 and 3 are candidates,
    # ---> but this doesn't affect anything here since 1 has no chance of winning.
    L = [ (1,1,1500), (1,2,  400), (1,3,  100),
          (2,1, 300), (2,2,46300), (2,3,  200),
          (3,1, 600), (3,2,  600), (3,3,50000) ]
    # with our procedure, audited only 1420 ballots
    # (with epsilon = 0.01) rather than 2496 ballots for CSS.
    r,a,t,n = make_profiles(L,printing_wanted)
    # schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
    schedule = bayes.make_schedule(n,[10,11])
    epsilon = 0.01
    ballot_polling = True
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,ballot_polling,audit_type="NP20"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)
    return result

def experiment_5(printing_wanted=True):
    if printing_wanted:
        print "Experiment 5. Data set from Checkoway/Sarwate/Shacham (section 3.4, page 9), divided by 10"
    L = [ (1,1,150), (1,2,  40), (1,3,  10),
          (2,1, 30), (2,2,4630), (2,3,  20),
          (3,1, 60), (3,2,  60), (3,3,5000) ]    
    r,a,t,n = make_profiles(L,printing_wanted)
    schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
    epsilon = 0.01
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)
    return result

def experiment_6(printing_wanted=True):
    if printing_wanted:
        print "Experiment 6. Small debugging data set."
    L = [ (1,1,4), (1,2,1),
          (2,1,2), (2,2,3) ]
    epsilon = 0.05
    r,a,t,n = make_profiles(L,printing_wanted)
    schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)
    return result

def experiment_7(printing_wanted=True):
    import polya
    if printing_wanted:
        print "Experiment 7: tracing path of subjective probabilities (uniform prior)."
    L = [ (1,1,5000), (1,2,   0), (1,3,  0),
          (2,1,   0), (2,2,4000), (2,3,  0),
          (3,1,   0), (3,2,   0), (3,3,1000) ]
    epsilon = 0.05
    r,a,t,n = make_profiles(L,printing_wanted)
    w = [dummy]+[0]*n                   # allocate this only once
    urn = [dummy]+[0]*(n+t)             # allocate this only once
    t1 = time.time(); 
    for s in range(0,200,5):
        trials = 1000
        wins = [dummy]+[0]*t                # keep track of wins
        r,a = myshuffle(r,a)
        for trial in xrange(trials):
            polya.polya(w,r,a,s,t,n,urn)    # create simulated ballot profile w
            W = bayes.tally(w,t)
            winner = bayes.f_plurality(W)  
            wins[winner] += 1
        fracs = [ wins[i]/float(trials) for i in range(1,t+1) ]
        print "%5d,"%s,
        for x in fracs:
            print "%7.4f,"%x,
        print
    t2 = time.time()
    if printing_wanted:
        print "Done in %g seconds."%(t2-t1)

def experiment_8(printing_wanted=True):
    if printing_wanted:
        print "Experiment 8. Same as 7, but just one run."
    L = [ (1,1,5000), (1,2,  80), (1,3,  5),
          (2,1,  10), (2,2,4500), (2,3,  5),
          (3,1,   0), (3,2,   0), (3,3,400) ]
    epsilon = 0.05
    r,a,t,n = make_profiles(L,printing_wanted)
    schedule = bayes.make_schedule(n,range(1,1000,10))
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
    t2 = time.time()
    if printing_wanted:
        print "Reported outcome is",result
        print "Done in %g seconds."%(t2-t1)
    return result

def experiment_9(printing_wanted=True):
    print "Experiment 9.  Miscertification rates on example from Checkoway et al., Section 4.1 (48)"
    print "Scaled down to n=1000 ballots, m ranges from 0.5% to 5%, 1000 simulations for each m"
    n=1000
    #L = [ (1, 1,   0), (1, 2,    0), (1, 3,  200),
    #      (2, 1, 200), (2, 2, 4800), (2, 3,  100),
    #      (3, 1,   0), (3, 2,    0), (3, 3, 4700) ]
    m_list = tuple(0.01*m for m in [1, 2, 3, 4, 5])
    epsilon_list = [ 0.00, 0.01, 0.02, 0.05, 0.07, 0.10 ]          # added 0.00 rlr 5/14
    epsilon_list = [ 0.10, 0.07, 0.05, 0.02, 0.01, 0.00 ]          # reverse so we see interesting results first
    num_trials=1000
    for epsilon in epsilon_list:
        print "epsilon=%7.4f"%epsilon
        for m in m_list:
            print "m=%7.4f"%m
            L = [ (1, 1, 0), (1, 2, 0), (1, 3, int(0.4*m*n)),
                  (2, 1, int(0.4*m*n)), (2, 2, int(0.5*n-0.4*m*n)), (2, 3, int(0.2*m*n)),
                  (3, 1, 0), (3, 2, 0), (3, 3, int(0.5*n-0.6*m*n))]
            count_ok=0
            for i in range(num_trials):
                r,a,t,n = make_profiles(L,printing_wanted)
                #schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
                schedule=bayes.make_schedule(n,[1,2])
                t1 = time.time(); 
                (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
                t2=time.time()
                if printing_wanted:
                    print "Reported outcome is",result,"with sample of size",s
                    print "Done in %g seconds."%(t2-t1)
                if result=="OK":
                    count_ok = count_ok+1
            print "epsilon = %7.4f, m = %7.4f, number of miscertifications = %d (out of %d trials)"%(epsilon,m,count_ok,num_trials)

def experiment_10(printing_wanted=True):
    if printing_wanted:
        print "Experiment 10.  Miscertification rates on a near tie."
    L = [(1,1,4999), (1,2,   2),                                       # increased 10x rlr 5/18
         (2,1,   0), (2,2,4999)]
    print "L = ",L
    epsilon_list = [ 0.00, 0.01, 0.02, 0.05, 0.07, 0.1 ]               # added 0.00 rlr 5/14
    num_trials=1000
    seed = 11
    print "random number seed = ",seed
    for epsilon in epsilon_list:
        for audit_type in ["N","P","NP"]:
            random.seed(seed)                 # fix seed, for reproducible results
            count_ok = 0
            for i in range(num_trials):
                r,a,t,n = make_profiles(L,printing_wanted)
                schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
                t1 = time.time(); 
                (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type=audit_type); 
                t2=time.time()
                if printing_wanted:
                    print "trial:",i
                    print "Reported outcome is",result
                    print "Done in %g seconds."%(t2-t1)
                if result=="OK":
                    count_ok = count_ok+1
            print "For audit type %2s, epsilon = %2.2f, number of miscertifications = %d (out of %d trials)"%(audit_type,epsilon,count_ok,num_trials)
    
def experiment_11(printing_wanted=True):
    print "Experiment 11.  Number of ballots audited for no-error example from Checkoway et al., Section 4.3 (49)"
    print "n=100,000 ballots, m ranges from 0.5% to 5%, 100 simulated audits for each m"
    n=100000
    #L = [ (1, 1,   0), (1, 2,    0), (1, 3,  200),
    #      (2, 1, 200), (2, 2, 4800), (2, 3,  100),
    #      (3, 1,   0), (3, 2,    0), (3, 3, 4700) ]
    m_list = tuple(0.01*m for m in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    epsilon = 0.01
    print "epsilon = ",epsilon
    num_trials = 100
    for m in m_list:
        L = [ (1, 1, int(0.1*n)), (1, 2, 0), (1, 3, 0),
              (2, 1, 0), (2, 2, int(0.45*n-0.5*m*n)), (2, 3, 0),
              (3, 1, 0), (3, 2, 0), (3, 3, int(0.45*n+0.5*m*n))]
        for audit_type in ["N","P","NP"]:
            num_audited=0
            for i in range(num_trials):
                r,a,t,n = make_profiles(L,printing_wanted)
                schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
                #schedule=bayes.make_schedule(n,[1,2])
                t1 = time.time(); 
                (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type=audit_type); 
                t2=time.time()
                num_audited = num_audited+s
                if printing_wanted:
                    print "Reported outcome is "+result+" after examining %d ballots"%s
                    print "Done in %g seconds."%(t2-t1)
            avg_num_audited = num_audited / float(num_trials)
            print "m=%7.4f audit_type=%2s avg_num_audited=%5d"%(m,audit_type,avg_num_audited)

def experiment_12(printing_wanted=True):
    print "Experiment 12.  Number of ballots audited for unidirectional error example from Checkoway et al., Section 4.3 (50)"
    print "n=100,000 ballots, m ranges from 0.5% to 5%, 100 simulated audits for each m"
    n=100000
    #L = [ (1, 1,   0), (1, 2,    0), (1, 3,  200),
    #      (2, 1, 200), (2, 2, 4800), (2, 3,  100),
    #      (3, 1,   0), (3, 2,    0), (3, 3, 4700) ]
    m_list = tuple(0.01*m for m in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    epsilon = 0.01
    error = 16/float(100000)
    num_trials = 100
    print "margin m     avg num ballots audited"
    print "--------     -----------------------"
    for m in m_list:
        L = [ (1, 1, int(0.1*n)), (1, 2, int(error*n)), (1, 3, int(error*n)),
              (2, 1, 0), (2, 2, int(0.45*n-0.5*m*n-error*n)), (2, 3, 0),
              (3, 1, 0), (3, 2, 0), (3, 3, int(0.45*n+0.5*m*n-error*n))]
        num_audited=0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
            #schedule=bayes.make_schedule(n,[1,2])
            t1 = time.time(); 
            (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
            t2=time.time()
            num_audited = num_audited+s
            if printing_wanted:
                print "Reported outcome is "+result+" after examining %d ballots"%s
                print "Done in %g seconds."%(t2-t1)
        avg_num_audited = num_audited / float(num_trials)
        print "%7.4f           %d"%(m,avg_num_audited)

def experiment_13(printing_wanted=True):
    print "Experiment 13.  Number of ballots audited for bidirectional error example from Checkoway et al., Section 4.3 (51)"
    print "n=100,000 ballots, m ranges from 0.5% to 5%, 100 simulated audits for each m"
    n=100000
    #L = [ (1, 1,   0), (1, 2,    0), (1, 3,  200),
    #      (2, 1, 200), (2, 2, 4800), (2, 3,  100),
    #      (3, 1,   0), (3, 2,    0), (3, 3, 4700) ]
    m_list = tuple(0.01*m for m in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    epsilon = 0.01
    error = 16/float(100000)
    num_trials = 100
    print "margin m     avg num ballots audited"
    print "--------     -----------------------"
    for m in m_list:
        L = [ (1, 1, int(0.1*n-4*error*n)), (1, 2, int(3*error*n)), (1, 3, int(3*error*n)),
              (2, 1, int(2*error*n)), (2, 2, int(0.45*n-0.5*m*n-3*error*n)), (2, 3, 0),
              (3, 1, int(2*error*n)), (3, 2, 0), (3, 3, int(0.45*n+0.5*m*n-3*error*n))]
        num_audited=0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
            #schedule=bayes.make_schedule(n,[1,2])
            t1 = time.time(); 
            (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
            t2=time.time()
            num_audited = num_audited+s
            if printing_wanted:
                print "Reported outcome is "+result+" after examining %d ballots"%s
                print "Done in %g seconds."%(t2-t1)
        avg_num_audited = num_audited / float(num_trials)
        print "%7.4f           %d"%(m,avg_num_audited)

def experiment_14(printing_wanted=True):
    print "Experiment 14.  Number of ballots audited for bidirectional errors with 2-errors example from Checkoway et al., Section 4.3 (52)"
    print "n=100,000 ballots, m ranges from 0.5% to 5%, 100 simulated audits for each m"
    n=100000
    #L = [ (1, 1,   0), (1, 2,    0), (1, 3,  200),
    #      (2, 1, 200), (2, 2, 4800), (2, 3,  100),
    #      (3, 1,   0), (3, 2,    0), (3, 3, 4700) ]
    m_list = tuple(0.01*m for m in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    epsilon = 0.01
    error = 16/float(100000)
    num_trials = 100
    print "margin m     avg num ballots audited"
    print "--------     -----------------------"
    for m in m_list:
        L = [ (1, 1, int(0.1*n-4*error*n)), (1, 2, int(3*error*n)), (1, 3, int(3*error*n)),
              (2, 1, int(2*error*n)), (2, 2, int(0.45*n-0.5*(m+7*error)*n)), (2, 3, 0),
              (3, 1, int(2*error*n)), (3, 2, 0), (3, 3, int(0.45*n+0.5*(m-7*error)*n))]
        num_audited=0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
            #schedule = bayes.make_schedule(n,[1,2])
            t1 = time.time(); 
            (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
            t2=time.time()
            num_audited = num_audited+s
            if printing_wanted:
                print "Reported outcome is "+result+" after examining %d ballots"%s
                print "Done in %g seconds."%(t2-t1)
        avg_num_audited = num_audited / float(num_trials)
        print "%7.4f           %d"%(m,avg_num_audited)

def experiment_15(printing_wanted=True):
    print "Experiment 15: IRV test."
    import vs       # voting system code 
    A = [ 1, 2, 3 ]                           # candidates (alternatives)
    params = vs.default_params()              # parameters (nothing special needed)
    vs.setup_TB(A,params)                     # establish tie-breaker values
    B123 = 1                    # ballot types in order as generated by vs.perms
    B132 = 2
    B213 = 3
    B231 = 4
    B312 = 5
    B321 = 6
    err = 1        # with err=1 we have an incorrect election
    L = [ (B123,B123,1000), (B123,B132,50*err),
          (B132,B132,1000), (B132,B123,60*err),
          (B213,B213,1200), (B213,B123,40*err),
          (B231,B231, 900), (B231,B213,50*err),
          (B312,B312,1000), (B312,B132,50*err),
          (B321,B321,1000), (B321,B312,100*err) ]
    r,a,t,n = make_profiles(L,printing_wanted)
    schedule = bayes.make_schedule(n,[10,11])
    # schedule = bayes.make_schedule(n,range(1,10000))
    epsilon = 0.001
    # list of voting system methods implemented in vs.py, just for reference:
    #    unanimous_winner
    #    majority_winner
    #    plurality_winners
    #    Condorcet_winner
    #    Borda_winner
    #    minimax_winner
    #    Smith_set
    #    IRV_winner
    #    Schulze_winner
    # following may not work if interface to cvxopt not available
    #    gt_winner
    # set global variable to select which voting system winner computation to use in vs.f_vs
    # print "minimax"
    # vs.vs_winner = vs.minimax_winner    
    print "IRV"
    vs.vs_winner = vs.IRV_winner
    # now do audit
    t1 = time.time(); 
    (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,ballot_polling=False,f=vs.f_vs,audit_type="P"); 
    t2=time.time()
    if printing_wanted:
        print "Reported outcome is ",result,"after examining %d ballots"%s
        print "Done in %g seconds."%(t2-t1)

def experiment_16(printing_wanted=True):
    print "Experiment 16.  Comparison with Stark's single-ballot audit in San Luis Obispo, Measure A, risk limit alpha = 10%"
    print "100 simulated audits"
    epsilon = 0.1
    num_trials = 100
    L = [ (1, 1, 7848), (1, 2, 0), (2, 1, 0), (2, 2, 2764) ]
    num_audited=0
    for i in range(num_trials):
        r,a,t,n = make_profiles(L,printing_wanted)
        schedule = bayes.make_schedule(n,range(1,n+1))
        t1 = time.time(); 
        (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
        t2=time.time()
        num_audited = num_audited+s
        if printing_wanted:
            print "Reported outcome is "+result+" after examining %d ballots"%s
            print "Done in %g seconds."%(t2-t1)
    avg_num_audited = num_audited / float(num_trials)
    print "Average number of ballots audited = %7.2f"%avg_num_audited

def experiment_17(printing_wanted=True):
    print "Experiment 17.  Comparison with Stark's ballot-polling audit in Monterey 2011, risk limit alpha = 10%"
    print "Assumes no errors in reported results, and combines write-ins and Mancini into one candidate as Stark did."
    print "100 simulated audits"
    epsilon = 0.1
    num_trials = 100
    L = [ (1, 1, 1353), (1, 2, 0), (2, 1, 0), (2, 2, 755) ]
    num_audited=0
    s_list = [ ]
    for i in range(num_trials):
        r,a,t,n = make_profiles(L,printing_wanted)
        schedule = bayes.make_schedule(n,range(1,n+1))
        t1 = time.time(); 
        audit_type = "N"
        (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,ballot_polling=True,audit_type=audit_type); 
        t2=time.time()
        num_audited = num_audited+s
        s_list.append(s)
        if printing_wanted:
            print "Reported outcome is "+result+" after examining %d ballots"%s
            print "Done in %g seconds."%(t2-t1)
        print "%d"%s
    avg_num_audited = num_audited / float(num_trials)
    print "Average number of ballots audited = %7.2f"%avg_num_audited
    s_list = sorted(s_list)
    print "Median number of ballots audited = %7.2f"%s_list[len(s_list)/2]

def experiment_18(printing_wanted=True):
    print "Experiment 18.  Single ballot comparison audit on Monterey 2011, Water Management District Director, risk limit alpha = 10%"
    print "Assumes no errors in reported results, and combines write-ins and Mancini into one candidate as Stark did in his ballot-polling audit."
    print "100 simulated audits"
    epsilon = 0.1
    num_trials = 100
    L = [ (1, 1, 1353), (1, 2, 0), (2, 1, 0), (2, 2, 755) ]
    num_audited=0
    for i in range(num_trials):
        r,a,t,n = make_profiles(L,printing_wanted)
        schedule = bayes.make_schedule(n,range(1,n+1))
        t1 = time.time(); 
        (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
        t2=time.time()
        num_audited = num_audited+s
        if printing_wanted:
            print "Reported outcome is "+result+" after examining %d ballots"%s
            print "Done in %g seconds."%(t2-t1)
        print "%d"%s
    avg_num_audited = num_audited / float(num_trials)
    print "Average number of ballots audited = %7.2f"%avg_num_audited

def experiment_19(printing_wanted=True):
    print "Experiment 19.  Comparison with Stark's comparison audit in Stanislaus Oakdale Measure O, risk limit alpha = 10%"
    print "Assumes no errors in reported results, ignores undervotes."
    print "100 simulated audits"
    epsilon = 0.1
    num_trials = 100
    L = [ (1, 1, 1728), (1, 2, 0), (2, 1, 0), (2, 2, 1392) ]
    num_audited=0
    s_list = [ ]
    for i in range(num_trials):
        r,a,t,n = make_profiles(L,printing_wanted)
        schedule = bayes.make_schedule(n,range(1,n+1))
        t1 = time.time(); 
        (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,True,audit_type="N"); 
        t2=time.time()
        num_audited = num_audited+s
        s_list.append(s)
        if printing_wanted:
            print "Reported outcome is "+result+" after examining %d ballots"%s
            print "Done in %g seconds."%(t2-t1)
        print "%d"%s
    avg_num_audited = num_audited / float(num_trials)
    print "Average number of ballots audited = %7.2f"%avg_num_audited
    s_list = sorted(s_list)
    print "Median number of ballots audited = %7.2f"%s_list[len(s_list)/2]
    n49 = len([x for x in s_list if x<49])
    print "Fraction of time bayes audit examines less than 49 ballots:", float(n49)/float(num_trials)

def experiment_20(printing_wanted=True):
    if printing_wanted:
        print "Experiment 20.  Miscertification rates on a near tie."
    L = [(1,1,499), (1,2,2),
         (2,1,0), (2,2,499)]
    epsilon_list = [ 0.07 ]
    num_trials=1000
    for epsilon in epsilon_list:
        count_ok = 0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[1,2,3,4,5,6,7,8,9,10])
            t1 = time.time(); 
            (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
            t2=time.time()
            if printing_wanted:
                print "Reported outcome is",result
                print "Done in %g seconds."%(t2-t1)
            if result=="OK":
                count_ok = count_ok+1
        print "For epsilon = %2.2f, there were %d miscertifications (out of %d trials)"%(epsilon,count_ok,num_trials)

def experiment_21(printing_wanted=True):
    print "Experiment 21: Miscertification on IRV example"
    import vs       # voting system code 
    A = [ 1, 2, 3 ]                           # candidates (alternatives)
    params = vs.default_params()              # parameters (nothing special needed)
    vs.setup_TB(A,params)                     # establish tie-breaker values
    B123 = 1                    # ballot types in order as generated by vs.perms
    B132 = 2
    B213 = 3
    B231 = 4
    B312 = 5
    B321 = 6
    err = 1        # with err=1 we have an incorrect election
    #L = [ (B123,B123,100), (B123,B132,5*err),
    #      (B132,B132,100), (B132,B123,6*err),
    #      (B213,B213,120), (B213,B123,4*err),
    #      (B231,B231, 90), (B231,B213,5*err),
    #      (B312,B312,100), (B312,B132,5*err),
    #      (B321,B321,100), (B321,B312,10*err) ]
    L = [ (B123, B123, 100), (B123, B132, 20),
          (B132, B132, 100), (B132, B123, 24),
          (B213, B213, 120), (B213, B123, 16),
          (B231, B231, 90), (B231, B213, 20),
          (B312, B312, 100), (B312, B132, 20),
          (B321, B321, 100), (B321, B312, 40) ]
    # schedule = bayes.make_schedule(n,range(1,10000))
    #epsilon_list = [0.01, 0.02, 0.05, 0.07, 0.10]
    epsilon_list = [0.01]
    # list of voting system methods implemented in vs.py, just for reference:
    #    unanimous_winner
    #    majority_winner
    #    plurality_winners
    #    Condorcet_winner
    #    Borda_winner
    #    minimax_winner
    #    Smith_set
    #    IRV_winner
    #    Schulze_winner
    # following may not work if interface to cvxopt not available
    #    gt_winner
    # set global variable to select which voting system winner computation to use in vs.f_vs
    # print "minimax"
    # vs.vs_winner = vs.minimax_winner    
    print "IRV"
    vs.vs_winner = vs.IRV_winner
    num_trials = 1000
    for epsilon in epsilon_list:
        count_ok = 0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[10,11])
            # now do audit
            t1 = time.time(); 
            (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,ballot_polling=False,f=vs.f_vs,audit_type="P"); 
            t2=time.time()
            print "Reported outcome is ",result,"after examining %d ballots"%s
            print "Done in %g seconds."%(t2-t1)
            if result=="OK":
                count_ok = count_ok+1
        print "For epsilon = %2.2f, there were %d miscertifications (out of %d trials)"%(epsilon,count_ok,num_trials)

def experiment_22(printing_wanted=True):
    if printing_wanted:
        print "Experiment 22.  Miscertification rates on another toy example."
    L = [ (1,1,401), (1,2, 50), (1,3, 50),
          (2,1, 50), (2,2,350), (2,3,  0),
          (3,1,  0), (3,2,100), (3,3,  0) ]
    epsilon_list = [ 0.01, 0.02, 0.05, 0.07, 0.10 ]
    # num_trials=1000
    num_trials=100
    for epsilon in epsilon_list:
        count_ok = 0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[10,11])
            t1 = time.time(); 
            (result,s)=bayes.audit_dirichlet(r,a,t,epsilon,schedule,printing_wanted,audit_type="P"); 
            t2=time.time()
            if printing_wanted:
                print "Reported outcome is",result
                print "Done in %g seconds."%(t2-t1)
            if result=="OK":
                count_ok = count_ok+1
                print "miscertification trial",i,"s=",s
        print "For epsilon = %2.2f, there were %d miscertifications (out of %d trials)"%(epsilon,count_ok,num_trials)
    
def experiment_23(printing_wanted=True):
    if printing_wanted:
        print "Experiment 23. To compare with go implementation for ballot polling."
    L = [ (1,1,223250), (1,2,225750), (1,3,225200), (1,4,225800) ]
    epsilon_list = [ 0.01, 0.02, 0.05, 0.07, 0.10 ]
    epsilon_list = [ 0.02 ]
    # num_trials=1000
    num_trials=1
    for epsilon in epsilon_list:
        count_ok = 0
        for i in range(num_trials):
            r,a,t,n = make_profiles(L,printing_wanted)
            schedule = bayes.make_schedule(n,[4,5])
            t1 = time.time(); 
            (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,audit_type="N"); 
            t2=time.time()
            if printing_wanted:
                print "Reported outcome is",result
                print "Done in %g seconds."%(t2-t1)
            if result=="OK":
                count_ok = count_ok+1
                print "miscertification trial",i,"s=",s
        print "For epsilon = %2.2f, there were %d miscertifications (out of %d trials)"%(epsilon,count_ok,num_trials)

def experiment_25(printing_wanted=True):
    print "Experiment 25.  Number of ballots audited in stratified audits"

    alln=300000
    # m_list = tuple(0.01*m for m in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    m_list = tuple(0.01*m for m in [1, 2, 5, 10])
    stratum_list = [[.86, False], [.14, True]]
    #stratum_list = [[1.0, True]]
    #stratum_list = [[.95, False], [.05, True]]
    assert sum(p for p, ballot_polling in stratum_list) == 1.0
    epsilon = 0.005
    max_trials = 10000
    num_shuffles = 100
    p_noncvrs = [.10, .20, .30, .40, .50, .60, .70, .80, 1.0]

    print "n=%d ballots, %d shuffles, %d trials for each, epsilon=%f" % (alln, num_shuffles, max_trials, epsilon)
    print "margins to try: %s" % (m_list, )
    print "values of non-CVR selections per CVR selection: %s" % (p_noncvrs, )

    for m in m_list:
        sizes = []
        # Make an L for each stratum fraction in the list of strata, plus one overall one
        for p, ballot_polling in stratum_list + [[1.0, True]]:
            n = alln * p
            sizes.append([ (1, 1, int(0.1*n)), (1, 2, 0), (1, 3, 0),
                   (2, 1, 0), (2, 2, int(0.45*n-0.5*m*n)), (2, 3, 0),
                   (3, 1, 0), (3, 2, 0), (3, 3, int(0.45*n+0.5*m*n))])

        # allL is the final, overall L, leaving one L in sizes for each stratum_list
        allL = sizes.pop()
        audit_type = "N"   # for audit_type in ["N"]: # FIXME: ["N","P","NP"]:

        for p_noncvr in p_noncvrs:
            num_audited=0
            snum_audited=0
            for i in range(num_shuffles):
                schedule_seed = [50, 55]
                schedule=bayes.make_schedule(n, schedule_seed)
                # schedule = [256] # Override for single-shot result

                # First, the overall, non-stratified view:
                print("\nm=%7.4f Non-stratified view" % m)
                r,a,t,n = make_profiles(allL,False)
                print(" tally: %s" % bayes.tally(r, t))
                t1 = time.time();
                (result,s)=bayes.audit(r,a,t,epsilon,schedule,printing_wanted,stratum_list[0][1],audit_type=audit_type,max_trials=max_trials);
                t2=time.time()

                num_audited += s

                if printing_wanted:
                    print "Reported non-stratified outcome is "+result+" after examining %d ballots"%s
                    print "Done in %g seconds."%(t2-t1)

                # Now a stratified view:
                print("\nm=%7.4f Stratified view" % m)
                profiles = []
                for i, L in enumerate(sizes):  # FIXME...
                    r,a,t,n = make_profiles(L,False)
                    print(" tally: %s" % bayes.tally(r, t))
                    # FIXME: deal with count? ballot_polling??
                    profiles.append([r, a, stratum_list[i][1]])

                # t1 = time.time();
                bayes.log_csv('win_probs', ['time', t1, 'margin', m] + stratum_list + ["schedule", schedule_seed])
                bayes.log_csv('tallies', ['time', t1, 'margin', m] + stratum_list + ["schedule", schedule_seed])
                (result,s)=bayes.stratified_audit_dirichlet(profiles,t,epsilon,schedule,printing_wanted,audit_type=audit_type,max_trials=max_trials,p_noncvr=p_noncvr);
                # t2=time.time()

                snum_audited += s
                if printing_wanted:
                    print "Reported stratified outcome is "+result+" after examining %d ballots"%s
                    print "Done in %g seconds."%(t2-t1)
            avg_num_audited = num_audited / float(num_shuffles)
            avg_snum_audited = snum_audited / float(num_shuffles)
            print "----\nm:%.3f p_noncvr:%.2f max_trials:%d num_shuffles:%d audit_type=%2s avg_snum_audited:%d, avg_num_audited:%d,"%(m, p_noncvr, max_trials, num_shuffles, audit_type, avg_snum_audited, avg_num_audited)


def main():
    bayes.setup_csv_logger('tallies')
    bayes.setup_csv_logger('win_probs')

    printing_wanted = True
    if printing_wanted:
        print "Bayes election audit testing...", time.asctime()
    seed = 11
    #random.seed(seed)                 # fix seed, for reproducible results
    for arg in sys.argv[1:]:
        c = int(arg)
        print "Running experiment number:",c
        pw = True
        if c == 1:
            experiment_1(pw)
        elif c==2:
            experiment_2(pw)
        elif c==3:
            experiment_3(pw)
        elif c == 4:
            experiment_4(pw)
        elif c == 5:
            experiment_5(pw)
        elif c == 6:
            experiment_6(pw)
        elif c == 7:
            experiment_7(False)
        elif c == 8:
            experiment_8(pw)
        elif c == 9:
            experiment_9(False)
        elif c == 10:
            experiment_10(False)
        elif c == 11:
            experiment_11(False)
        elif c == 12:
            experiment_12(False)
        elif c == 13:
            experiment_13(False)
        elif c == 14:
            experiment_14(False)
        elif c == 15:
            experiment_15(True)
        elif c == 16:
            experiment_16(False)
        elif c == 17:
            experiment_17(False)
        elif c == 18:
            experiment_18(False)
        elif c == 19:
            experiment_19(False)
        elif c == 20:
            experiment_20(False)
        elif c == 21:
            experiment_21(False)
        elif c == 22:
            experiment_22(False)
        elif c == 23:
            experiment_23(True)
        elif c == 25:
            experiment_25(True)


# cProfile.run("main()")
if __name__=="__main__":
    main()
