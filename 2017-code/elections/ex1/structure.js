{"__comment": "Election dervied from suggestin by Neal McBurnett (6/2017)",

 "election_type": "Synthetic",

  "__comment": "five contests",
  "cids": ["I", "C1", "C2", "C3", "F23"],

  "__comment": "three paper ballot collections",
  "pbcids": ["PBC1", "PBC2", "PBC3"],

  "collection_type":  {"PBC1": "CVR",
                       "PBC2": "CVR",
                       "PBC3": "CVR"},

  "__comment": "=====STRUCTURE=====",
  "rel": {
      "I": {"PBC1": "True",
            "PBC2": "True",
            "PBC3": "True"},
      "C1": {"PBC1": "True"},
      "C2": {"PBC2": "True"},
      "C3": {"PBC3": "True"},
      "F23": {"PBC2": "True",
              "PBC3": "True"}},

  "__comment": "valid votes for each contest (can win)",
  "vvids": {"I": ["0", "1"],
            "C1": ["0", "1"],
            "C2": ["0", "1"],
            "C3": ["0", "1"],
            "F23": ["0", "1"]},

  "__comment": "invalid votes for each contest (can't win)",
  "ivids": {"I": ["Invalid", "Overvote", "Undervote"],
            "C1": ["Invalid", "Overvote", "Undervote"],
            "C2": ["Invalid", "Overvote", "Undervote"],
            "C3": ["Invalid", "Overvote", "Undervote"],
            "F23": ["Invalid", "Overvote", "Undervote"]}
}            
            