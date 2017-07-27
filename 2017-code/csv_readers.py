# csv_readers.py
# Ronald L. Rivest and Karim Husayn Karimi
# July 27, 2017
# python3

"""
Code to read the various files that multi.py uses from their CSV formats.
"""

"""
All CSV files have a single header line, giving the column (field) names.

For most (non-varlen) file formats, a data row must have length no longer than the header row,
and missing values are represented as "".

For "varlen" files (files with variable row lengths), it is a little bit 
different: the last header may correspond to 0, 1, 2, or more valuesin a data row.
So the data row may be shorter (by one), equal to, or longer than the header row.
In any case, the values for the last field are *always* compiled into a tuple
(possibly an empty tuple).
The reader returns a list of dictionaries, one per row.
Example (regular csv file):
    A,B,C
    1,2,3
    4,5
becomes:
    [ {'A':'1', 'B':'2', 'C':'3'},
      {'A':'4', 'B':'5', 'C':''} 
    ]
Example: (varlen csv file)
    A,B,C
    1,2,3
    4,5
    6,7,8,9
becomes:
    [ {'A':'1', 'B':'2', 'C':('3',)},
      {'A':'4', 'B':'5', 'C':()},
      {'A':'6', 'B':'5', 'C':(8,9)},
    ]
"""

import csv

import ids
import utils


def read_csv_file(filename, expected_fieldnames=None, varlen=False):
    """
    Read CSV file and check expected fieldnames; varlen if variable-length rows.
    """

    # print("Reading CSV file:", filename)
    with open(filename) as file:
        reader = csv.reader(file)
        rows = [row for row in reader]
        fieldnames = rows[0]
        rows = rows[1:]
        
        # gather, clean, and trim field names, eliminating blanks
        fieldnames = [ids.clean_id(fieldname) for fieldname in fieldnames]
        while len(fieldnames)>0 and fieldnames[-1]=='':
            fieldnames.pop()
        if len(set(fieldnames)) != len(fieldnames):
            utils.myerror("Duplicate field name:"+fieldnames)

        # data rows
        row_dicts = []
        for row in rows:
            row = ["" if item==None else ids.clean_id(item) for item in row]
            while len(row)>0 and row[-1] == '':
                row.pop()
            if not varlen:
                if len(row) > len(fieldnames):
                    utils.mywarning("Ignoring extra values in row:"+str(row))
                    row = row[:len(fieldnames)]
                while len(row) < len(fieldnames):
                    row.append("")
            row_dict = {}
            for (fieldname, value) in zip(fieldnames, row):
                row_dict[fieldname] = value
            if varlen:
                if len(row) < len(fieldnames)-1:
                    if len(row) > 0:
                        utils.mywarning("Ignoring too-short row:"+str(row))
                    continue
                last_fieldname = fieldnames[-1]
                last_value = tuple(row[len(fieldnames)-1:])
                row_dict[last_fieldname] = last_value
            row_dicts.append(row_dict)
        if expected_fieldnames!=None:
            expected_fieldnames = [ids.clean_id(id) for id in expected_fieldnames]
            if expected_fieldnames != fieldnames:
                utils.myerror("File {} has fieldnames {} instead of expected {}."
                              .format(filename, fieldnames, expected_fieldnames))
        return row_dicts


if __name__=="__main__":

    filename = "test_data/csv_readers_test_reg.csv"
    print("Regular (non-varlen) csv file:", filename)
    for row in read_csv_file(filename):
        for fieldname in sorted(row):
            print("{}:'{}' ".format(fieldname, row[fieldname]), end='')
        print()

    filename = "test_data/csv_readers_test_varlen.csv"
    print("Varlen csv file:", filename)
    for row in read_csv_file(filename, varlen=True):
        for fieldname in sorted(row):
            print("{}:'{}' ".format(fieldname, row[fieldname]), end='')
        print()


    
