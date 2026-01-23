# RNAutils.py - ViennaRNA Wrapper Functions

**Purpose:** Wrapper functions for calling ViennaRNA tools (RNAfold, RNAsubopt) to predict RNA secondary structures.

**Location:** `/data_preprocessing/RNAutils.py`

---

## Overview

This module provides Python interfaces to ViennaRNA command-line tools, which predict RNA secondary structures based on thermodynamic models.

---

## Prerequisites

ViennaRNA must be installed and in your PATH:

```bash
# Check installation
RNAfold --version

# Install on Ubuntu
sudo apt install vienna-rna

# Install on macOS
brew install viennarna
```

---

## Function Reference

### RNAfold(seqs, RNAfold_bin="RNAfold", temperature=37, maxBPspan=0, commands_file=None)

Predicts minimum free energy (MFE) structures for a batch of sequences.

```python
def RNAfold(seqs, RNAfold_bin="RNAfold", temperature=37, maxBPspan=0, commands_file=None):
    """
    Args:
        seqs: List of RNA sequences (can be DNA, T will be treated as U)
        RNAfold_bin: Path to RNAfold executable
        temperature: Temperature in Celsius (default 37°C)
        maxBPspan: Maximum base pair span (0 = no limit)
        commands_file: Optional file with additional RNAfold commands

    Returns:
        List of [structure_string, mfe_value] pairs
    """
```

**How it works:**
1. Writes sequences to a temporary file
2. Calls RNAfold with `--noPS` (no PostScript output) and `-j8` (8 parallel threads)
3. Parses output to extract structures and MFE values
4. Returns list of [structure, energy] pairs

**Example:**
```python
from data_preprocessing.RNAutils import RNAfold

results = RNAfold(["GCGCGCGCGC", "AAAAUUUU"])
# results[0] = ["((((....))))", -3.5]  # example structure and energy
# results[1] = ["........", 0.0]
```

**Output format:**
- Structure: Dot-bracket notation
  - `.` = unpaired nucleotide
  - `(` = 5' partner of a base pair
  - `)` = 3' partner of a base pair
- MFE: Minimum free energy in kcal/mol (more negative = more stable)

---

### RNAsubopt(seq, RNAsubopt_bin="RNAsubopt", delta_energy=5.0)

Generates suboptimal structures within an energy range.

```python
def RNAsubopt(seq, RNAsubopt_bin="RNAsubopt", delta_energy=5.0):
    """
    Args:
        seq: Single RNA sequence
        RNAsubopt_bin: Path to RNAsubopt executable
        delta_energy: Energy range above MFE (default 5.0 kcal/mol)

    Returns:
        List of (structure_string, energy_value) tuples
    """
```

**Example:**
```python
from data_preprocessing.RNAutils import RNAsubopt

structures = RNAsubopt("GCGCGCGCGC", delta_energy=2.0)
# Returns all structures within 2 kcal/mol of the MFE
# [(structure1, energy1), (structure2, energy2), ...]
```

**Use case:** Exploring alternative folds that may be biologically relevant.

---

### RNAsample(seqs, RNAfold_bin="RNAfold", temperature=37, num_structs=5, maxBPspan=0)

Samples structures from the Boltzmann ensemble.

```python
def RNAsample(seqs, RNAfold_bin="RNAfold", temperature=37, num_structs=5, maxBPspan=0):
    """
    Args:
        seqs: List of RNA sequences
        RNAfold_bin: Path to RNAfold executable
        temperature: Temperature for Boltzmann sampling
        num_structs: Number of structures to sample per sequence
        maxBPspan: Maximum base pair span

    Returns:
        List of lists of sampled structure strings
    """
```

**How it works:**
Uses RNAfold with `-p` (partition function) and `--stochBT_en` to sample from the Boltzmann distribution of structures.

**Example:**
```python
from data_preprocessing.RNAutils import RNAsample

samples = RNAsample(["GCGCGCGCGC"], num_structs=10)
# samples[0] = list of 10 sampled structures
```

**Use case:** Monte Carlo sampling of RNA structural ensembles.

---

### RNA_partition_function(seqs, constraints, RNAfold_bin="RNAfold", temperature=37, commands_file=None)

Computes partition function with structural constraints.

```python
def RNA_partition_function(seqs, constraints, RNAfold_bin="RNAfold", temperature=37, commands_file=None):
    """
    Args:
        seqs: List of RNA sequences
        constraints: List of constraint strings (same length as sequences)
        RNAfold_bin: Path to RNAfold executable
        temperature: Temperature for calculation

    Returns:
        List of partition function values (log scale)
    """
```

**Constraint notation:**
- `.` = no constraint
- `x` = position must be unpaired
- `(` or `)` = position must be paired

**Example:**
```python
from data_preprocessing.RNAutils import RNA_partition_function

# Force first 5 nucleotides to be unpaired
pf = RNA_partition_function(
    ["GCGCGCGCGC"],
    ["xxxxx....."]
)
```

---

## Implementation Details

### Parallel Processing

RNAfold is called with `-j8` for 8-way parallelization:
```python
cmd_line = [
    RNAfold_bin,
    "-i", temp_file_name,
    "--noPS",
    "-j8",  # 8 parallel threads
    "-T", str(temperature),
]
```

### Temperature Effects

Default temperature is 37°C (body temperature). Higher temperatures:
- Destabilize base pairs
- Favor more open structures
- Affect Boltzmann sampling

### maxBPspan Parameter

Limits maximum distance between base-paired nucleotides:
- `maxBPspan=0`: No limit (default)
- `maxBPspan=30`: Base pairs can span at most 30 nucleotides

This can model local folding constraints.

---

## Typical Usage in the Project

```python
from data_preprocessing.utils import rna_fold_structs, compute_structure

# Get structure for model input
sequences = ["ACGUACGUACGUACGUACGU..." * 3]  # 90 nt

# Using rna_fold_structs
structures, mfes = rna_fold_structs(sequences)
print(structures[0])  # "(((....)))..."
print(mfes[0])        # -5.2

# Using compute_structure (includes one-hot encoding)
struct_oh, structures, mfes = compute_structure(sequences)
print(struct_oh.shape)  # (1, 90, 3)
```

---

## Error Handling

If ViennaRNA is not installed:
```python
FileNotFoundError: [Errno 2] No such file or directory: 'RNAfold'
```

Solution:
```bash
# Install ViennaRNA
sudo apt install vienna-rna  # Ubuntu
brew install viennarna       # macOS
```

---

## Performance Considerations

- Batch processing is more efficient than single sequences
- ViennaRNA uses O(n³) algorithm for structure prediction
- For very long sequences (>1000 nt), consider using maxBPspan
- The 8-thread parallelization significantly speeds up batch predictions
