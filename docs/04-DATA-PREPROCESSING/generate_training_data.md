# generate_training_data.py - Detailed Explanation

**Purpose:** Combines splicing analysis from multiple libraries, applies quality filters, computes features (RNA structure), and creates train/test datasets.

**Location:** `/data_preprocessing/generate_training_data.py`

---

## Overview

This is the final preprocessing step that transforms splicing statistics into model-ready training data.

---

## Key Logic Blocks

### 1. read_dataset() Function (Lines 16-31)

```python
def read_dataset(splicing_analysis_csv_path, filter_cryptic_restriction_site=True):
    # Load the CSV file
    barcode_statistics = pd.read_csv(splicing_analysis_csv_path).set_index("barcode")

    # Remove badly coupled barcodes
    barcode_statistics = barcode_statistics[barcode_statistics.badly_coupled == False]

    # Filter barcodes containing restriction sites
    if filter_cryptic_restriction_site:
        contains_restriction_site = barcode_statistics.apply(
            lambda x: utils.contains_Esp3I_site(utils.add_flanking(x.exon, 5))
                   or utils.contains_Esp3I_site(utils.add_barcode_flanking(x.name, 5)),
            axis=1,
        )
        barcode_statistics = barcode_statistics[~contains_restriction_site]

    return barcode_statistics
```

**Logic:**
1. Load splicing analysis CSV
2. Remove rows marked as `badly_coupled` (unreliable barcode-exon mapping)
3. Remove sequences containing Esp3I restriction sites (CGTCTC or GAGACG) which cause cloning artifacts

### 2. to_input_data() Function (Lines 34-39)

```python
def to_input_data(df, flanking_length=10):
    assert flanking_length <= 30 and flanking_length >= 0

    return utils.create_input_data(
        [utils.add_flanking(exon, flanking_length) for exon in df.exon]
    )
```

**Logic:**
1. Add 10 nt of flanking sequence on each side of the 70 nt exon → 90 nt total
2. Call `create_input_data()` which:
   - One-hot encodes the sequence (90 × 4)
   - Predicts RNA secondary structure using ViennaRNA (90 × 3)
   - Computes wobble pair indicators (90 × 1)

### 3. to_target_data() Function (Lines 42-45)

```python
def to_target_data(df):
    return np.array(
        df.num_exon_inclusion / (df.num_exon_inclusion + df.num_exon_skipping)
    )
```

**Logic:** Computes PSI (Percent Spliced In):
```
PSI = num_exon_inclusion / (num_exon_inclusion + num_exon_skipping)
```

This gives a value between 0 (all skipping) and 1 (all inclusion).

### 4. Main Script - Data Loading (Lines 48-71)

```python
data_files = [
    "BS11504A_S1_splicing_analysis.csv",
    "BS11505A_S2_splicing_analysis.csv",
    "BS11506A_S3_splicing_analysis.csv",
]

# Find and load all three CSV files
splicing_analysis_csvs = [
    a for b in [list(Path(data_folder).rglob(f"*{data_file}")) for data_file in data_files]
    for a in b
]

datasets = [read_dataset(d) for d in splicing_analysis_csvs]
```

**Logic:** Recursively finds the three splicing analysis CSV files (one per library) and loads them.

### 5. Main Script - Merging Libraries (Lines 73-96)

```python
# Identify numeric columns (counts) vs non-numeric columns
numeric_columns = np.unique([e for d in datasets for e in d.columns.values if "num" in e])
non_numeric_columns = np.unique([e for d in datasets for e in d.columns.values if e not in numeric_columns])

# Sum numeric columns across libraries
d_numeric = sum([d[numeric_columns] for d in datasets])

# Join with non-numeric columns from first dataset
dataset = (datasets[0][non_numeric_columns]).join(d_numeric).dropna()

# Add derived statistics
dataset["others"] = (
    dataset.num_unknown_splicing
    + dataset.num_intron_retention
    + dataset.num_bad_reads
    + dataset.num_bad_exon1
)
dataset["total"] = (
    dataset.others
    + dataset.num_exon_skipping
    + dataset.num_exon_inclusion
    + dataset.num_splicing_in_exon
)
```

**Logic:**
1. Identify which columns are counts (contain "num")
2. Sum counts across all three libraries for each barcode
3. Compute aggregate statistics:
   - `others`: All non-standard splicing outcomes
   - `total`: Total reads for this barcode

### 6. Main Script - Quality Filtering (Lines 98-108)

```python
# Filter 1: Minimum read count
MIN_READS = 60
dataset = dataset[dataset.num_exon_skipping + dataset.num_exon_inclusion >= MIN_READS]

# Filter 2: Clean splicing required
# Inclusion + skipping must be >80% of total reads
dataset = dataset[
    (dataset.num_exon_inclusion + dataset.num_exon_skipping) / dataset.total > 0.8
]
```

**Logic:**
1. **Minimum reads filter:** At least 60 reads of inclusion + skipping combined
2. **Clean splicing filter:** At least 80% of reads must be either inclusion or skipping (not intron retention, cryptic splicing, etc.)

