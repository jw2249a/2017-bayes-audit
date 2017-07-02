# Documentation for multi.py (Bayeian audit support program)

``multi.py`` is Python3 software (or suite of programs) to support
the post-election auditing of elections with multiple contests and
multiple separately-managed collections of paper ballots.

The software is designed to be helpful for auditing elections such as
the November 2017 Colorado election, which has hundreds of contests
spread across 64 counties.

## Election structure

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

Note that some contests may be associated with collections of both types,
some CVR collections as well as some noCVR collections.

We assume that the vote-casting, scanning, and subsequent storage
process yields a ``**ballot manifest**'' for each collection,
specifying how many paper ballots are in the collection, how they are
organized, and how they are stored.  The ballot manifest defines the
population of paper ballots in the collection that will be sampled
during the audit.

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

## Overall audit structure

We assume that the election has the following components:
1. ("_Pre-election_") Election definition and setup.
2. ("_Election_") Vote-casting, interpretation and preliminary reporting.
3. ("_Post-election_") Audit.
4. ("_Certification_") Certification.

### (Pre-election) Election definition.

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

### Identifiers

The data structures for ``multi.py`` use identifiers extensively.
Identifiers are more-or-less arbitrary strings of characters.
Identifiers may be used as part of a filename so it should preferably
not contain blanks, special characters, or depend on capitalization.
(Blanks could be used, but may require escaping in some contexts, e.g.,
writing as "John\ Smith".)

We have:

* **Contest Identifiers** (example: ``"DenverMayor"``)
  A contest identifier is called a ``"cid"`` in the code.

* **Selection Identifiers** (examples: ``"Yes"`` or ``"JohnSmith"``)
  A selection identifier is called a ``"selid"`` in the code.
  Roughly speaking, there should be one selection identifier for each
  optical scan bubble.
  A **write-in** selection has a selection id beginning with a plus
  sign (example: ``"+BobWhite"``).
  (When the list of valid selections is given, we can list
  ``"+"`` as a valid selection to indicate that
  write-ins are allowed.)

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
  is printed, when it is scanned, or when it is stored.

Identifiers must not contain embedded commas (because of the
way we encode tuples of identifiers as json keys).
Identifiers should preferably contain only characters from
the set:

    A-Z   a-z   0-9  plus(+) hyphen(-) underscore(_) period(.)

Other charcters, such as blanks, might also be usable, but may
cause problems, as identifiers are used as parts of filenames.

### Votes

A **vote** is what is indicated by a voter on a paper ballot for a
particular contest.  A vote is a (possibly empty) list of selection
ids for a contest.

A vote is more specific than a ballot, as a ballot may contain
many contests.

On the other hand, a vote is a larger notion than a selection,
since the voter may indicate more than one selection for a
contest.  (Either by mistake, with an overvote, or intentionally
when it is allowed, as for approval voting.)

Thus, a vote is a **sequence** of selections.  Possibly of zero
length, possibly of length one, possibly of length greater than
one.  With plurality voting, the sequence is of length one for
a valid selection, but it may be of length zero (an undervote)
or of length greater than one (an overvote).

Implementation note: Within Python, we represent a vote as a
tuple, such as

    ()               for the empty sequence

    ("AliceJones")   a vote with only one selection

    ("AliceJones", "+BobSmith")  a vote with two selections, one of
                     which is a write-in for Bob Smith.

Implementation note: Within a json file, a vote is represented
as a comma-separated string of selection ids:

    ""               for the empty sequence

    "AliceJones"     a vote with one selections, for AliceJones

    "AliceJones,+BobSmith"  a vote with two selections,
                     one for Alice Jones and one for Bob Smith


### File names

During an audit, data may be augmented or improved somehow.  We
use a file naming scheme that doesn't overwrite older data.

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



###  Directory structure

