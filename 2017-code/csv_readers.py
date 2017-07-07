# csv_readers.py
# Ronald L. Rivest and Karim Husayn Karimi
# July 7, 2017
# python3

"""
Code to read the various files that multi.py uses from their CSV
formats, and put the results into the Election data structure.
"""

"""
All CSV files have a single header line, giving the column (field) names.

For most file formats, a data row must have length no longer than the header row.

For vote files, it is a little bit different:
the last header is called "Selections", and there may
be 0, 1, 2, or more selections made by the voter.  So the data row
may be shorter (by one), equal to, or longer than the header row.
In any case, the selections for a vote file row and compiled into
a tuple.
"""




