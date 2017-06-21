# nmcb.py
# Ronald L. Rivest
# Jun 19, 2017
# python3

"""
Test election for testing Bayesian post-election audit code (multi.py)
"""

def election_structure(e):

    e.election_type = "Synthetic"

    # four contests
    e.cids = ["I", "C1", "C2", "C3", "F23"]

    # three paper ballot collections
    e.pbcids = ["PBC1", "PBC2", "PBC3"]

    e.collection_type["PBC1"] = "CVR"
    e.collection_type["PBC2"] = "CVR"
    e.collection_type["PBC3"] = "CVR"

    # Structure
    for cid in e.cids:
        e.rel[cid] = dict()
    e.rel["I"]["PBC1"] = True            # I is in all counties
    e.rel["I"]["PBC2"] = True          
    e.rel["I"]["PBC3"] = True          
    e.rel["C1"]["PBC1"] = True           # C1 is only in PBC1
    e.rel["C2"]["PBC2"] = True           # C2 is only in PBC2
    e.rel["C3"]["PBC3"] = True           # C3 is only in PBC3
    e.rel["F23"]["PBC2"] = True          # F23 is in both PBC2 and PBC3
    e.rel["F23"]["PBC3"] = True

    e.vvids["I"] = ["0", "1"]              # valid votes for each contest
    e.vvids["C1"] = ["0", "1"]
    e.vvids["C2"] = ["0", "1"]
    e.vvids["C3"] = ["0", "1"]
    e.vvids["F23"] = ["0", "1"]
    for cid in e.cids:                     # invalid votes for each contest
        e.ivids[cid] = ["Invalid", "Overvote", "Undervote"]
    for cid in e.cids:
        if any([e.collection_type[pbcid]=="noCVR" \
                for pbcid in e.rel[cid]]):
            e.ivids[cid].append("noCVR")

def election_data(e):

    # 100000 ballots for each paper ballot collection
    for pbcid in e.pbcids:
        e.n[pbcid] = 10000

    # e.t = vote totals for each cid pbcid vid combo
    for cid in e.cids:
        e.t[cid] = dict()
        for pbcid in e.pbcids:
            e.t[cid][pbcid] = dict()
            for vid in e.vids[cid]:
                e.t[cid][pbcid][vid] = 0
    e.t["I"]["PBC1"]["1"] = 5050           # I is in all counties (margin 1%)
    e.t["I"]["PBC1"]["0"] = 4950
    e.t["I"][ "PBC2"]["1"] = 5050          
    e.t["I"]["PBC2"]["0"] = 4950
    e.t["I"]["PBC3"]["1"] = 5050          
    e.t["I"]["PBC3"]["0"] = 4950
    e.t["C1"]["PBC1"]["1"] = 6500          # C1 is only in PBC1 (margin 30%)
    e.t["C1"]["PBC1"]["0"] = 3500
    e.t["C2"]["PBC2"]["1"] = 6000          # C2 is only in PBC2 (margin 20%)
    e.t["C2"]["PBC2"]["0"] = 4000
    e.t["C3"]["PBC3"]["1"] = 5500          # C3 is only in PBC3 (margin 10%)
    e.t["C3"]["PBC3"]["0"] = 4500
    e.t["F23"]["PBC2"]["1"] = 5250         # F23 is in both PBC2 and PBC3 (margin 5%)
    e.t["F23"]["PBC2"]["0"] = 4750
    e.t["F23"]["PBC3"]["1"] = 5250
    e.t["F23"]["PBC3"]["0"] = 4750
    
    # e.ro = reported outcomes for each cid (all correct here)
    e.ro["I"] = "1"                         
    e.ro["C1"] = "1"
    e.ro["C2"] = "1"
    e.ro["C3"] = "1"
    e.ro["F23"] = "0"

def audit_parameters(e):

    e.risk_limit["I"] = 0.05               # risk limit by contest
    e.risk_limit["C1"] = 0.05
    e.risk_limit["C2"] = 0.05
    e.risk_limit["C3"] = 0.05
    e.risk_limit["F23"] = 0.10  
    e.audit_rate["PBC1"] = 40    # max rate/stage for auditing ballots by pbcid
    e.audit_rate["PBC2"] = 50 
    e.audit_rate["PBC3"] = 60

    e.pseudocount = 0.5

    # Each contest status should be "Auditing" or "Just Watching"
    e.contest_status["I"] = "Auditing"
    e.contest_status["C1"] = "Auditing"
    e.contest_status["C2"] = "Auditing"
    e.contest_status["C3"] = "Auditing"
    e.contest_status["F23"] = "Auditing"