Something like the following.  Here we use "month-day" as
version labels.

    $ ls -R
    010-structure
    020-reported-votes
    030-ballot-manifests
    040-audit-seed
    050-sampling-orders
    060-audited-votes
    070-audit-stages

    ./010-structure:
    election-09-08.csv
    contests-09-08.csv
    collections-09-08.csv

    ./020-reported-votes:
    REP-DEN-A01-11-07.csv
    REP-LOG-B13-11-07.csv

    ./030-ballot-manifests:
    MAN-DEN-A01-11-07.csv
    MAN-LOG-B13-11-07.csv

    ./040-audit-seed:
    audit-seed-11-20.csv

    ./050-sampling-orders:
    ORD-DEN-A01-11-20.csv
    ORD-LOG-B13-11-20.csv

    ./060-audited-votes:
    SAM-DEN-A01-11-21.csv
    SAM-DEN-A01-11-22.csv
    SAM-LOG-B13-11-21.csv
    SAM-LOG-B13-11-22.csv

    ./070-audit-stages:
    001
    002
    003

    ./070-audit-stages/001:
    010-audit-parameters-11-22.csv
    020-audit-inputs-11-22.csv
    030-audit-output-11-22.csv
    040-audit-plan-11-22.csv

    ./070-audit-stages/002:
    010-audit-parameters-11-23.csv
    020-audit-inputs-11-23.csv
    030-audit-outputs-11-23.csv
    040-audit-plan-11.23.csv

    ./070-audit-stages/003:

 
## Election file

An **election file** gives some high-level attributes of the election.

| Attribute     | Value                                   |
| ---           | ---                                     |
| Election name | Colorado general election               |
| Election date | 2017-11-07                              |
| Election info | https://sos.co.gov/election/2017-11-07/ |

This is a CSV file, with the name ``election.csv`` (possibly with a version
label, as in ``election-08-11.csv``).

## Contests file

A **contests file** is needed to specify the contests
of the election, their type (e.g. plurality), whether
write-ins are allowed, and the officially allowed selections.

| Contest id      | Contest type | Winners   |Write-ins  | Selections | ...       |...         |...        |...         |
| ---             | ---          | ---       |---        | ---        | ---        |---        |---         |
| DEN-prop-1      | Plurality    | 1         | No        | Yes        | No        |            |           |            |
| DEN-prop-2      | Plurality    | 1         | No        | Yes        | No        |            |           |            |
| DEN-mayor       | Plurality    | 1         | Yes       | John Smith | Bob Cat   | Mary Mee   |           |            |
| LOG-mayor       | Plurality    | 1         | Yes       | Susan Hat  | Barry Su  | Benton Liu |           |            |
| US-Senate-1     | Plurality    | 1         | Yes       | Deb O'Crat | Rhee Pub  | Val Green  | Sarah Day |            |
| Boulder-clerk   | IRV          | 1         | Yes       | Rock Ohn   | Peh Bull  | Roll Stone |           |            |
| Boulder-council | Plurality    | 4         | Yes       | Dave Diddle| Ben Borg  | Sue Mee    | Fan Tacy  | Jill Snead |

Additional contest types may be supported as needed.

This is a CSV file, with the name ``contests.csv`` (possibly with a version
label, as in ``contests-09-06.csv``).

## Collections file

A **collections file** is needed to specify the various
collections of paper ballots, contact info for the collection
manager, collection type (CVR or noCVR),
and a list of contests that may appear on ballots in that collection.

| Collection id | Contact (Mgr)    |  CVR type | Contests   | ...        | ...         |...         |...    |
| ---           | ---              | ---       | ---        | ---        | ---         |---         |---    |
| DEN-A01       | abe@co.gov       | CVR       | DEN-prop-1 | DEN-prop-2 | US-Senate-1 |            |       |
| DEN-A02       | bob@co.gov       | CVR       | DEN-prop-1 | DEN-prop-2 | US-Senate-1 |            |       |
| LOG-B13       | carol@co.gov     | noCVR     | LOG-mayor  | US-Senate-1|             |            |       |

This is a CSV file, with the name ``collections.csv`` (possibly with a version
label, as in ``collections-09-06.csv``).

Note that this representation doesn't represent the common notion of
a "ballot style," where a style can viewed as a set of contests that
co-occur on a ballot.  If a collection may hold ballots of several different
styles, then the collections file shows every contest that may appear on
any allowed ballot in the collection.

## Reported Vote file

A **reported vote file** is a CSV format file containing a number of
rows, where each row represents a voter's choices for a
particular contest. 

