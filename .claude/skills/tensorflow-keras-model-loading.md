# Skill: Loading Legacy TensorFlow/Keras Models

## Problem Encountered
When trying to load a pre-trained H5 model created in 2021 with TensorFlow 2.5, we encountered multiple errors with TensorFlow 2.20 (Python 3.12):

1. `ValueError: Unknown layer: 'SlicingOpLambda'`
2. `ValueError: Unknown layer: 'Custom>RegularizedBiasLayer'`
3. `IndexError: list index out of range` in `process_node`

## Root Cause
- **TensorFlow 2.16+ uses Keras 3** which has breaking changes for loading old H5 models
- Models with Lambda layers and custom layers saved with Keras 2 cannot be loaded with Keras 3
- The `tf_keras` compatibility layer does NOT fully work for complex models with Lambda layers

## Solution

### 1. Use Python 3.10 + TensorFlow 2.15
TensorFlow 2.15 is the **last version with native Keras 2 support**:

```bash
# Install Python 3.10 via pyenv
pyenv install 3.10.13

# Create virtual environment
~/.pyenv/versions/3.10.13/bin/python -m venv venv310
source venv310/bin/activate

# Install TensorFlow 2.15 (NOT 2.16+)
pip install tensorflow==2.15.0
```

### 2. Use `@register_keras_serializable()` Pattern
The original codebase uses decorators to auto-register custom layers:

```python
@tf.keras.utils.register_keras_serializable()
class MyCustomLayer(Layer):
    ...
```

When you import from the module containing these decorators, the layers are automatically registered:

```python
# This auto-registers all custom layers
from quad_model import *

# Then you can load the model directly
model = load_model('model.h5')
```

### 3. Don't Pass Custom Objects Manually (Usually)
If the original code uses `@register_keras_serializable()`, you typically don't need to pass `custom_objects` to `load_model()`. The decorators handle registration.

## TensorFlow/Keras Version Compatibility Matrix

| Python | TensorFlow | Keras | Can Load Old H5? |
|--------|------------|-------|------------------|
| 3.12   | 2.16-2.20  | 3.x   | NO - Lambda layer bugs |
| 3.11   | 2.15       | 2.15  | YES |
| 3.10   | 2.10-2.15  | 2.x   | YES |
| 3.10   | 2.8-2.9    | 2.x   | YES |

## Key Lessons

### DO:
- Check when the model was created and what TensorFlow version was used
- Look for existing notebooks that successfully load the model
- Match the Python + TensorFlow version to the model's creation era
- Use `@register_keras_serializable()` for custom layers
- Pin TensorFlow version in requirements.txt (`tensorflow==2.15.0`)

### DON'T:
- Assume latest TensorFlow will load old models
- Use `tf_keras` for complex models with Lambda layers (it's buggy)
- Try to manually pass all custom objects if decorators exist
- Use Python 3.12 with TensorFlow < 2.16 (incompatible)

## Quick Diagnosis

If you see these errors, it's likely a Keras 2 vs 3 compatibility issue:
- `Unknown layer: 'SlicingOpLambda'`
- `Unknown layer: 'Custom>...'`
- `IndexError: list index out of range` in functional.py
- Errors mentioning `_inbound_nodes`

## Files to Check in Legacy Projects

1. Look for `quad_model.py` or similar files with custom layer definitions
2. Check if layers use `@tf.keras.utils.register_keras_serializable()`
3. Find notebooks that successfully load the model (check their imports)
4. Check model creation date from filename (e.g., `_20210731_` = July 2021)

## Working Example

```python
"""Load legacy Keras model (created with TF 2.5-2.10)"""
import sys
sys.path.insert(0, 'figures')  # or wherever quad_model.py lives

# Import registers all custom layers via decorators
from quad_model import *
from tensorflow.keras.models import load_model

# Now load works without custom_objects
model = load_model('output/model.h5')

# Make predictions
predictions = model.predict(data)
```
