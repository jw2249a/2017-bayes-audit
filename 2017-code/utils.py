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


