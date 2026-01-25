# train_model.py - Training Script Explanation

**Purpose:** Trains the interpretable splicing model using a three-step procedure with progressive batch sizes.

**Location:** `/model_training/train_model.py`

---

## Command Line Arguments

```bash
python model_training/train_model.py \
    --index 0 \                    # Grid search index (0 for single model)
    --data_folder ./data \          # Path to training data
    --model_folder ./output \       # Where to save models
    --results_folder ./output \     # Where to save evaluation results
    --epochs_per_batch_step 10      # Epochs per batch size
```

---

## Key Logic Blocks

### 1. Configuration (Lines 68-97)

```python
# Grid search parameters (single configuration for production)
grid_parameters = {
    "energy_activation": ["softplus"],
    "activity_regularization": [0.0001],
    "position_regularization": [5e-06],
    "adjacency_regularization": [0.01],
    "adjacency_regularization_so": [0.001],
    "position_regularization_structure": [0.0],
    "adjacency_regularization_structure": [0.0],
    "adjacency_regularization_so_structure": [0.0],
    "filter_width": [6],
    "num_filters": [20],
    "structure_filter_width": [30],
    "num_structure_filters": [8],
    "dropout_rate": [0.01],
    "model_type": ["custom_adjacency_regularizer"],
}
```

**Note:** In the production script, these are single-element lists (no actual grid search). The full `model_grid_search.py` has multiple values for hyperparameter exploration.

---

### 2. Data Loading (Lines 99-102)

```python
xTr = load(os.path.join(args.data_folder, "xTr_ES7_HeLa_ABC.pkl.gz"))
yTr = load(os.path.join(args.data_folder, "yTr_ES7_HeLa_ABC.pkl.gz"))
xTe = load(os.path.join(args.data_folder, "xTe_ES7_HeLa_ABC.pkl.gz"))
yTe = load(os.path.join(args.data_folder, "yTe_ES7_HeLa_ABC.pkl.gz"))
```

**Data shapes:**
- `xTr`: Tuple of 3 arrays (seq_oh, struct_oh, wobble)
- `yTr`: 1D array of PSI values
- Same for test set

---

### 3. Model Creation (Lines 119-142)

```python
model = get_model(
    input_length=90,
    randomized_region=(10, 80),  # Where the actual exon is
    num_filters=model_hparams["num_filters"],
    num_structure_filters=model_hparams["num_structure_filters"],
    filter_width=model_hparams["filter_width"],
    structure_filter_width=model_hparams["structure_filter_width"],
    dropout_rate=model_hparams["dropout_rate"],
    activity_regularization=model_hparams["activity_regularization"],
    tune_energy=True,
    position_regularization=model_hparams["position_regularization"],
    adjacency_regularization=model_hparams["adjacency_regularization"],
    adjacency_regularization_so=model_hparams["adjacency_regularization_so"],
    position_regularization_structure=model_hparams["position_regularization_structure"],
    adjacency_regularization_structure=model_hparams["adjacency_regularization_structure"],
    adjacency_regularization_so_structure=model_hparams["adjacency_regularization_so_structure"],
    energy_activation=model_hparams["energy_activation"],
)
```

---

### 4. Batch Schedule (Lines 146-147)

```python
batch_schedule = [16, 64, 128, 256, 512, 1024, 2048]
epoch_schedule = [args.epochs_per_batch_step] * 7  # 10 epochs each
```

**Rationale:**
- Start with small batches: noisy gradients help escape local minima
- End with large batches: faster convergence, better generalization
- Total per step: 7 × 10 = 70 epochs

---

### 5. Step 1: Train Sequence Layers (Lines 149-164)

```python
# Selector is initialized to [1, 0, 0] - sequence branch only
for b, e in zip(batch_schedule, epoch_schedule):
    train_model(
        model,
        xTr,
        yTr,
        filename=os.path.join(args.model_folder, f"{model_fname}_step1.h5"),
        epochs=e,
        batch_size=b,
    )

# Evaluate and save
eval_scores = model.evaluate(xTe, yTe)
dump(eval_scores, os.path.join(args.results_folder, f"{model_fname}_step1.results"))
```

**What's trained:**
- `qc_incl` and `qc_skip` convolutional filters
- `position_bias_incl` and `position_bias_skip`
- `energy_seq` SumDiff layer (w, b)

---

### 6. Step 2: Train Structure Layers (Lines 166-185)

```python
# Switch to structure branch
model.get_layer("output_selector").set_weights(
    [np.array([0, 1.0, 0]).astype(np.float32)]
)

# Train with same schedule
for b, e in zip(batch_schedule, epoch_schedule):
    train_model(
        model,
        xTr,
        yTr,
        filename=os.path.join(args.model_folder, f"{model_fname}_step2.h5"),
        epochs=e,
        batch_size=b,
    )
```

**What's trained:**
- `c_incl_struct` and `c_skip_struct` convolutional filters
- `position_bias_incl_struct` and `position_bias_skip_struct`
- `energy_seq_struct` SumDiff layer

