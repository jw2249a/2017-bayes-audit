# utils.py
# Ronald L. Rivest
# July 8, 2017
# python3

"""
Code to work with multi.py on post-election audits.
Various utilities.
"""

import datetime
import numpy as np
import os
import sys

##############################################################################
# datetime
##############################################################################


def datetime_string():
    """ Return current datetime as string e.g. '2017-06-26-21-18-30' 
        Year-Month-Day-Hours-Minutes-Seconds
        May be used as a version label in an output filename.
    """
    # https://docs.python.org/3.6/library/datetime.html

    t = datetime.datetime.now()
    return t.strftime("%Y-%m-%d-%H-%M-%S")

def date_string():
    """ Return current date as string e.g. '2017-06-26' 
        Year-Month-Day
        May be used as a version label in an output filename.
    """
    # https://docs.python.org/3.6/library/datetime.html

    t = datetime.datetime.now()
    return t.strftime("%Y-%m-%d")



##############################################################################
# myprint  (like logging, maybe, but maybe simpler)
##############################################################################

myprint_files = {"stdout": sys.stdout}

def myprint(*args, **kwargs):
    """ variant print statement; prints to all files in myprint_files. """

    for output_file_name in myprint_files:
        kwargs["file"] = myprint_files[output_file_name]
        print(*args, **kwargs)


def close_myprint_files():
    """ Close myprint files other than stdout and stderr. """

    for output_file_name in myprint_files:
        if output_file_name not in ["stdout", "stderr"]:
            myprint_files[output_file_name].close()
            del myprint_files[output_file_name]


# error and warning messages


def myerror(msg):
    """ Print error message and halt immediately """

    print("FATAL ERROR:", msg)
    quit()


warnings_given = 0


def mywarning(msg):
    """ Print error message, but keep going.
        Keep track of how many warnings have been given.
    """

    global warnings_given
    warnings_given += 1
    print("WARNING:", msg)


##############################################################################
# Input/output at the file-handling level
##############################################################################

def greatest_name(dirpath, startswith, endswith, dir_wanted=False):
    """ 
    Return the filename (or, optionally, directory name) in the given directory 
    that begins and ends with strings startswith and endswith, respectively.
    If there ts more than one such file, return the greatest (lexicographically)
    such filename.  Raise an error if there are no such files.
    The portion between the prefix startswith and the suffix endswith is called
    the version label in the documentation.
    If switch "dir_wanted" is True, then return greatest directory name, not filename.
    Example:  greatest_name(".", "foo", ".csv")
    will return "foo-11-09.csv" from a directory containing files
    with names  "foo-11-09.csv", "foo-11-08.csv", and "zeb-12-12.csv".
    """

    selected_filename = ""
    for filename in os.listdir(dirpath):
        full_filename = os.path.join(dirpath,filename)
        if (dir_wanted == False and os.path.isfile(full_filename) or \
            dir_wanted == True and not os.path.isfile(full_filename)) and\
           filename.startswith(startswith) and \
           filename.endswith(endswith) and \
           filename > selected_filename:
            selected_filename = filename
    if selected_filename == "":
        if dir_wanted == False:
            utils.myerror("No files in `{}` have a name starting with `{}` and ending with `{}`."
                          .format(dirpath, startswith, endswith))
        else:
            utils.myerror ("No directories in `{}` have a name starting with `{}` and ending with `{}`."
                           .format(dirpath, startswith, endswith))
    return selected_filename


##############################################################################
## Using an id as a counter (for ballot manifest expansion)
##############################################################################


def count_on(start, num):
    """ 
    Return a list of values, starting with "start", of total length num. 

    Here start may be an integer, in which case we just return a list of
    integers.

    Otherwise start may be a string, ending in a decimal field; we increment
    within that decimal field.  If there is no decimal field suffix to start,
    then one is added, with an initial value of 1, but only if num>1.
    Size of decimal suffix field is preserved, unless we need to expand it
    for larger integers.
    """

    assert num >= 0

    if num <= 0:
        return []
    if num ==1:
        return [start]
    if isinstance(start, int):
        return list(range(start, start+num))
    assert isinstance(start, str)
    prefix = list(start)
    digits = []
    while len(prefix)>0 and prefix[-1].isdigit():
        digits.append(prefix.pop())
    digits.reverse()
    if digits==[]:
        digits=["1"]
    counter = int("".join(digits))
    prefix = "".join(prefix)
    template = "{{:0{}d}}".format(len(digits))
    ans = [prefix + template.format(counter+i) \
           for i in range(num)]
    return ans


def test_count_on():

    for start, num in [(1,3), ("x", 3), ("A-98", 3), ("y", 1)]:
        print(start, num, end=" ==> ")
        print(count_on(start, num))
    """
    1 3 ==> [1, 2, 3]
    x 3 ==> ['x1', 'x2', 'x3']
    A-98 3 ==> ['A-98', 'A-99', 'A-100']
    y 1 ==> ['y']
    """

# test_count_on


##############################################################################
## Convert to array of 32-bit values
##

def convert_int_to_32_bit_numpy_array(v):
    """
    Convert value v, which should be an arbitrarily large python integer
    (or convertible to one) to a numpy array of 32-bit values, 
    since this format is needed to initialize a numpy.random.RandomState 
    object.  More precisely, the result is a numpy array of type int64, 
    but each value is between 0 and 2**32-1, inclusive.

    Example: input 2**64 + 5 yields np.array([5, 0, 1], dtype=int)
    """

    try:
        v = int(v)
        if v<0:
            raise ValueError
    except ValueError:
        myerror("{} is not a nonnegative integer, or convertible to one.".format(v))
    v_parts = []
    radix = 2**32
    while v>0:
        v_parts.append(v % radix)
        v = v // radix
    # note: v_parts will be empty list if v==0, that is OK
    return np.array(v_parts, dtype=int)
        
def RandomState(seed):
    """
    Return a np.random.RandomState object, initialized
    from an arbitrarily-large non-negative integer seed.

    The numpy.random.RandomState object does not take long integers
    (more than 2**32-1) as input, although it will take as input a
    numpy.array of int64's to initialize the RandomState, as long as
    each element of that array is between 0 and 2**32-1, inclusive.
    This can be problematic for our audit, as the audit seed may well
    be a 20-digit integer.

    Thus, utils.py now has the routine
        utils.RandomState(seed)
    which takes as input an arbitrarily large nonnegative integer seed,
    and returns a numpy.random.RandomState object initialized via
    an a numpy.array object
    initialized from seed.
    """

    seed_as_array = convert_int_to_32_bit_numpy_array(seed)
    return np.random.RandomState(seed_as_array)


if __name__=="__main__":
    pass


    
