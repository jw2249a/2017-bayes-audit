# Documentation for multi.py (Bayesian audit support program)

``multi.py`` is Python3 software (or suite of programs) to support
the post-election auditing of elections with multiple contests and
multiple separately-managed collections of paper ballots.

The software is designed to be helpful for auditing elections such as
the November 2017 Colorado election, which has hundreds of contests
spread across 64 counties.

**This README file is a *design document*, not a description of
what the code does now.  The code here is still very fragmentary,
alsmot entirely non-functional, and built according to a rather
different specification.  It is in the process of becoming code that
matches this design document.  But don't expect it to match what is
described here.  At least not yet.**

## Election and audit

We assume the following:
* a number of **contests** (for now, all plurality contests),
* a number of **voters**,
* a single **paper ballot** from each voter,
* paper ballots organized into a set of disjoint **collections**
      (for example, one or a few collections per county),
* a **collection manager** for each collection (may be the same
  manager for several collections),
* all ballots in a collection have the same **ballot style** (that is,
  they show the same contests on each ballot in the collection),
  (** THIS IS BEING FIXED **)
* for a given contest, there may be one or several collections having ballots
  showing that contest,

We assume that the election has the following components:
1. ("_Pre-election_") Election definition and setup.
2. ("_Election_") Vote-casting, interpretation and preliminary reporting.
3. ("_Post-election_") Audit.
4. ("_Certification_") Certification.

## Scanning of cast paper ballots

We assume that all the paper ballots in each collection have been **scanned** by
an **optical scanner**.  There may be a different scanner for each collection.

We distinguish two types of collections, according to the type of information
produced by the scanner:
* in a "**CVR collection**", the scanner produces an electronic **cast vote
  record** (CVR) for each paper ballot scanned, giving the choices made for each
  contest on that paper ballot.
* in a "**noCVR collection**", the scanner does not produce a separate
  electronic record for each paper ballot scanned; it only produces a summary
  tally showing for each contest and each possible choice (vote) on that
  contest, how many ballots in the collection showed the given choice.
Note that some contests may be associated with collections of both types:
some CVR collections as well as some noCVR collections.

We assume that the vote-casting, scanning, and subsequent storage
process yields a "**ballot manifest**" for each collection,
specifying how many paper ballots are in the collection, how they are
organized, and how they are stored.  The ballot manifest defines the
population of paper ballots in the collection that will be sampled
during the audit.

Some elections have so many contests that the ballot is comprised of
two or more separate "cards".  We do not deal with this complexity; we
assume in such multi-card cases that the cards for a single ballot are
always kept together. (Obviously a false assumption in practice.)

## Auditing

A post-election audit provides statistical assurance that the reported
outcomes are correct (if they are), using computations on a small
random sample of the cast paper ballots.  Audits are often several
orders of magnitude more efficient than doing a full manual recount of
all cast paper ballots.

