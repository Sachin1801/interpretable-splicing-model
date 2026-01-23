"""Model wrapper service for PSI prediction."""

import subprocess
import numpy as np
import tensorflow as tf
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import logging
import sys

from webapp.app.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Add figures directory to path - this auto-registers custom layers
# via @register_keras_serializable decorators when quad_model is imported
sys.path.insert(0, str(settings.project_root / 'figures'))
from quad_model import *  # noqa: E402, F401, F403

from tensorflow.keras.models import load_model


class SplicingPredictor:
    """Wrapper class for the splicing prediction model."""

    _instance: Optional["SplicingPredictor"] = None
    _model: Optional[tf.keras.Model] = None

    def __new__(cls):
        """Singleton pattern to ensure model is loaded only once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the predictor and load the model if not already loaded."""
        if self._model is None:
            self._load_model()

    def _load_model(self):
        """Load the pre-trained TensorFlow model."""
        logger.info(f"Loading model from {settings.model_path}")

        try:
            # Simple load - custom layers already registered via quad_model import
            self._model = load_model(str(settings.model_path))
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    @property
    def model(self) -> tf.keras.Model:
        """Get the loaded model."""
        if self._model is None:
            self._load_model()
        return self._model

    def validate_sequence(self, sequence: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a sequence meets requirements.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check length
        if len(sequence) != settings.exon_length:
            return False, f"Sequence must be exactly {settings.exon_length} nucleotides (got {len(sequence)})"

        # Check characters
        valid_chars = set("ACGT")
        sequence_upper = sequence.upper()
        invalid_chars = set(sequence_upper) - valid_chars
        if invalid_chars:
            return False, f"Sequence contains invalid characters: {invalid_chars}. Only A, C, G, T are allowed."

        return True, None

    def add_flanking(self, exon_sequence: str) -> str:
        """Add flanking sequences to the exon."""
        pre = settings.pre_sequence[-settings.flanking_length:]
        post = settings.post_sequence[:settings.flanking_length]
        return pre + exon_sequence.upper() + post

    def _nts_to_vector(self, sequence: str) -> np.ndarray:
        """One-hot encode a nucleotide sequence."""
        mapping = {"A": 0, "C": 1, "G": 2, "T": 3}
        encoded = np.zeros((len(sequence), 4))
        for i, nt in enumerate(sequence):
            encoded[i, mapping[nt]] = 1
        return encoded

    def _structure_to_vector(self, structure: str) -> np.ndarray:
        """One-hot encode an RNA secondary structure."""
        mapping = {".": 0, "(": 1, ")": 2}
        encoded = np.zeros((len(structure), 3))
        for i, s in enumerate(structure):
            encoded[i, mapping[s]] = 1
        return encoded

    def _get_structure(self, sequence: str, timeout: int = 30) -> Tuple[Optional[str], Optional[float]]:
        """
        Predict RNA secondary structure using ViennaRNA.

        Args:
            sequence: The RNA sequence (with T replaced by U)
            timeout: Maximum time in seconds for structure prediction

        Returns:
            Tuple of (structure, minimum_free_energy) or (None, None) if failed
        """
        try:
            # Convert T to U for RNA
            rna_sequence = sequence.replace("T", "U")

            result = subprocess.run(
                ["RNAfold", "--noPS"],
                input=rna_sequence,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.warning(f"RNAfold returned non-zero exit code: {result.stderr}")
                return None, None

            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:
                logger.warning("RNAfold output format unexpected")
                return None, None

            # Parse structure and MFE from output
            parts = lines[1].split()
            structure = parts[0]

            # Extract MFE from parentheses
            mfe_str = parts[-1].strip("()")
            mfe = float(mfe_str)

            return structure, mfe

        except subprocess.TimeoutExpired:
            logger.warning(f"RNAfold timed out after {timeout} seconds")
            return None, None
        except Exception as e:
            logger.error(f"Error running RNAfold: {e}")
            return None, None

    def _compute_wobbles(self, sequence: str, structure: str) -> np.ndarray:
        """
        Compute wobble pair indicators (G-U base pairs).

        Args:
            sequence: The DNA sequence
            structure: The secondary structure string

        Returns:
            Array of shape (length, 1) with 1s at wobble positions
        """
        # Find base pairing from structure
        stack = []
        pairs = {}
        for i, s in enumerate(structure):
            if s == "(":
                stack.append(i)
            elif s == ")":
                if stack:
                    j = stack.pop()
                    pairs[i] = j
                    pairs[j] = i

        # Check for G-U wobble pairs
        wobble = np.zeros((len(sequence), 1))
        for i in range(len(sequence)):
            if i in pairs:
                j = pairs[i]
                pair = {sequence[i], sequence[j]}
                if pair == {"G", "T"}:
                    wobble[i] = 1
                    wobble[j] = 1

        return wobble

    def prepare_input(
        self,
        exon_sequence: str
    ) -> Tuple[List[np.ndarray], Optional[str], Optional[float], List[str]]:
        """
        Prepare model input from an exon sequence.

        Args:
            exon_sequence: The 70nt exon sequence

        Returns:
            Tuple of:
                - List of input arrays [seq_oh, struct_oh, wobble]
                - Structure string (or None if prediction failed)
                - MFE (or None if prediction failed)
                - List of warning messages
        """
        warnings = []

        # Add flanking sequences
        full_sequence = self.add_flanking(exon_sequence.upper())

        # One-hot encode sequence
        seq_oh = self._nts_to_vector(full_sequence)

        # Get structure prediction
        structure, mfe = self._get_structure(full_sequence, timeout=settings.prediction_timeout)

        if structure is None:
            # Fall back to all-unpaired structure
            warnings.append("RNA structure prediction failed. Using default unpaired structure.")
            structure = "." * len(full_sequence)
            mfe = 0.0

        # One-hot encode structure
        struct_oh = self._structure_to_vector(structure)

        # Compute wobble pairs
        wobble = self._compute_wobbles(full_sequence, structure)

        # Add batch dimension
        inputs = [
            np.expand_dims(seq_oh, 0),
            np.expand_dims(struct_oh, 0),
            np.expand_dims(wobble, 0),
        ]

        return inputs, structure, mfe, warnings

    def predict_single(self, exon_sequence: str) -> Dict[str, Any]:
        """
        Make a prediction for a single sequence.

        Args:
            exon_sequence: The 70nt exon sequence

        Returns:
            Dictionary with prediction results
        """
        # Validate sequence
        is_valid, error = self.validate_sequence(exon_sequence)
        if not is_valid:
            raise ValueError(error)

        # Prepare input
        inputs, structure, mfe, warnings = self.prepare_input(exon_sequence)

        # Run prediction
        psi = float(self.model.predict(inputs, verbose=0)[0, 0])

        # Get interpretation
        interpretation = self._get_interpretation(psi)

        return {
            "psi": psi,
            "structure": structure,
            "mfe": mfe,
            "interpretation": interpretation,
            "warnings": warnings,
        }

    def predict_batch(self, sequences: List[str]) -> List[Dict[str, Any]]:
        """
        Make predictions for multiple sequences.

        Args:
            sequences: List of 70nt exon sequences

        Returns:
            List of prediction result dictionaries
        """
        results = []
        for seq in sequences:
            try:
                result = self.predict_single(seq)
                result["sequence"] = seq
                result["status"] = "success"
            except Exception as e:
                result = {
                    "sequence": seq,
                    "status": "error",
                    "error": str(e),
                }
            results.append(result)
        return results

    def get_force_plot_data(self, exon_sequence: str) -> Dict[str, Any]:
        """
        Extract force plot data for visualization.

        Args:
            exon_sequence: The 70nt exon sequence

        Returns:
            Dictionary with force plot data for Plotly
        """
        # Prepare input
        inputs, structure, mfe, _ = self.prepare_input(exon_sequence)

        # Layer names to extract
        layer_names = [
            "qc_incl",
            "qc_skip",
            "position_bias_incl",
            "position_bias_skip",
        ]

        activations = {}
        for name in layer_names:
            try:
                layer = self.model.get_layer(name)
                intermediate_model = tf.keras.Model(
                    inputs=self.model.inputs,
                    outputs=layer.output,
                )
                activation = intermediate_model.predict(inputs, verbose=0)[0]
                activations[name] = activation.tolist()
            except Exception as e:
                logger.warning(f"Could not extract layer {name}: {e}")
                activations[name] = None

        return {
            "positions": list(range(settings.total_length)),
            "activations": activations,
            "structure": structure,
            "mfe": mfe,
        }

    def get_heatmap_data(self, exon_sequence: str) -> Dict[str, Any]:
        """
        Extract filter activations for heatmap visualization.

        Args:
            exon_sequence: The 70nt exon sequence

        Returns:
            Dictionary with heatmap data:
            - positions: list of position numbers (1-90)
            - nucleotides: list of nucleotide characters
            - filter_names: list of filter names
            - activations: 2D matrix (filters × positions)
        """
        # Prepare input
        inputs, structure, mfe, _ = self.prepare_input(exon_sequence)

        # Get full sequence for nucleotide labels
        full_sequence = self.add_flanking(exon_sequence.upper())

        # Layer configurations: (layer_name, prefix, num_filters, kernel_width)
        layer_configs = [
            ("qc_incl", "incl", 20, 6),
            ("qc_skip", "skip", 20, 6),
            ("c_incl_struct", "incl_struct", 8, 30),
            ("c_skip_struct", "skip_struct", 8, 30),
        ]

        filter_names = []
        all_activations = []

        for layer_name, prefix, num_filters, kernel_width in layer_configs:
            try:
                layer = self.model.get_layer(layer_name)
                intermediate_model = tf.keras.Model(
                    inputs=self.model.inputs,
                    outputs=layer.output,
                )
                # Get activations: shape (1, output_len, num_filters)
                raw_activations = intermediate_model.predict(inputs, verbose=0)[0]
                output_len = raw_activations.shape[0]

                for i in range(num_filters):
                    filter_name = f"{prefix}_{i+1}"
                    filter_names.append(filter_name)

                    # Get this filter's activations and apply ReLU
                    filter_activations = np.maximum(0, raw_activations[:, i])

                    # Pad to 90 positions if needed
                    if output_len < settings.total_length:
                        # Center the activations with padding
                        pad_left = (settings.total_length - output_len) // 2
                        pad_right = settings.total_length - output_len - pad_left
                        padded = np.pad(filter_activations, (pad_left, pad_right), mode='constant')
                    else:
                        # Already correct length
                        padded = filter_activations

                    all_activations.append(padded.tolist())

            except Exception as e:
                logger.warning(f"Could not extract layer {layer_name}: {e}")

        return {
            "positions": list(range(1, settings.total_length + 1)),
            "nucleotides": list(full_sequence),
            "filter_names": filter_names,
            "activations": all_activations,
            "structure": structure,
        }

    @staticmethod
    def _get_interpretation(psi: float) -> str:
        """Get human-readable interpretation of PSI value."""
        if psi >= 0.8:
            return "Strong exon inclusion predicted"
        elif psi >= 0.6:
            return "Moderate inclusion tendency"
        elif psi >= 0.4:
            return "Balanced inclusion/skipping"
        elif psi >= 0.2:
            return "Moderate skipping tendency"
        else:
            return "Strong exon skipping predicted"


# Global predictor instance
_predictor: Optional[SplicingPredictor] = None


def get_predictor() -> SplicingPredictor:
    """Get the global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = SplicingPredictor()
    return _predictor
