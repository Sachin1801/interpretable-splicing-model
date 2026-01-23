#!/usr/bin/env python
"""Extract example sequences from test data for the 'Try Example' feature."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from joblib import load
import json


def oh_to_sequence(one_hot):
    """Convert one-hot encoding back to sequence string."""
    alphabet = "ACGT"
    return "".join(alphabet[np.argmax(pos)] for pos in one_hot)


def main():
    """Extract example sequences from test data."""
    data_path = project_root / "data"

    print("Loading test data...")
    xTe = load(data_path / "xTe_ES7_HeLa_ABC.pkl.gz")
    yTe = load(data_path / "yTe_ES7_HeLa_ABC.pkl.gz")

    print(f"Test set size: {len(yTe)} samples")
    print(f"PSI range: {yTe.min():.3f} - {yTe.max():.3f}")
    print(f"PSI mean: {yTe.mean():.3f}")

    # Get sequences from one-hot encoding
    # xTe is tuple: (seq_oh, struct_oh, wobble)
    seq_oh = xTe[0]  # Shape: (N, 90, 4)

    # Extract the 70nt exon part (positions 10-80)
    exon_seq_oh = seq_oh[:, 10:80, :]

    # Find sequences with specific PSI values
    examples = []

    # High PSI (>0.85)
    high_psi_idx = np.where(yTe > 0.85)[0]
    if len(high_psi_idx) > 0:
        idx = high_psi_idx[0]
        seq = oh_to_sequence(exon_seq_oh[idx])
        examples.append({
            "name": "High Inclusion Example",
            "sequence": seq,
            "description": f"This sequence demonstrates strong exon inclusion (actual PSI = {yTe[idx]:.3f})",
            "expected_psi": float(yTe[idx]),
        })
        print(f"High PSI example: {seq[:20]}... (PSI={yTe[idx]:.3f})")

    # Medium PSI (0.45-0.55)
    medium_psi_idx = np.where((yTe > 0.45) & (yTe < 0.55))[0]
    if len(medium_psi_idx) > 0:
        idx = medium_psi_idx[0]
        seq = oh_to_sequence(exon_seq_oh[idx])
        examples.append({
            "name": "Balanced Example",
            "sequence": seq,
            "description": f"This sequence shows balanced inclusion/skipping (actual PSI = {yTe[idx]:.3f})",
            "expected_psi": float(yTe[idx]),
        })
        print(f"Medium PSI example: {seq[:20]}... (PSI={yTe[idx]:.3f})")

    # Low PSI (<0.15)
    low_psi_idx = np.where(yTe < 0.15)[0]
    if len(low_psi_idx) > 0:
        idx = low_psi_idx[0]
        seq = oh_to_sequence(exon_seq_oh[idx])
        examples.append({
            "name": "High Skipping Example",
            "sequence": seq,
            "description": f"This sequence demonstrates strong exon skipping (actual PSI = {yTe[idx]:.3f})",
            "expected_psi": float(yTe[idx]),
        })
        print(f"Low PSI example: {seq[:20]}... (PSI={yTe[idx]:.3f})")

    # Save examples to JSON
    output_path = project_root / "webapp" / "static" / "examples.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump({"sequences": examples}, f, indent=2)

    print(f"\nExamples saved to: {output_path}")
    print(f"Total examples: {len(examples)}")

    return examples


if __name__ == "__main__":
    main()
