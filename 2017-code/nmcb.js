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
            "F23": ["Invalid", "Overvote", "Undervote"]},

  "__comment": "=====ELECTION DATA=====",

  "__comment": "number of ballots for each paper ballot collection",
  "n": {"PBC1": 10000,
        "PBC2": 10000,
        "PBC3": 10000},

  "__comment": "e.t = vote totals for each cid pbcid vid combo",
 "t": { "I": {"PBC1": {"1": 5050,
                       "0": 4950},
              "PBC2": {"1": 5050,
                       "0": 4950},
              "PBC3": {"1": 5050,
                       "0": 4950}},
        "C1": {"PBC1": {"1": 6500,
                        "0": 3500}},
        "C2": {"PBC2": {"1": 6000,
                        "0": 4000}},
        "C3": {"PBC3": {"1": 5500,
                        "0": 4500}},
        "F23": {"PBC2": {"1": 5250,
                         "0": 4750},
                "PBC3": {"1": 5250,
                         "0": 4750}}},
    
  "__comment": "e.ro = reported outcomes for each cid (not all correct here)",
  "ro": {"I": "1",
         "C1": "1",
         "C2": "1",
         "C3": "1",
         "F23": "0"},

  "__comment": "=====AUDIT PARAMETERS=====",

  "risk_limit": {"I": 0.05,
                 "C1": 0.05,
                 "C2": 0.05,
                 "C3": 0.05,
                 "F23": 0.10},

  "audit_rate": {"PBC1": 40,
                 "PBC2": 50,
                 "PBC3": 60},

  "pseudocount": 0.001,

  "contest_status": {"I": "Auditing",
                     "C1": "Auditing",
                     "C2": "Auditing",
                     "C3": "Auditing",
                     "F23": "Auditing"}
  }

