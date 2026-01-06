# utils.py - Utility Functions Reference

**Purpose:** Common utility functions for data preprocessing, sequence manipulation, and feature engineering.

**Location:** `/data_preprocessing/utils.py`

---

## Function Reference

### String Manipulation Functions

#### human_format(num)
Formats large numbers with K/M/B/T suffixes.

```python
def human_format(num):
    num = float("{:.3g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return "{}{}".format(
        "{:f}".format(num).rstrip("0").rstrip("."),
        ["", "K", "M", "B", "T"][magnitude]
    )

# Examples:
human_format(1234)      # "1.23K"
human_format(1000000)   # "1M"
human_format(999)       # "999"
```

---

#### hamming(s1, s2)
Calculates Hamming distance between two equal-length strings.

```python
def hamming(s1, s2):
    assert len(s1) == len(s2)
    if s1 == s2:
        return 0  # Fast path for equal strings
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))

# Examples:
hamming("ACGT", "ACGT")  # 0
hamming("ACGT", "ACGA")  # 1
hamming("ACGT", "TGCA")  # 4
```

**Used for:** Allowing small mismatches when validating adapter sequences.

---

#### revcomp(str)
Returns reverse complement of a DNA sequence.

```python
def revcomp(str):
    complement = {
        "A": "T", "C": "G", "G": "C", "T": "A",
        "a": "t", "c": "g", "g": "c", "t": "a",
    }
    return "".join(complement.get(base, base) for base in reversed(str))

# Examples:
revcomp("ACGT")    # "ACGT" (palindrome)
revcomp("AACGT")   # "ACGTT"
revcomp("GCTA")    # "TAGC"
```

**Used for:** Extracting barcodes which are read in opposite orientation.

---

#### get_qualities(str)
Converts ASCII quality string to integer Phred scores.

```python
def get_qualities(str):
    return [ord(str[i]) - 33 for i in range(len(str))]

# Example:
get_qualities("IIIII")  # [40, 40, 40, 40, 40] (high quality)
get_qualities("!!!!!") # [0, 0, 0, 0, 0] (lowest quality)
```

**Note:** Not actively used in preprocessing but available for quality filtering.

---

#### contains_Esp3I_site(str)
Checks if sequence contains Esp3I restriction enzyme recognition site.

```python
def contains_Esp3I_site(str):
    return ("CGTCTC" in str) or ("GAGACG" in str)

# Examples:
contains_Esp3I_site("ACGTCTCGT")  # True (contains CGTCTC)
contains_Esp3I_site("ACGTACGT")   # False
```

**Used for:** Filtering out sequences that may have cloning artifacts.

---

### File I/O Functions

#### tqdm_readline(file, pbar)
Reads a line from file and updates progress bar.

```python
def tqdm_readline(file, pbar):
    line = file.readline()
    pbar.update(len(line))  # Update progress by bytes read
    return line
```

**Used internally by:** `process_paired_fastq_file()`

---

#### process_paired_fastq_file(filename1, filename2, callback)
Reads paired-end FASTQ files and calls a callback for each read pair.

```python
def process_paired_fastq_file(filename1, filename2, callback):
    file_size = os.path.getsize(filename1)
    with tqdm(total=file_size) as pbar:
        file1 = open(filename1, "r")
        file2 = open(filename2, "r")
        total_reads = 0

        while True:
            # Read R1
            temp = tqdm_readline(file1, pbar).strip()  # Header
            if temp == "":
                break  # End of file
            read_1 = tqdm_readline(file1, pbar).strip()  # Sequence
            tqdm_readline(file1, pbar)  # + line
            read_1_q = tqdm_readline(file1, pbar).strip()  # Quality

            # Read R2 (no progress bar update)
            file2.readline()  # Header
            read_2 = file2.readline().strip()  # Sequence
            file2.readline()  # + line
            read_2_q = file2.readline().strip()  # Quality

            callback(read_1, read_2, read_1_q, read_2_q)
            total_reads += 1

    return total_reads
```