The format is capable of representing votes in more
complex voting schemes, like approval or instant runoff (IRV).

Here are the fields of a row of a reported vote file:

1. **Paper Ballot Collection Identifier** (pbcid)
   Typically, all rows in a vote file will have the same pbcid.

2. **Source**: An indication of the source of this ballot.  Might
   be a scanner id or other indicator.  Could just be "L" for "listing".

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
   tuple ``(,)``.  The python representation uses tuples, not lists,
   since tuples are hashable and so may be used as keys in
   python dictionaries.

**Example**: A reported vote file table from a scanner.  Here
each row represents a single vote of a voter in a contest.  
There are three voters (ballot ids ``B-231``, ``B-777``, and ``B888``) and three
contests.


|Collection id   | Source | Ballot id   | Contest     | Selections     | ...       |
|---             |---     | ---         | ---         | ---            | ---       |
|DEN-A01         | L      | B-231       | DEN-prop-1  | Yes            |           |
|DEN-A01         | L      | B-231       | DEN-prop-2  |                |           |
|DEN-A01         | L      | B-231       | US-Senate-1 | Rhee Pub       | Sarah Day |
|DEN-A01         | L      | B-777       | DEN-prop-1  | No             |           |
|DEN-A01         | L      | B-777       | DEN-prop-2  | Yes            |           |
|DEN-A01         | L      | B-777       | US-Senate-1 | +Harry Potter  |           |
|DEN-A01         | L      | B-888       | US-Senate-1 | -Invalid       |           |


The second row is an undervote, and the third row is an overvote.  The sixth
row has a write-in for Harry Potter.  The last row represents a vote that
is invalid for some unspecified reason.

The reported vote file will have a name of the ``REP-<bcid>.csv``, possibly
with a version label.  An example filename: ``REP-DEN-A01-11-09.csv``.

## Sample vote file (actual vote file)

A **sample vote file** represents a set of votes that have
been sampled during an audit.  It is similar to a reported
file, but the Source field is now used differently, to
indicate the sort of sampling used to produce this entry.

1. **source** (src): one of three values:
    * **P**: a ballot chosen uniformly from PBC
    * **PC**: a ballot chosen uniformly from all ballots
      within the PBC for a particular contest
    * **PCR**: a ballot chosen uniformly from all ballots
      within the PBC for a particular contest having a particular
      reported vote.

    The **P** label is the usual indicator for a sample.
    
    The **PC** and **PCR** labels are unlikely to be used (at least at
    first).  If the sample was restricted to a particular
    contest or reported vote, then that information was obtained
    from the reported vote file.

Here is an example of a sample vote file for the ``DEN-A01`` collection,
containing a single ballot that was chosen uniformly from all ballots in
that collection (thus the ``P`` for Source).

|Collection id   |Source | Ballot id   | Contest     | Selections     | ...       |
|---             |---    | ---         | ---         | ---            | ---       |
|DEN-A01         |P      | B-231       | DEN-prop-1  | Yes            |           |
|DEN-A01         |P      | B-231       | DEN-prop-2  | No             |           |
|DEN-A01         |P      | B-231       | US-Senate-1 | Rhee Pub       | Sarah Day |

Compared to the reported vote file above, we note a discrepancy in the
interpretation of contest ``DEN-prop-2`` for ballot ``B-231``: the scanner showed
an undervote, while the hand examination showed a ``No`` vote.

The sample vote file will have a name of the form ``SAM-<bcid>.csv``, possibly
with a version label.  An example filename: ``SAM-DEN-A01-11-09.csv``.

As noted elsewhere, if the sample is expanded, then the new sample vote file will
contain records for not only the newly examined ballots, but also for the previously
examined ballots.
The file ``SAM-DEN-A01-11-10.csv`` will be an augmented version of the file
``SAM-DEN-A01-11-09.csv``.

## Audit seed file

The **audit seed file** contains the audit seed used to control the random
sampling of the audit.

| Audit seed           |
|---                   | 
| 13456201235197891138 |

The audit seed should be made by rolling a decimal die twenty or more
times.  This should be done **after** the reported votes have been
collected and published by Audit Central.

