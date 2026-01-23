# Model Architecture Overview

This document explains the neural network architecture used for interpretable splicing prediction.

---

## Design Philosophy

The model is designed for **interpretability** - understanding *why* an exon is included or skipped, not just predicting the outcome. Key design choices:

1. **Energy-based model:** Prediction is framed as a competition between inclusion and skipping "forces"
2. **Position-specific biases:** Every position in the exon has learned importance weights
3. **Separate branches:** Inclusion and skipping are modeled by different filters
4. **Smoothness regularization:** Position biases vary smoothly along the sequence
5. **Three-step training:** Sequence → Structure → Fine-tuning for controlled learning

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 INPUTS                                       │
│                                                                              │
│   seq_input (90, 4)      struct_input (90, 3)      wobble_input (90, 1)     │
│   One-hot DNA            One-hot structure         Wobble pair indicators   │
└─────────────────────────────────────────────────────────────────────────────┘
         │                         │                         │
         │                         └────────────┬────────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────────────────┐      ┌─────────────────────────────────────────┐
│    SEQUENCE BRANCH          │      │         STRUCTURE BRANCH                 │
│                             │      │                                          │
│  ┌─────────────────────┐   │      │  ┌──────────────────────────────────┐   │
│  │ qc_incl             │   │      │  │ Concatenate([seq, struct, wobble])│   │
│  │ Conv1D(20, 6)       │   │      │  │ Shape: (90, 8)                    │   │
│  │ "inclusion filters" │   │      │  └──────────────────────────────────┘   │
│  └──────────┬──────────┘   │      │                   │                      │
│             │               │      │                   ▼                      │
│             ▼               │      │  ┌──────────────────────────────────┐   │
│  ┌─────────────────────┐   │      │  │ c_incl_struct / c_skip_struct     │   │
│  │ position_bias_incl  │   │      │  │ Conv1D(8, 30)                     │   │
│  │ RegularizedBiasLayer│   │      │  │ "structure filters"               │   │
│  └──────────┬──────────┘   │      │  └──────────────────────────────────┘   │
│             │               │      │                   │                      │
│             ▼               │      │                   ▼                      │
│  ┌─────────────────────┐   │      │  ┌──────────────────────────────────┐   │
│  │ Dropout(0.01)       │   │      │  │ position_bias_incl_struct         │   │
│  └──────────┬──────────┘   │      │  │ RegularizedBiasLayer              │   │
│             │               │      │  └──────────────────────────────────┘   │
│  ┌─────────────────────┐   │      │                   │                      │
│  │ qc_skip             │   │      │                   ▼                      │
│  │ Conv1D(20, 6)       │   │      │  ┌──────────────────────────────────┐   │
│  │ "skipping filters"  │   │      │  │ Dropout(0.01)                     │   │
│  └──────────┬──────────┘   │      │  └──────────────────────────────────┘   │
│             │               │      │                   │                      │
│             ▼               │      │                   ▼                      │
│  ┌─────────────────────┐   │      │  ┌──────────────────────────────────┐   │
│  │ position_bias_skip  │   │      │  │ Trim to (85, 8)                   │   │
│  │ RegularizedBiasLayer│   │      │  │ [:, 2:-3, :]                      │   │
│  └──────────┬──────────┘   │      │  └──────────────────────────────────┘   │
│             │               │      │                                          │
│             ▼               │      │                                          │
│  ┌─────────────────────┐   │      │                                          │
│  │ Dropout(0.01)       │   │      │                                          │
│  └──────────┬──────────┘   │      │                                          │
│             │               │      │                                          │
└─────────────┼───────────────┘      └──────────────────────┼───────────────────┘
              │                                              │
              │  Shape: (85, 20)                             │  Shape: (85, 8)
              │                                              │
              └──────────────────────┬───────────────────────┘
                                     │
                                     ▼
                    ┌───────────────────────────────────────┐
                    │         Concatenate                   │
                    │   seq_struct_concat_incl (85, 28)     │
                    │   seq_struct_concat_skip (85, 28)     │
                    └───────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENERGY COMPUTATION                                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ energy_seq = SumDiff([                                               │   │
│  │     softplus(dropout_bias_incl),                                     │   │
│  │     softplus(dropout_bias_skip)                                      │   │
│  │ ])                                                                   │   │
│  │                                                                      │   │
│  │ Formula: w * (sum(incl) - sum(skip)) + b                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ energy_seq_struct = SumDiff([                                        │   │
│  │     softplus(seq_struct_concat_incl),                                │   │
│  │     softplus(seq_struct_concat_skip)                                 │   │
│  │ ])                                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESIDUAL TUNER                                     │
│                                                                              │
│  gen_func = ResidualTuner(hidden_units=4)                                   │
│                                                                              │
│  Architecture:                                                               │
│  input → Dense(4) → BN → ReLU → Dense(4) → BN → ReLU → Dense(1) → + input  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT SELECTOR                                 │
│                                                                              │
│  output = Selector([energy_seq, energy_seq_struct, gen_func])               │
│                                                                              │
│  Selector weights: [w0, w1, w2] (non-trainable, set programmatically)       │
│  Step 1: [1, 0, 0] - sequence only                                          │
│  Step 2: [0, 1, 0] - sequence + structure                                   │
│  Step 3: [0, 0, 1] - with residual tuner                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FINAL OUTPUT                                    │
│                                                                              │
│  output = Sigmoid(selected_output)                                          │
│                                                                              │
│  PSI prediction: 0 (all skipping) to 1 (all inclusion)                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Custom Layers

