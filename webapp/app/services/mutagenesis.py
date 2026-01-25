"""Mutagenesis service for generating single-point mutations."""

from typing import List, Dict, Tuple

NUCLEOTIDES = ['A', 'C', 'G', 'T']


def generate_all_mutations(sequence: str) -> List[Dict]:
    """
    Generate all possible single-point mutations for a sequence.

    For a 70-nucleotide sequence, this generates 210 mutations
    (70 positions × 3 alternate nucleotides per position).

    Args:
        sequence: The reference sequence (must be 70nt, ACGT only)

    Returns:
        List of mutation dictionaries with:
        - position: 1-indexed position in sequence
        - original: Original nucleotide
        - mutant: Mutant nucleotide
        - mutant_sequence: Full mutated sequence
    """
    sequence = sequence.upper()
    mutations = []

    for i, original_nt in enumerate(sequence):
        position = i + 1  # 1-indexed

        for mutant_nt in NUCLEOTIDES:
            if mutant_nt != original_nt:
                # Create mutated sequence
                mutant_sequence = sequence[:i] + mutant_nt + sequence[i+1:]

                mutations.append({
                    'position': position,
                    'original': original_nt,
                    'mutant': mutant_nt,
                    'mutation_label': f"{original_nt}{position}{mutant_nt}",
                    'mutant_sequence': mutant_sequence,
                })

    return mutations


def calculate_delta_psi(reference_psi: float, mutation_psi: float) -> float:
    """Calculate delta PSI (mutation effect)."""
    return mutation_psi - reference_psi


def organize_mutations_for_heatmap(mutations: List[Dict]) -> Dict:
    """
    Organize mutation results for heatmap visualization.

    Returns a structure suitable for plotting a heatmap with:
    - Rows: mutation types (A→C, A→G, A→T, C→A, C→G, C→T, G→A, G→C, G→T, T→A, T→C, T→G)
    - Columns: positions (1-70)
    - Values: delta PSI

    Args:
        mutations: List of mutation results with psi and delta_psi

    Returns:
        Dictionary with positions, mutation_types, and matrix data
    """
    # Define all possible mutation types
    mutation_types = []
    for original in NUCLEOTIDES:
        for mutant in NUCLEOTIDES:
            if original != mutant:
                mutation_types.append(f"{original}→{mutant}")

    # Create a mapping for quick lookup
    mutation_map = {}
    for m in mutations:
        key = (m['position'], m['original'], m['mutant'])
        mutation_map[key] = m

    # Build the matrix
    # For each position, we only have 3 valid mutations (not 12)
    # We'll organize by: for each position, which mutations are possible
    positions = list(range(1, 71))

    # Create a simplified structure: position -> {mutant_nt -> delta_psi}
    position_data = []
    for pos in positions:
        pos_mutations = {}
        for m in mutations:
            if m['position'] == pos:
                pos_mutations[m['mutant']] = {
                    'delta_psi': m.get('delta_psi', 0),
                    'psi': m.get('psi', 0),
                    'original': m['original'],
                    'mutant': m['mutant'],
                    'mutation_label': m['mutation_label'],
                }
        position_data.append({
            'position': pos,
            'original': mutations[0]['original'] if mutations else 'N',
            'mutations': pos_mutations,
        })

    # Find the original nucleotide at each position from the mutations
    original_at_pos = {}
    for m in mutations:
        original_at_pos[m['position']] = m['original']

    # Create matrix data for heatmap (3 rows: mutation to A, C, G, T but excluding original)
    # Actually, let's create it as 3 rows per position representing the 3 possible mutations
    heatmap_data = {
        'positions': positions,
        'original_sequence': ''.join([original_at_pos.get(i, 'N') for i in positions]),
        'mutations': mutations,
        'matrix': {
            'A': [],  # PSI when mutated TO A
            'C': [],  # PSI when mutated TO C
            'G': [],  # PSI when mutated TO G
            'T': [],  # PSI when mutated TO T
        },
        'delta_matrix': {
            'A': [],  # Delta PSI when mutated TO A
            'C': [],  # Delta PSI when mutated TO C
            'G': [],  # Delta PSI when mutated TO G
            'T': [],  # Delta PSI when mutated TO T
        },
    }

    for pos in positions:
        original = original_at_pos.get(pos, 'N')
        for to_nt in NUCLEOTIDES:
            if to_nt == original:
                # No mutation - this is the reference, use None
                heatmap_data['matrix'][to_nt].append(None)
                heatmap_data['delta_matrix'][to_nt].append(None)
            else:
                # Find the mutation
                found = False
                for m in mutations:
                    if m['position'] == pos and m['mutant'] == to_nt:
                        heatmap_data['matrix'][to_nt].append(m.get('psi'))
                        heatmap_data['delta_matrix'][to_nt].append(m.get('delta_psi'))
                        found = True
                        break
                if not found:
                    heatmap_data['matrix'][to_nt].append(None)
                    heatmap_data['delta_matrix'][to_nt].append(None)

    return heatmap_data


def get_top_mutations(mutations: List[Dict], n: int = 10, by: str = 'delta_psi') -> Tuple[List[Dict], List[Dict]]:
    """
    Get top N mutations with highest positive and negative effects.

    Args:
        mutations: List of mutation results
        n: Number of top mutations to return
        by: Field to sort by ('delta_psi' or 'psi')

    Returns:
        Tuple of (top_positive, top_negative) mutation lists
    """
    # Filter to only mutations with valid delta_psi
    valid = [m for m in mutations if m.get('delta_psi') is not None]

    # Sort by delta_psi
    sorted_mutations = sorted(valid, key=lambda x: x.get('delta_psi', 0), reverse=True)

    top_positive = sorted_mutations[:n]
    top_negative = sorted_mutations[-n:][::-1]  # Reverse to show most negative first

    return top_positive, top_negative
