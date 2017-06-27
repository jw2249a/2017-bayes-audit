# Documentation for multi.py (Bayeian audit support program)

``multi.py`` is Python3 software (or suite of programs) to support
the post-election auditing of elections with multiple contests and
multiple separately-managed collections of paper ballots.

The software is designed to be helpful for auditing elections such as
the November 2017 Colorado election, which has hundreds of contests
spread across 64 counties.

## Election structure

We assume the following:
   -- a number of **contests** (for now, all plurality contests),
   -- a number of **voters**,
   -- a single **paper ballot** from each voter,
   -- paper ballots organized into a set of disjoint **collections**
      (for example, one or a few collections per county),
   -- each collection is managed by a **collection manager**,
   -- an **Audit Coordinator** who coordinates the audit in collaboration
      with the collection managers (the Coordinator might be from the
      Secretary of State's office).