``Multi.py`` supports "Bayesian" audits, a form of post-election auditing
proposed by 
[Rivest and Shen (2012)](http://people.csail.mit.edu/rivest/pubs.html#RS12z).

A Bayesian audit provides an answer to the question 
"``What is the probability that the reported election outcome is wrong?``"
We call this probability the **Bayesian risk** perceived for the reported
outcome, given the audit data.

A Bayesian audit continues to draw ballots at random for manual
examination and interpretation, until the estimated Bayesian risk
drops below a prespecified risk limit (such as 5%) for all contests.
With typical contests, only a small number of ballots may need to be
examined before the risk limit is reached and the audit stops.
Contests that are very close, however, may require extensive sampling
before the risk limits are reached.

See Rivest (''Bayesian audits: Explained and Extended'', draft available
from author) for an expanded discussion of Bayesian audits.

Bayesian risk-limiting audits are subtly different than the ``frequentist'' risk-limiting
audits promulgated by Stark and others.
(REFS) Details omitted here, but Bayesian audits provide additional
capabilities and flexibility, at the cost of some additional (but still
very reasonable) computation during the audit.

We assume the existence of an **Audit Coordinator** who coordinates
the audit in collaboration with the collection managers (the
Coordinator might be from the Secretary of State's office).

## Implementation notes: identifiers, votes, file names, and directory structure

This section describes some low-level but essential details regarding
the use of identifiers in ``multi.py``, the way in which votes in a contest are
represented as a sets of identifiers, 
use of CSV file formats,
how transparency and reproducibility
are supported by the use of file names that include version labels, and
how ``multi.py`` structures information in a directory.

### Identifiers

The data structures for ``multi.py`` use identifiers extensively.
Identifiers are more-or-less arbitrary strings of characters.

We have:

* **Contest Identifiers** (example: ``"DenverMayor"``)
  A contest identifier is called a ``"cid"`` in the code.

* **Selection Identifiers** (examples: ``"Yes"`` or ``"JohnSmith"``)
  A selection identifier is called a ``"selid"`` in the code.
  Roughly speaking, there should be one selection identifier for each
  optical scan bubble.  If bubble are arranged in a matrix, as
  they might be for preferential voting, score voting, or 3-2-1
  voting, then the selid might have the form "rowid:colid", as
  in "Smith:1" or "Jones:Excellent".
  A **write-in** selection has a selection id beginning with a plus
  sign (example: ``"+BobWhite"``).
  Other potentially useful selection ids include
    1. **``-Unknown``**: Nothing is known about the ballot. It might
       not even contain the desired contest.
    2. **``-Absent``**: The contest is missing from the ballot. Perhaps
       the wrong ballot was pulled.
    3. **``-NoRecord``**: The ballot contains the desired contest, but
       the voter's selection was not recorded.  Perhaps useful if the
       desired contest is no longer being audited.
    4. **``-Invalid``**: The voter selections were invalid somehow.
    5. **``-Expected``**: The ballot style indicates that the ballot
       *should* contain this contest, but the ballot hasn't been
       further examined yet. (Requires a ballot style on the ballot.)
    6. **``-NotExpected``** The ballot style indicates that the ballot
       *should* *not* contain this contest, but the ballot hasn't been
       further examined yet. (Requires a ballot style on the ballot.)

* **Paper Ballot Collection Identifiers** (example: ``"BoulderPBC25"``)
  A paper ballot collection identifier is called a ``"pbcid"`` in the code.

* A **Ballot Identifier** is a unique identifier assigned to a particular
  paper ballot (example: ``"25-72"``).
  A ballot id is called a ``"bid"`` in the code.
  Ballots within a collection must have unique bids, but it is not
  necessary that ballots in different collections have different
  bids.  A ballot id may encode the physical storage location of
  the ballot (e.g. the box number and position within box), but
  need not do so.  The ballot id might or might not include the
  pbcid. The ballot id might be generated when the ballot
  is printed, when it is scanned, or when it is stored.  The
  ballot ids need not be "sequential".

  (CO remark: A ballot id (or at least the ballot location may consist of
  a four-tuple (TabulatorId, BatchId, RecordId, CountingGroupId).)

Identifiers are converted to "reduced" form when first encountered, by
removing any initial or final whitespace characters, and converting
any internal subsequence of two or more whitespace characters to a
single blank.

When an identifier (usually a collection identifier) is used as part
of a filename, all characters in the identifier other than

    A-Z   a-z   0-9  plus (+) hyphen(-) underscore(_) period(.)

are removed.

### Votes

A **vote** is what is indicated by a voter on a paper ballot for a
particular contest.  A vote is a (possibly empty) **set** of selection
ids for a contest.

A vote is more specific than a ballot, as a ballot may contain
many contests.

On the other hand, a vote is a larger notion than a selection,
since the voter may indicate more than one selection for a
contest.  (Either by mistake, with an overvote, or intentionally
when it is allowed, as for approval voting.)

Thus, a vote is a **set** of selections.  Possibly empty,
possibly of size one, possibly of greater size.
With plurality voting, the set is of size one for
a valid selection, but it may be of size zero (an undervote)
or of sizegreater than one (an overvote).

Implementation note: Within Python, we represent a vote as a
tuple, such as

    ()               for the empty set

    ("AliceJones",)  a vote with only one selection

    ("AliceJones", "+BobSmith")  a vote with two selections, one of
                     which is a write-in for Bob Smith.

We use a Python tuple rather than a Python set, since the tuple
is hashable.  But the intent is to represent a set, not a sequence.
To that end, the default order of a vote is with the selids
sorted into increasing order (as strings).

### File formats

``Multi.py`` uses CSV (comma-separated values) format for files;
a single header row specifies the column labels, and each subsequent line of
the file specifies one spreadsheet row.  A compressed format is
suggested in the Appendix below.

### File names

During an audit, data may be augmented or improved somehow.  We
use a file naming scheme that doesn't overwrite older data.

We support the principles of "**transparency**" and
"**repoducibility**": the information relied upon by the audit, and
the information produced by the audit, should be identifiable,
readable by the public, and usable to confirm the audit computations.
To support this principle, information is never changed in-place;
the older version is kept, but a newer version is added.

This is done by interpreting part of the filename as a
"version label".  When looking for a file, there may be
several files that differ only in the version label portion of
their filename.  If so, the system uses the one with the
version label that is (lexicographically) greatest.
The version label is arbitrary text; it may encode a
date, time, or some other form of version indicator.

When the system searches for a file in a given directory,
it looks for a file with a filename having a given "prefix"
(such as "data") and a given "suffix" (such as ".csv"). A
file with filename

    ``data.csv``

matches the search request, but has no version label (more precisely,
a zero-length string as a version label).  A file
with filename

    ``data-v005.csv``

also matches the search request, but has ``"-v005"`` as the version
label (for that search).  Similarly a filename:

    ``data-2017-11-07.csv``

as ``"-2017-11-07-08"`` as its version label for this search.

Note that version labels are compared as **strings**, not as **numbers**.
For good results:
* For numbers, use _fixed-width_ numeric fields, since the comparisons
  are lexicographic.  Don't be bitten by thinking that ``"-v10"`` is
  greater than ``"-v5"`` -- it isn't!
* For dates, used fixed-field numeric fields for each component, and
  order the fields from most significant to least significant (e.g.
  year, month, day, hour, minute, second), as is done in the ISO 8601
  standard, so lexicographic comparisons give the desired result.

Note that having no version label means having the empty string
as the version label, which compares "before" all other strings,
so your first version might have no version label, with later
versions having increasing version labels.

Within a directory, if two or more files differ only in their version labels,
then the file with the greatest version label is operative, and the
others are ignored (but may be kept around for archival purposes).

In our application, version labels are used as follows.  When
an audit sample is augmented, a new file is created to contain
**all** of the sampled ballot data (previously sampled, and the
new data as well).  The new file is given a version label that is
greater than the previous version label.  

If this sample is augmented, the above file is not changed, but
a new file with a later date is just added to the directory.
The earlier file may be deleted, if desired.


###  Directory structure

The information for an election is kept in a single directory
structure, as documented here.  Information for a different election
would be kept in a separate similar (but disjoint) directory
structure.

The top-level directory might be named something like
``./elections/CO-2017-general-election``.  The contents
of that directory might look as follows.
(Here we illustrate the use of "year-month-day" version labels.)

    1-structure
       11-election-2017-09-08.csv
       12-contests-2017-09-08.csv
       13-collections-2017-09-08.csv

    2-election
       21-reported-votes
          reported-cvrs-DEN-A01-2017-11-07.csv
          reported-cvrs-DEN-A02-2017-11-07.csv
          reported-cvrs-LOG-B13-2017-11-07.csv
       22-ballot-manifests
          manifest-DEN-A01-2017-11-07.csv
          manifest-DEN-A01-2017-11-07.csv
          manifest-LOG-B13-2017-11-07.csv
       23-reported-outcomes-2017-11-07.csv

    3-audit
       31-setup
          311-audit-seed-2017-11-20.csv
       32-audit-orders
          audit-order-DEN-A01-2017-11-20.csv
          audit-order-DEN-A02-2017-11-20.csv
          audit-order-LOG-B13-2017-11-20.csv
       33-audited-votes
          audited-votes-DEN-A01-2017-11-21.csv
          audited-votes-DEN-A02-2017-11-21.csv
          audited-votes-LOG-B13-2017-11-22.csv
       33-audit-stages
          audit-stage-000
             10-audit-parameters-global-2017-11-22.csv
             11-audit-parameters-contest-2017-11-22.csv
             12-audit-parameters-collection-2017-11-22.csv
             20-audit-snapshot-2017-11-22.csv
             30-audit-output-2017-11-22.csv
          audit-stage-001
             10-audit-parameters-global-2017-11-22.csv
             11-audit-parameters-contest-2017-11-22.csv
             12-audit-parameters-collection-2017-11-22.csv
             20-audit-snapshot-2017-11-22.csv
             30-audit-output-2017-11-22.csv
          audit-stage-002
             10-audit-parameters-global-2017-11-23.csv
             11-audit-parameters-contest-2017-11-23.csv
             12-audit-parameters-collection-2017-11-23.csv
             20-audit-snapshot-2017-11-23.csv
             30-audit-output-2017-11-23.csv
          audit-stage-003
             ...
 
## (Pre-election) Election definition.

The election definition phase answers the questions:
* What contests are there?
* For each contest, what selections (choices) may the voter mark?
* For each contest, what **voting method** will be used to determine the
  outcome?
* How many collections of cast paper ballots will there be?
* For each such collection, who will be the collection manager?
* For each collection, which contests may be on the ballots in
  that collection?
* How will the paper ballots in each collection be scanned?
* For each collection, will it be a CVR collection or a noCVR
  collection?

Election officials answer these questions with three CSV files:
an "**election file**", a "**contests file**", and a
"**collections file**".  It is likely that these three
election-definition files are produced from similar files used
for the election itself.

### Election file

An **election file** gives some high-level attributes of the election.

| Attribute         | Value                                   |
| ---               | ---                                     |
| Election name     | Colorado 2017 General Election          |
| Election dirname  | CO-2017-11-07                           |
| Election date     | 2017-11-07                              |
| Election URL      | https://sos.co.gov/election/2017-11-07/ |


The election dirname is the name of the directory where information
about this election is held.  This directory is within some
"standard directory where election information is held", such
as "./elections".

This is a CSV file, with the name ``11-election.csv`` (possibly with a version
label, as in ``11-election-2017-09-08.csv``).

### Contests file

A **contests file** is needed to specify the contests
of the election, their type (e.g. plurality), whether
write-ins are allowed (and if so, whether they may be arbitrary, or whether they
must be pre-qualified), and the officially allowed selections.

| Contest id      | Contest type | Winners   |Write-ins  | Selections | ...       |...         |...          |...         |
| ---             | ---          | ---       |---        | ---        | ---       |---         |---          |---         |
| DEN-prop-1      | Plurality    | 1         | No        | Yes        | No        |            |             |            |
| DEN-prop-2      | Plurality    | 1         | No        | Yes        | No        |            |             |            |
| DEN-mayor       | Plurality    | 1         | Qualified | John Smith | Bob Cat   | Mary Mee   |+Jack Frost  |            |
| LOG-mayor       | Plurality    | 1         | Arbitrary | Susan Hat  | Barry Su  | Benton Liu |             |            |
| US-Senate-1     | Plurality    | 1         | Qualified | Deb O'Crat | Rhee Pub  | Val Green  | Sarah Day   | +Tom Cruz  |
| Boulder-clerk   | IRV          | 1         | Arbitrary | Rock Ohn   | Peh Bull  | Roll Stone |             |            |
| Boulder-council | Plurality    | 4         | No        | Dave Diddle| Ben Borg  | Sue Mee    | Fan Tacy    | Jill Snead |

If the contest only allows pre-qualified write-ins, then those pre-qualified
write-in names (with preceding "+" signs) are given on the contest row, but
not printed on the ballot.

Additional contest types may be supported as needed.

This is a CSV file, with the name ``12-contests.csv`` (possibly with a version
label, as in ``12-contests-2017-09-08.csv``).

### Collections file

A **collections file** is needed to specify the various
collections of paper ballots, contact info for the collection
manager, collection type (CVR or noCVR),
and a list of contests that may appear on ballots in that collection.

| Collection id | Manager          | CVR type  | Contests   | ...        | ...         |...         |...    |
| ---           | ---              | ---       | ---        | ---        | ---         |---         |---    |
| DEN-A01       | abe@co.gov       | CVR       | DEN-prop-1 | DEN-prop-2 | US-Senate-1 |            |       |
| DEN-A02       | bob@co.gov       | CVR       | DEN-prop-1 | DEN-prop-2 | US-Senate-1 |            |       |
| LOG-B13       | carol@co.gov     | noCVR     | LOG-mayor  | US-Senate-1|             |            |       |

This is a CSV file, with the name ``13-collections.csv`` (possibly with a version
label, as in ``13-collections-09-08.csv``).

Note that this representation doesn't represent the common notion of
a "ballot style," where a style can viewed as a set of contests that
co-occur on a ballot.  If a collection may hold ballots of several different
styles, then the collections file shows every contest that may appear on
any allowed ballot in the collection.

## Election data (CVRs, ballot manifests, and reported outcomes)

When the election is run, paper ballots are cast and scanned.  The
electronic results are organized in "**reported vote files**".
The paper ballots are organized into collections and stored.
A "**ballot manifest**" is produced for each paper ballot collection,
describing the collection and enabling random sampling from that
collection. A "**reported outcomes**" file lists the reported
outcome for each contest.

### Reported Vote file (CVRs)

A **reported vote file** is a CSV format file containing a number of
rows, where (for a CVR collection) each row represents a voter's choices for a
particular contest. These are the **cast vote records** (CVRs) of the election.

The format is capable of representing votes in more
complex voting schemes, like approval or instant runoff (IRV).

Here are the fields of a row of a reported vote file:

1. **Paper Ballot Collection Identifier** (pbcid)
   Typically, all rows in a vote file will have the same pbcid.

2. **Scanner**: Gives an id of the device that scanned this ballot.
   May be blank.

2. **Ballot identifier** (bid)

3. **Contest Identifier** (cid)

7. **Selections** (vote): Columns 4 and on are to record the voter's choices
   for that contest.  A typical plurality election will only have one
   choice, so the selection id (selid) is entered in column 4 and the later
   columns are blank.

   For other contest types (e.g. approval voting) there may be more than
   one selection, so they are listed in columns 4, 5, ...
   In general, each selection id corresponds to a single bubble that
   the voter has filled in on the paper ballot.

   Preferential voting can also be handled with these fields, in which
   case the order of the selections matters: the first selection is
   the most favored, and so on.  With approval voting or vote-for-k
   voting, the order of the selections doesn't matter.

   An undervote for a plurality vote will have columns 4-... blank,
   whereas an overvote will have more than one such column filled in.

   Implementation note: the voter's selections are combined into
   a python "tuple".  An empty vote is the zero-length python
   tuple ``()``.  The python representation uses tuples, not lists,
   since tuples are hashable and so may be used as keys in
   python dictionaries.

For a noCVR collection, the format is the same except that the "Ballot ID" field
is replaced by a "Tally" field.

**Example:** A reported vote file table from a scanner in a CVR collection.  Here
each row represents a single vote of a voter in a contest.  There are three voters
(ballot ids ``B-231``, ``B-777``, and ``B888``) and three
contests.


|Collection id   | Scanner  | Ballot id   | Contest     | Selections     | ...       |
|---             |---       | ---         | ---         | ---            | ---       |
|DEN-A01         |FG231     | B-231       | DEN-prop-1  | Yes            |           |
|DEN-A01         |FG231     | B-231       | DEN-prop-2  |                |           |
|DEN-A01         |FG231     | B-231       | US-Senate-1 | Rhee Pub       | Sarah Day |
|DEN-A01         |FG231     | B-777       | DEN-prop-1  | No             |           |
|DEN-A01         |FG231     | B-777       | DEN-prop-2  | Yes            |           |
|DEN-A01         |FG231     | B-777       | US-Senate-1 | +Tom Cruz      |           |
|DEN-A01         |FG231     | B-888       | US-Senate-1 | -Invalid       |           |


The second row is an undervote, and the third row is an overvote.  The sixth
row has a write-in for Tom Cruz.  The last row represents a vote that
is invalid for some unspecified reason.

The reported vote file will have a name of the form
``reported-cvrs-<pbcid>.csv``, possibly
with a version label.  An example filename: ``reported-cvrs-DEN-A01-2017-11-09.csv``.

**Example:** If the reported vote file is for a noCVR collection, the "Ballot id"
column is replaced by a "Tally" column:

|Collection id   | Scanner  | Tally       | Contest     | Selections     | ...       |
|---             |---       | ---         | ---         | ---            | ---       |
|LOG-B13         |FG231     | 2034        | LOG-mayor   | Susan Hat      |           |
|LOG-B13         |FG231     | 1156        | LOG-mayor   | Barry Su       |           |
|LOG-B13         |FG231     | 987         | LOG-mayor   | Benton Liu     |           |
|LOG-B13         |FG231     | 3           | LOG-mayor   | -Invalid       |           |
|LOG-B13         |FG231     | 1           | LOG-mayor   | +Lizard People |           |
|LOG-B13         |FG231     | 3314        | US-Senate-1 | Rhee Pub       |           |
|LOG-B13         |FG231     | 542         | US-Senate-1 | Deb O'Crat     |           |
|LOG-B13         |FG231     | 216         | US-Senate-1 | Val Green      |           |
|LOG-B13         |FG231     | 99          | US-Senate-1 | Sarah Day      |           |
|LOG-B13         |FG231     | 9           | US-Senate-1 | +Tom Cruz      |           |
|LOG-B13         |FG231     | 1           | US-Senate-1 | -Invalid       |           |

This file format for noCVRs is also used for output tally files for CVR
collections.


### Ballot manifest file

A **ballot manifest file** lists all of the ballot ids for a given collection.
Each ballot id may be given explicitly, or, if some ballots are organized
into a batch (box) with sequential ballot ids, the first ballot id of the batch and
the size of the batch may be given.

It indicates the physical location of each ballot (giving a box id and position within box),
any "stamp" or other identification imprinted on the ballot,
and any additional comments about specific ballots.

The **``Collection id``** field specifies the collection id for the ballot manifest.
This should the same for all rows in the file.

The **``Box id``** field gives the identifier for the box containing the ballot(s)
described in that row.  The box id should be unique within the paper ballot collection.
If it is omitted, a box id is assumed to be equal to the collection id. (Maybe there
are no "boxes" for this collection.)

The **``Position``** field gives the position (starting with 1) of the ballot within
the box.  The auditor may find a particular ballot by counting to the right position
in the box.  It is assumed that the order of ballots within a box is never
changed.

The **``Stamp``** field, if used, gives the "stamp" that may have been
impressed (imprinted) on the ballot when it was scanned or organized
into boxes.  It is assumed that the stamps values are unique within a
box.  They may be increasing in order within a box, but need not be.
The stamps do not need to be numeric.  If stamps are used, the auditor
knows she has the desired ballot if it has the expected stamp value.
If no stamp value is specified, a value of ``""`` (the empty string)
is assumed.  If both the **``Position``** field and the **``Stamp``** field are
used, the **``Position``** field is used only as a hint as to where the ballot
with the right stamp value is in the box.  The **``Stamp``** and the
**``Comments``** are the only optional fields.

The **``Ballot id``** gives a ballot id for the ballot described
in that row.  It should be unique within all ballots of the collection.
It may encode information (such as the box id) within it, but need not.
If the row describes multiple ballots, via the "Number of ballots" feature
about to be described, then those ballots should all have (generated)
ballot ids that are unique within the collection.

The **``Number of ballots``** field enables compact encoding of
boxes of ballots for the manifest.

If the **``Number of ballots``** field should be equal to 1 if the row represents
a single ballot.  This is perhaps the typical case.

if the **``Number of ballots``** field is greater than one, then the given
row represents a batch of ballots of size "Number of ballots".  
Typically, the row would represent all ballots in a particular box.

In this case, the fields of the row describe the *first* ballot in the
batch.  To generate the other rows, the **``Position``**, **``Stamp``**
(if present), and **``Ballot id``** fields are increased by one for
each successive newly-generated ballot
Other fields are just copied for the newly-generated rows.
This compact format may not be used if the ballot stamps are present
but not sequential.

The auto-incrementing for position, stamp, and ballot-id increments
just the number given in the trailing digit sequence of the position, stamp, or
ballot-id, and preserves the length of that trailing digit sequence if
possible (so ``"B-0001"`` increments to ``"B-0002"`` and not ``"B-2"``, but
``"XY-9"`` increments to ``"XY-10"``).  If the given ballot id does not
contain a trailing digit sequence, then a trailing digit sequence of
``"1"`` is generated for the first ballot of the generated set.

The size of the collection is just the sum of the values in the "Number of ballots" field.

The **``Number of ballots``** feature is just for compactness and
convenience; when the ballot manifest file is read in by ``multi.py``,
it expands such rows representing multiple ballots into individual
rows as described above.  So, the compact format is just "shorthand" for the
official fully-expanded one-ballot-per-row format.

Here is an example of a ballot manifest file.

| Collection id | Box id    | Position  | Stamp     | Ballot id | Number of ballots | Comments |
|---            | --        | ---       | ---       | ---       | ---               | ---      |
| LOG-B13       | B         | 1         | XY04213   | B-0001    |  1                |          |
| LOG-B13       | B         | 2         | XY04214   | B-0002    |  1                |          |
| LOG-B13       | B         | 3         | XY04215   | B-0003    |  1                |          |
| LOG-B13       | C         | 1         | QE55311   | C-0001    |  3                |          |
| LOG-B13       | D         | 1         |           | D-0001    |  50               |          |
| LOG-B13       | E         | 1         | FF91320   | E-0200    |  50               |          |
| LOG-B13       | F         | 1         | JS23334   | F-0001    |  1                | See Doc. #211 |

Box B has three ballots, which are individually described, one row per ballot.
Box C also has three ballots, but the compact format is used here.  The positions
of the three ballots are 1,2,3; the stamps are ``QE55311``, ``QE55312``, and ``QE55313``;
and the ballot ids are ``C-0001``, ``C-0002``, and ``C-0003``. 
(The ballot ids here just encode the box id and position; they need not do so, as
we see for box E.)
Box D has 50 unstamped ballots, in positions
1--50, and ballot ids ``D-0001`` to ``D-0050``.
Box F has a single ballot, with a comment (perhaps it was a provisional ballot).

If ballot stamps are not used, or if ballot stamps are sequential, then the
ballot manifest might be easy to create by hand, thus removing the need to
trust vendor software to create the ballot manifest.  The auditor will need
to create one line of the ballot manifest file per box in the collection.

A ballot manifest file has a filename of the form
``manifest-<pbcid>.csv``, e.g. ``manifest-LOG-B13-2017-11-07.csv``
(possibly with a version label, as exemplified).

### Reported outcomes file

A "**reported outcomes file**" gives the reported outcome for every
contests.  It may indicate final vote tallies for the winner, and
do the same for the losers.

| Contest id      | Winner(s)  | ...        | ...       | ...         |
| ---             |  -         | ---        |---        |---          |
| DEN-prop-1      | Yes        |            |           |             |
| DEN-mayor       | John Smith |            |           |             |
| Boulder-council | Dave Diddle| Ben Borg   | Sue Mee   | Jill Snead  |

When a contest outcome includes multiple winners, they are listed in
additional columns, as shown.  The order of these winners may be important,
depending on the contest type and outcome rule.

This file shows only the reported winners, it does not show tally
information, or additional information about how the winner(s) was/were
computed (such as intermediate IRV round information, or tie-breaking
decisions).  Additional output files may include this information.  But
since this information is not relevant for the audit, we do not describe
it here.

A reported outcomes file has a filename of the form
``23-reported-outcomes.csv``, e.g. ``23-reported-outcomes-2017-11-07.csv``
(possibly with a version label, as exemplified).

## Audit

The audit process begins with a single "audit setup" phase,
in which a random "**audit seed**" is generated, and a
"**sampling order**" is then produced for each collection.

Following that is the actual audit, which involves coordinated
work between the various collections and Audit Central.

The collection managers arrange for the retrieval of paper ballots in
the order prescribed by the sampling order for their collection.  At
predetermined times (or when possible or convenient) the collection
manager will send to Audit Central an "**audited votes file**"
describing (in a cumulative way) the hand-to-eye interpretations of
all ballots retrieved so far in that collection.  Each new upload
has a larger (later) version label.

Audit Central will process the uploaded sample data, and determine
for each contest whether the audit is complete or not.  Audit Central
then provides guidance to the collection mangers (in the form of a
"**plan**") that details the work yet to be done.  

(For contests whose ballots are entirely within one collection, the
``multi.py`` software may in principle also be run by the collection manager,
if desired, to give faster evaluation of the audit progress. But the audited
votes data should nonetheless be uploaded to Audit Central.)

### Audit setup

The audit setup determines the "**audit seed**", a long random number,
and then from the audit seed a "**sampling order**" for each collection,
listing the ballots of that collection in a scrambled order.

#### Audit seed file

The **audit seed file** contains the audit seed used to control the random
sampling of the audit.

| Audit seed           |
|---                   | 
| 13456201235197891138 |

The audit seed should be made by rolling a decimal die twenty or more
times.  **It is important that this be done *after* the reported votes have been
collected and published by Audit Central.**  The generation of the audit
seed should preferably be done in a videotaped public ceremony.  

The audit seed file has a filename of the form
``311-audit-seed-2017-11-20.csv`` or the like.
(This example shows a version label to record the date, but the audit
seed should only be made once.)

#### Audit orders and audited-votes files

We envision an ongoing two-way dialogue between AC (Audit Central) and
the various collection managers (CMs, one per collection) during the audit.

The AC provides a sequence of specific auditing requests: ballots to
be pulled, and contests from those pulled ballots for which the 
collection manager (or her delegate) should record the voter's selection(s).

A CM responds with the requested information, in the order requested.

For each paper ballot collection, the
**audit order file** is an append-only list of the audit requests
made by AC for ballots in that collection.  This list will grow
longer as the audit proceeds.

Correspondingly, for each paper ballot collection the **audited votes**
file gives the records provided by the CM to AC for the requested records.
This is an append-only file.

We can view the two files as *transcripts* of the two-way dialogue between
AC and the CM.  

The conversation is **asynchronous**; either party may add additional
information to its file at any time.

The **``audit-orders``** file may be dynamically computed as the audit
progress, which is why it need not be specified "all at once" before the audit
begins.  For example, it may be determined that a particular scanner has
a high error rate, and so later sampling may emphasize ballots scanned
with that scanner.  All the same, the AC should provide sufficient
"advance notice" of auditing requests that CMs can "work ahead" if they
wish, for example by combining requests for ballots from the same box.


#### Audit order file

A **audit order file** lists a sequence of ballots requested for audit
from a collection.

The audit order file may become longer as the audit progresses.  If so,
new requests are added to the end; the file is append-only.

The order of the requests is a random order determined
cryptographically, depending the audit seed.  The order should be
unpredictable to an adversary, which is why the audit seed should be
determined only **after** the reported votes for all the collections
are recorded and filed.

The sample order field indicates the order in which they must be
examined during the audit.  Ballots may not be skipped during the
audit.  (Technically, it is OK if the ballots audited may be re=ordered
to form the order given in the audit order file.  That is, the auditor
should make sure to audit any skipped ballots before reporting the results
of the audit to AC.)

When a ballot is audited, the auditor should report the voter's selection(s)
for all contests that are open status and either active or opportunistic sampling
mode.  Other contests should not be reported.

The audit order file can be viewed as an initial segment of a permuted
ballot manifest file.  The differences are that
* The ballots are given numbers giving their positions in the audit order.
* Each line represents a single ballot; no batching of lines is allowed.
* AC may determine the order dynamically, depending on what is seen during
  the audit.  While AC could in principle and perhaps in fact just be requesting ballots that
  form an initial segment of some fixed predetermined scrambled ballot
  manifest file, the AC could alternatively dynamically determine how to
  extend the audit order file as the audit progresses.

Here is an example audit order file, specifying the first seven ballots to be
audited from collection LOG-B13.

|Ballot order | Collection id | Box id    | Position  | Stamp     | Ballot id |  Comments |
|---          |---            | --        | ---       | ---       | ---       |  ---      |
| 1           | LOG-B13       | B         | 3         | XY04213   | B-0003    |           |
| 2           | LOG-B13       | C         | 2         | QE55312   | C-0002    |           |
| 3           | LOG-B13       | F         | 1         | JS23334   | F-0001    | See Doc #211 |
| 4           | LOG-B13       | D         | 7         |           | D-0007    |           |
| 5           | LOG-B13       | B         | 1         | XY04211   | B-0001    |           |
| 6           | LOG-B13       | D         | 39        |           | D-0039    |           |


The auditor may naturally group the requests for ballots from box B, and those from
box D.

Sampling is done without replacement.  Each ballot in the collection
appears at most once in the audit order file.  The audit order file
may grow to include all ballots in the collection.

To produce the audit order, ``multi.py`` feeds the audit seed,
followed by a comma, the collection id, another comma, and a decimal
counter value, into a cryptographic random number function
(specifically, SHA256 used in counter mode, starting with counter
value 1).  The Fisher-Yates algorithm is then used to produce a random
permutation of the ballots, using these random numbers.  This reference
random order is what is used if no dynamic determination of audit order
is used.  Otherwise, the order used will be a subsequence or otherwise
closely related to this random order.

An audit order file has a filename of the form
``audit-order-<pbcid>.csv``.  Example:
``audit-order-DEN-A01-2017-11-20.csv`` (including a version label).

The audit order file and the reported cvrs file may be used
with an appropriate UI interface to generate the audited votes
file. 


### Audited votes

#### Sample vote file (actual vote file)

A **sample vote file** represents a set of votes that have been
sampled during an audit.  It is similar to a reported vote file (for a CVR
collection), but the scanner field is omitted.

Here is an example of a sample vote file for the ``DEN-A01`` collection, for
two ballots and three contests each.


|Collection id   | Ballot id   | Contest     | Selections     | ...       |
|---             | ---         | ---         | ---            | ---       |
|DEN-A01         | B-231       | DEN-prop-1  | Yes            |           |
|DEN-A01         | B-231       | DEN-prop-2  | No             |           |
|DEN-A01         | B-231       | US-Senate-1 | Rhee Pub       | Sarah Day |
|DEN-A01         | B-777       | DEN-prop-1  | No             |           |
|DEN-A01         | B-777       | DEN-prop-2  | Yes            |           |
|DEN-A01         | B-777       | US-Senate-1 | +Tom Cruz      |           |

Compared to the reported vote file above, we note a discrepancy in the
interpretation of contest ``DEN-prop-2`` for ballot ``B-231``: the scanner showed
an undervote, while the hand examination showed a ``No`` vote.

The sample vote file will have a name of the form ``audited-votes-<bcid>.csv``, possibly
with a version label.  An example filename: ``audited-votes-DEN-A01-2017-11-21.csv``.

As noted, if the sample is expanded, then the new sample vote file will
contain records for not only the newly examined ballots, but also for the previously
examined ballots.
For example, the file ``audited-votes-DEN-A01-2017-11-22.csv`` will be an augmented version of the file
``audited-votes-DEN-A01-2017-11-21.csv``.

### Audit stages

#### Audit parameters files

An **audit parameters** file gives parameters used in the audit.  
There are *three* such files: one for global parameters, one for
parameters by contest, and one for parameters by collection.

These audit parameters files are **per stage**, since they may
be updated from stage to stage.  Typically, however, they will not
change, and the audit parameters for one stage will just be a
copy of the audit parameters from the previous stage.

##### Global audit parameters

The **global audit parameters file** is simple.

| Global Audit Parameter | Value |
| ---                    | ---   |
| max audit stages       | 20    |

The filename is of the form
``10-audit-parameters-global-2017-11-22.csv``
(showing a year-month-day version label).

##### Contest audit parameters

The **contest audit parameters file** shows the audit measurements
and risk limits that will be applied to contests.  

Each row specifies a risk measurement specific to a particular contest.
The measured risk quantifies, on a scale from 0.0 (no risk) to 1.0
(extreme risk), the risk associated with stopping the audit now and
accepting the reported election outcome as correct.

At the end of each stage, each risk measurement is performed.

The measured risk is compared against a specified **risk limi** (such as 0.05);
if the measured risk is less than the specified risk limit, we say
the test **passes**.

The measured risk is also compared against a specified
**risk upset threshold** (such as 0.99).
If the measured risk *exceeds* the specified risk upset threshold, then
we say the test **signals an upset** , as the measured risk is so high
as to provide strong evidence that the reported election outcome is
incorrect.

Normally, each contest has exactly one row in the file, specifying
a risk measurement to be performed.  But a contest may have no row
in the file, in which case risk is not measured for that contest.
Or, a contest may have more than one row, meaning that risk on that
contest is measured in more than one way.  (This latter capability
is perhaps most useful for research purposes, but is noted here.)


Here is a sample contest audit parameters file:

| Contest              | Risk Measurement Method | Risk Limit | Risk Upset Threshold       | Sampling Mode | Status | Param 1 | Param 2 |
| ---                  | ---                     | ---        | ---                        |---            | ---    | ---     | ---     |
| DEN-prop-1           | Bayes                   | 0.05       | 0.99                       | Active        | Open   |         |         |
| DEN-prop-2           | Bayes                   | 1.00       | 1.00                       | Opportunistic | Passed |         |         |
| DEN-mayor            | Bayes                   | 0.05       | 0.99                       | Active        | Open   |         |         |
| LOG-mayor            | Bayes                   | 0.05       | 0.99                       | Active        | Off    |         |         |
| US-Senate-1          | Bayes                   | 0.05       | 0.99                       | Active        | Upset  |         |         |
| Boulder-clerk        | Bayes                   | 1.00       | 0.99                       | Active        | Open   |         |         |
| Boulder-council      | Bayes                   | 1.00       | 0.99                       | Active        | Open   |         |         |
| Boulder-council      | Frequentist             | 0.05       | 1.00                       | Opportunistic | Open   |         |         |


Each row describes a risk measurement that will be done on the specified contest
(given in the first column) at the end of each stage.  

The second column specifies the risk measurement method.  The example
shows using ``Bayes`` and ``Frequentist`` as risk measurement methods.
Each such method invokes a specific software module for measuring the
risk, given the reported outcome and the tally of votes in the sample
for that contest.  The method may also use additional method-specific
parameters, as specified in the later columns of the row.

The measured risk will be a value between 0.00 and 1.00, inclusive;
larger values correspond to more risk.

The third column specifies the **risk limit** for that measurement.  If the
measured risk is at most the specified risk limit, then that measurement **passes**.
When all risk measurements pass, the audit may stop.

If the risk limit is 1.00, then the measurement is still made, but
the test always passes.  

The fourth column specifies the **risk upset threshold**.  If the measured
risk reaches or exceeds the risk upset threshold, then test **signals an upset**
for that contest, and the auditing program may cease
to sample more ballots in order to measure the risk of this contest, since it is
apparent that the reported outcome is incorrect and a full hand count should be
performed.

The fifth column specifies the **sampling mode** for that test, which should
be one of ``Active`` or ``Opportunistic``.  If the test specifies active
sampling, then requests will be made to collection managers to draw samples
that will shed light on the risk measurement and test.  Otherwise, if
the sampling mode is opportunistic, then no active sampling will be done, but
sample data will be obtained only by "piggybacking" on active sampling done
for other tests, since a pulled ballot may have the votes for several
contests recorded.

The sixth column specifes the **status** of the test, which should be
one of ``Open``, ``Passed``, ``Upset``, or ``Off``.  The status
describes the status of this test, from the last stage risk
measurements.  This is the only column that we expect to change from
stage to stage of the audit.  Normally all tests start with an
``Open`` status, and the audit proceeds to sample for the still-open
active tests until they are all ``Passed`` or ``Upset``.  The ``Off``
status is for administrative use, to designate and turn off tests that
aren't being exercised in the current audit; a test that is ``Off``
isn't measured and remains off.  For example, when running an audit in
a county only on local contests, only the local contests may be
specified as ``Open``; others are turned ``Off``.

The audit may stop when no active tests remain open.

Columns 7 and later specify additional parameters that might be needed for the
specified risk measurement method.  (None shown here, but something like
a gamma value for the frequentist method might be a possible example.)

Minor remark: We note again that **a contest can participate in more
than one risk measurement**.  In the example shown above, the last contest
(Boulder-council) has *two* measurements specified: one by a Bayes method
and one by a frequentist (RLA) method.  This flexibility may allow more
convenient testing and comparison of different risk-measurement methods.
(Although it should be noted that the notions of ``risk'' may differ, so
that this is a bit of an apples-and-oranges comparison.)
This feature may also enable the simultaneous use of different Bayesian
priors (say one for each candidate), as explained in
[Rivest and Shen (2012)](http://people.csail.mit.edu/rivest/pubs.html#RS12z).

The filename for a contest audit parameters file is of the form
``11-audit-parameters-contest-2017-11-22.csv``
(showing a year-month-day version label).

##### Collection audit parameters

A **collection audit parameters file** gives audit parameters that
are specific to each collection.

| Collection     | max audit rate  |
|---             |---              |
|  DEN-A01       | 50              |
|  DEN-A02       | 50              |
|  LOG-B13       | 30              |

At this point, we only have one collection-specific audit parameter:
the *max audit rate*, which is the maximum number of
ballots that can be examined in one stage for that collection.

The filename for a collection audit parameters file is of the form
``12-audit-parameters-collection-2017-11-22.csv``
(showing a year-month-day version label).

#### Output file formats (per stage)

The outputs include a file ``20-audit-snapshot.csv`` that gives the SHA256
hashes of the files used as inputs to the computations of that stage.
This is a "snapshot" of the current directory structure.  It is used
if/when re-running a audit stage computation.

The output file ``30-audit-outputs.csv`` gives the detailed audit outputs
for the stage.

The file ``40-audit-plan.csv`` gives the workload estimates and auditing
plan (broken down by collection) for the next stage.

(More details to be determined.)

## Audit workflow

This section describes the audit workflow, from the point of
view of the audit participants (AC coordinator, collection manager,
observer).

### Pre-election

Defines election structure, global parameters, contests, and collections.
Goes into directory:

    1-structure

### Election

Gathers cast vote records, organizes paper ballots into collections,
and produces ballot manifests.
Goes into directories:

    2-election
      21-reported-votes
      22-ballot-manifests
      23-reported-outcomes

### Setup audit

Produce random audit seed.
Produce initial random audit orders from the audit seed
and the ballot manifests.
These go into the audit seed file and
the audit-orders directory.

    3-audit
       31-setup
          311-audit-seed.csv
       32-audit-orders
          audit-order-DEN-A01-2017-11-20.csv
          audit-order-DEN-A02-2017-11-20.csv
          audit-order-LOG-B13-2017-11-20.csv


Produce first *plan* for the audit, put this information
into directory/file:

    3-audit
      33-audit-stages
         audit-stage-000
             40-audit-plan.csv

### Start audit

Collection managers start sampling ballots, and putting
the resulting information into directory

    3-audit
       32-audited-votes

This is **asynchronous**: collection managers can update
their audited votes file whenever they are ready to do so.
These updates do **not** need to be synchronized on a
per-stage basis.  (Note again that each updated audited-votes
file contains *all* of the audited votes from the collection;
they are cumulative.) (For non-Bayesian risk measurement
methods, the uploads may need to be synchronized.)

### Audit stages

Audit Central determines when a new audit stage is ready to start.
A new ``stage-nnn`` subdirectory is created, and the audit
computations begin, based on all available sampling data
(from ``32-audited-votes``) at the time the stage begins.

We assume that a stage is represented by a three-digit integer,
starting at "000" for the initialization information stage (no ballots
sampled yet), followed by "001", "002", ...

#### Per-stage audit files

##### Audit parameters files

The **audit parameters files** for a stage may be copied from the
previous stage, and possibly adjusted by hand by Audit
Central to reflect pending deadlines, additional resources now available,
etc.

Formats are as specified above.

##### Audit snapshot file

The **audit snapshot** file lists the all files currently
in the directory for the election, together with their
SHA256 hash values.
The audit snapshot file is an *output* of the audit program, not an
input to the program.  It lists the files that the audit program
will use for the computation of this stage.  The SHA-256 hashes
are there for definiteness, allowing at a later time for you to check that you still
have the correct input files, if you want to check the audit program by re-running it.
(If the audit stage is re-run, it will use the same files, even if files
with later version labels have been added to the directory structure.)


| Filename                   | Hash |
|---                         |---                  |
| ``11-election-2017-09-08.csv``           | ``ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb`` |
| ``12-contests-2017-09-08.csv``           | ``3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d`` |
| ``13-collections-2017-09-08.csv``        | ``2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6`` |
| ...                                  | ...                                                              |
| ``audited-votes-LOG-B13-2017-11-22.csv`` | ``18ac3e7343f016890c510e93f935261169d9e3f565436429830faf0934f4f8e4`` |
| ``23-reported-outcomes-2017-11-07.csv`` | ``252f10c83610ebca1a059c0bae8255eba2f95be4d1d7bcfa89d7248a82d9f111`` |
| ...
| ``12-audit-parameters-collection-2017-11-22.csv`` | ``3f79bb7b435b05321651daefd374cdc681dc06faa65e374e38337b88ca046dea`` |


##### Audit output file(s)

The **audit outputs** file(s) give the measured risks.

The computation of Audit Central determines which measurements
have now reached their risk limits, so that certain collection
managers may be told that their work is completed.

Format: TBD

##### Audit plan file

The **audit plan** file gives estimated workloads (amount of work
remaining) for each collection manager, and provides guidelines
on how to allocate the work between collections (if there is
an exploitable tradeoff, to reduce overall workload). (Some
optimization may be applied here.)

| Collection             | Audited so far | Next stage increment request  | Estimated total needed |
|---                     |---             |---                            |---                     |
|  DEN-A01               | 150            | 50                            | 300                    |
|  DEN-A02               | 150            | 50                            | 300                    |
|  LOG-B13               |  90            | 30                            | 150                    |


The sum of "audited-so-far" and "next stage increment request" should equal the
size of the "audit-order" file.

## Command-line interface to ``multi.py``

This section sketches the command-line interface to ``multi.py``.
Here we assume that the election data is in the directory
``./elections/CO-2017-11``.

| Command                                  | Action                              |
|---                                       |---                                  |
| ``python --read-structure CO-2017-11``   | Reads and checks structure          |
| ``python --read-reported CO-2017-11``    | Reads and checks reported data      |
| ``python --read-seed CO-2017-11``        | Reads and checks audit seed         |
| ``python --make-audit orders CO-2017-11``| Produces initial audit order files  |
| ``python --read-audited CO-2017-11``     | Reads and checks audited votes      |
| ``python --stage 002 CO-2017-11``        | Runs stage 002 of the audit         |

The program ``multi.py`` will be run by Audit Central for each stage.

It may also be run by an audit observer, since no data is ever lost.  That is,
inputs to each audit stage computation are still available for re-doing any
of the audit computations.  (The snapshots file may need to be used here to
assist in obtaining the correct input files.)

Because of the way ``multi.py`` works, the program can be run by Audit
Central, or by a local collection manager.  For the latter use, the audit
parameters should to be adjusted to only those audit contests local to the collection, 
by setting the risk limits to all other contests to 1.00.


## Appendix

### Compression (notes for future work)

As the reported votes files are certain to be the largest files used by ``multi.py``,
some form of compression may be useful.

Here is a suggestion (for possible later implementation), suitable for compressing
CSV files.  Call this format ``redundant row compression`` (RRC), and give the
compressed file a name ``foo.csv.rrc``.

An RRC file compresses each row, using the previous rows if
possible.  An RRC cell entry of the form **&c^b** means "copy c cell
contents, starting with the current column, from the row b rows
previous to this one.  Either &c or ^b may be omitted, and these can
be given in either order.  They both default to 1 if either ^ or & is
present, so **^** means copy the corresponding cell from the previous row, **&4**
means copy the next four corresponding cells from the previous row, and **&3^9**
means copy the next three cells from the row nine rows earlier.

Example:  The following file:

|Collection id   | Scanner  | Ballot id   | Contest     | Selections     | ...       |
|---             |---       | ---         | ---         | ---            | ---       |
|DEN-A01         |FG231     | B-231       | DEN-prop-1  | Yes            |           |
|DEN-A01         |FG231     | B-231       | DEN-prop-2  |                |           |
|DEN-A01         |FG231     | B-231       | US-Senate-1 | Rhee Pub       | Sarah Day |
|DEN-A01         |FG231     | B-777       | DEN-prop-1  | No             |           |
|DEN-A01         |FG231     | B-777       | DEN-prop-2  | Yes            |           |
|DEN-A01         |FG231     | B-777       | US-Senate-1 | +Tom Cruz      |           |
|DEN-A01         |FG231     | B-888       | US-Senate-1 | -Invalid       |           |

can be compressed to the RRC CSV file:

```
Collection id,Scanner,Ballot id,Contest,Selections,...
DEN-A01,FG231,B-231,DEN-prop-1,Yes,
&3,DEN-prop-2,
&3,US-Senate-1,Rhee Pub,Sarah Day
&2,B-777,^3,No
&3,^3,Yes
&3,^2,+Tom Cruz
&2,B-888,^,-Invalid
```









