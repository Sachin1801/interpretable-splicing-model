"""Simple script to test the pre-trained splicing model.

This script uses the approach from the original notebooks:
- figures/generate_csv_for_supplementary.ipynb
- 2022_03_11_figures/position_specific_activations.ipynb

Requires: Python 3.10 + TensorFlow 2.10 (see README for setup)
"""

import sys

# Add figures directory to path so we can import quad_model
sys.path.insert(0, 'figures')

# Import from quad_model - this auto-registers all custom layers
# via @tf.keras.utils.register_keras_serializable() decorators
from quad_model import *
from tensorflow.keras.models import load_model
from joblib import load as jload
import numpy as np

print("Loading model...")
model = load_model('output/custom_adjacency_regularizer_20210731_124_step3.h5')
print("Model loaded successfully!")

print("\nLoading test data...")
xTe = jload('data/xTe_ES7_HeLa_ABC.pkl.gz')
yTe = jload('data/yTe_ES7_HeLa_ABC.pkl.gz')

num_samples = len(xTe[0]) if isinstance(xTe, list) else len(xTe)
print(f"Number of test samples: {num_samples}")

print("\nRunning predictions...")
predictions = model.predict(xTe, verbose=0)

print(f"\nResults:")
print(f"Predictions shape: {predictions.shape}")
print(f"\nFirst 10 predictions vs actual PSI values:")
print("-" * 50)
print(f"{'Predicted PSI':<15} {'Actual PSI':<15} {'Diff':<10}")
print("-" * 50)
for i in range(min(10, len(predictions))):
    pred = predictions[i, 0]
    actual = yTe[i]
    diff = pred - actual
    print(f"{pred:<15.4f} {actual:<15.4f} {diff:<10.4f}")

# Calculate overall metrics
from sklearn.metrics import mean_squared_error, r2_score
mse = mean_squared_error(yTe, predictions)
r2 = r2_score(yTe, predictions)
correlation = np.corrcoef(yTe.flatten(), predictions.flatten())[0, 1]

print(f"\nOverall Metrics:")
print(f"  MSE: {mse:.6f}")
print(f"  R2 Score: {r2:.4f}")
print(f"  Correlation: {correlation:.4f}")
