# test1.py
# Ronald L. Rivest and Karim Husayn Karimi
# August 17, 2017
# Routine to experiment with scipy.optimize.minimize

import scipy.optimize

# function to minimize:
def g(xy):
    (x,y) = xy
    return x+y

# constraints

# constraint 1: y <= x/2
def f1(xy):
    (x,y) = xy
    return x/2 - y

# constraint 2: y >= 1/x
def f2(xy):
    (x,y) = xy
    return y - 1.0/x

constraints = [
                { "type": "ineq",
                  "fun": f1
                },
                { "type": "ineq",
                  "fun": f2
                }
               ]

print(scipy.optimize.minimize(g, (10, 5), constraints=constraints))

                  
