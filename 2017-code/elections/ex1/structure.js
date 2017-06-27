{"__comment": "Election dervied from suggestin by Neal McBurnett (6/2017)",

 "election_type": "Synthetic",

  "__comment": "five contests",
  "cids": ["I", "C1", "C2", "C3", "F23"],

  "__comment": "three paper ballot collections",
  "pbcids": ["PBC1", "PBC2", "PBC3"],

  "collection_type":  {"PBC1": "noCVR",
                       "PBC2": "CVR",
                       "PBC3": "CVR"},

  "__comment": "=====STRUCTURE=====",
  "rel": {
      "I": {"PBC1": true,
            "PBC2": true,
            "PBC3": true},
      "C1": {"PBC1": true},
      "C2": {"PBC2": true},
      "C3": {"PBC3": true},
      "F23": {"PBC2": true,
              "PBC3": true}},

  "__comment": "valid votes for each contest (can win)",
  "vvotids": {"I": ["0", "1"],
              "C1": ["0", "1"],
              "C2": ["0", "1"],
              "C3": ["0", "1"],
              "F23": ["0", "1"]},

  "__comment": "invalid votes for each contest (can't win)",
  "ivotids": {"I": ["Invalid", "Overvote", "Undervote"],
              "C1": ["Invalid", "Overvote", "Undervote"],
              "C2": ["Invalid", "Overvote", "Undervote"],
              "C3": ["Invalid", "Overvote", "Undervote"],
              "F23": ["Invalid", "Overvote", "Undervote"]}
}            
            
