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
* for a given contest, there may be one or more collections having ballots
  showing that contest,

## Scanning of cast paper ballots

We assume that all the paper ballots in each collection have been **scanned** by
an **optical scanner*.  There may be a different scanner for each collection.
We distinguish two types of collections, according to the type of information
produced by the scanner:
* in a ``**CVR collection**'', the scanner produces an electronic **cast vote
  record** (CVR) for each paper ballot scanned, giving the choices made for each
  contest on that paper ballot.
* in a ``**noCVR** collection'', the scanner does not produce a separate
  electronic record for each paper ballot scanned; it only produces a summary
  tally showing for each contest and each possible choice (vote) on that
  contest, how may ballots in the collection showed the given choice.

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

Multi.py supports "Bayesian" audits, a form of post-election auditing
proposed by 
[Rivest and Shen (2012)](http://people.csail.mit.edu/rivest/pubs.html#RS12z).

A Bayesian audit provides an answer to the question 
``What is the probability that the reported election outcome is wrong?``
We call this probability the **Bayesian risk** perceived for the reported
outcome, given the audit data.

A Bayesian audit continues to draw ballots at random for manual
examination and interpretation, until the estimated Bayesian risk
drops below a prespecified risk limit (such as 5%) for all contests.
With typical contests, only a small number of ballots may need to be
examined before the risk limit is reached and the audit stops.
Contests that are very close, however, may require extensive sampling
before the risk limits are reached.

See Rivest (``Bayesian audits: Explained and Extended'', draft available
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
2. ("_Election_") Vote-casting and interpretation.
3. ("_Post-election_") Audit.

### (Pre-election) Election definition.

The election definition phase answers the questions:
* What contests are there?
* For each contest, what constitutes a valid vote?
* For each contest, what possible invalid vote types
  are there?
* For each contest, what **outcome rule** will be used to determine the
  outcome?
* How many collections of cast paper ballots will there be?
* For each such collection, who will be the collection manager?
* For each collection, which contests will be on the ballots in
  that collection?
* How will the paper ballots in each collection be scanned?
* For each collection, will it be a CVR collection or a noCVR
  collection?

### Identifiers

The data structure for ``multi.py`` use identifiers extensively.
Identifiers are more-or-less arbitrary strings of characters.
Identifiers may be used as part of a filename so it should preferably
not contain blanks, special characters, or depend on capitalization.
(Blanks could be used, but may require escaping in some contexts, e.g.,
writing as "John\ Smith".)

We have:

* **Contest Identifiers** (example: ``"DenverMayor"``)
  A contest identifier is called a ``"cid"`` in the code.

* **Selection Identifiers** (examples: ``"Yes"`` or ``"JohnSmith"`` or ``"Undervote"``)
  A selection identifier is called a ``"selid"`` in the code.

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

### File names

During an audit, data may be augmented or improved somehow.  We
use a file naming scheme that doesn't overwrite older data.

This is done by interpreting part of the filename as a
"version label".  When looking for a file, there may be
several files that differ only the version label portion of
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

Something like this:

    $ ls -R
    010-structure
    020-reported-votes
    030-ballot-manifests
    040-audit-seed
    050-sample-orders
    060-audited-votes
    070-audit-stages

    ./010-structure:
    structure-09-08.js

    ./020-reported-votes:
    DEN-11-07.csv
    LOG-11-07.csv

    ./030-ballot-manifests:
    DEN-11-07.csv
    LOG-11-07.csv

    ./040-audit-seed:
    audit-seed-11-20.js

    ./050-sample-orders:
    DEN-11-20.csv
    LOG-11-20.csv

    ./060-audited-votes:
    DEN-11-21.csv
    DEN-11-22.csv
    LOG-11-21.csv
    LOG-11-22.csv

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

 
###  Random number generation

###  Sampling

### Vote file formats

A **vote file** is a CSV format file containing a number of
rows, where each row represents a voter's choices for a
particular contest.

The format is common for vote files representing cast vote
records and for vote files representing sampled ballots.
The format is capable of representing votes in more
complex voting schemes, like approval or instant runoff (IRV).

The format is also the same for representing a tally of votes,
where aggregation has been performed.  In this case the ballot
identifiers are omitted by the tally field is used.

When the vote file is used to represent a sample of ballots, the
nature of the sampling is also indicated.

Here are the fields of a row of a vote file:

1. **row type** (rt): one of four values:

    * **RS**: a single reported vote
    * **RT**: a tally of one or more reported votes
    * **AS**: a single actual vote (from audit)
    * **AT**: a tally of one or more actual votes

2. **source** (src): one of four values:
    * **L**: a complete list of relevant ballots
    * **P**: a ballot chosen uniformly from PBC
    * **PC**: a ballot chosen uniformly from all ballots
      within the PBC for a particular contest
    * **PCR**: a ballot chosen uniformly from all ballots
      within the PBC for a particular contest having a particular
      reported vote.

    The **L** label is appropriate for a listing of reported votes.
    The others may be used for statistical samples in the audit.

    The **P** label is appropriate for a typical audit sample.
    
    The **PC** and **PCR** labels are unlikely to be used (at least at
    first).  If the sample was restricted to a particular
    contest or reported vote, then that information was obtained
    from the CVR records (i.e. with row type **RS**).

3. **Paper Ballot Collection Identifier** (pbcid)

4. **Ballot identifier** (bid): blank for rows of type **RT** or **AT**, since
   these are aggregate tally rows.  Otherwise gives the bid for a single
   ballot.

5. **tally**: This is 1 for rows of type **RS**
   **AS**, since they represent just a single ballot.
   Otherwise, gives the tally (a nonnegative integer) for a number
   of ballots for rows of type **RT** or **AT**; the tally is the number
   of rows summarized.  The summarized rows must agree on all fields except
   the bid field.  The bid field is blank for row types **RT** and **AT**.

6. **Contest Identifier** (cid)

7. **selections** (vote): Columns 7 and on are to record the voter's choices
   for that contest.  A typical plurality election will only have one
   choice, so the selection id (selid) is entered in column 7 and the later
   columns are blank.

   For other contest types (e.g. approval voting) there may be more than
   one selection, so they are listed in columns 7, 8, ...
   In general, each selection id corresponds to a single bubble that
   the voter has filled in on the paper ballot.  Preferential voting can
   also be handled with these fields.

   An undervote for a plurality vote will have columns 7-... blank,
   whereas an overvote will have more than one such column filled in.

   Implementation note: the voter's selections are combined into
   a python "tuple".  An empty vote is the zero-length python
   tuple ``(,)``.  The representation uses tuples, and not lists,
   since tuples are hashable and so may be used as keys in
   python dictionaries.

**Example**: A two-row vote file table for an audit sample.  Here
each row represents a single vote of a voter in a contest.  The ballots
were sampled uniformly at random from the PBC.  The two rows represent
different contests on the same ballot.


| RT | SRC | PBCID | BID | Tally | Contest | Selections | ...       |
| ---| --- | ---   | --- | ---   | ---     | ---        | ---       |
| AS |   P | DEN12 | B23 | 1     | Clerk   | BobStone   |           |
| AS |   P | DEN12 | B23 | 1     | Mayor   | JohnSmith  | MaryJones |


    The second row is an overvote.

   













