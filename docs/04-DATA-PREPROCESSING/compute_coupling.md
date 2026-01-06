# compute_coupling.py - Detailed Explanation

**Purpose:** Maps DNA barcodes to their corresponding exon sequences using plasmid sequencing data.

**Location:** `/data_preprocessing/compute_coupling.py`

---

## Overview

This script reads paired-end FASTQ files from plasmid sequencing and establishes which barcode corresponds to which exon sequence. This is necessary because the experimental design uses barcodes to track individual exon variants.

---

## Key Logic Blocks

### 1. Global State and Imports (Lines 1-31)

```python
couplings = {}  # Main data structure: barcode → (Counter of exons, bad_read_count)
good_reads = 0
reads_with_N = 0
unidentified_reads = 0
lib_num = 0
```

The script uses global variables to accumulate statistics across all reads. The `couplings` dictionary maps each barcode to:
- A `Counter` of observed exon sequences
- A count of bad reads for that barcode

### 2. collect_barcodes() Function (Lines 26-79)

This is the core function that processes each read pair.

#### Read 1 Validation (Barcode Read)

```python
# Read 1 must be exactly 54 nucleotides
assert len(read_1) == 54

# Reject reads containing 'N' (ambiguous bases)
if "N" in read_1:
    reads_with_N += 1
    return

# Check adapter sequence at positions 5-21
# Expected: "TTTAAACGGGCCCTAT" with positions 19-20 being "AT"
if (read_1[5 + 14 : 5 + 16] != "AT") or (hamming(read_1[5 : 5 + 16], "TTTAAACGGGCCCTAT") >= 2):
    unidentified_reads += 1
    return

# Check adapter sequence at positions 41-54
# Expected: "TCTAGTGAGACGT" with positions 41-42 being "TC"
if (read_1[41:43] != "TC") or (hamming(read_1[41:], "TCTAGTGAGACGT") >= 2):
    unidentified_reads += 1
    return
```

**Logic:** The read must match expected adapter sequences with at most 1 mismatch (Hamming distance < 2). This validates that the read is a genuine barcode read.

#### Barcode Extraction

```python
BARCODE_POSITION = 21
barcode = revcomp(read_1[BARCODE_POSITION : BARCODE_POSITION + 20])
```

**Logic:** The 20-nucleotide barcode is located at positions 21-40 in Read 1. It's stored as the reverse complement because of sequencing orientation.

#### Read 2 Validation (Exon Read)

```python
# Read 2 must be exactly 106 nucleotides
assert len(read_2) == 106

# Check for ambiguous bases
if "N" in read_2:
    couplings[barcode][1] += 1  # Count as bad read
    return

# Check prefix (first 12 nt)
READ_2_PREFIX = "GCCATCCAGGTT"
if read_2[:12] != READ_2_PREFIX:
    couplings[barcode][1] += 1
    return

# Check internal sequence (positions 82-87)
if read_2[82:87] != "CAGGT":
    couplings[barcode][1] += 1
    return
```

**Logic:** Read 2 must have specific prefix and suffix sequences that flank the exon. This validates proper library construction.

#### Exon Extraction

```python
exon = read_2[12 : 12 + 70]  # 70 nt exon at positions 12-82
couplings[barcode][0][exon] += 1
```

**Logic:** The 70-nucleotide exon is extracted from the validated region and counted for this barcode.

### 3. Main Processing Loop (Lines 82-116)

```python
ALL_LIBRARY_NAMES = {0: "ES7A"}
ALL_FILE_NAMES = {0: "BS06911A_S22"}
ALL_BASE_DIR_NAMES = {0: os.path.join(args.input_folder, "Sample_BS06911A/")}

for lib_num in ALL_LIBRARY_NAMES:
    # Reset counters for each library
    good_reads = 0
    reads_with_N = 0
    unidentified_reads = 0
    couplings = {}

    # Process FASTQ files
    num_reads = process_paired_fastq_file(
        FULL_FILE_NAME + "_R1_001.fastq",
        FULL_FILE_NAME + "_R2_001.fastq",
        collect_barcodes,  # Callback function
    )
```

**Logic:** For each library, the script reads paired FASTQ files and calls `collect_barcodes()` for each read pair.

### 4. Coupling Validation (Lines 118-206)

This section validates which barcode-exon pairs are reliable.

