# Figures and Analysis Overview

This module contains tools for visualizing model predictions and analyzing the interpretable components.

---

## File Summary

| File | Purpose |
|------|---------|
| `force_plot.py` | Force plot visualizations showing position contributions |
| `sequence_logo.py` | Sequence logo generation for motif analysis |
| `draw_stem_loop.py` | RNA secondary structure visualization |
| `figutils.py` | Common figure utilities |
| `mukund_utils.py` | Extended analysis utilities |
| `kl.py` | KL divergence estimation |
| `generate_custom_model.py` | Generate models with modified parameters |

---

## Jupyter Notebooks

### figure_force_plots.ipynb
**Figures:** Main figures 3, 4, 5, S6-S8

Creates force plot visualizations showing:
- Validation sequences (V1-V5)
- G-poor filter analysis (D1-D4)
- Secondary structure exons (S1-S5)
- Saliency-colored stem-loop structures

### figure_extended_other_datasets.ipynb
**Figures:** S3, S5

Cross-validates model on external datasets:
- FAS exon 6 (Baeza et al.)
- WT1 exon 5 (Ke et al.)
- SMN1, SMN2, CFTR, BRCA2 (Rosenberg et al.)

### figure_validation_skipping_count.ipynb
**Figures:** S9

Experimental validation of:
- G-poor filter effects on splicing
- Secondary structure filter effects

### generate_csv_for_supplementary.ipynb
Exports training/test data with predictions to CSV format.

---

## Force Plot Concept

Force plots decompose the model's prediction into interpretable components:

```
                 Inclusion forces →
    ╔══════════════════════════════════════════════════════╗
    ║  ████████████████████████████                       ║
    ║                              ██████████████████████ ║
    ╚══════════════════════════════════════════════════════╝
                                   ← Skipping forces

    Δ = sum(inclusion) - sum(skipping)
    PSI = sigmoid(Δ)
```

Each position in the sequence contributes either to inclusion or skipping based on the convolutional filter activations and position-specific biases.

---

## Running Notebooks

```bash
cd figures
jupyter notebook
```

Then open the desired notebook:
- `figure_force_plots.ipynb`
- `figure_extended_other_datasets.ipynb`
- `figure_validation_skipping_count.ipynb`

**Required model file:** `custom_adjacency_regularizer_20210731_124_step3.h5`

---

## Key Visualization Functions

### Force Plot (force_plot.py)

```python
from force_plot import draw_force_plot

fig = draw_force_plot(
    sequences=[seq1, seq2],  # 90 nt sequences
    annotations=['Seq 1', 'Seq 2'],
    highlight_forces=['G-poor', 'CU-rich'],  # Optional
)
fig.savefig('force_plot.pdf')
```

### Sequence Logo (sequence_logo.py)

```python
from sequence_logo import plot_logo

# Plot logo from DataFrame of k-mers and activations
plot_logo(df, threshold=0.5, ax=ax, color_map={'A': 'green', 'C': 'blue', 'G': 'orange', 'U': 'red'})
```

### Stem-Loop Structure (draw_stem_loop.py)

```python
from draw_stem_loop import draw_stem_loop

draw_stem_loop(
    nts='GCGCUUUUGCGC',
    stem_length=4,
    colors=[...],  # Per-nucleotide colors
    filename='stem_loop.svg'
)
```

---

## Analysis Workflow

1. **Load trained model:**
   ```python
   model = load_model('custom_adjacency_regularizer_20210731_124_step3.h5', ...)
   ```

2. **Extract filter activations:**
   ```python
   qc_incl = model.get_layer('qc_incl')
   activations = qc_incl.predict(X)
   ```

3. **Analyze motif preferences:**
   ```python
   from figutils import compute_activations_simple_conv
   motif_data = compute_activations_simple_conv(qc_incl, window_size=6)
   ```

4. **Create visualizations:**
   - Force plots for individual predictions
   - Sequence logos for filter preferences
   - Stem-loop cartoons for structure analysis
