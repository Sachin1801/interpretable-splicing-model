# Quick Start Guide

This guide shows you how to use the interpretable splicing model to make predictions.

---

## Option 1: Use Pre-trained Model (Recommended)

The repository includes a pre-trained model and preprocessed data. You can start making predictions immediately.

### Load the Model

```python
import tensorflow as tf
import numpy as np
import sys

# Add project to path
sys.path.append('/path/to/interpretable-splicing-model')

from model_training.model import binary_KL, Selector, ResidualTuner, SumDiff, RegularizedBiasLayer

# Load pre-trained model
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

print("Model loaded!")
```

### Make Predictions on Test Data

```python
from joblib import load

# Load test data
xTe = load('data/xTe_ES7_HeLa_ABC.pkl.gz')
yTe = load('data/yTe_ES7_HeLa_ABC.pkl.gz')

print(f"Test set size: {len(yTe)} samples")
print(f"Input shapes: seq={xTe[0].shape}, struct={xTe[1].shape}, wobble={xTe[2].shape}")

# Make predictions
predictions = model.predict(xTe)

# Evaluate
from sklearn.metrics import mean_squared_error, r2_score
rmse = np.sqrt(mean_squared_error(yTe, predictions))
r2 = r2_score(yTe, predictions)

print(f"RMSE: {rmse:.4f}")
print(f"R²: {r2:.4f}")
```

### Predict on Your Own Sequence

```python
import subprocess
import numpy as np

# Your 70-nucleotide exon sequence
exon_sequence = "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC"

# Add flanking sequences (10 nt each side)
PRE_SEQUENCE = "TCTGCCTATGTCTTTCTCTGCCATCCAGGTT"
POST_SEQUENCE = "CAGGTCTGACTATGGGACCCTTGATGTTTT"
full_sequence = PRE_SEQUENCE[-10:] + exon_sequence + POST_SEQUENCE[:10]

print(f"Full sequence (90 nt): {full_sequence}")

# One-hot encode sequence
def nts_to_vector(nts):
    mapping = {'A': 0, 'C': 1, 'G': 2, 'T': 3}
    encoded = np.zeros((len(nts), 4))
    for i, nt in enumerate(nts):
        encoded[i, mapping[nt]] = 1
    return encoded

seq_oh = nts_to_vector(full_sequence)

# Get RNA secondary structure using ViennaRNA
result = subprocess.run(
    ['RNAfold', '--noPS'],
    input=full_sequence.replace('T', 'U'),
    capture_output=True,
    text=True
)
structure = result.stdout.strip().split('\n')[1].split()[0]

# One-hot encode structure
def structure_to_vector(struct):
    mapping = {'.': 0, '(': 1, ')': 2}
    encoded = np.zeros((len(struct), 3))
    for i, s in enumerate(struct):
        encoded[i, mapping[s]] = 1
    return encoded

struct_oh = structure_to_vector(structure)

# Compute wobble pairs
def compute_wobbles(seq, struct):
    # Find matching parentheses
    stack = []
    pairs = {}
    for i, s in enumerate(struct):
        if s == '(':
            stack.append(i)
        elif s == ')':
            j = stack.pop()
            pairs[i] = j
            pairs[j] = i

    # Check for G-U wobble pairs
    wobble = np.zeros((len(seq), 1))
    for i in range(len(seq)):
        if i in pairs:
            j = pairs[i]
            pair = {seq[i], seq[j]}
            if pair == {'G', 'T'} or pair == {'G', 'U'}:
                wobble[i] = 1
                wobble[j] = 1
    return wobble

wobble = compute_wobbles(full_sequence, structure)

# Prepare input (add batch dimension)
X = [
    np.expand_dims(seq_oh, 0),
    np.expand_dims(struct_oh, 0),
    np.expand_dims(wobble, 0)
]

# Predict
psi = model.predict(X)[0, 0]
print(f"Predicted PSI: {psi:.3f}")
print(f"Interpretation: {psi*100:.1f}% exon inclusion expected")
```

---

## Option 2: Train from Scratch

If you want to retrain the model:

### Using Pre-processed Data

```bash
# Train model (uses data/*.pkl.gz files)
./train_model.sh
```

Or manually:

```bash
python model_training/train_model.py \
    --index 0 \
    --data_folder ./data \
    --model_folder ./output \
    --results_folder ./output \
    --epochs_per_batch_step 10
```

### From Raw FASTQ Files

If you have raw sequencing data:

```bash
# Step 1: Preprocess raw data
./preprocess.sh

# Step 2: Train model
./train_model.sh
```

---

## Option 3: Generate Figures

The Jupyter notebooks in `figures/` reproduce the paper's figures:

```bash
cd figures
jupyter notebook
```

Available notebooks:
- `figure_force_plots.ipynb` - Main figures 3, 4, 5, S6-S8
- `figure_extended_other_datasets.ipynb` - Cross-validation (S3, S5)
- `figure_validation_skipping_count.ipynb` - Validation (S9)
- `generate_csv_for_supplementary.ipynb` - Export data

---

## Common Use Cases

### 1. Batch Prediction

```python
# Predict on multiple sequences
sequences = [
    "ACGT..." * 17 + "AC",  # 70 nt each
    "GCTA..." * 17 + "GC",
]

# Process all sequences
X_batch = []
for seq in sequences:
    full_seq = PRE_SEQUENCE[-10:] + seq + POST_SEQUENCE[:10]
    # ... one-hot encode each ...
    X_batch.append([seq_oh, struct_oh, wobble])

# Predict
predictions = model.predict([
    np.stack([x[0] for x in X_batch]),
    np.stack([x[1] for x in X_batch]),
    np.stack([x[2] for x in X_batch]),
])
```

### 2. Analyze Model Interpretability

```python
# Get intermediate layer outputs for interpretability
layer_names = ['qc_incl', 'qc_skip', 'position_bias_incl', 'position_bias_skip']

for name in layer_names:
    layer = model.get_layer(name)
    intermediate_model = tf.keras.Model(
        inputs=model.inputs,
        outputs=layer.output
    )
    activations = intermediate_model.predict(X)
    print(f"{name}: shape={activations.shape}")
```

### 3. Compare Wild-type vs Mutant

```python
# Wild-type sequence
wt_seq = "ACGTACGT..." # 70 nt

# Mutant with single nucleotide change
mut_seq = wt_seq[:35] + 'C' + wt_seq[36:]  # G->C at position 35

# Predict both
wt_psi = predict_single_sequence(wt_seq)
mut_psi = predict_single_sequence(mut_seq)

print(f"Wild-type PSI: {wt_psi:.3f}")
print(f"Mutant PSI: {mut_psi:.3f}")
print(f"Delta PSI: {mut_psi - wt_psi:.3f}")
```

---

## Output Interpretation

| PSI Value | Interpretation |
|-----------|----------------|
| 0.0 - 0.2 | Strong exon skipping |
| 0.2 - 0.4 | Moderate skipping tendency |
| 0.4 - 0.6 | Balanced inclusion/skipping |
| 0.6 - 0.8 | Moderate inclusion tendency |
| 0.8 - 1.0 | Strong exon inclusion |

---

## Next Steps

- [Data Preprocessing](./04-DATA-PREPROCESSING/) - Understand input data pipeline
- [Model Architecture](./05-MODEL-ARCHITECTURE/) - Deep dive into the neural network
- [Building a Web Server](./08-EXTENDING-FOR-NAR.md) - Deploy as NAR web server
