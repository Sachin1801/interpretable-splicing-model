# compute_splicing_outcomes.py - Detailed Explanation

**Purpose:** Analyzes cDNA sequencing reads to classify splicing patterns for each barcode.

**Location:** `/data_preprocessing/compute_splicing_outcomes.py`

---

## Overview

This script reads cDNA sequencing data and determines what splicing outcome occurred for each transcript. It classifies each read as exon inclusion, exon skipping, intron retention, or other patterns.

---

## Read Structure (Header Comments, Lines 1-13)

```python
# Read 1: NNNNN[N][N]TTTAAACGGGCCCTATNNNNNNNNNNNNNNNNNNNNTCTAGAGCGAG[CT]
#   Number of Ns (UMI) is random 5-7; barcode is 20N

# Read 2:
#   Diversity: [NN]  (0-2Ns)
#   End of exon 1: AAGTTGGTGGTGAGGCCCTGGGCAG
#   Exon 2: GTT[70nt randomized exon]CAG
#   Exon 3: CTCCTGGGCAACGTGCTGGTCTGTGTGCTGGCC...
```

Read 1 contains a UMI (Unique Molecular Identifier) of 5-7 nt followed by the barcode. Read 2 contains the spliced exons.

---

## Key Logic Blocks

### 1. Configuration (Lines 38-51)

```python
NUM_LIBS = 3
ALL_LIBRARY_NAMES = {0: "ES7_HeLa_A", 1: "ES7_HeLa_B", 2: "ES7_HeLa_C"}
ALL_FILE_NAMES = {0: "BS11504A_S1", 1: "BS11505A_S2", 2: "BS11506A_S3"}
```

Three biological replicates (A, B, C) are processed independently.

### 2. identify_splicing_pattern() Function (Lines 65-162)

This is the core classification function.

#### UMI Length Detection (Lines 80-101)

```python
# Try UMI lengths of 5, 6, or 7 nucleotides
umi_length = -1
for i in (5, 6, 7):
    # Check adapter sequence at expected position
    if (read_1[i + 14 : i + 16] != "AT") or \
       (hamming(read_1[i : i + 16], "TTTAAACGGGCCCTAT") >= 2):
        continue
    # Check end adapter
    if (read_1[i + 36 : i + 38] != "TC") or \
       (hamming(read_1[i + 36 :], "TCTAGAGCGAGCT."[: 4 - i]) >= 2):
        continue
    umi_length = i
    break

if umi_length == -1:  # Could not identify frame
    bad_read_1_reads += 1
    return
```

**Logic:** The UMI length varies from 5-7 nt. The script tries each possible length and checks if the adapter sequences align properly.

#### Barcode Extraction and Validation (Lines 103-107)

```python
barcode = revcomp(read_1[umi_length + 16 : umi_length + 16 + 20])
if not barcode in barcode_statistics.index:
    unknown_barcode_reads += 1
    return
```

**Logic:** Extract the 20-nt barcode and verify it exists in the coupling database from the previous step.

#### Read 2 Frame Detection (Lines 112-129)

```python
EXON_1 = "AAGTTGGTGGTGAGGCCCTGGGCAG"  # 25 nt
read2_frame = -1
for i in range(3):  # Try 0, 1, or 2 nt offset
    if hamming(read_2[i : i + 25], EXON_1) > 2:
        continue
    read2_frame = i
    break

if read2_frame == -1:
    barcode_statistics.at[barcode, "num_bad_exon1"] += 1
    return
```

**Logic:** Read 2 may have 0-2 random nucleotides at the start (diversity elements). The script finds where Exon 1 begins by looking for the expected sequence.

#### Splicing Classification (Lines 131-162)

This is the key classification logic:

```python
# Check for EXON SKIPPING
# Exon 3 starts immediately after Exon 1
if read_2[read2_frame + 25 : read2_frame + 35] == "CTCCTGGGCA":
    barcode_statistics.at[barcode, "num_exon_skipping"] += 1
    return

# Check for INTRON RETENTION
# Intron 1 sequence appears after Exon 1
if read_2[read2_frame + 25 : read2_frame + 35] == "GTTGGTATCA":
    barcode_statistics.at[barcode, "num_intron_retention"] += 1
    return

# Check for EXON INCLUSION
# Full exon 2 (GTT + 70nt exon + CAG) followed by exon 3
expected_sequence = "GTT" + barcode_statistics.at[barcode, "exon"] + "CAG" + "CTCCT."[:-1-read2_frame]
if hamming(read_2[read2_frame + 25 :], expected_sequence) <= 2:
    barcode_statistics.at[barcode, "num_exon_inclusion"] += 1
    return

# Check for CRYPTIC SPLICING WITHIN EXON
# Beginning of exon 2 present, but exon 3 appears before exon 2 ends
if (read_2[read2_frame + 25 : read2_frame + 31] == "GTT" + barcode_statistics.at[barcode, "exon"][:3]) and \
   ("CTCCTGGGCAA" in read_2[read2_frame + 31 :]):
    barcode_statistics.at[barcode, "num_splicing_in_exon"] += 1
    return

# Unknown pattern
barcode_statistics.at[barcode, "num_unknown_splicing"] += 1
```

