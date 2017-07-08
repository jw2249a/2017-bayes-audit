# read_reported.py
# Ronald L. Rivest (with Karim Husayn Karimi)
# July 7, 2017
# python3

"""
Code that works with multi.py for post-election audit support.
This code reads and checks the "reported" results: votes
and reported outcomes.

The directory format is illustrated by this example from
README.md:

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

The 2-election directory is a subdirectory of the main
directory for the election.

There are three file types here:
   reported-cvrs
   ballot-manifests
   reported-outcomes

Here is an example of a reported-cvrs file, from
the README.md file:

Collection id   , Source , Ballot id   , Contest     , Selections
DEN-A01         , L      , B-231       , DEN-prop-1  , Yes       
DEN-A01         , L      , B-231       , DEN-prop-2  
DEN-A01         , L      , B-231       , US-Senate-1 , Rhee Pub       , Sarah Day
DEN-A01         , L      , B-777       , DEN-prop-1  , No            
DEN-A01         , L      , B-777       , DEN-prop-2  , Yes           
DEN-A01         , L      , B-777       , US-Senate-1 , +Tom Cruz     
DEN-A01         , L      , B-888       , US-Senate-1 , -Invalid      

If the collection is noCVR, then the format is slightly different:

Collection id   , Source , Tally       , Contest     , Selections 
LOG-B13         , L      , 2034        , LOG-mayor   , Susan Hat  
LOG-B13         , L      , 1156        , LOG-mayor   , Barry Su   
LOG-B13         , L      , 987         , LOG-mayor   , Benton Liu 
LOG-B13         , L      , 3           , LOG-mayor   , -Invalid   
LOG-B13         , L      , 1           , LOG-mayor   , +Lizard People
LOG-B13         , L      , 3314        , US-Senate-1 , Rhee Pub      
LOG-B13         , L      , 542         , US-Senate-1 , Deb O'Crat    
LOG-B13         , L      , 216         , US-Senate-1 , Val Green     
LOG-B13         , L      , 99          , US-Senate-1 , Sarah Day     
LOG-B13         , L      , 9           , US-Senate-1 , +Tom Cruz     
LOG-B13         , L      , 1           , US-Senate-1 , -Invalid      


Here is an example of a ballot-manifests file, from the README.md file:

Collection id , Original index , Ballot id , Location       
LOG-B13       , 1              , B-0001    , Box 001 no 0001
LOG-B13       , 2              , B-0002    , Box 001 no 0002
LOG-B13       , 3              , B-0003    , Box 001 no 0003
LOG-B13       , 4              , B-0004    , Box 001 no 0004
LOG-B13       , 5              , C-0001    , Box 002 no 0001

Here is an example of a reported outcomes file, from the README.md file:

Contest id      , Winner(s)
DEN-prop-1      , Yes      
DEN-mayor       , John Smith 
Boulder-council , Dave Diddle, Ben Borg   , Sue Mee   , Jill Snead

"""

"""
Code TBD
"""

pass


