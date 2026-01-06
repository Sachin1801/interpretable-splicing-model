# Installation Guide

## Prerequisites

- **Python 3.8+** (tested with 3.8)
- **pip** package manager
- **ViennaRNA** for RNA secondary structure prediction

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/[your-repo]/interpretable-splicing-model.git
cd interpretable-splicing-model
```

---

## Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

---

## Step 3: Install Python Dependencies

### Core Dependencies (Required)

```bash
pip install tensorflow==2.10
pip install numpy==1.22.4
pip install pandas==1.5.0
pip install joblib==1.2.0
pip install scikit-learn==1.1.2
pip install tqdm
```

### Figure Generation Dependencies (Optional)

```bash
pip install matplotlib==3.6.0
pip install seaborn==0.12.0
pip install logomaker==0.8
pip install drawsvg
```

### All at Once

Create a `requirements.txt`:

```txt
tensorflow==2.10
numpy==1.22.4
pandas==1.5.0
joblib==1.2.0
scikit-learn==1.1.2
tqdm
matplotlib==3.6.0
seaborn==0.12.0
logomaker==0.8
drawsvg
```

Then install:

```bash
pip install -r requirements.txt
```

---

## Step 4: Install ViennaRNA

ViennaRNA is required for RNA secondary structure prediction.

### On Ubuntu/Debian

```bash
sudo apt update
sudo apt install vienna-rna
```

### On macOS (via Homebrew)

```bash
brew install viennarna
```

### From Source (Any Platform)

```bash
# Download from https://www.tbi.univie.ac.at/RNA/
wget https://www.tbi.univie.ac.at/RNA/download/sourcecode/2_4_x/ViennaRNA-2.4.17.tar.gz
tar -xzf ViennaRNA-2.4.17.tar.gz
cd ViennaRNA-2.4.17
./configure
make
sudo make install
```

### Verify Installation

```bash
RNAfold --version
# Should output: RNAfold 2.4.17 or similar
```

---

## Step 5: Verify Installation

### Test Python Dependencies

```python
import tensorflow as tf
import numpy as np
import pandas as pd
import joblib
import sklearn

print(f"TensorFlow: {tf.__version__}")
print(f"NumPy: {np.__version__}")
print(f"Pandas: {pd.__version__}")
print(f"Scikit-learn: {sklearn.__version__}")
```

### Test Model Loading

```python
import tensorflow as tf
from model_training.model import get_model, binary_KL

# Load the pre-trained model
model = tf.keras.models.load_model(
    'output/custom_adjacency_regularizer_20210731_124_step3.h5',
    custom_objects={'binary_KL': binary_KL}
)

print("Model loaded successfully!")
print(f"Input shapes: {[inp.shape for inp in model.inputs]}")
print(f"Output shape: {model.output.shape}")
```

### Test ViennaRNA

```python
import subprocess

# Test RNAfold
result = subprocess.run(
    ['RNAfold', '--noPS'],
    input='ACGUACGUACGU',
    capture_output=True,
    text=True
)
print(result.stdout)
# Should output structure like: ACGUACGUACGU\n............  ( 0.00)
```

---

## Directory Structure After Installation

```
interpretable-splicing-model/
├── venv/                    # Virtual environment (if created)
├── data/                    # Pre-processed datasets
│   ├── xTr_ES7_HeLa_ABC.pkl.gz
│   ├── yTr_ES7_HeLa_ABC.pkl.gz
│   ├── xTe_ES7_HeLa_ABC.pkl.gz
│   └── yTe_ES7_HeLa_ABC.pkl.gz
├── output/                  # Trained model
│   └── custom_adjacency_regularizer_20210731_124_step3.h5
├── model_training/
├── data_preprocessing/
├── figures/
├── preprocess.sh
├── train_model.sh
└── README.md
```

---

## GPU Support (Optional)

TensorFlow will automatically use GPU if CUDA is properly configured.

### Check GPU Availability

```python
import tensorflow as tf
print("GPUs available:", tf.config.list_physical_devices('GPU'))
```

### Install CUDA (if needed)

For GPU acceleration with TensorFlow 2.10:
- CUDA 11.2
- cuDNN 8.1

Refer to: https://www.tensorflow.org/install/gpu

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'model'"

Make sure you're running from the project root directory:

```bash
cd interpretable-splicing-model
python -c "from model_training.model import get_model; print('OK')"
```

### "RNAfold: command not found"

ViennaRNA is not installed or not in PATH:

```bash
# Check if installed
which RNAfold

# Add to PATH if installed in custom location
export PATH=$PATH:/path/to/ViennaRNA/bin
```

### TensorFlow Import Errors

Ensure compatible versions:

```bash
pip install tensorflow==2.10 --force-reinstall
```

### Memory Issues During Training

Reduce batch size in training script:

```python
batch_schedule = [16, 32, 64, 128]  # Instead of going up to 2048
```

---

## Next Steps

- [Quick Start Guide](./03-QUICK-START.md) - Learn to run the model
- [Data Preprocessing](./04-DATA-PREPROCESSING/) - Understand the data pipeline
- [Model Architecture](./05-MODEL-ARCHITECTURE/) - Deep dive into the neural network
