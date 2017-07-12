# utils.py
# Ronald L. Rivest
# July 8, 2017
# python3

"""
Code to work with multi.py on post-election audits.
Various utilities.
"""

import datetime
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
    raise Exception


warnings_given = 0


def mywarning(msg):
    """ Print error message, but keep going.
        Keep track of how many warnings have been given.
    """

    global warnings_given
    warnings_given += 1
    print("WARNING:", msg)


##############################################################################
## using an id as a counter (for ballot manifest expansion)


def count_on(start, num):
    """ 
    Return a list of values, starting with "start", of total length num. 

    Here start may be an integer, in which case we just return a list of
    integers.

    Otherwise start may be a string, ending in a decimal field; we increment
    within that decimal field.
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

if __name__=="__main__":
    test_count_on()


    
