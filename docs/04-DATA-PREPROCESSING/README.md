# Data Preprocessing Overview

This module processes raw sequencing data into training-ready datasets for the splicing model.

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAW FASTQ FILES                              │
│  Plasmid sequencing: barcode-exon pairs                         │
│  cDNA sequencing: splicing outcomes                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   compute_coupling.py                            │
│  Input:  Paired FASTQ files from plasmid sequencing             │
│  Output: coupling.csv (barcode → exon mapping)                  │
│                                                                  │
│  Key steps:                                                      │
│  1. Validate read format (54 nt for R1, 106 nt for R2)         │
│  2. Extract 20 nt barcode from R1                               │
│  3. Extract 70 nt exon from R2                                  │
│  4. Filter badly coupled barcodes                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              compute_splicing_outcomes.py                        │
│  Input:  Paired FASTQ files from cDNA sequencing                │
│          coupling.csv from previous step                         │
│  Output: splicing_analysis.csv (per-barcode splicing counts)    │
│                                                                  │
│  Key steps:                                                      │
│  1. Identify barcode in each read                               │
│  2. Classify splicing pattern:                                  │
│     - Exon inclusion                                            │
│     - Exon skipping                                             │
│     - Intron retention                                          │
│     - Splicing within exon                                      │
│     - Unknown                                                   │
│  3. Aggregate counts per barcode                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              generate_training_data.py                           │
│  Input:  splicing_analysis.csv files (3 libraries)              │
│  Output: Training/test datasets (pkl.gz files)                  │
│                                                                  │
│  Key steps:                                                      │
│  1. Merge data across libraries                                 │
│  2. Filter by read count (≥60 reads)                           │
│  3. Filter by splicing quality (>80% inclusion+skipping)       │
│  4. Add flanking sequences                                      │
│  5. Compute RNA secondary structure                             │
│  6. One-hot encode sequences                                    │
│  7. Train/test split (80/20)                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Descriptions

| File | Purpose | Lines |
|------|---------|-------|
| [compute_coupling.py](./compute_coupling.md) | Map barcodes to exon sequences | 208 |
| [compute_splicing_outcomes.py](./compute_splicing_outcomes.md) | Classify splicing patterns | 215 |
| [generate_training_data.py](./generate_training_data.md) | Create training/test datasets | 145 |
| [utils.py](./utils.md) | Utility functions | 239 |
| [RNAutils.py](./RNAutils.md) | ViennaRNA wrapper functions | ~100 |

---

## Read Formats

### Plasmid Sequencing (for compute_coupling.py)

**Read 1 (54 nt):** Contains barcode
```
Position:    1-5    6-21            22-41        42-54
Content:     [...]  TTTAAACGGGCCCTAT  [BARCODE]   TCTAGTGAGACGT
             noise  adapter          20nt barcode adapter
```

**Read 2 (106 nt):** Contains exon
```
Position:    1-12         13-82     83-106
Content:     GCCATCCAGGTT  [EXON]    CAGGT...
             prefix       70nt exon  suffix
```

### cDNA Sequencing (for compute_splicing_outcomes.py)

**Read 1 (54 nt):** Contains UMI + barcode
```
Position:    1-5/6/7  +16          +20           +13
Content:     [UMI]    adapter      [BARCODE]     adapter
             5-7nt    fixed        20nt          fixed
```

**Read 2 (106 nt):** Contains exons 1, 2, 3
```
Structure depends on splicing outcome:
- Exon inclusion:  [Exon1][Exon2][Exon3]
- Exon skipping:   [Exon1][Exon3]
- Intron retention: [Exon1][Intron]...
```

---

## Output Data Format

### coupling.csv

| Column | Description |
|--------|-------------|
| `barcode` | 20 nt barcode sequence (index) |
| `exon` | 70 nt exon sequence |
| `badly_coupled` | Boolean: barcode-exon mapping unclear |
| `contains_restriction_site` | Boolean: has CGTCTC or GAGACG |
| `num_reads` | Number of reads for this barcode |

