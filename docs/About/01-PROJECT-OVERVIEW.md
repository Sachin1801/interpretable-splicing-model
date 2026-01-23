# Interpretable Splicing Model - Project Overview

## What This Project Does

This project implements an **interpretable deep neural network** that predicts RNA alternative splicing outcomes. Specifically, it predicts the **PSI (Percent Spliced In)** value for a given exon sequence - the fraction of transcripts that include (rather than skip) a particular exon.

**Citation:** Liao SE, Sudarshan M, and Regev O. "Machine learning for discovery: deciphering RNA splicing logic." bioRxiv (2022). [Link](https://www.biorxiv.org/content/10.1101/2022.10.01.510472v1)

---

## Biological Background

### What is Alternative Splicing?

Alternative splicing is a process by which a single gene can produce multiple different mRNA transcripts by including or excluding certain exons:

```
Gene:       [Exon 1]---intron---[Exon 2]---intron---[Exon 3]

Exon Inclusion:    [Exon 1][Exon 2][Exon 3]  →  PSI = 1.0
Exon Skipping:     [Exon 1][Exon 3]          →  PSI = 0.0
Mixed:             Some include, some skip    →  PSI = 0.5
```

### Key Concepts

| Term | Definition |
|------|------------|
| **PSI (Percent Spliced In)** | Fraction of transcripts including the exon (0.0 to 1.0) |
| **Exon Inclusion** | The exon is present in the mature mRNA |
| **Exon Skipping** | The exon is absent from the mature mRNA |
| **Intron Retention** | The intron is not removed during splicing |
| **Barcode** | A 20-nucleotide DNA sequence used to identify specific exon variants |
| **Coupling** | The relationship between a barcode and its associated exon sequence |

---

## Project Directory Structure

```
interpretable-splicing-model/
│
├── data/                              # Preprocessed training/test data
│   ├── xTr_ES7_HeLa_ABC.pkl.gz       # Training features (seq + structure)
│   ├── yTr_ES7_HeLa_ABC.pkl.gz       # Training labels (PSI values)
│   ├── xTe_ES7_HeLa_ABC.pkl.gz       # Test features
│   └── yTe_ES7_HeLa_ABC.pkl.gz       # Test labels
│
├── data_preprocessing/                # Scripts to process raw sequencing data
│   ├── compute_coupling.py           # Maps barcodes to exon sequences
│   ├── compute_splicing_outcomes.py  # Classifies splicing patterns
│   ├── generate_training_data.py     # Creates training/test datasets
│   ├── utils.py                      # Utility functions
│   └── RNAutils.py                   # ViennaRNA wrapper functions
│
├── model_training/                    # Model definition and training
│   ├── model.py                      # Neural network architecture
│   ├── train_model.py                # Training script
│   └── model_grid_search.py          # Hyperparameter search
│
├── figures/                           # Visualization and analysis
│   ├── *.ipynb                       # Jupyter notebooks for figures
│   ├── force_plot.py                 # Force plot visualization
│   ├── sequence_logo.py              # Sequence logo generation
│   ├── draw_stem_loop.py             # RNA structure visualization
│   └── data/                         # Supplementary data files
│
├── output/                            # Trained model outputs
│   └── custom_adjacency_regularizer_20210731_124_step3.h5
│
├── preprocess.sh                      # Data preprocessing pipeline
├── train_model.sh                     # Model training script
└── README.md                          # Original README
```

---

## How the Model Works

### Input Features (90 nucleotides total)

The model takes three types of input for each sequence:

1. **Sequence One-Hot Encoding** (90 × 4)
   - 10 nt upstream flanking + 70 nt exon + 10 nt downstream flanking
   - Each position encoded as [A, C, G, T]

2. **Secondary Structure** (90 × 3)
   - RNA secondary structure predicted by ViennaRNA
   - Each position encoded as [unpaired '.', open '(', close ')']

3. **Wobble Pairs** (90 × 1)
   - Indicates G-U/U-G base pairs (non-Watson-Crick)
   - 1 if position is part of a wobble pair, 0 otherwise

### Model Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUTS                                   │
│   [Sequence 90×4]  [Structure 90×3]  [Wobble 90×1]              │
└─────────────────────────────────────────────────────────────────┘
                    │              │              │
                    ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SEQUENCE BRANCH                               │
│   Conv1D (20 filters, width 6) → Position Bias → Dropout        │
│   Separate filters for INCLUSION and SKIPPING                   │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STRUCTURE BRANCH                              │
│   Concatenate [seq, struct, wobble]                             │
│   Conv1D (8 filters, width 30) → Position Bias → Dropout        │
│   Separate filters for INCLUSION and SKIPPING                   │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ENERGY COMPUTATION                            │
│   SumDiff: energy = sum(inclusion) - sum(skipping)              │
│   Higher energy → more likely to include exon                   │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESIDUAL TUNER                                │
│   Small MLP for fine-tuning predictions                         │
│   ResidualTuner: x + MLP(x)                                     │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT                                        │
│   Sigmoid activation → PSI prediction (0 to 1)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Why It's Interpretable

1. **Position-specific biases** show which positions in the exon affect splicing
2. **Convolutional filters** reveal sequence motifs that promote inclusion or skipping
3. **Separate inclusion/skipping branches** decompose the prediction into competing forces
4. **Smoothness regularization** ensures position biases vary smoothly along the sequence
5. **Force plots** visualize the contribution of each position to the final prediction

---

## Data Pipeline

```
Raw FASTQ Files
      │
      ▼
┌─────────────────────────────────────┐
│  compute_coupling.py                │
│  - Reads plasmid sequencing         │
│  - Maps barcodes → exon sequences   │
│  - Output: coupling.csv             │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  compute_splicing_outcomes.py       │
│  - Reads cDNA sequencing            │
│  - Classifies splicing patterns     │
│  - Output: splicing_analysis.csv    │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  generate_training_data.py          │
│  - Merges across libraries          │
│  - Filters low-quality data         │
│  - Computes RNA structures          │
│  - Creates train/test split         │
│  - Output: xTr/yTr/xTe/yTe.pkl.gz   │
└─────────────────────────────────────┘
```

---

## Training Strategy

The model uses a **3-step training procedure**:

| Step | What's Trained | Selector Setting | Purpose |
|------|---------------|------------------|---------|
| 1 | Sequence filters + biases | [1, 0, 0] | Learn sequence motifs |
| 2 | Structure filters + biases | [0, 1, 0] | Learn structure effects |
| 3 | Residual tuner | [0, 0, 1] | Fine-tune predictions |

Each step uses **progressive batch size scheduling**:
- Start with batch size 16
- Increase to 64 → 128 → 256 → 512 → 1024 → 2048
- 10 epochs at each batch size

---

## Key Files Summary

| File | Purpose | Size |
|------|---------|------|
| `xTr_ES7_HeLa_ABC.pkl.gz` | Training features | 20.8 MB |
| `yTr_ES7_HeLa_ABC.pkl.gz` | Training PSI labels | 704 KB |
| `xTe_ES7_HeLa_ABC.pkl.gz` | Test features | 5.2 MB |
| `yTe_ES7_HeLa_ABC.pkl.gz` | Test PSI labels | 178 KB |
| `custom_adjacency_regularizer_20210731_124_step3.h5` | Trained model | 269 KB |

---

## Next Steps

- **Installation:** See [02-INSTALLATION-GUIDE.md](./02-INSTALLATION-GUIDE.md)
- **Quick Start:** See [03-QUICK-START.md](./03-QUICK-START.md)
- **Understanding Data Preprocessing:** See [04-DATA-PREPROCESSING/](./04-DATA-PREPROCESSING/)
- **Understanding the Model:** See [05-MODEL-ARCHITECTURE/](./05-MODEL-ARCHITECTURE/)
- **Building a NAR Web Server:** See [08-EXTENDING-FOR-NAR.md](./08-EXTENDING-FOR-NAR.md)
