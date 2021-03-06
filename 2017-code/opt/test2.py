# test2.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# python3

"""
Routine test experiment with random-walk (simulated
annealing-like) optimization routine.

d = number of dimension (e.g. d=64)
x = d-dimensional point
p(x) = probability that an 'experiment' fails at point x
    0 <= p(x) <= 1
We expect that p(x) decrease with increasing x in any
coordinate.

We wish to minimize sum(x), subject to p(x) <= 0.05 say.
"""

import numpy as np

def compute_p(xs, us):
    zs = xs / us                       # normalize to zs in [0,1]
    return 0.10 * (1-np.product(zs))
                                      
def main():

    xs = np.array((500, 500, 500))     # sample increments per pbc
    us = np.array((1000, 1000, 1000))   # upper bounds on sample increments
    d = len(xs)

    steps = 1
    delta = 10
    risk_limit = 0.05
    success_move_prob = risk_limit / (1 - risk_limit)

    while steps < 10000:

        steps += 1
        p = compute_p(xs, us)
        failure = (np.random.uniform() < p)  # just one trial
        i = np.random.choice(range(d))
        print (sum(xs), xs, p, failure, i)
        step_size = delta
        step_size = 200 / np.log(steps)
        if failure:
            xs[i] = min(us[i], xs[i] + step_size)
        elif np.random.uniform() <= success_move_prob:
            xs[i] = max(0, xs[i] - step_size)

main()