### splicing_analysis.csv

| Column | Description |
|--------|-------------|
| `barcode` | 20 nt barcode sequence (index) |
| `exon` | 70 nt exon sequence |
| `badly_coupled` | From coupling.csv |
| `num_exon_inclusion` | Count of inclusion reads |
| `num_exon_skipping` | Count of skipping reads |
| `num_intron_retention` | Count of intron retention reads |
| `num_splicing_in_exon` | Count of cryptic splicing reads |
| `num_unknown_splicing` | Count of unclassified reads |
| `num_bad_reads` | Count of low-quality reads |
| `num_bad_exon1` | Count of reads with bad exon 1 |

### Training Data (pkl.gz)

| File | Shape | Description |
|------|-------|-------------|
| `xTr_ES7_HeLa_ABC.pkl.gz` | Tuple of 3 arrays | (seq_oh, struct_oh, wobble) |
| | `[0]`: (N, 90, 4) | Sequence one-hot |
| | `[1]`: (N, 90, 3) | Structure one-hot |
| | `[2]`: (N, 90, 1) | Wobble indicators |
| `yTr_ES7_HeLa_ABC.pkl.gz` | (N,) | PSI values (0-1) |

---

## Running the Pipeline

### Full Pipeline (from raw data)

```bash
export DATA_FOLDER=./fasta_files

# Step 1: Compute barcode-exon coupling
python data_preprocessing/compute_coupling.py --input_folder $DATA_FOLDER

# Step 2: Analyze splicing outcomes
python data_preprocessing/compute_splicing_outcomes.py \
    --input_folder $DATA_FOLDER \
    --output_folder $DATA_FOLDER \
    --plasmid_coupling_file_name $DATA_FOLDER/Sample_BS06911A/coupling.csv

# Step 3: Generate training data
python data_preprocessing/generate_training_data.py --input_folder $DATA_FOLDER
```

### Or Use the Script

```bash
./preprocess.sh
```

---

## Data Quality Filters

The pipeline applies several quality filters:

1. **Barcode coupling quality:**
   - Minimum 2 reads per barcode
   - Second most common exon must be <25% of most common
   - Bad reads must be <25% of total

2. **Splicing analysis quality:**
   - Minimum 60 total reads (inclusion + skipping)
   - Inclusion + skipping must be >80% of all reads
   - Removes cryptic splicing artifacts

3. **Restriction site filter:**
   - Removes sequences containing CGTCTC or GAGACG (Esp3I sites)
   - These can cause cloning artifacts

---

## Key Constants

```python
# Flanking sequences (from utils.py)
PRE_SEQUENCE = "TCTGCCTATGTCTTTCTCTGCCATCCAGGTT"   # 32 nt before exon
POST_SEQUENCE = "CAGGTCTGACTATGGGACCCTTGATGTTTT"  # 32 nt after exon

# Adapter sequences for barcode validation
BARCODE_ADAPTER_5 = "TTTAAACGGGCCCTAT"  # 16 nt
BARCODE_ADAPTER_3 = "TCTAGTGAGACGT"     # 13 nt

# Reference exon sequences
EXON_1 = "AAGTTGGTGGTGAGGCCCTGGGCAG"     # 25 nt
EXON_3_START = "CTCCTGGGCA"               # 10 nt
INTRON_1_START = "GTTGGTATCA"             # 10 nt
```

---

## Next: Detailed File Documentation

- [compute_coupling.py](./compute_coupling.md) - Barcode-exon mapping
- [compute_splicing_outcomes.py](./compute_splicing_outcomes.md) - Splicing classification
- [generate_training_data.py](./generate_training_data.md) - Dataset generation
- [utils.py](./utils.md) - Utility functions
- [RNAutils.py](./RNAutils.md) - RNA structure utilities
