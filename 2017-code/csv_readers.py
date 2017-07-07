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
In any case, the selections for a vote file row are compiled into
a tuple.

The reader returns a list of dictionaries, one per row.
"""

import csv

def clean_id(id):
    """ 
    Return id with initial and final whitespace removed, and
    with any internal whitespace sequences replaced by a single
    blank.  Also, all nonprintable characters are removed.
    """

    id = id.strip()
    new_id = ""
    for c in id:
        if c.isspace():
            c = " "
        if (c != " " or (len(new_id)>0 and new_id[-1] != " ")) \
           and c.isprintable():
            new_id += c
    return new_id


def read_csv_file(filename, votefile=False):

    with open(filename) as file:
        reader = csv.DictReader(file)
        rows = [row for row in reader]
        for row in rows:
            if None in row and not votefile:
                # raise Exception("Too many values in row:"+str(row))
                print("Warning: Too many values in row:"+str(row))
                del row[None]
            for fieldname in reader.fieldnames:
                clean_fieldname = clean_id(fieldname)
                if clean_fieldname != fieldname:
                    if clean_fieldname in row:
                        print("Warning: field name given twice:", clean_fieldname)
                    row[clean_fieldname] = row[fieldname]
                    del row[fieldname]
                    fieldname = clean_fieldname
                if row[fieldname] == None:
                    row[fieldname] = ""
                if isinstance(row[fieldname], str):
                    row[fieldname] = clean_id(row[fieldname])
            if votefile:
                lastfieldname = clean_id(reader.fieldnames[-1])
                if row[lastfieldname] == None:
                    value = ()
                elif None not in row:
                    value = (row[lastfieldname],)
                else:
                    value = tuple([row[lastfieldname]] + \
                                   [clean_id(id) for id in row[None]])
                    del row[None]
                row[lastfieldname] = value
        return rows


if __name__=="__main__":
    print("Regular csv file:")
    for row in read_csv_file("test_reg.csv"):
        print([(fn, row[fn]) for fn in sorted(row)])
    print("Vote csv file:")
    for row in read_csv_file("test_vote.csv", votefile=True):
        print([(fn, row[fn]) for fn in sorted(row)])
    



