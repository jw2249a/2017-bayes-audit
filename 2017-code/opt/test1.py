# test1.py
# Ronald L. Rivest and Karim Husayn Karimi
# August 17, 2017
# Routine to experiment with scipy.optimize.minimize

import scipy.optimize
from scipy.stats import norm

# function to minimize:
def g(xy):
    (x,y) = xy
    print("g({},{})".format(x,y))
    return x + y 

# constraints

noise_level = 0.05

# constraint 1: y <= x/2
def f1(xy):
    (x,y) = xy
    return x/2 - y + noise_level * norm.rvs(0)

# constraint 2: y >= 1/x
def f2(xy):
    (x,y) = xy
    return y - 1.0/x + noise_level * norm.rvs(0)

constraints = [
                { "type": "ineq",
                  "fun": f1
                },
                { "type": "ineq",
                  "fun": f2
                }
               ]

print(scipy.optimize.minimize(g,
                              (11, 5),
                              method = "COBYLA",
                              tol = 0.01,
                              constraints=constraints))

                  
