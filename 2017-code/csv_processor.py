import csv
import csv_readers

election_file = '/Users/hkarimi/Desktop/husayn_bayes_local/2017-code/test_files/election_file.csv'
contests_file = '/Users/hkarimi/Desktop/husayn_bayes_local/2017-code/test_files/contests_file.csv'
collections_file = '/Users/hkarimi/Desktop/husayn_bayes_local/2017-code/test_files/collections_file.csv'
reported_vote_file = '/Users/hkarimi/Desktop/husayn_bayes_local/2017-code/test_files/reported_vote_file.csv'

#get e.rn_p and e.bids_p
def reported_number_p(filename):
    hit_ballots = set()
    rn_p = dict()
    bids_p = dict()
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.reader(f, delimiter = '|')
        for (i,row) in enumerate(reader):
            filtered_ids=list(filter(lambda a: a!='', row[0].split(',')))
            pbcid = filtered_ids[0]
            bid = filtered_ids[2]
            if i!=0:
                if pbcid not in rn_p:
                    rn_p[pbcid]=1
                else:
                    if bid not in hit_ballots:
                        rn_p[pbcid]+=1
                if pbcid not in bids_p:
                    bids_p[pbcid]=[bid]
                else:
                    if bid not in bids_p[pbcid]:
                        bids_p[pbcid].append(bid)
                hit_ballots.add(bid)
    return (rn_p, bids_p)

def reported_number_cpr(filename):
    rn_cpr = dict()
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.reader(f, delimiter ='|')
        for (i,row)in enumerate(reader):
            if i!=0:
                filtered_ids=list(filter(lambda a:a!='', row[0].split(',')))
                pbcid = filtered_ids[0]
                cid = filtered_ids[3]
                selection = tuple(filtered_ids[4:])
                #this is probably not efficient at all 
                if cid in rn_cpr:
                    if pbcid in rn_cpr[cid]:
                        if selection in rn_cpr[cid][pbcid]:
                            rn_cpr[cid][pbcid][selection]+=1
                        else:
                            nested_set(rn_cpr, [cid, pbcid, selection], 1)
                    else:
                        nested_set(rn_cpr, [cid, pbcid, selection], 1)
                else:
                    nested_set(rn_cpr, [cid, pbcid, selection], 1)
    return rn_cpr 

#just call reported_number_cr and sum over reported outcomes
def reported_number_c(filename):
    rn_cr = reported_number_cr(filename)
    rn_c = dict()
    for cid in rn_cr:
        for reported_vote in rn_cr[cid]:
            if cid not in rn_c:
                rn_c[cid]=rn_cr[cid][reported_vote]
            else:
                rn_c[cid]+=rn_cr[cid][reported_vote]
    return rn_c 

#sum over all pbcids 
def reported_number_cr(filename):
    rn_cr = dict()
    rn_cpr = reported_number_cpr(filename)
    for cid in rn_cpr:
        rn_cr[cid] = dict() 
        for pbcid in rn_cpr[cid]:
            for reported_vote in rn_cpr[cid][pbcid]:
                if reported_vote not in rn_cr[cid]:
                    rn_cr[cid][reported_vote] = rn_cpr[cid][pbcid][reported_vote]
                else:
                    rn_cr[cid][reported_vote] += rn_cpr[cid][pbcid][reported_vote]
    return rn_cr 

def reported_outcome_c(filename):
    ro_c = dict()
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.reader(f, delimiter = '|') 
        for(i,row) in enumerate(reader):
            filtered_ids=list(filter(lambda a: a!='', row[0].split(',')))
            contest = filtered_ids[0]
            selection = filtered[1:]
            ro_c[contest]=selection
    return ro_c 

#return the election name 
def election_basics(filename):
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.DictReader(f)
        for (i,row) in enumerate(reader):
            if row['Attribute'] == 'Election name':
                return row['Value'] 

def populate_collections(filename):
    collection_type_p = {}
    pbcids = set() 
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.reader(f, delimiter = '|')
        for (i,row) in enumerate(reader):
            filtered_ids=list(filter(lambda a: a!='', row[0].split(',')))
            if i!= 0:
                pbcids.add(filtered_ids[0])
                if filtered_ids[0] not in collection_type_p:
                    collection_type_p[filtered_ids[0]] = filtered_ids[2] 
    return (collection_type_p, pbcids)

#is e.selid_c all possible selids for each contestid or is it for specifically reported and actual. 
#not from the contests file?
def populate_contests(filename):
    selid_c = dict() 
    cids = set()
    rows_ordered = csv_readers.read_csv_file(filename, varlen=True)
    print('csv_readers returned:', rows_ordered)
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.reader(f, delimiter = '|')
        for (i,row) in enumerate(reader):
            filtered_ids=list(filter(lambda a: a != '', row[0].split(',')))
            if i!=0:
                cids.add(filtered_ids[0])
                if filtered_ids[0] not in selid_c:
                    selid_c[filtered_ids[0]] = filtered_ids[4:]
    return (selid_c, cids)

#list of tuples for each contest
def all_votes_c(reported_file, audited_file):
    votes_c = dict() 
    def all_votes_c_sub(filename):
        with open(reported_file, 'r', encoding="utf8") as f:
            reader = csv.reader(f, delimeter = '|')
            for(i,row) in enumerate(reader):
                filtered_ids=list(filter(lambda a:a !='', row[0].split(',')))
                if i!=0:
                    selection = filtered_ids[4:]
                    contest = filtered_ids[3]
                    if contest not in votes_c:
                        votes_c[contest]=[tuple(selection)]
                    else:
                        votes_c[contest].append(tuple(selection))
    all_votes_c(reported_file)
    all_votes_c(audited_file)
    return votes_c

# 1) make sure selid is one of the possible selid for the given cid 
# 2) write-in candidates? 
def actual_vote_sanity_checker(audited_file, contests_file):
    selid_c = populate_contests(contests_file)
    invalid_bids = [] 
    with open(filename, 'r', encoding="utf8") as f:
        reader = csv.reader(f, delimeter = '|')
        for(i,row) in enumerate(reader):
            filtered_ids=list(filter(lambda a:a !='', row[0].split(',')))
            vote = filtered_ids[4:]
            contest = filtered_ids[3]
            for selection_part in vote:
                if selection_part not in selid_c[contest]:
                    invalid_bids.append(filtered_ids[2])
    return invalid_bids

def reported_results():
    #construct e.ro (the results) 
    reported_totals, _ = vote_totals(reported)
    e_ro = dict()
    for contest in reported_totals:
        results = dict()
        for pbcid in reported_totals[contest]:
            for selid in reported_totals[contest][pbcid]:
                if selid not in results:
                    results[selid] = reported_totals[contest][pbcid][selid]
                else:
                    results[selid] += reported_totals[contest][pbcid][selid]
        e_ro[contest]=sorted(results, key=lambda k: results[k])[-1]
    return e_ro 

def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value

if __name__ == "__main__":
    election_name = election_basics(election_file)
    print('the election name is:', election_name)
    (selid_c, cids) = populate_contests(contests_file)
    print('selid_c is:', selid_c)
    print('cids is:', cids)
    (collection_type_p, pbcids) = populate_collections(collections_file)
    print('collection_type_p is:', collection_type_p)
    print('pbcids are:', pbcids)
    rn_cpr = reported_number_cpr(reported_vote_file)
    print('rn_cpr is:', rn_cpr)
    rn_cr = reported_number_cr(reported_vote_file)
    print('rn_cr is:', rn_cr)
    rn_c = reported_number_c(reported_vote_file)
    print('rn_c is:', rn_c)