The audit seed file has a filename of the form
``audit-seed-11-20.csv`` or the like (shown here
with a version label).


## Ballot manifest file

A **ballot manifest file** lists all of the ballot ids for a given collection.
It may also indicate their physical location (if it is not already encoded in
the ballot id).

| Collection id | Original index | Ballot id | Location          |
|---            | ---            |---        | ---               |
| LOG-B13       | 1              | B-0001    | Box 001 no 0001   |
| LOG-B13       | 2              | B-0002    | Box 001 no 0002   |
| LOG-B13       | 3              | B-0003    | Box 001 no 0003   |
| LOG-B13       | 4              | B-0004    | Box 001 no 0004   |
| LOG-B13       | 5              | C-0001    | Box 002 no 0001   |

A ballot manifest file has a filename of the form
``MAN-<pbcid>.csv``, e.g. ``MAN-DEN-A01-11-07.csv``
(possibly with a version label, as exemplified).

## Sampling order file

A **sampling order file** lists all the ballots from a collection
in a cryptographically scrambled order depending on the audit seed.
The sample order field
indicates the order in which they are to be examined during
the audit.  Ballots must not be skipped during the audit.

| Collection id | Sample order  | Original index | Ballot id | Location          |
|---            |---            | ---            | ---       | ---               |
| LOG-B13       |  1            | 4              | B-0004    | Box 001 no 0004   |
| LOG-B13       |  2            | 3              | B-0003    | Box 001 no 0003   |
| LOG-B13       |  3            | 1              | B-0001    | Box 001 no 0001   |
| LOG-B13       |  4            | 5              | C-0001    | Box 002 no 0001   |
| LOG-B13       |  5            | 2              | B-0002    | Box 001 no 0002   |

A sampling order file has a filename of the form
``ORD-<pbcid>.csv``.  Example: ``ORD-DEN-A01-11-20.csv`` (including a version label).

The sampling order ORD file and the reported vote REP file may be used
with an appropriate UI interface to generate the sampled vote
SAM file.  (With care to handling the case that the sampled ballot does not
seem to be of the correct ballot style.)

## Audit parameters file

An **audit parameters** file gives parameters used in the audit.  These
parameters may be global, or specific to particular contests or
collections.

Here is a sample audit parameters file:

| Parameter            | For           | Value           |
| ---                  | ---           | ---             |
| max stages           |               | 20              |
| audit status         | DEN-prop-1    | Auditing        |
| risk limit           | DEN-prop-1    | 0.05            |
| audit status         | DEN-prop-2    | Just Watching   |
| risk limit           | DEN-prop-2    | 1.00            |
| audit status         | DEN-mayor     | Auditing        |
| risk limit           | DEN-mayor     | 0.05            |
| audit status         | LOG-mayor     | Auditing        |
| risk limit           | LOG-mayor     | 0.05            |
| audit status         | US-Senate-1   | Auditing        |
| risk limit           | US-Senate-1   | 0.025           |
| audit status         | Boulder-clerk | Just Watching   |
| risk limit           | Boulder-clerk | 1.00            |
| bayes pseudocount    |               | 10              |
| max audit rate       | DEN-A01       | 60              |
| max audit rate       | LOG-B13       | 60              |

Each contest should initially have a status of ``Just Watching``, or
``Auditing``.

The ``risk limit`` should be 1.00 for a ``Just Watching`` contest,
and a target value (nominally 0.05) for other contests.

The ``max audit rate`` for a collection is the maximum number of
ballots that can be examined in one stage.

An audit parameters file has a filename of the form
``010-audit-parameters-11-23.csv`` (including version label).

##  Random number generation

The audit seed is fed into a cryptographic random number function,
such as SHA256 used in counter mode.

##  Sampling

Sampling is done without replacement.

## Output file formats (per stage)

The outputs include a file ``020-audit-inputs.csv`` that gives the SHA256
hashes of the files used as inputs to the computations of that stage.

The output file ``030-audit-outputs.csv`` gives the detailed audit outputs
for the stage.

The file ``040-audit-plan.csv`` gives the workload estimates and auditing
plan (broken down by collection) for the next stage.

(More details to be determined.)












