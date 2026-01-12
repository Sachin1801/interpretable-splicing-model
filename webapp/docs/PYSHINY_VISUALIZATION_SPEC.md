# PyShiny Visualization Specification

> **For**: Visualization teammate assignment
> **Project**: RNA Splicing Prediction Web Application
> **Date**: 2026-01-12

---

## Executive Summary

This document specifies all visualization work needed for the interpretable RNA splicing prediction webapp. The project uses PyShiny for interactive visualizations. Your task is to implement these visualizations to complement the existing FastAPI + Jinja2 frontend.

**Critical path**: Force Plot Backend → Force Plot Frontend

---

## Table of Contents

1. [Project Context](#1-project-context)
2. [Current Architecture](#2-current-architecture)
3. [Visualization Tasks](#3-visualization-tasks)
4. [Reference Code](#4-reference-code)
5. [Technical Details](#5-technical-details)
6. [Getting Started](#6-getting-started)

---

## 1. Project Context

### What This App Does

This web application predicts **PSI (Percent Spliced In)** values for RNA exon sequences:
- **Input**: 70-nucleotide DNA sequence (exon)
- **Output**: PSI value (0-1) indicating how often the exon is included in mature mRNA
- **PSI = 1**: Exon always included
- **PSI = 0**: Exon always skipped

### Why Visualizations Matter

The model is **interpretable** - it can show WHY it made a prediction by visualizing:
- Which positions in the sequence promote inclusion
- Which positions promote skipping
- How RNA secondary structure affects splicing

### Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Backend API | ✅ Complete | FastAPI, predictions work |
| HTML Templates | ✅ Complete | Jinja2 + Tailwind CSS |
| Basic Force Plot | ⚠️ Partial | Shows bars but data incomplete |
| Advanced Visualizations | ❌ Not started | Your task |

---

## 2. Current Architecture

### File Structure

```
webapp/
├── app/
│   ├── main.py              # FastAPI app + routes
│   ├── api/routes.py        # API endpoints
│   └── services/
│       └── predictor.py     # Model wrapper (MODIFY THIS)
├── templates/
│   └── result.html          # Results page (force plot here)
├── static/
│   └── js/
│       └── result.js        # Current Plotly visualization
└── docs/
    └── PYSHINY_VISUALIZATION_SPEC.md  # This file
```

### Data Flow

```
User submits sequence
    ↓
/api/predict endpoint
    ↓
SplicingPredictor.predict_single()
    ├── add_flanking(70nt → 90nt)
    ├── nts_to_vector() → one-hot encoding
    ├── get_structure() → ViennaRNA call
    ├── model.predict() → PSI value
    └── get_force_plot_data() → [INCOMPLETE - needs work]
    ↓
Store in database (Job model)
    ↓
/result/{job_id} page
    ↓
result.js fetches /api/result/{job_id}
    ↓
Plotly renders force plot
```

### Current Force Plot Issue

The `get_force_plot_data()` method extracts raw neural network activations but doesn't:
1. Cluster filters by behavior
2. Aggregate into meaningful "forces"
3. Apply the link function for PSI scale

**This is the critical blocking task.**

---

## 3. Visualization Tasks

### TASK 1: Force Plot Backend (CRITICAL - Do First)

**Location**: `webapp/app/services/predictor.py`
**Priority**: BLOCKING - all other viz tasks depend on this

#### What You Need to Implement

```python
def _compute_forces(self, sequence: str) -> dict:
    """
    Compute position-wise force contributions for the force plot.

    Returns:
        {
            "positions": [1, 2, ..., 90],
            "inclusion_forces": {
                "group_1": [force_at_pos_1, force_at_pos_2, ...],
                "group_2": [...],
                ...
            },
            "skipping_forces": {
                "group_1": [...],
                ...
            },
            "delta_force": [incl_1 - skip_1, incl_2 - skip_2, ...],
            "annotations": ["incl_seq_0", "skip_struct_1", ...],
            "psi_scale": {
                "midpoint": 0.5,
                "positions": [...]  # for secondary y-axis
            }
        }
    """
```

#### Steps to Implement

1. **Extract layer outputs** (partially done):
   ```python
   # Get intermediate layer outputs
   qc_incl = model.get_layer('qc_incl').output  # inclusion activations
   qc_skip = model.get_layer('qc_skip').output  # skipping activations
   ```

2. **Cluster filters** (NEW - reference `figures/force_plot.py:get_membership_dict()`):
   ```python
   # Group filters by correlation of their activations
   # Creates groups like: [filter_0, filter_3, filter_7] → "group_A"
   ```

3. **Aggregate activations** (NEW):
   ```python
   # Sum ReLU activations within each group
   # Result: one force value per position per group
   ```

4. **Apply link function** (NEW - reference `figures/force_plot.py:get_model_midpoint()`):
   ```python
   # Map force values to PSI scale
   # Find the midpoint where PSI = 0.5
   ```

#### Reference Implementation

Study these files carefully:
- `/figures/force_plot.py` - Lines 100-250 have the clustering logic
- `/figures/force_plot.py:draw_force_plot()` - The full visualization pipeline
- `/2022_03_11_figures/position_specific_activations.ipynb` - Working examples

---

### TASK 2: Enhanced Force Plot Frontend

**Location**: `webapp/static/js/result.js` OR new PyShiny component
**Priority**: HIGH (after Task 1)

#### Current Implementation (Basic)

```javascript
// webapp/static/js/result.js
function createForcePlot(forceData) {
    // Simple bar chart with green/red colors
    // Doesn't show filter groups
    // Doesn't have secondary PSI axis
}
```

#### Target Implementation

**Option A: Enhanced Plotly (Recommended for now)**
- Stacked bar chart showing filter group contributions
- Color each segment by group
- Secondary y-axis showing PSI values
- Hover shows: position, nucleotide, structure, force breakdown

**Option B: PyShiny + Plotly**
- Full PyShiny component with reactive updates
- Filter group selector
- Interactive highlighting

#### Visual Design

```
┌─────────────────────────────────────────────────────────┐
│                    Force Plot                            │
│  PSI ───────────────────────────────────────────── 0.9  │
│                                                          │
│  ▓▓▓▓                              ▓▓▓▓▓▓               │
│  ▓▓▓▓  ▓▓▓                    ▓▓▓  ▓▓▓▓▓▓  ▓▓▓         │
│  ▓▓▓▓  ▓▓▓  ▓▓              ▓▓▓▓▓  ▓▓▓▓▓▓  ▓▓▓  ▓▓    │
│ ─────────────────────────────────────────────────  0.5  │
│        ░░░              ░░░                              │
│        ░░░  ░░░░░      ░░░░                              │
│                                                          │
│  |----5' flank----|--------EXON--------|--3' flank--|   │
│  1    10   20   30   40   50   60   70   80   90        │
│                                                          │
│  ▓ Inclusion forces (by group)                          │
│  ░ Skipping forces (by group)                           │
└─────────────────────────────────────────────────────────┘
```

---

### TASK 3: Position Saliency Heatmap

**Location**: New component in result page
**Priority**: HIGH

#### What It Shows

A heatmap showing which positions in the sequence are most important for the prediction.

```
Position:  1  2  3  4  5  ... 86 87 88 89 90
           ┌──────────────────────────────────┐
Filter 1   │██░░░░░░░░████████░░░░░░░░░░░░░░██│
Filter 2   │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
Filter 3   │░░██████████░░░░░░░░██████████░░░░│
...        │                                  │
Filter 20  │░░░░░░░░░░░░░░████████░░░░░░░░░░░░│
           └──────────────────────────────────┘

██ = High activation (important)
░░ = Low activation (less important)
```

#### Data Needed

```python
{
    "positions": [1-90],
    "filters": ["filter_1", "filter_2", ...],
    "activations": [
        [pos1_f1, pos2_f1, ...],  # filter 1 activations
        [pos1_f2, pos2_f2, ...],  # filter 2 activations
        ...
    ],
    "filter_types": ["sequence", "structure", ...],
    "filter_roles": ["inclusion", "skipping", ...]
}
```

#### Implementation

- Plotly heatmap with custom colorscale
- Blue for inclusion filters, Red for skipping filters
- Click to highlight in force plot
- Hover to show exact values

---

### TASK 4: RNA Structure Viewer

**Location**: Result page, below force plot
**Priority**: HIGH

#### Current State

Just text display of dot-bracket notation:
```
Structure: ...(((...)))...((((....))))...
MFE: -12.30 kcal/mol
```

#### Target: Option A - Styled Text (Simpler)

```html
<div class="structure-viewer">
  <span class="unpaired">...</span>
  <span class="paired-left">(((</span>
  <span class="unpaired">...</span>
  <span class="paired-right">)))</span>
  ...
</div>
```

- Color-coded by pairing status
- Hover to highlight paired bases
- Show nucleotide sequence aligned below

#### Target: Option B - Interactive Diagram (More Complex)

Use **Forna.js** library to render actual 2D structure:
- Nucleotides as circles
- Base pairs as lines
- Stems and loops clearly visible
- Click to highlight positions

---

### TASK 5: PSI Gauge/Indicator

**Location**: Result page, prominent display
**Priority**: MEDIUM

#### Current State

Just a colored number:
```html
<p class="text-5xl font-bold text-green-600">0.963</p>
```

#### Target: Gauge Chart

```
            High Inclusion
                 ▲
        ┌────────┴────────┐
       ╱                   ╲
      │   ●──────────────→  │  0.96
      │                     │
       ╲                   ╱
        └────────┬────────┘
                 ▼
            High Skipping
```

- Plotly gauge or indicator
- Color gradient: Red (0) → Yellow (0.5) → Green (1)
- Animated needle/indicator
- Clear labels for interpretation

---

### TASK 6: Batch Results Visualization

**Location**: New batch results page
**Priority**: MEDIUM

#### What It Shows

When user submits multiple sequences:

```
┌─────────────────────────────────────────────────────────┐
│ Batch Results (15 sequences)                             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PSI Distribution          Summary Stats                 │
│  ┌────────────┐            ─────────────                │
│  │    ▓▓▓▓    │            Mean: 0.62                   │
│  │  ▓▓▓▓▓▓▓▓  │            Std:  0.28                   │
│  │▓▓▓▓▓▓▓▓▓▓▓▓│            Min:  0.08                   │
│  └────────────┘            Max:  0.97                   │
│   0    0.5    1                                          │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ # │ Sequence (first 20nt)  │ PSI   │ Category │ Plot   │
├───┼────────────────────────┼───────┼──────────┼────────┤
│ 1 │ GGTAGTACGCCAATTCGCC... │ 0.963 │ High     │ [═══]  │
│ 2 │ CTACCACCTCCCAAGCTTA... │ 0.487 │ Variable │ [═══]  │
│ 3 │ ACACTCCGCAGCACACTCG... │ 0.008 │ Low      │ [═══]  │
└───┴────────────────────────┴───────┴──────────┴────────┘
```

#### Components

1. **PSI histogram** - Distribution of predictions
2. **Summary statistics** - Mean, std, min, max
3. **Sortable table** - Click headers to sort
4. **Mini force plots** - Small inline visualization per row
5. **Click to expand** - Full details for each sequence

---

### TASK 7: Activation Gallery (Advanced)

**Location**: New page `/methodology/activations`
**Priority**: LOW (nice to have)

#### What It Shows

A gallery of what each neural network filter has learned:

```
┌─────────────────────────────────────────────────────────┐
│ Filter Gallery - Understanding What the Model Learned    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│ │ Filter 1     │  │ Filter 2     │  │ Filter 3     │   │
│ │ [Seq Logo]   │  │ [Seq Logo]   │  │ [Seq Logo]   │   │
│ │ Type: Seq    │  │ Type: Struct │  │ Type: Seq    │   │
│ │ Role: Incl   │  │ Role: Skip   │  │ Role: Incl   │   │
│ │ [Click]      │  │ [Click]      │  │ [Click]      │   │
│ └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

This is complex - only do if time permits.

---

## 4. Reference Code

### Key Files to Study

| File | What to Learn |
|------|---------------|
| `/figures/force_plot.py` | **CRITICAL** - Main force plot algorithm |
| `/figures/figutils.py` | Data preparation utilities |
| `/figures/quad_model.py` | Model architecture, custom layers |
| `/figures/sequence_logo.py` | Sequence logo visualization |
| `/2022_03_11_figures/position_specific_activations.ipynb` | Working visualization examples |
| `/2022_03_11_figures/figure_force_plots.ipynb` | Force plot examples |

### force_plot.py Key Functions

```python
# Get filter groupings by correlation
get_membership_dict(model, activations) → {filter_id: group_id}

# Compute the PSI midpoint for scaling
get_model_midpoint(model) → float

# Main visualization function
draw_force_plot(
    sequences,           # List of 70nt sequences
    annotations,         # Labels for each sequence
    highlight_forces=[], # Which forces to emphasize
    figsize=(20, 5),
    vertical=False,
    custom_model=model,
) → matplotlib figure
```

### Model Layer Names

```python
# Key layers in the trained model
"qc_incl"           # Inclusion branch convolution output
"qc_skip"           # Skipping branch convolution output
"position_bias_incl" # Position-specific inclusion bias
"position_bias_skip" # Position-specific skipping bias
"energy_seq_struct"  # Link function (energy to PSI)
```

---

## 5. Technical Details

### Model Input/Output

**Input** (90 positions × 8 features):
```python
sequence_onehot  # Shape: (90, 4) - A, C, G, T
structure_onehot # Shape: (90, 3) - unpaired, left-pair, right-pair
wobble_indicator # Shape: (90, 1) - G-U wobble base pairs
```

**Output**:
```python
psi  # Shape: (1,) - float between 0 and 1
```

### Intermediate Activations

```python
# After convolution, before aggregation
qc_incl_activations  # Shape: (90-5, 20) for 20 filters, width 6
qc_skip_activations  # Shape: (90-29, 8) for 8 filters, width 30

# After position bias
inclusion_energy  # Shape: (1,) - summed inclusion forces
skipping_energy   # Shape: (1,) - summed skipping forces
```

### Color Scheme

| Element | Color | Hex |
|---------|-------|-----|
| Inclusion (positive) | Green | #22c55e |
| Skipping (negative) | Red | #ef4444 |
| Neutral | Gray | #9ca3af |
| Primary (buttons) | Blue | #3b82f6 |
| Background | Light gray | #f9fafb |

---

## 6. Getting Started

### Setup Environment

```bash
# 1. Navigate to project
cd /path/to/interpretable-splicing-model

# 2. Activate virtual environment
source venv310/bin/activate

# 3. Install dependencies (if not done)
pip install -r webapp/requirements.txt

# 4. Start the server
python -m uvicorn webapp.app.main:app --reload --port 8000

# 5. Open browser
open http://localhost:8000
```

### Test a Prediction

```bash
# Submit a test sequence
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"sequence": "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT"}'

# Response includes job_id, use it to view results
open http://localhost:8000/result/{job_id}
```

### Run Research Notebooks

```bash
# Start Jupyter
cd 2022_03_11_figures
jupyter notebook

# Open position_specific_activations.ipynb to see working visualizations
```

### Development Workflow

1. **Understand the data** - Run notebooks to see what visualizations look like
2. **Modify backend** - Update `predictor.py` to compute forces correctly
3. **Test API** - Verify `/api/result/{job_id}` returns proper force data
4. **Update frontend** - Modify `result.js` or add PyShiny components
5. **Test end-to-end** - Full flow from input to visualization

---

## Questions?

If you have questions about:
- **Model architecture**: Check `/figures/quad_model.py` and doc files in `/01-10_*.md`
- **Visualization logic**: Check `/figures/force_plot.py` and research notebooks
- **API structure**: Check `/webapp/app/api/routes.py`
- **Frontend**: Check `/webapp/templates/result.html` and `/webapp/static/js/result.js`

---

## Success Criteria

Your work is complete when:

- [ ] Force plot shows correct stacked bar visualization with filter groups
- [ ] Hovering shows position, nucleotide, structure, and force breakdown
- [ ] Position saliency heatmap renders correctly
- [ ] Structure viewer shows colored dot-bracket notation
- [ ] PSI gauge provides intuitive visual feedback
- [ ] All visualizations work on Chrome, Firefox, Safari
- [ ] Mobile responsive (readable on 375px+ screens)
- [ ] No console errors
- [ ] Loading states during data fetch

---

**This is important work that will make the model's predictions interpretable and useful for researchers.**
