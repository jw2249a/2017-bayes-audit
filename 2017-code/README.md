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

We assume that all the ballots in each collection have been **scanned** by
an **optical scanner*.  There may be a different scanner for each collection.
We distinguish two types of collections, according to the type of information
produced by the scanner:
* in a ``**CVR collection**'', the scanner produces an electronic **cast vote
  record** (CVR) for each paper ballot scanned, giving the choices made for each
  contest on that paper ballot.
* in a ``**noCVR**'' collection'', the scanner does not produce a separate
  electronic record for each paper ballot scanner; it only produces a summary
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

Multi.py supports ``Bayesian'' audits, a form of post-election auditing
proposed by 
[Rivest and Shen (2012)](http://people.csail.mit.edu/rivest/pubs.html#RS12z).

A Bayesian audit provides an answer to the question ``What is the
probability that the reported election outcome is wrong?''  We call
this probability the ``Bayesian risk'' perceived for the reported
outcome, given the audit data.

A Bayesian audit continues to draw ballots at random for manual
examination and interpretation, until the estimated Bayesian risk
drops below a prespecified risk limit (such as 5%) for all contests.
With typical contests, only a small number of ballots may need to be
examined before the risk limit is reached and the audit stops.
Contests that are very close, however, may require extensive sampling
before 

See Rivest (``Bayesian audits: Explained and Extended'', draft available
from author) for a discussion of Bayesian audits.

Bayesian audits are subtly different than the ``frequentist'' risk-limiting
audits promulgated by Stark and others.
(REFS) Details omitted here, but Bayesian audits provide additional
capabilities and flexibility, at the cost of some additional (but still
very reasonable) computation during the audit.

We assume the existence of an **Audit Coordinator** who coordinates
the audit in collaboration with the collection managers (the
Coordinator might be from the Secretary of State's office).