**Note:** Sequence layers from Step 1 continue to be refined.

---

### 7. Step 3: Train Residual Tuner (Lines 187-206)

```python
# Switch to residual tuner output
model.get_layer("output_selector").set_weights(
    [np.array([0, 0.0, 1.0]).astype(np.float32)]
)

# Train with same schedule
for b, e in zip(batch_schedule, epoch_schedule):
    train_model(
        model,
        xTr,
        yTr,
        filename=os.path.join(args.model_folder, f"{model_fname}_step3.h5"),
        epochs=e,
        batch_size=b,
    )

# Final evaluation
eval_scores = model.evaluate(xTe, yTe)
print(eval_scores)
```

**What's trained:**
- `gen_func` ResidualTuner (Dense layers, BatchNorm)

---

## Training Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         STEP 1                                   │
│                   Train Sequence Layers                          │
│                                                                  │
│  Selector: [1, 0, 0]                                            │
│  Output: energy_seq only                                         │
│                                                                  │
│  Trained:                                                        │
│  • qc_incl, qc_skip (Conv1D filters)                            │
│  • position_bias_incl, position_bias_skip                        │
│  • energy_seq (SumDiff)                                          │
│                                                                  │
│  Batch schedule: 16 → 64 → 128 → 256 → 512 → 1024 → 2048       │
│  Epochs: 10 per batch size = 70 total                           │
│                                                                  │
│  Output: model_step1.h5                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STEP 2                                   │
│                   Train Structure Layers                         │
│                                                                  │
│  Selector: [0, 1, 0]                                            │
│  Output: energy_seq_struct (includes seq + struct)               │
│                                                                  │
│  Trained:                                                        │
│  • c_incl_struct, c_skip_struct (Conv1D filters)                │
│  • position_bias_incl_struct, position_bias_skip_struct         │
│  • energy_seq_struct (SumDiff)                                   │
│  • + continued refinement of Step 1 layers                       │
│                                                                  │
│  Batch schedule: same as Step 1                                 │
│                                                                  │
│  Output: model_step2.h5                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STEP 3                                   │
│                   Train Residual Tuner                           │
│                                                                  │
│  Selector: [0, 0, 1]                                            │
│  Output: gen_func (residual tuner applied to energy_seq_struct)  │
│                                                                  │
│  Trained:                                                        │
│  • gen_func (ResidualTuner - Dense, BatchNorm)                  │
│  • + continued refinement of all previous layers                 │
│                                                                  │
│  Batch schedule: same as Step 1                                 │
│                                                                  │
│  Output: model_step3.h5 (FINAL MODEL)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Output Files

| File | Description |
|------|-------------|
| `model_step1.h5` | Model after sequence training |
| `model_step1.results` | Test set evaluation (binary_KL) |
| `model_step2.h5` | Model after structure training |
| `model_step2.results` | Test set evaluation |
| `model_step3.h5` | **Final model** |
| `model_step3.results` | Final test set evaluation |
| `*_lookup.pkl` | Hyperparameter configuration |

---

## train_model() Function (from model.py, Lines 276-316)

```python
def train_model(model, input_data, target_data, filename,
                validation_split=0.25, epochs=256, batch_size=128,
                custom_callbacks=[], verbose=1):

    # Save best model during training
    model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=filename,
        save_weights_only=False,
        monitor="val_binary_KL",
        mode="min",
        save_best_only=True,
    )

    # Stop if no improvement for 10 epochs
    early_stopping_callback = tf.keras.callbacks.EarlyStopping(
        monitor="val_binary_KL",
        patience=10,
        mode="min",
        restore_best_weights=True,
    )

    history = model.fit(
        input_data,
        target_data,
        batch_size=batch_size,
        epochs=epochs,
        validation_split=validation_split,
        callbacks=[model_checkpoint_callback, early_stopping_callback] + custom_callbacks,
    )

    return history
```

---

## Running Training

### Default (uses ./data and ./output)

```bash
./train_model.sh
```

### Custom paths

```bash
python model_training/train_model.py \
    --index 0 \
    --data_folder /path/to/data \
    --model_folder /path/to/models \
    --results_folder /path/to/results \
    --epochs_per_batch_step 10
```

### Reduced training (faster, for testing)

```bash
python model_training/train_model.py \
    --index 0 \
    --data_folder ./data \
    --model_folder ./output \
    --results_folder ./output \
    --epochs_per_batch_step 2  # Only 2 epochs per batch
```

---

## Expected Output

```
TF version: 2.10.0
Using seed: 981
Number of total models: 1. Running index 0
gpus: []  # or list of GPUs
custom_adjacency_regularizer_20260102_0

Step 1 Training:
Epoch 1/10
...
Step 1 Evaluation: [0.0234, 0.0234]

Step 2 Training:
...
Step 2 Evaluation: [0.0189, 0.0189]

Step 3 Training:
...
Step 3 Evaluation: [0.0156, 0.0156]

[0.0156, 0.0156]
```

Final binary_KL loss should be around 0.015-0.020 on the test set.
