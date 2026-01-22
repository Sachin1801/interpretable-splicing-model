"""Visualization data computation for silhouette and heatmap views.

Adapted from interpretable-splicing-model-pyshiny/src/vis_data.py
"""

import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from pathlib import Path
from typing import Dict, Any, List, Tuple

from webapp.app.config import settings
from webapp.app.services.predictor import get_predictor


# Load model configuration data
def _load_model_data() -> Dict[str, Any]:
    """Load model data configuration (filter groupings, boundaries, etc.)."""
    model_data_path = Path(__file__).parent.parent.parent / "data" / "model_data_18.json"
    with open(model_data_path, "r") as f:
        return json.load(f)


def _load_dataset_data() -> Dict[str, Any]:
    """Load dataset configuration (flanking sequences, etc.)."""
    dataset_data_path = Path(__file__).parent.parent.parent / "data" / "datasets_data.json"
    with open(dataset_data_path, "r") as f:
        return json.load(f)


def shift_row(row: np.ndarray, shift: int, total_len: int = 90) -> np.ndarray:
    """Shift an activation row by a given amount."""
    shift = int(shift)
    out = np.zeros(total_len)
    out[shift:len(row)+shift] += row
    return out


def collapse(
    groups: Dict[str, List[int]],
    shifted_acts: np.ndarray,
    logo_boundaries: List[Dict],
    sequence_length: int
) -> np.ndarray:
    """Collapse individual filter activations into grouped super-features."""
    collapsed_acts = np.zeros((sequence_length, len(groups), 2))
    for i in range(sequence_length):
        for feature_id in groups.keys():
            filter_strengths = shifted_acts[i, groups[feature_id]]
            feature_strength = filter_strengths.sum()
            repr_filter = groups[feature_id][np.argmax(filter_strengths)]
            feature_length = logo_boundaries[repr_filter]["length"]
            collapsed_acts[i, int(feature_id)-1, :] = [feature_strength, feature_length]
    return collapsed_acts


