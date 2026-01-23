# Data Files Documentation

This document describes all data files in the project.

---

## Training/Test Data (in `/data/`)

### xTr_ES7_HeLa_ABC.pkl.gz
**Training Features**

| Property | Value |
|----------|-------|
| Size | 20.8 MB |
| Format | Joblib compressed pickle |
| Type | Tuple of 3 numpy arrays |

**Structure:**
```python
from joblib import load
xTr = load('data/xTr_ES7_HeLa_ABC.pkl.gz')

# xTr is a tuple: (seq_oh, struct_oh, wobble)
seq_oh = xTr[0]      # Shape: (N, 90, 4) - Sequence one-hot
struct_oh = xTr[1]   # Shape: (N, 90, 3) - Structure one-hot
wobble = xTr[2]      # Shape: (N, 90, 1) - Wobble indicators
```

**Encoding details:**
- Sequence: A=[1,0,0,0], C=[0,1,0,0], G=[0,0,1,0], T=[0,0,0,1]
- Structure: .=[1,0,0], (=[0,1,0], )=[0,0,1]
- Wobble: 1=G-U pair present, 0=no wobble

---

### yTr_ES7_HeLa_ABC.pkl.gz
**Training Labels**

| Property | Value |
|----------|-------|
| Size | 704 KB |
| Format | Joblib compressed pickle |
| Type | numpy array |

**Structure:**
```python
yTr = load('data/yTr_ES7_HeLa_ABC.pkl.gz')
# Shape: (N,) - PSI values between 0 and 1
print(f"Range: {yTr.min():.3f} - {yTr.max():.3f}")
print(f"Mean: {yTr.mean():.3f}")
```

**PSI interpretation:**
- 0.0 = All transcripts skip the exon
- 1.0 = All transcripts include the exon
- 0.5 = Equal inclusion and skipping

---

### xTe_ES7_HeLa_ABC.pkl.gz
**Test Features**

| Property | Value |
|----------|-------|
| Size | 5.2 MB |
| Format | Same as xTr |

---

### yTe_ES7_HeLa_ABC.pkl.gz
**Test Labels**

| Property | Value |
|----------|-------|
| Size | 178 KB |
| Format | Same as yTr |

---

## Inspecting the Data

```python
from joblib import load
import numpy as np

# Load all data
xTr = load('data/xTr_ES7_HeLa_ABC.pkl.gz')
yTr = load('data/yTr_ES7_HeLa_ABC.pkl.gz')
xTe = load('data/xTe_ES7_HeLa_ABC.pkl.gz')
yTe = load('data/yTe_ES7_HeLa_ABC.pkl.gz')

# Print shapes
print("Training set:")
print(f"  Sequence: {xTr[0].shape}")
print(f"  Structure: {xTr[1].shape}")
print(f"  Wobble: {xTr[2].shape}")
print(f"  Labels: {yTr.shape}")

print("\nTest set:")
print(f"  Sequence: {xTe[0].shape}")
print(f"  Labels: {yTe.shape}")

# PSI distribution
print(f"\nPSI statistics (training):")
print(f"  Min: {yTr.min():.3f}")
print(f"  Max: {yTr.max():.3f}")
print(f"  Mean: {yTr.mean():.3f}")
print(f"  Std: {yTr.std():.3f}")
```

Expected output:
```
Training set:
  Sequence: (~150000, 90, 4)
  Structure: (~150000, 90, 3)
  Wobble: (~150000, 90, 1)
  Labels: (~150000,)

Test set:
  Sequence: (~37000, 90, 4)
  Labels: (~37000,)

PSI statistics (training):
  Min: 0.000
  Max: 1.000
  Mean: ~0.5
  Std: ~0.3
```

---

## Supplementary Data (in `/figures/data/`)

### barcode_statistics_train_ES7_HeLa_ABC.csv.gz
**Per-barcode training statistics**

| Column | Description |
|--------|-------------|
| barcode | 20 nt barcode sequence (index) |
| exon | 70 nt exon sequence |
| badly_coupled | Boolean |
| contains_restriction_site | Boolean |
| num_reads | Total DNA reads |
| num_exon_inclusion | Inclusion read count |
| num_exon_skipping | Skipping read count |
| num_intron_retention | Intron retention count |
| num_splicing_in_exon | Cryptic splicing count |
| num_unknown_splicing | Unknown pattern count |
| num_bad_reads | Low quality reads |
| num_bad_exon1 | Bad exon 1 reads |

### barcode_statistics_test_ES7_HeLa_ABC.csv.gz
Same format as training statistics.

### borg_experiment_data_events.csv.gz
Experimental validation data for G-poor filter analysis.

### structure_experiment_data_events.csv.gz
Experimental validation data for secondary structure filter analysis.

---

## Trained Model

### custom_adjacency_regularizer_20210731_124_step3.h5

| Property | Value |
|----------|-------|
| Location | `/output/` (primary) and `/figures/` (copy) |
| Size | 269 KB |
| Format | Keras HDF5 |
| Date | 2021-07-31 |

**Loading the model:**
```python
import tensorflow as tf
from model_training.model import binary_KL, Selector, ResidualTuner, SumDiff, RegularizedBiasLayer

model = tf.keras.models.load_model(
    'output/custom_adjacency_regularizer_20210731_124_step3.h5',
    custom_objects={
        'binary_KL': binary_KL,
        'Selector': Selector,
        'ResidualTuner': ResidualTuner,
        'SumDiff': SumDiff,
        'RegularizedBiasLayer': RegularizedBiasLayer,
    }
)
```

**Model performance:**
- Test set binary_KL: ~0.015-0.020
- Approximate RMSE: ~0.12
- Approximate R²: ~0.85

---

## Converting One-Hot Back to Sequence

```python
def oh_to_sequence(one_hot):
    """Convert one-hot encoding back to sequence string."""
    alphabet = 'ACGT'
    return ''.join(alphabet[np.argmax(pos)] for pos in one_hot)

def oh_to_structure(one_hot):
    """Convert one-hot encoding back to structure string."""
    alphabet = '.()'
    return ''.join(alphabet[np.argmax(pos)] for pos in one_hot)

# Example
seq = oh_to_sequence(xTr[0][0])  # First sequence
struct = oh_to_structure(xTr[1][0])  # First structure
print(f"Sequence: {seq}")
print(f"Structure: {struct}")
```

---

## Dataset Creation Process

The data files were created by:

1. **Plasmid sequencing** → `coupling.csv` (barcode-exon mapping)
2. **cDNA sequencing** → `splicing_analysis.csv` (splicing counts per barcode)
3. **Merging 3 libraries** (A, B, C) → Combined counts
4. **Quality filtering:**
   - Remove badly_coupled barcodes
   - Remove restriction site sequences
   - Require ≥60 reads (inclusion + skipping)
   - Require >80% clean splicing
5. **Feature extraction:**
   - Add 10 nt flanking sequences
   - One-hot encode sequences
   - Predict RNA structures with ViennaRNA
   - Identify wobble base pairs
6. **Train/test split:** 80/20 with random seed 420
