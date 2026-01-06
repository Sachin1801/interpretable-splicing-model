# API Reference

Complete reference for all functions and classes in the project.

---

## Data Preprocessing Module

### utils.py

#### String Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `human_format` | `(num: float) → str` | Format number with K/M/B suffix |
| `hamming` | `(s1: str, s2: str) → int` | Hamming distance between strings |
| `revcomp` | `(str: str) → str` | Reverse complement of DNA |
| `get_qualities` | `(str: str) → List[int]` | ASCII quality to Phred scores |
| `contains_Esp3I_site` | `(str: str) → bool` | Check for restriction site |

#### File I/O

| Function | Signature | Description |
|----------|-----------|-------------|
| `tqdm_readline` | `(file, pbar) → str` | Read line with progress update |
| `process_paired_fastq_file` | `(f1, f2, callback) → int` | Process paired FASTQ files |

#### Sequence Features

| Function | Signature | Description |
|----------|-----------|-------------|
| `add_flanking` | `(nts: str, len: int) → str` | Add flanking sequences |
| `add_barcode_flanking` | `(nts: str, len: int) → str` | Add barcode flanking |
| `nts_to_vector` | `(nts: str, rna=False) → ndarray` | One-hot encode sequence |
| `folding_to_vector` | `(nts: str) → ndarray` | One-hot encode structure |
| `str_to_vector` | `(str: str, template: str) → ndarray` | Generic one-hot encoding |
| `ei_vec` | `(i: int, len: int) → List[int]` | Create one-hot vector |

#### RNA Structure

| Function | Signature | Description |
|----------|-----------|-------------|
| `rna_fold_structs` | `(seqs, maxBPspan=0) → (structs, mfes)` | Predict structures |
| `compute_structure` | `(seqs) → (struct_oh, structs, mfes)` | One-hot encoded structures |
| `compute_seq_oh` | `(seqs) → ndarray` | One-hot encode sequences |
| `compute_wobbles` | `(seqs, structs) → ndarray` | Identify wobble pairs |
| `create_input_data` | `(seqs) → (seq_oh, struct_oh, wobbles)` | Complete feature extraction |

#### Structure Analysis

| Function | Signature | Description |
|----------|-----------|-------------|
| `find_parentheses` | `(s: str) → Dict[int, int]` | Map base pair positions |
| `compute_bijection` | `(s: str) → ndarray` | Pairing array |
| `compute_wobble_indicator` | `(seq, struct) → List[int]` | Wobble pair flags |

---

### RNAutils.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `RNAfold` | `(seqs, bin, temp, span, cmd) → List[[str, float]]` | MFE structure prediction |
| `RNAsubopt` | `(seq, bin, delta) → List[(str, float)]` | Suboptimal structures |
| `RNAsample` | `(seqs, bin, temp, n, span) → List[List[str]]` | Boltzmann sampling |
| `RNA_partition_function` | `(seqs, constraints, ...) → List[float]` | Partition function |

---

### compute_coupling.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `collect_barcodes` | `(r1, r2, r1_q, r2_q) → None` | Extract barcode-exon pairs |

**Global variables:** `couplings`, `good_reads`, `reads_with_N`, `unidentified_reads`

---

### compute_splicing_outcomes.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `identify_splicing_pattern` | `(r1, r2, r1_q, r2_q) → None` | Classify splicing |

**Splicing categories:** `num_exon_inclusion`, `num_exon_skipping`, `num_intron_retention`, `num_splicing_in_exon`, `num_unknown_splicing`

---

### generate_training_data.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `read_dataset` | `(path, filter=True) → DataFrame` | Load filtered CSV |
| `to_input_data` | `(df, flanking=10) → tuple` | Create model inputs |
| `to_target_data` | `(df) → ndarray` | Compute PSI values |

---

## Model Training Module

### model.py

#### Custom Layers

| Class | Purpose | Key Parameters |
|-------|---------|----------------|
| `Selector` | Select between inputs | `trainable=False` |
| `ResidualTuner` | Residual MLP | `hidden_units=100` |
| `SumDiff` | Energy difference | `freeze=False` |
| `RegularizedBiasLayer` | Position bias | Regularization params |

#### Regularizers

| Class/Function | Purpose |
|----------------|---------|
| `MultiRegularizer` | Combined regularizer |
| `pos_reg` | L2 position penalty |
| `adj_reg_fo` | First-order smoothness |
| `adj_reg_so` | Second-order smoothness |

#### Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `binary_KL` | `(y_true, y_pred) → scalar` | Binary KL divergence loss |
| `regularized_act` | `(x, reg, act) → tensor` | Activation with regularization |
| `train_model` | `(model, X, y, file, ...) → history` | Train with checkpointing |
| `get_model` | `(**kwargs) → Model` | Create model instance |

#### get_model() Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_length` | int | 90 | Sequence length |
| `randomized_region` | tuple | (10, 80) | Exon position |
| `num_filters` | int | 20 | Sequence filters |
| `num_structure_filters` | int | 8 | Structure filters |
| `filter_width` | int | 6 | Sequence filter size |
| `structure_filter_width` | int | 30 | Structure filter size |
| `dropout_rate` | float | 0.01 | Dropout probability |
| `activity_regularization` | float | 0.0 | Activation L1 |
| `position_regularization` | float | 2.5e-5 | Position L2 |
| `adjacency_regularization` | float | 0.0 | First-order smoothness |
| `adjacency_regularization_so` | float | 0.0 | Second-order smoothness |
| `energy_activation` | str | "softplus" | Energy activation |
| `tune_energy` | bool | True | Train energy params |

