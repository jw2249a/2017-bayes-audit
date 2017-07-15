# sampling_orders.py
# Ronald L. Rivest
# July 10, 2017
# python3

"""
Routine to work with multi.py program for election audits.
Generates random sampling orders from a ballot manifest 
and an audit seed, for each paper ballot collection.

The overall algorithm is the "Fisher-Yates shuffle":
     https://en.wikipedia.org/wiki/FisherYates_shuffle

The method used uses SHA256 in counter mode, as in
the program:
     https://people.csail.mit.edu/rivest/sampler.py

"""

import hashlib

import multi


def sha256(hash_input):
    """ 
    Return value of SHA256 hash of input 
    bytearray hash_input, as a nonnegative integer.
    """

    assert isinstance(hash_input, bytearray)
    return int(hashlib.sha256(hash_input).hexdigest(), 16)


def shuffle(L, seed):
    """ Return shuffled copy of list L, based on seed. """

    L = list(L).copy()
    for i in range(len(L)):
        hash_input = bytearray(str(seed)+","+str(i),'utf-8')
        hash_value = sha256(hash_input)
        j = hash_value % (i+1)             # random modulo (i+1)
        L[i], L[j] = L[j], L[i]            # swap
    return L


def test_shuffle(seed=1234567890):

    for i in range(3):
        L = range(20)
        print(shuffle(L, seed+i))
    """
    [12, 13, 2, 18, 3, 8, 9, 7, 17, 6, 16, 5, 11, 19, 1, 14, 10, 0, 4, 15]
    [4, 2, 9, 8, 14, 6, 3, 5, 7, 15, 18, 10, 19, 1, 13, 11, 17, 12, 0, 16]
    [13, 12, 1, 0, 3, 4, 19, 10, 11, 5, 7, 2, 17, 16, 18, 14, 8, 6, 9, 15]
    """
    

def compute_sampling_orders(e):

    for pbcid in e.pbcids:
        print("!!!", pbcid)
        compute_sampling_order(e, pbcid)


def compute_sampling_order(e, pbcid):

    pairs = zip(list(range(1, 1+len(e.bids_p[pbcid]))),
                ebids_p[pbcid])
    shuffled_pairs = shuffle(pairs, str(e.audit_seed)+","+pbcid)
    e.shuffled_indices_p[pbcid] = [i for (i,b) in shuffled_pairs]
    e.shuffled_bids_p[pbcid] = [b for (i,b) in shuffled_pairs]


def write_sampling_orders(e):

    for pbcid in e.pbcids:
        write_sampling_order(e, pbcid)
        

def write_sampling_order(e, pbcid):

    dirpath = os.path.join(multi.ELECTIONS_ROOT, se.election_dirname, "2-reported")
    os.makedirs(dirpath, exist_ok=True)
    ds = utils.date_string()
    filename = os.path.join(dirpath, "manifest-"+pbcid+"-"+ds+".csv")
    with open(filename, "w") as file:
        for fieldname in ["Collection id", "Sample order", "Original index", "Ballot id",
                          "Location", "Comments"]:
            file.write("{},".format(fieldname))
        file.write("\n")
        for i, index in enumerate(e.shuffled_indices_p[pbcid]):
            file.write(pbcid+",")
            file.write("{},".format(i))
            file.write("{},".format(index))
            file.write("{},".format(e.shuffled_bids_p[pbcid][i]))
            file.write("{},".format(e.location_p[pbcid][index]))
            file.write("{},".format(e.comments_p[pbcid][index]))


def test_sampling_orders():

    import syn2
    e = syn2.SynElection()
    # TODO: need to load ballot manifests right here
    compute_sampling_orders(e)
    write_sampling_orders(e)
    

if __name__=="__main__":


    test_shuffle()

    test_sampling_orders()


    
    