| Layer | Purpose | Trainable Parameters |
|-------|---------|---------------------|
| `Selector` | Selects between multiple inputs | Selector weights (non-trainable) |
| `ResidualTuner` | Residual MLP for fine-tuning | Dense weights, BatchNorm params |
| `SumDiff` | Computes energy difference | w (scale), b (bias) |
| `RegularizedBiasLayer` | Position-specific bias | Per-position weights |

### 2. Regularizers

| Regularizer | Formula | Purpose |
|-------------|---------|---------|
| Position | `sum(w²)` | Prevent large position biases |
| First-order adjacency | `sum((w[i+1] - w[i])²)` | Smooth position-to-position changes |
| Second-order adjacency | `sum((w[i+2] - 2*w[i+1] + w[i])²)` | Smooth rate of change |

### 3. Loss Function

**Binary KL Divergence:**
```python
binary_KL = mean(BCE(y_true, y_pred) - BCE(y_true, y_true))
```

Equivalent to KL divergence between true and predicted Bernoulli distributions.

---

## Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `input_length` | 90 | Sequence length (10 + 70 + 10) |
| `num_filters` | 20 | Sequence convolutional filters |
| `filter_width` | 6 | Sequence filter size |
| `num_structure_filters` | 8 | Structure convolutional filters |
| `structure_filter_width` | 30 | Structure filter size |
| `dropout_rate` | 0.01 | Dropout probability |
| `position_regularization` | 5e-6 | Position bias L2 penalty |
| `adjacency_regularization` | 0.01 | First-order smoothness |
| `adjacency_regularization_so` | 0.001 | Second-order smoothness |
| `activity_regularization` | 0.0001 | Activation L1 penalty |
| `energy_activation` | softplus | Ensures positive energies |

---

## Training Strategy

### Three-Step Training

| Step | Selector Weights | What's Trained | Epochs |
|------|-----------------|----------------|--------|
| 1 | [1, 0, 0] | Sequence filters + position biases | 70 |
| 2 | [0, 1, 0] | Structure filters + position biases | 70 |
| 3 | [0, 0, 1] | Residual tuner | 70 |

### Progressive Batch Size

Each step uses increasing batch sizes:
```python
batch_schedule = [16, 64, 128, 256, 512, 1024, 2048]
epochs_per_batch = 10
# Total: 7 × 10 = 70 epochs per step
```

Rationale: Start with small batches for initial exploration, increase for faster convergence.

---

## File Documentation

- [model.md](./model.md) - Detailed line-by-line explanation of model.py
- [train_model.md](./train_model.md) - Training script documentation