```python
MIN_NUMBER_OF_READS = 2  # Minimum reads to consider a barcode

for barcode in couplings.keys():
    coupling_data = couplings[barcode][0]
    reads_for_barcode = sum(coupling_data.values())

    # Skip barcodes with too few reads
    if reads_for_barcode < MIN_NUMBER_OF_READS:
        continue

    # Get most common exon for this barcode
    sequence_frequencies = Counter(coupling_data)
    num_reads_most_common = sequence_frequencies.most_common(1)[0][1]

    # Check if second-most-common exon is too common (suggests bad coupling)
    if (len(sequence_frequencies) > 1) and \
       (sequence_frequencies.most_common(2)[1][1] >= max(2, num_reads_most_common / 4)):
        badly_coupled = True

    # Check if too many bad reads
    elif couplings[barcode][1] >= max(2, num_reads_most_common / 4):
        badly_coupled = True

    else:
        badly_coupled = False
```

**Logic:** A barcode is considered "badly coupled" if:
1. The second-most-common exon appears in ≥25% as many reads as the most common (suggests mixed population)
2. Bad reads account for ≥25% of good reads (suggests sequencing problems)

#### Restriction Site Check

```python
most_common_full_exon_with_flanking = "AGGTT" + most_common_full_exon + "CAGGT"
most_common_full_exon_contains_restriction_site = (
    "CGTCTC" in most_common_full_exon_with_flanking
) or ("GAGACG" in most_common_full_exon_with_flanking)
```

**Logic:** Checks for Esp3I restriction sites (CGTCTC or its reverse complement GAGACG), which can cause cloning artifacts.

### 5. Output Generation (Lines 196-207)

```python
df = pd.DataFrame(
    barcode_coupling,
    columns=[
        "barcode",
        "exon",
        "badly_coupled",
        "contains_restriction_site",
        "num_reads",
    ],
).set_index("barcode")
df.to_csv(ALL_BASE_DIR_NAMES[lib_num] + "coupling.csv")
```

**Logic:** Saves the validated barcode-exon mappings to a CSV file.

---

## Data Flow Diagram

```
FASTQ Read Pair
      │
      ▼
┌──────────────────────────────────────────────────┐
│             collect_barcodes()                    │
├──────────────────────────────────────────────────┤
│  Read 1 (54 nt)         Read 2 (106 nt)         │
│  ┌──────────────┐       ┌────────────────┐      │
│  │ Adapter (21) │       │ Prefix (12)    │      │
│  │ Barcode (20) │       │ Exon (70)      │      │
│  │ Adapter (13) │       │ Suffix (24)    │      │
│  └──────────────┘       └────────────────┘      │
│         │                       │                │
│         ▼                       ▼                │
│    Validate adapters     Validate prefix/suffix  │
│         │                       │                │
│         ▼                       ▼                │
│    Extract barcode       Extract exon            │
│    (revcomp)                                     │
│         │                       │                │
│         └───────┬───────────────┘                │
│                 ▼                                │
│    couplings[barcode][exon] += 1                 │
└──────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────────────────────────────────────┐
│           Validation Step                         │
├──────────────────────────────────────────────────┤
│  For each barcode:                               │
│  • Check read count ≥ 2                          │
│  • Check if single dominant exon                 │
│  • Check restriction sites                       │
│  • Mark as badly_coupled if problematic          │
└──────────────────────────────────────────────────┘
      │
      ▼
     coupling.csv
```

---

## Key Functions Used

| Function | Source | Purpose |
|----------|--------|---------|
| `hamming(s1, s2)` | utils.py | Calculate Hamming distance between strings |
| `revcomp(s)` | utils.py | Reverse complement of DNA sequence |
| `process_paired_fastq_file()` | utils.py | Read paired FASTQ files and call callback |
| `human_format(n)` | utils.py | Format large numbers (e.g., 1000 → 1K) |

---

## Example Output

```
barcode,exon,badly_coupled,contains_restriction_site,num_reads
ACGTACGTACGTACGTACGT,NNNN...70nt...NNNN,False,False,150
GCTAGCTAGCTAGCTAGCTA,NNNN...70nt...NNNN,True,False,45
TTAATTAATTAATTAATTAA,NNNN...70nt...NNNN,False,True,89
```

---

## Statistics Printed

```
Done reading file BS06911A_S22 : 5M total reads; 200K unidentified reads; 50K reads with N; 4.7M good reads
Total number of barcodes seen: 100K
Barcodes with enough reads: 95K
Uniquely coupled barcodes: 90K
Barcodes with too many errors in exon reads: 2K
Barcodes with no clear majority exon: 3K
```
