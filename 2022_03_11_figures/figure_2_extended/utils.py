import os
from tqdm.auto import tqdm
import numpy as np

def ei_vec(i,len):  # give a one-hot encoding
    result = [0 for i in range(len)]
    result[i] = 1
    return result


def str_to_vector(str, template):
#   return [ei_vec(template.index(nt),len(template)) for nt in str]
    mapping = dict(zip(template, range(len(template))))    
    seq = [mapping[i] for i in str]
    return np.eye(len(template))[seq]


def nts_to_vector(nts, rna=False):
    if rna:
        return str_to_vector(nts, "ACGU")
    return str_to_vector(nts, "ACGT")


def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

def hamming(s1, s2):
    """Calculate the Hamming distance between two bit strings"""
    assert len(s1) == len(s2)
    if (s1 == s2): 
       return 0  # optimization in case strings are equal
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

def revcomp(str):
    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'a': 't', 'c': 'g', 'g': 'c', 't': 'a'}
    return "".join(complement.get(base, base) for base in reversed(str))
    
def get_qualities(str):
    return [ord(str[i])-33 for i in range(len(str))]

def contains_Esp3I_site(str):
    return ("CGTCTC" in str) or ("GAGACG" in str)

## Reads a line from file, and updates tqdm
def tqdm_readline(file, pbar):
    line = file.readline()
    pbar.update(len(line))
    return line

## Reads both FASTQ file, and applies callback on each read
## Returns number of reads
def process_paired_fastq_file(filename1, filename2, callback):
    file_size = os.path.getsize(filename1)
    with tqdm(total=file_size) as pbar:

        file1 = open(filename1,"r") 
        file2 = open(filename2,"r")
        
        total_reads = 0

        while True:
            temp = tqdm_readline(file1,pbar).strip() # header
            if (temp==''):
                break # end of file
            read_1 = tqdm_readline(file1,pbar).strip()
            tqdm_readline(file1,pbar) # header
            read_1_q = tqdm_readline(file1,pbar).strip()
            
            file2.readline() # header
            read_2 = file2.readline().strip()
            file2.readline() # header
            read_2_q = file2.readline().strip()
            
            callback(read_1, read_2, read_1_q, read_2_q)
            
            total_reads += 1

    return total_reads


import matplotlib.pyplot as plt
import scipy.stats
from matplotlib import cm
import numpy as np
    
def scatter_with_kde(x,y,ax,alpha=0.1):
    assert(len(x)==len(y))
    if (len(x)<10000):
        kde = scipy.stats.gaussian_kde([x,y])
    else: # subsample
        indices_to_pick = np.random.choice(range(len(x)), size=10000)
        kde = scipy.stats.gaussian_kde([x[indices_to_pick],y[indices_to_pick]])
    zz = kde([x,y])
    cc = cm.jet((zz-zz.min())/(zz.max()-zz.min()))
    ax.scatter(x,y, alpha=alpha, s =1,  facecolors=cc)

PRE_SEQUENCE = "TCTGCCTATGTCTTTCTCTGCCATCCAGGTT"
POST_SEQUENCE = "CAGGTCTGACTATGGGACCCTTGATGTTTT"
def add_flanking(nts, flanking_len):
    return PRE_SEQUENCE[-flanking_len:] + nts + POST_SEQUENCE[:flanking_len]
   

BARCODE_PRE_SEQUENCE = "CACAAGTATCACTAAGCTCGCTCTAGA"
BARCODE_POST_SEQUENCE = "ATAGGGCCCGTTTAAACCCGCTGAT"
def add_barcode_flanking(nts, flanking_len):
    return BARCODE_PRE_SEQUENCE[-flanking_len:] + nts + BARCODE_POST_SEQUENCE[:flanking_len]

def find_parentheses(s):
    """ Find and return the location of the matching parentheses pairs in s.

    Given a string, s, return a dictionary of start: end pairs giving the
    indexes of the matching parentheses in s. Suitable exceptions are
    raised if s contains unbalanced parentheses.

    """

    # The indexes of the open parentheses are stored in a stack, implemented
    # as a list

    stack = []
    parentheses_locs = {}
    for i, c in enumerate(s):
        if c == '(':
            stack.append(i)
        elif c == ')':
            try:
                parentheses_locs[stack.pop()] = i
            except IndexError:
                raise IndexError('Too many close parentheses at index {}'
                                                                .format(i))
    if stack:
        raise IndexError('No matching close parenthesis to open parenthesis '
                         'at index {}'.format(stack.pop()))
    return parentheses_locs


# compute_bijection("(((....)))....(...)")
# array([ 9,  8,  7,  3,  4,  5,  6,  2,  1,  0, 10, 11, 12, 13, 18, 15, 16,
#       17, 14])
def compute_bijection(s):
    parens = find_parentheses(s)
    ret = np.arange(len(s))
    for x in parens:
        ret[x] = parens[x]
        ret[parens[x]] = x
    return ret

def compute_wobble_indicator(sequence, structure):
    ## Compute an indicator vector of all the wobble base pairs (G-U or U-G)
    assert(len(sequence)==len(structure))
    bij = compute_bijection(structure)
    return [(1 if {sequence[i], sequence[bij[i]]}=={'G','T'} else 0) for i in range(len(sequence))]    

def folding_to_vector(nts):
   #return str_to_vector(nts, ".,|{}()")
   return str_to_vector(nts, ".()")
