# f.py
# Ronald L. Rivest and Karim Husayn Karimi
# August 4, 2017
# python3

"""Implement function f(b_1, ..., b_k) for
optimization studies of auditing sampling plan.

From email of today to Husayn:

We suppose we have  k  strata.   

Within each stratum, we have a choice as to how many new ballots to
sample.

Let b_i denote the recommended number of new ballots to sample in
stratum i.

Let s_i denote the number of ballots already sample in stratum i.

Let n_i denote the total size of stratum i

Then b_i is constrained: 0 <= b_i <= n_i - s_i .

We have a k-dimensional search problem.  

The variables we can choose are the b_i 's.  They are constrained as
noted.

We can let s'_i denote s_i + b_i, the new size of the sample in
stratum i.

We wish to minimize sum(b's) subject to 
    f(b's) <= risk_limit, 
where f  measures the risk.

There are lots of ways to approach this problem, and there exist
library packages in python (numpy) for doing such optimization.  

To make things even more concrete, let me suggest a particular special
case of our problem, yielding a particular way of computing f.  This
is only an example, a simple model, useful for testing our ideas...

We assume a single contest, and assume that a vote is a real number
(positive or negative).   

Let x_{ij} denote the j-th ballot in stratum i, for i = 1, ..., k and
j = 1, ..., n_i.

The contest is determined by whether the sum of all of the votes is
positive or not.  Alice wins if the sum is positive; otherwise Bob wins.

Suppose Alice is the reported winner.  

Then the risk is the chance that the sum of all the votes is negative.

We assume that each  x_{ij}  is normally distributed with mean  mu_i 
that depends on i  (but not on j).  

So different strata have different biases.

Let  m_i  denote the mean value observed so far of the values  x_{ij}
for x_{ij} in the sample of size s_i for stratum i.

Then, given what we have seem from the sample in the i-th stratum,
our estimate of the sum of the votes in the entire i-th stratum is just
X_i, where 

      E(X_i)  =  m_i  n_i

The auditor may assume that the actual value is close to this.  Indeed,
the variance of this estimate  is   n_i^2 / s_i .   

Thusly: the variance of our estimate m_i of mu_i is (roughly) 1/s_i, 
and we are scaling up by a factor of (n_i/s_i), and this
is quadratic, so  (n_i/s_i)^2 / s_i = n_i^2 / s_i .

So, in our experiments, we can compute  f(s_1, ..., s_k)  as

      f(s_1, ..., s_k) = Prob ( sum(X_i) < 0 )

where

      X_i ~ N( m_i n_i , n_i^2 / s_i )

(That is, X_i is normally distributed with mean  m_i n_i and variance
n_i^2 / s_i .)

This can be computed using 

       f(s_1, ..., s_k) = scipy.random.norm(X, V).cdf(0)

where

       X was computed as sum(X_i)
       and each X_i is as above

and

      V = sum_i  (n_i^2 / s_i)

So, for a particular  b_1, ..., b_k,  we look at
s'_1, ..., s'_k  where   s'_i = s_i + b_i, and evaluate
f(s'_1, ..., s'_k).
"""


import numpy as np
import scipy.stats

class PQ(object):
    """ PQ is problem spec/state for optimization. """

    def __init__(self, mu, s, n):
        """ 
        mu is dim-k vector of reals (true means of votes)
        s is dim-k vector of integers (sample sizes so far)
        n is dim-k vector of integers (strata sizes)
        """
        
        mu = np.array(mu)
        s = np.array(s)
        n = np.array(n)

        assert all(0<s) and all(s<=n)

        self.mu = mu
        self.s = s
        self.n = n

        # m is dim-k array of observed sample means
        self.m = scipy.stats.norm.rvs(mu)   

    def f(self, b):
        """
        Return 'risk' associated with dim-k vector b
        of additional sample sizes
        """

        b = np.array(b)
        assert all(np.zeros(len(b))<=b) and \
               all(b<=self.n-self.s)

        Vs = self.n*self.n/(self.s+b)
        EX = sum(self.m*self.n)
        SDX = np.sqrt(sum(Vs))
        print(EX, SDX)

        return scipy.stats.norm.cdf(0, loc=EX, scale=SDX)

P = PQ( (0.100, -0.001),         # mu's
        (30, 50),                # s's
        (10000, 1000000))        # n's

print(P.f((0, 0)))
print(P.f((100, 0)))
print(P.f((0, 100)))
print(P.f((100, 100)))

