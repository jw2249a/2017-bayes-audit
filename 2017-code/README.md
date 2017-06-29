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
We have:

* **Contest Identifiers** (example: ``"Denver Mayor"``)
  A contest identifier is called a ``"cid"`` in the code.

* **Selection Identifiers** (examples: ``"Yes"`` or ``"John Smith"`` or ``"Undervote"``)
  A selection identifier is called a ``"selid"`` in the code.

* **Paper Ballot Collection Identifiers** (example: ``"BoulderPBC25"``)
  A paper ballot collection identifier is called a ``"pbcid"`` in the code.
  A pbcid may be used as part of a filename so it should preferable not
  contain blanks, special characters, or depend on capitalization.

* A **Ballot Identifier** is a unique identifier assigned to a particular
  paper ballot (example: ``"DN-25-72"``).
  A ballot id is called a ``"bid"`` in the code.
  Ballots within a collection must have unique bids, but it is not
  necessary that ballots in different collections have different
  bids.  A ballot id may encode the physical storage location of
  the ballot (e.g. the box number and position within box), but
  need not do so.  The ballot id might be generated when the ballot
  is printed, when it is scanned, or when it is stored.

### File names

During an audit, data may be augmented or improved somehow.  We
use a file naming scheme that doesn't overwrite older data.

This is done by making date and times part of the file name.
For example, we might have a file name of the form

    ``DEN-2017-07-02-05-22.11.csv``

to record the votes from a sample from the paper ballot collection
with pbcid DEN.

If this sample is augmented, the above file is not changed, but
a new file with a later date is just added to the directory.

Within a directory, if two files differ only in the date or time,
then the later file is operative, and the earlier one is ignored
(but kept around for archival purposes).

###  Directory structure

Something like this:

    ``
    010-structure
    020-reported-selections
    030-ballot-manifests
    040-audit-seeds
    050-sample-orders
    060-audited-selections
    070-audit-stages

    ./010-structure:
    structure-2017-06-26-22-35-59.js

    ./020-reported-selections:
    DEN-2017-06-27-08-03-49.csv
    LOG-2017-06-28-08-03-49.csv

    ./030-ballot-manifests:
    DEN-2017-06-27-08-03-50.csv
    LOG-2017-06-28-09-10-33.csv

    ./040-audit-seeds:
    seed-2017-06-30-13-01-22.js

    ./050-sample-orders:
    DEN-2017-07-01-07-08-35.csv
    LOG-2017-07-01-07-08-35.csv

    ./060-audited-selections:
    DEN-2017-07-02-05-22.11.csv
    LOG-2017-07-02-06-23.10.csv

    ./070-audit-stages:
    001
    002
    003

    ./070-audit-stages/001:
    audit-inputs-2017-07-02-06-33-40.csv
    audit-outputs-2017-07-02-06-33-40.csv
    audit-parameters-2017-07-02-06-33-40.csv
    audit-plan-2017-07-02-06-33-40.csv

    ./070-audit-stages/002:
    audit-inputs-2017-07-03-10-44-34.csv
    audit-outputs-2017-07-02-06-33-40.csv
    audit-parameters-2017-07-03-10-44-34.js
    audit-plan-2017-07-03-10-44-34.csv
    ``

###  Random number generation

###  Sampling