**Classification Logic:**

| Pattern | Detection Method | Meaning |
|---------|-----------------|---------|
| Exon Skipping | Exon 3 immediately after Exon 1 | Exon 2 is completely excluded |
| Intron Retention | Intron 1 sequence after Exon 1 | Intron not removed |
| Exon Inclusion | Full Exon 2 + Exon 3 | Normal splicing including Exon 2 |
| Splicing in Exon | Start of Exon 2, then Exon 3 appears | Cryptic splice site within Exon 2 |
| Unknown | None of above | Unclassifiable |

### 3. Main Processing Loop (Lines 167-214)

```python
for lib_num in tqdm(range(NUM_LIBS), desc="Iterating libraries"):
    # Initialize barcode_statistics from coupling.csv
    barcode_statistics = pd.read_csv(PLASMID_COUPLING_FILE_NAME).set_index("barcode")

    # Add columns for counting splicing outcomes
    barcode_statistics["num_intron_retention"] = [0] * len(barcode_statistics)
    barcode_statistics["num_exon_inclusion"] = [0] * len(barcode_statistics)
    barcode_statistics["num_exon_skipping"] = [0] * len(barcode_statistics)
    barcode_statistics["num_bad_reads"] = [0] * len(barcode_statistics)
    barcode_statistics["num_bad_exon1"] = [0] * len(barcode_statistics)
    barcode_statistics["num_splicing_in_exon"] = [0] * len(barcode_statistics)
    barcode_statistics["num_unknown_splicing"] = [0] * len(barcode_statistics)

    # Process FASTQ files
    num_reads = process_paired_fastq_file(
        os.path.join(INPUT_FOLDER, FULL_FILE_NAME + "_R1_001.fastq"),
        os.path.join(INPUT_FOLDER, FULL_FILE_NAME + "_R2_001.fastq"),
        identify_splicing_pattern,
    )

    # Save results
    barcode_statistics.to_csv(os.path.join(OUTPUT_FOLDER, FILE_NAME + "_splicing_analysis.csv"))
```

---

## Data Flow Diagram

```
cDNA Read Pair
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│              identify_splicing_pattern()                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Read 1: Detect UMI length (5-7 nt)                         │
│          Extract barcode                                     │
│          Validate against coupling database                  │
│                                                              │
│  Read 2: Detect frame (0-2 nt diversity)                    │
│          Locate Exon 1 end                                   │
│          Check what follows Exon 1:                          │
│                                                              │
│          ┌────────────────┐                                  │
│          │ Exon 3 start?  │──Yes──► EXON SKIPPING           │
│          └───────┬────────┘                                  │
│                  │ No                                        │
│                  ▼                                           │
│          ┌────────────────┐                                  │
│          │ Intron 1 start?│──Yes──► INTRON RETENTION        │
│          └───────┬────────┘                                  │
│                  │ No                                        │
│                  ▼                                           │
│          ┌────────────────┐                                  │
│          │ Full Exon 2?   │──Yes──► EXON INCLUSION          │
│          └───────┬────────┘                                  │
│                  │ No                                        │
│                  ▼                                           │
│          ┌────────────────┐                                  │
│          │ Partial Exon 2?│──Yes──► SPLICING IN EXON        │
│          └───────┬────────┘                                  │
│                  │ No                                        │
│                  ▼                                           │
│          UNKNOWN SPLICING                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
      │
      ▼
  barcode_statistics DataFrame
  (increments appropriate column)
      │
      ▼
  splicing_analysis.csv
```

---

## Reference Sequences

```python
# Exon 1 (25 nt) - end of Exon 1, splices to Exon 2 or 3
EXON_1 = "AAGTTGGTGGTGAGGCCCTGGGCAG"

# Exon 2 structure (variable, 76 nt total)
# "GTT" + [70 nt randomized exon] + "CAG"

# Exon 3 start (10 nt) - distinguishes skipping from inclusion
EXON_3_START = "CTCCTGGGCA"

# Intron 1 start (10 nt) - indicates intron retention
INTRON_1_START = "GTTGGTATCA"
```

---

## Output Format

```csv
barcode,exon,badly_coupled,num_exon_inclusion,num_exon_skipping,num_intron_retention,num_splicing_in_exon,num_unknown_splicing,num_bad_reads,num_bad_exon1
ACGTACGT...,NNNN...70nt...,False,150,30,5,2,8,3,1
```

---

## Statistics Printed

```
Done reading file BS11504A_S1 (ES7_HeLa_A) : 10M total reads; 500K reads with unknown barcode 100K reads with bad Read 1
```

---

## Key Differences from compute_coupling.py

| Aspect | compute_coupling.py | compute_splicing_outcomes.py |
|--------|--------------------|-----------------------------|
| Input | Plasmid DNA | cDNA (spliced RNA) |
| Purpose | Map barcodes to exons | Count splicing outcomes |
| UMI | Fixed 0 nt offset | Variable 5-7 nt |
| Read 2 | Contains single exon | Contains spliced exons 1+2+3 |
| Output | coupling.csv | splicing_analysis.csv |