### 7. Main Script - Train/Test Split (Lines 110-117)

```python
TEST_SPLIT_FRACTION = 0.2
dataset_tr, dataset_te = train_test_split(
    dataset,
    test_size=TEST_SPLIT_FRACTION,
    train_size=1 - TEST_SPLIT_FRACTION,
    random_state=SEED,
)
```

**Logic:** 80% training, 20% test split with fixed random seed (420) for reproducibility.

### 8. Main Script - Feature Computation (Lines 119-126)

```python
print('Computing structure, one-hot-encoding... ', end='')
xTr = to_input_data(dataset_tr)  # Returns (seq_oh, struct_oh, wobbles)
yTr = to_target_data(dataset_tr)  # Returns PSI values

xTe = to_input_data(dataset_te)
yTe = to_target_data(dataset_te)
print('Done.')
```

**Logic:** For each dataset:
1. `to_input_data()`:
   - Adds flanking sequences
   - One-hot encodes DNA sequences
   - Predicts RNA secondary structure using ViennaRNA
   - Identifies wobble base pairs
2. `to_target_data()`:
   - Computes PSI values

### 9. Main Script - Saving Output (Lines 128-144)

```python
data_dump_list = [xTr, yTr, xTe, yTe, dataset_tr, dataset_te]
dataset_names = [
    "xTr", "yTr", "xTe", "yTe",
    "barcode_statistics_train", "barcode_statistics_test",
]

for D, Dn in zip(data_dump_list, dataset_names):
    dump(D, Path(data_folder) / f"{Dn}_ES7_HeLa_ABC.pkl.gz")
```

**Logic:** Saves six files:
- `xTr_ES7_HeLa_ABC.pkl.gz`: Training features (tuple of 3 arrays)
- `yTr_ES7_HeLa_ABC.pkl.gz`: Training labels (PSI values)
- `xTe_ES7_HeLa_ABC.pkl.gz`: Test features
- `yTe_ES7_HeLa_ABC.pkl.gz`: Test labels
- `barcode_statistics_train_ES7_HeLa_ABC.pkl.gz`: Raw training DataFrame
- `barcode_statistics_test_ES7_HeLa_ABC.pkl.gz`: Raw test DataFrame

---

## Data Flow Diagram

```
3 × splicing_analysis.csv
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                    read_dataset()                             │
│  • Load CSV                                                   │
│  • Remove badly_coupled rows                                  │
│  • Remove rows with restriction sites                         │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                    Merge Libraries                            │
│  • Sum numeric columns across 3 libraries                     │
│  • Compute 'others' and 'total' columns                       │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                    Quality Filtering                          │
│  • Filter: inclusion + skipping ≥ 60 reads                   │
│  • Filter: (inclusion + skipping) / total > 0.8              │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│                    Train/Test Split                           │
│  • 80% training, 20% test                                     │
│  • Random seed: 420                                           │
└──────────────────────────────────────────────────────────────┘
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ to_input_data│      │to_target_data│      │ Raw DataFrame│
│              │      │              │      │              │
│ • add_flank  │      │    PSI =     │      │ Save as-is   │
│ • seq_oh     │      │ incl/(incl+  │      │              │
│ • struct_oh  │      │    skip)     │      │              │
│ • wobbles    │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
    xTr/xTe              yTr/yTe          barcode_statistics
   (pkl.gz)             (pkl.gz)              (pkl.gz)
```

---

## Output File Shapes

| File | Type | Shape |
|------|------|-------|
| `xTr_ES7_HeLa_ABC.pkl.gz` | Tuple | (seq_oh, struct_oh, wobble) |
| → `seq_oh` | ndarray | (N_train, 90, 4) |
| → `struct_oh` | ndarray | (N_train, 90, 3) |
| → `wobble` | ndarray | (N_train, 90, 1) |
| `yTr_ES7_HeLa_ABC.pkl.gz` | ndarray | (N_train,) |
| `xTe_ES7_HeLa_ABC.pkl.gz` | Tuple | Same structure as xTr |
| `yTe_ES7_HeLa_ABC.pkl.gz` | ndarray | (N_test,) |

---

## Inspecting the Output

```python
from joblib import load

# Load training data
xTr = load('data/xTr_ES7_HeLa_ABC.pkl.gz')
yTr = load('data/yTr_ES7_HeLa_ABC.pkl.gz')

print(f"Number of training samples: {len(yTr)}")
print(f"Sequence shape: {xTr[0].shape}")
print(f"Structure shape: {xTr[1].shape}")
print(f"Wobble shape: {xTr[2].shape}")
print(f"PSI range: {yTr.min():.3f} - {yTr.max():.3f}")
print(f"Mean PSI: {yTr.mean():.3f}")
```

Expected output:
```
Number of training samples: ~150,000
Sequence shape: (150000, 90, 4)
Structure shape: (150000, 90, 3)
Wobble shape: (150000, 90, 1)
PSI range: 0.000 - 1.000
Mean PSI: ~0.5
```