**Usage:**
```python
def my_callback(read_1, read_2, read_1_q, read_2_q):
    # Process each read pair
    pass

num_reads = process_paired_fastq_file("R1.fastq", "R2.fastq", my_callback)
```

---

### Sequence Feature Functions

#### Flanking Sequence Constants

```python
PRE_SEQUENCE = "TCTGCCTATGTCTTTCTCTGCCATCCAGGTT"   # 32 nt upstream of exon
POST_SEQUENCE = "CAGGTCTGACTATGGGACCCTTGATGTTTT"  # 32 nt downstream of exon

BARCODE_PRE_SEQUENCE = "CACAAGTATCACTAAGCTCGCTCTAGA"   # 27 nt
BARCODE_POST_SEQUENCE = "ATAGGGCCCGTTTAAACCCGCTGAT"   # 25 nt
```

---

#### add_flanking(nts, flanking_len)
Adds genomic flanking sequences to an exon.

```python
def add_flanking(nts, flanking_len):
    return PRE_SEQUENCE[-flanking_len:] + nts + POST_SEQUENCE[:flanking_len]

# Example:
exon = "A" * 70  # 70 nt exon
full_seq = add_flanking(exon, 10)  # 90 nt total
# Returns: "ATCCAGGTT" + exon + "CAGGTCTGAC"
```

---

#### add_barcode_flanking(nts, flanking_len)
Adds flanking sequences to a barcode.

```python
def add_barcode_flanking(nts, flanking_len):
    return BARCODE_PRE_SEQUENCE[-flanking_len:] + nts + BARCODE_POST_SEQUENCE[:flanking_len]
```

---

### One-Hot Encoding Functions

#### ei_vec(i, len)
Creates a one-hot vector.

```python
def ei_vec(i, len):
    result = [0 for i in range(len)]
    result[i] = 1
    return result

# Example:
ei_vec(2, 4)  # [0, 0, 1, 0]
```

---

#### str_to_vector(str, template)
One-hot encodes a string based on a template alphabet.

```python
def str_to_vector(str, template):
    mapping = dict(zip(template, range(len(template))))
    seq = [mapping[i] for i in str]
    return np.eye(len(template))[seq]

# Example:
str_to_vector("AC", "ACGT")
# array([[1, 0, 0, 0],   # A
#        [0, 1, 0, 0]])  # C
```

---

#### nts_to_vector(nts, rna=False)
One-hot encodes a nucleotide sequence.

```python
def nts_to_vector(nts, rna=False):
    if rna:
        return str_to_vector(nts, "ACGU")
    return str_to_vector(nts, "ACGT")

# Example:
nts_to_vector("ACGT")
# array([[1, 0, 0, 0],   # A
#        [0, 1, 0, 0],   # C
#        [0, 0, 1, 0],   # G
#        [0, 0, 0, 1]])  # T
```

---

#### folding_to_vector(nts)
One-hot encodes an RNA secondary structure.

```python
def folding_to_vector(nts):
    return str_to_vector(nts, ".()")

# Example:
folding_to_vector("((..))")
# array([[0, 1, 0],   # (
#        [0, 1, 0],   # (
#        [1, 0, 0],   # .
#        [1, 0, 0],   # .
#        [0, 0, 1],   # )
#        [0, 0, 1]])  # )
```

**Encoding:** `.` = unpaired, `(` = opening base pair, `)` = closing base pair

---

### RNA Structure Functions

#### rna_fold_structs(seq_nts, maxBPspan=0, RNAfold_bin="RNAfold")
Predicts RNA secondary structure using ViennaRNA.

```python
def rna_fold_structs(seq_nts, maxBPspan=0, RNAfold_bin="RNAfold"):
    struct_mfes = RNAutils.RNAfold(
        seq_nts,
        maxBPspan=maxBPspan,
        RNAfold_bin=RNAfold_bin,
    )
    structs = [e[0] for e in struct_mfes]  # Structure strings
    mfes = np.array([e[1] for e in struct_mfes])  # Free energies
    return structs, mfes

# Example:
structs, mfes = rna_fold_structs(["GCGCGCGCGC"])
# structs: ["((((....))))"] or similar
# mfes: array([-5.2]) or similar
```

