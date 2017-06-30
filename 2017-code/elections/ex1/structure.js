{"__comment": "Election dervied from suggestin by Neal McBurnett (6/2017)",

  "__comment": "=====STRUCTURE=====",

 "election_type": "Synthetic",

  "__comment": "five contests",
  "cids": ["I", "C1", "C2", "C3", "F23"],

  "__comment": "valid selections for each contest",
  "selids": {"I": {"0": true,
                   "1": true},
             "C1": {"0": true,
                    "1": true},
             "C2": {"0": true,
                    "1": true},
             "C3": {"0": true,
                    "1": true},
             "F23": {"0": true,
                     "1": true}}

  "__comment": "three paper ballot collections",
  "pbcids": ["PBC1",
             "PBC2",
             "PBC3"],

  "__comment": "type of each collection: CVR or noCVR",
  "collection_type":  {"PBC1": "CVR",
                       "PBC2": "CVR",
                       "PBC3": "CVR"},

  "__comment": "e.rel[cid][pbcid] true if pbc can contain ballot with that contest",
  "rel": {
      "I": {"PBC1": true,
            "PBC2": true,
            "PBC3": true},
      "C1": {"PBC1": true},
      "C2": {"PBC2": true},
      "C3": {"PBC3": true},
      "F23": {"PBC2": true,
              "PBC3": true}},

}            
            