---

## Figures Module

### force_plot.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_link_midpoint` | `(fn, mid, eps, ...) → float` | Find sigmoid midpoint |
| `collapse_filters` | `(act_i, act_s, ...) → (df_i, df_s)` | Group filter activations |
| `create_force_data` | `(act_i, act_s, ...) → (Series, Series)` | Aggregate forces |
| `merge_small_forces` | `(forces, thresh) → Series` | Combine small contributions |
| `draw_force_plot` | `(seqs, annots, ...) → Figure` | Create visualization |

### sequence_logo.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `plot_logo` | `(df, thresh, ax, colors) → None` | Draw sequence logo |
| `compute_freqs` | `(kmers) → DataFrame` | Nucleotide frequencies |
| `compute_info` | `(freqs) → ndarray` | Information content |
| `compute_heights` | `(freqs) → DataFrame` | Logo heights |
| `sequence_logo_heights` | `(df) → DataFrame` | Combined calculation |
| `draw_floating_logo` | `(heights, ..., ax) → None` | Overlay logo on axes |
| `compute_EDLogo_scores` | `(kmers, normed) → DataFrame` | Enrichment/depletion |
| `plot_EDLogo` | `(df, thresh, ax) → None` | Draw ED logo |

### draw_stem_loop.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `draw_line` | `(d, x1, y1, x2, y2, color) → None` | SVG line |
| `draw_nucleotide` | `(d, x, y, nt, color) → None` | SVG nucleotide circle |
| `draw_oligo` | `(d, xs, ys, nts, colors) → None` | SVG oligonucleotide |
| `draw_stem_loop` | `(nts, stem_len, colors, file) → None` | Complete stem-loop SVG |

### kl.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `knn_distance` | `(point, sample, k) → float` | k-NN distance |
| `verify_sample_shapes` | `(s1, s2, k) → None` | Validate input shapes |
| `naive_estimator` | `(s1, s2, k) → float` | Brute-force KL estimate |
| `scipy_estimator` | `(s1, s2, k) → float` | KDTree-based KL |
| `skl_estimator` | `(s1, s2, k) → float` | sklearn-based KL |
| `skl_estimator_efficient` | `(s1, s2, k) → float` | Vectorized KL |

### generate_custom_model.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `lanczos_kernel` | `(x, order) → ndarray` | Lanczos interpolation kernel |
| `lanczos_interpolate` | `(arr, positions, order) → ndarray` | Interpolate at positions |
| `lanczos_resampling` | `(arr, new_len, order) → ndarray` | Resample to new length |
| `resample_one_positional_bias` | `(weights, len, pad) → ndarray` | Resample position bias |
| `resample_positional_bias_weights` | `(weights, len, pad) → ndarray` | Resample all biases |
| `generate_custom_model` | `(new_len, delta_basal) → Model` | Create modified model |

### figutils.py

| Function | Signature | Description |
|----------|-----------|-------------|
| `subsample_points` | `(x, y, max) → (x, y)` | Random subsampling |
| `scatter_with_kde` | `(x, y, ax, alpha) → None` | Density scatter plot |
| `safelog` | `(x, tol) → ndarray` | Numerically safe log |
| `bin_kl` | `(y_true, y_pred) → ndarray` | Binary KL divergence |
| `flatten_dict` | `(d) → (keys, values)` | Flatten nested dict |
| `insert_motif_in_middle_of_sequence` | `(seq, motif) → str` | Insert motif |
| `insert_motif_in_middle_of_sequences` | `(seqs, motif) → Dict` | Batch insert |
| `landing_pads_to_sw_exons` | `(mers, motif, pre, post) → List` | Create landing pads |
| `all_seqs` | `(length) → List[str]` | Generate all k-mers |
| `extract_str_patches` | `(lst, n) → List[List[str]]` | Extract n-grams |
| `compute_activations_simple_conv` | `(layer, window) → Dict` | k-mer activations |

---

## Usage Examples

### Making Predictions

```python
from model_training.model import binary_KL, Selector, ResidualTuner, SumDiff, RegularizedBiasLayer
import tensorflow as tf
from joblib import load

# Load model
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

# Load test data
xTe = load('data/xTe_ES7_HeLa_ABC.pkl.gz')
yTe = load('data/yTe_ES7_HeLa_ABC.pkl.gz')

# Predict
predictions = model.predict(xTe)
```

### Creating Force Plots

```python
import sys
sys.path.append('figures')
from force_plot import draw_force_plot

fig = draw_force_plot(
    sequences=['ATGC...' * 22 + 'AT'],  # 90 nt
    annotations=['My Sequence'],
)
fig.savefig('my_force_plot.pdf')
```

### Processing New Sequences

```python
from data_preprocessing.utils import add_flanking, create_input_data

exon = 'ACGT' * 17 + 'AC'  # 70 nt
full_seq = add_flanking(exon, 10)  # 90 nt

seq_oh, struct_oh, wobbles = create_input_data([full_seq])

# Now use with model
X = [seq_oh, struct_oh, wobbles]
psi = model.predict(X)[0, 0]
print(f"Predicted PSI: {psi:.3f}")
```