---

#### compute_structure(seq_nts, RNAfold_bin="RNAfold")
Computes one-hot encoded structure.

```python
def compute_structure(seq_nts, RNAfold_bin="RNAfold"):
    structs, mfes = rna_fold_structs(seq_nts, RNAfold_bin=RNAfold_bin)
    struct_oh = np.array([folding_to_vector(x) for x in structs])
    return struct_oh, structs, mfes
```

---

#### compute_seq_oh(seq_nts)
One-hot encodes a batch of sequences.

```python
def compute_seq_oh(seq_nts):
    return np.array(
        [nts_to_vector(x) for x in [seq.replace("U", "T") for seq in seq_nts]]
    )
```

---

### Wobble Pair Functions

#### find_parentheses(s)
Returns a dictionary mapping opening to closing parenthesis positions.

```python
def find_parentheses(s):
    stack = []
    parentheses_locs = {}
    for i, c in enumerate(s):
        if c == "(":
            stack.append(i)
        elif c == ")":
            parentheses_locs[stack.pop()] = i
    return parentheses_locs

# Example:
find_parentheses("((..))")  # {0: 5, 1: 4}
```

---

#### compute_bijection(s)
Returns an array where each position points to its base pair partner.

```python
def compute_bijection(s):
    parens = find_parentheses(s)
    ret = np.arange(len(s))
    for x in parens:
        ret[x] = parens[x]
        ret[parens[x]] = x
    return ret

# Example:
compute_bijection("((..))")  # array([5, 4, 2, 3, 1, 0])
# Position 0 pairs with 5, position 1 pairs with 4, etc.
```

---

#### compute_wobble_indicator(sequence, structure)
Identifies G-U wobble base pairs.

```python
def compute_wobble_indicator(sequence, structure):
    assert len(sequence) == len(structure)
    bij = compute_bijection(structure)
    return [
        (1 if {sequence[i], sequence[bij[i]]} == {"G", "T"} else 0)
        for i in range(len(sequence))
    ]

# Example:
compute_wobble_indicator("GCGT", "(())")
# If position 0 (G) pairs with position 3 (T), returns [1, 0, 0, 1]
```

**G-U wobble pairs:** Non-Watson-Crick base pairs that are still relatively stable in RNA.

---

### Main Feature Extraction Function

#### create_input_data(seq_nts, RNAfold_bin="RNAfold")
Complete feature extraction pipeline.

```python
def create_input_data(seq_nts, RNAfold_bin="RNAfold"):
    # 1. One-hot encode sequences
    seq_oh = compute_seq_oh(seq_nts)

    # 2. Compute RNA structures and one-hot encode
    struct_oh, structs, _ = compute_structure(seq_nts, RNAfold_bin=RNAfold_bin)

    # 3. Identify wobble base pairs
    wobbles = compute_wobbles(seq_nts, structs)

    return seq_oh, struct_oh, wobbles
```

**Returns:**
- `seq_oh`: (N, 90, 4) - Sequence one-hot encoding
- `struct_oh`: (N, 90, 3) - Structure one-hot encoding
- `wobbles`: (N, 90, 1) - Wobble pair indicators

---

## Usage Example

```python
from data_preprocessing.utils import *

# Prepare sequences
sequences = [
    add_flanking("ACGT" * 17 + "AC", 10),  # 90 nt total
    add_flanking("GCTA" * 17 + "GC", 10),
]

# Extract features
seq_oh, struct_oh, wobbles = create_input_data(sequences)

print(f"Sequences: {seq_oh.shape}")     # (2, 90, 4)
print(f"Structures: {struct_oh.shape}") # (2, 90, 3)
print(f"Wobbles: {wobbles.shape}")      # (2, 90, 1)
```