def collapse_activations(
    incl_acts: np.ndarray,
    skip_acts: np.ndarray,
    incl_seq_groups: Dict[str, List[int]],
    skip_seq_groups: Dict[str, List[int]],
    incl_struct_groups: Dict[str, List[int]],
    skip_struct_groups: Dict[str, List[int]],
    seq_logo_boundaries: Dict[str, List[Dict]],
    struct_logo_boundaries: Dict[str, List[Dict]],
    num_seq_filters: int,
    num_struct_filters: int,
    sequence_length: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Collapse filter activations into super-features with proper shifting."""
    # Shift by start boundaries
    seq_incl_shifts = [seq_logo_boundaries["incl"][i]["left"] for i in range(num_seq_filters)]
    seq_skip_shifts = [seq_logo_boundaries["skip"][i]["left"] for i in range(num_seq_filters)]

    struct_incl_shifts = [struct_logo_boundaries["incl"][i]["left"] for i in range(num_struct_filters)]
    struct_skip_shifts = [struct_logo_boundaries["skip"][i]["left"] for i in range(num_struct_filters)]

    # Separate activations
    seq_incl_acts = incl_acts[:, :num_seq_filters]
    seq_skip_acts = skip_acts[:, :num_seq_filters]
    struct_incl_acts = incl_acts[:, num_seq_filters:]
    struct_skip_acts = skip_acts[:, num_seq_filters:]

    # Shift sequence activations
    shifted_seq_incl_acts = np.array([
        shift_row(row, row_shift, sequence_length)
        for row, row_shift in zip(seq_incl_acts.T, seq_incl_shifts)
    ]).T
    shifted_seq_skip_acts = np.array([
        shift_row(row, row_shift, sequence_length)
        for row, row_shift in zip(seq_skip_acts.T, seq_skip_shifts)
    ]).T

    # Handle structure activations with padding for edges
    left_padding_struct_incl_acts = np.copy(struct_incl_acts[:12, :])
    right_padding_struct_incl_acts = np.copy(struct_incl_acts[-12:, :])
    struct_incl_acts[:12, :] = 0.
    struct_incl_acts[-12:, :] = 0.
    shifted_struct_incl_acts = np.array([
        shift_row(row, row_shift, sequence_length)
        for row, row_shift in zip(struct_incl_acts.T, struct_incl_shifts)
    ]).T
    shifted_struct_incl_acts[:12, :] += left_padding_struct_incl_acts
    shifted_struct_incl_acts[-12:, :] += right_padding_struct_incl_acts

    left_padding_struct_skip_acts = np.copy(struct_skip_acts[:12, :])
    right_padding_struct_skip_acts = np.copy(struct_skip_acts[-12:, :])
    struct_skip_acts[:12, :] = 0.
    struct_skip_acts[-12:, :] = 0.
    shifted_struct_skip_acts = np.array([
        shift_row(row, row_shift, sequence_length)
        for row, row_shift in zip(struct_skip_acts.T, struct_skip_shifts)
    ]).T
    shifted_struct_skip_acts[:12, :] += left_padding_struct_skip_acts
    shifted_struct_skip_acts[-12:, :] += right_padding_struct_skip_acts

    # Collapse into super-features
    collapsed_seq_incl_acts = collapse(
        groups=incl_seq_groups,
        shifted_acts=shifted_seq_incl_acts,
        logo_boundaries=seq_logo_boundaries["incl"],
        sequence_length=sequence_length
    )
    collapsed_struct_incl_acts = collapse(
        groups=incl_struct_groups,
        shifted_acts=shifted_struct_incl_acts,
        logo_boundaries=struct_logo_boundaries["incl"],
        sequence_length=sequence_length
    )
    collapsed_seq_skip_acts = collapse(
        groups=skip_seq_groups,
        shifted_acts=shifted_seq_skip_acts,
        logo_boundaries=seq_logo_boundaries["skip"],
        sequence_length=sequence_length
    )
    collapsed_struct_skip_acts = collapse(
        groups=skip_struct_groups,
        shifted_acts=shifted_struct_skip_acts,
        logo_boundaries=struct_logo_boundaries["skip"],
        sequence_length=sequence_length
    )

    return (
        collapsed_seq_incl_acts, collapsed_struct_incl_acts,
        collapsed_seq_skip_acts, collapsed_struct_skip_acts
    )


def transform(d: Dict, parent: str) -> Dict:
    """Transform dict tree to nested JSON format."""
    if "strength" in d[parent].keys():
        return {"name": parent, "strength": d[parent]["strength"], "length": d[parent]["length"]}
    return {"name": parent, "children": [transform(d[parent], child) for child in d[parent]]}


def get_feature_activations_helper(
    collapsed_acts: np.ndarray,
    acts_dict: Dict,
    name: str,
    sequence_length: int,
    threshold: float
) -> None:
    """Build feature activations tree."""
    for fi in range(collapsed_acts.shape[1]):
        acts_dict[f"{name}_{fi+1}"] = {}
        for i in range(sequence_length):
            feature_strength = collapsed_acts[i, fi, 0]
            feature_length = int(collapsed_acts[i, fi, 1])
            pos_ind = i + 1
            if "struct" in name:
                if i < 12 or i > 77:
                    feature_length = 1
                else:
                    pos_ind -= 12
            if feature_strength > threshold:
                acts_dict[f"{name}_{fi+1}"][f"pos_{pos_ind}"] = {
                    "strength": feature_strength,
                    "length": feature_length,
                }


def get_feature_activations(
    collapsed_seq_incl_acts: np.ndarray,
    collapsed_struct_incl_acts: np.ndarray,
    collapsed_seq_skip_acts: np.ndarray,
    collapsed_struct_skip_acts: np.ndarray,
    sequence_length: int,
    incl_bias: float,
    skip_bias: float,
    threshold: float = 0.001
) -> List[Dict]:
    """Build hierarchical feature activations structure."""
    feature_activations = {
        "incl": {"incl_bias": {"strength": incl_bias, "length": 0}},
        "skip": {"skip_bias": {"strength": skip_bias, "length": 0}}
    }
    get_feature_activations_helper(collapsed_seq_incl_acts, feature_activations["incl"],
        "incl", sequence_length, threshold)
    get_feature_activations_helper(collapsed_struct_incl_acts, feature_activations["incl"],
        "incl_struct", sequence_length, threshold)
    get_feature_activations_helper(collapsed_seq_skip_acts, feature_activations["skip"],
        "skip", sequence_length, threshold)
    get_feature_activations_helper(collapsed_struct_skip_acts, feature_activations["skip"],
        "skip_struct", sequence_length, threshold)
    return [
        transform(feature_activations, "incl"),
        transform(feature_activations, "skip"),
    ]


def get_nucleotide_activations_helper(
    collapsed_acts: np.ndarray,
    acts_dict: Dict,
    name: str,
    sequence_length: int,
    filter_width: int,
    threshold: float
) -> None:
    """Build per-nucleotide activations tree."""
    for i in range(sequence_length):
        for fi in range(collapsed_acts.shape[1]):
            fix_feature_length = sequence_length
            pos_ind = i + 1
            if "struct" in name:
                if i < 12 or i > 77:
                    first_start_ind = i
                    fix_feature_length = 1
                else:
                    first_start_ind = max(12, i - filter_width + 1)
            else:
                first_start_ind = max(0, i - filter_width + 1)
            for start_ind in range(first_start_ind, i + 1):
                feature_strength = collapsed_acts[start_ind, fi, 0]
                feature_length = min(fix_feature_length, int(collapsed_acts[start_ind, fi, 1]))
                if feature_strength > threshold and start_ind + feature_length > i:
                    if f"{name}_{fi+1}" not in acts_dict[f"pos_{pos_ind}"].keys():
                        acts_dict[f"pos_{pos_ind}"][f"{name}_{fi+1}"] = {}
                    acts_dict[f"pos_{pos_ind}"][f"{name}_{fi+1}"][f"feature_pos_{i-start_ind+1}"] = {
                        "strength": feature_strength / feature_length,
                        "length": feature_length,
                    }


def get_nucleotide_activations(
    collapsed_seq_incl_acts: np.ndarray,
    collapsed_struct_incl_acts: np.ndarray,
    collapsed_seq_skip_acts: np.ndarray,
    collapsed_struct_skip_acts: np.ndarray,
    sequence_length: int,
    seq_filter_width: int,
    struct_filter_width: int,
    threshold: float = 0.001
) -> List[Dict]:
    """Build hierarchical per-nucleotide activations structure."""
    nucleotide_activations = {"incl": {}, "skip": {}}
    for i in range(sequence_length):
        nucleotide_activations["incl"][f"pos_{i+1}"] = {}
        nucleotide_activations["skip"][f"pos_{i+1}"] = {}

    get_nucleotide_activations_helper(collapsed_seq_incl_acts, nucleotide_activations["incl"],
        "incl", sequence_length, seq_filter_width, threshold)
    get_nucleotide_activations_helper(collapsed_struct_incl_acts, nucleotide_activations["incl"],
        "incl_struct", sequence_length, struct_filter_width, threshold)
    get_nucleotide_activations_helper(collapsed_seq_skip_acts, nucleotide_activations["skip"],
        "skip", sequence_length, seq_filter_width, threshold)
    get_nucleotide_activations_helper(collapsed_struct_skip_acts, nucleotide_activations["skip"],
        "skip_struct", sequence_length, struct_filter_width, threshold)

    # Remove empty positions
    for i in range(sequence_length):
        if len(nucleotide_activations["incl"][f"pos_{i+1}"]) == 0:
            nucleotide_activations["incl"].pop(f"pos_{i+1}")
        if len(nucleotide_activations["skip"][f"pos_{i+1}"]) == 0:
            nucleotide_activations["skip"].pop(f"pos_{i+1}")

    return [
        transform(nucleotide_activations, "incl"),
        transform(nucleotide_activations, "skip"),
    ]


def get_vis_data(exon_sequence: str, threshold: float = 0.001) -> Dict[str, Any]:
    """
    Compute visualization data for an exon sequence.

    Args:
        exon_sequence: The 70nt exon sequence
        threshold: Minimum activation strength to include

    Returns:
        Dictionary with visualization data including:
        - exon, sequence, structs
        - predicted_psi, delta_force, incl_strength, skip_strength
        - feature_activations (hierarchical feature contributions)
        - nucleotide_activations (per-position contributions)
    """
    # Normalize input
    exon = exon_sequence.upper().replace("T", "U")

    # Get predictor and prepare input
    predictor = get_predictor()

    # Add flanking sequences (uses settings from webapp config)
    full_sequence = predictor.add_flanking(exon_sequence.upper())
    sequence_length = len(full_sequence)

    # Get structure prediction
    inputs, structure, mfe, warnings = predictor.prepare_input(exon_sequence)

    # Get model and make prediction
    model = predictor.model
    predicted_psi = float(model.predict(inputs, verbose=0)[0, 0])

    # Load model configuration
    model_data = _load_model_data()

    # Get configuration values
    link_midpoint = model_data["link_midpoint"]
    incl_bias, skip_bias = (abs(link_midpoint), 0) if link_midpoint < 0 else (0, abs(link_midpoint))

    num_seq_filters = model_data["num_seq_filters"]
    num_struct_filters = model_data["num_struct_filters"]
    seq_filter_width = model_data["seq_filter_width"]
    struct_filter_width = model_data["struct_filter_width"]

    # Get filter groups
    incl_seq_groups = model_data["incl_seq_groups"]
    skip_seq_groups = model_data["skip_seq_groups"]
    incl_struct_groups = model_data["incl_struct_groups"]
    skip_struct_groups = model_data["skip_struct_groups"]

    # Get filter boundaries
    seq_logo_boundaries = model_data["seq_logo_boundaries"]
    struct_logo_boundaries = model_data["struct_logo_boundaries"]

    # Create intermediate model to extract activations
    # activation_2 = inclusion activations, activation_3 = skipping activations
    activations_model = Model(inputs=model.inputs, outputs=[
        model.get_layer("activation_2").output,
        model.get_layer("activation_3").output
    ])

    data_incl_acts, data_skip_acts = activations_model.predict(inputs, verbose=0)
    incl_acts = data_incl_acts[0]
    skip_acts = data_skip_acts[0]

    incl_strength = incl_bias + incl_acts.sum()
    skip_strength = skip_bias + skip_acts.sum()
    delta_force = incl_strength - skip_strength

    # Collapse filter activations into super-features
    (
        collapsed_seq_incl_acts, collapsed_struct_incl_acts,
        collapsed_seq_skip_acts, collapsed_struct_skip_acts
    ) = collapse_activations(
        incl_acts=incl_acts,
        skip_acts=skip_acts,
        incl_seq_groups=incl_seq_groups,
        skip_seq_groups=skip_seq_groups,
        incl_struct_groups=incl_struct_groups,
        skip_struct_groups=skip_struct_groups,
        seq_logo_boundaries=seq_logo_boundaries,
        struct_logo_boundaries=struct_logo_boundaries,
        num_seq_filters=num_seq_filters,
        num_struct_filters=num_struct_filters,
        sequence_length=sequence_length,
    )

    # Build hierarchical data structures
    feature_activations = get_feature_activations(
        collapsed_seq_incl_acts=collapsed_seq_incl_acts,
        collapsed_struct_incl_acts=collapsed_struct_incl_acts,
        collapsed_seq_skip_acts=collapsed_seq_skip_acts,
        collapsed_struct_skip_acts=collapsed_struct_skip_acts,
        sequence_length=sequence_length,
        incl_bias=incl_bias,
        skip_bias=skip_bias,
        threshold=threshold
    )

    nucleotide_activations = get_nucleotide_activations(
        collapsed_seq_incl_acts=collapsed_seq_incl_acts,
        collapsed_struct_incl_acts=collapsed_struct_incl_acts,
        collapsed_seq_skip_acts=collapsed_seq_skip_acts,
        collapsed_struct_skip_acts=collapsed_struct_skip_acts,
        sequence_length=sequence_length,
        seq_filter_width=seq_filter_width,
        struct_filter_width=struct_filter_width,
        threshold=threshold
    )

    return {
        "exon": exon,
        "sequence": full_sequence,
        "structs": structure,
        "predicted_psi": float(predicted_psi),
        "delta_force": float(delta_force),
        "incl_bias": float(incl_bias),
        "skip_bias": float(skip_bias),
        "incl_strength": float(incl_strength),
        "skip_strength": float(skip_strength),
        "feature_activations": {
            "name": "feature_activations",
            "children": feature_activations
        },
        "nucleotide_activations": {
            "name": "nucleotide_activations",
            "children": nucleotide_activations
        },
    }
