/**
 * File parsing utilities for CSV and FASTA files.
 * Also handles multi-sequence text input parsing.
 */

/**
 * Parse FASTA format text.
 * Format: >Name\nSEQUENCE\n>Name2\nSEQUENCE2
 * @param {string} text - FASTA formatted text
 * @returns {Array<{name: string, sequence: string}>}
 */
function parseFasta(text) {
    const sequences = [];
    const lines = text.trim().split('\n');
    let currentName = '';
    let currentSeq = '';
    let seqCount = 0;

    for (const line of lines) {
        const trimmedLine = line.trim();
        if (trimmedLine.startsWith('>')) {
            // Save previous sequence if exists
            if (currentSeq) {
                sequences.push({
                    name: currentName || `Seq_${seqCount}`,
                    sequence: currentSeq.toUpperCase()
                });
            }
            seqCount++;
            // Extract name from header (remove > and trim)
            currentName = trimmedLine.substring(1).trim() || `Seq_${seqCount}`;
            currentSeq = '';
        } else if (trimmedLine) {
            // Append to current sequence (remove whitespace)
            currentSeq += trimmedLine.replace(/\s/g, '');
        }
    }

    // Don't forget the last sequence
    if (currentSeq) {
        sequences.push({
            name: currentName || `Seq_${seqCount}`,
            sequence: currentSeq.toUpperCase()
        });
    }

    return sequences;
}

/**
 * Parse plain sequences (one per line, no headers).
 * @param {string} text - Plain text with one sequence per line
 * @returns {Array<{name: string, sequence: string}>}
 */
function parsePlainSequences(text) {
    const lines = text.trim().split('\n');
    const sequences = [];

    for (let i = 0; i < lines.length; i++) {
        const seq = lines[i].trim().toUpperCase().replace(/\s/g, '');
        if (seq.length > 0) {
            sequences.push({
                name: `Seq_${sequences.length + 1}`,
                sequence: seq
            });
        }
    }

    return sequences;
}

/**
 * Auto-detect format and parse multi-sequence text.
 * If any line starts with '>', treat as FASTA, otherwise plain sequences.
 * @param {string} text - Text to parse
 * @returns {Array<{name: string, sequence: string}>}
 */
function parseMultiSequenceText(text) {
    const trimmed = text.trim();

    if (!trimmed) {
        return [];
    }

    // Check if it looks like FASTA (any line starts with >)
    if (trimmed.includes('>')) {
        return parseFasta(trimmed);
    }

    // Otherwise treat as plain sequences
    return parsePlainSequences(trimmed);
}

/**
 * Detect the delimiter used in a CSV file.
 * @param {string} text - CSV text content
 * @returns {string} Detected delimiter: ',', ';', or '\t'
 */
function detectDelimiter(text) {
    const firstLine = text.split('\n')[0] || '';

    // Count occurrences of each potential delimiter in first line
    const tabCount = (firstLine.match(/\t/g) || []).length;
    const semicolonCount = (firstLine.match(/;/g) || []).length;
    const commaCount = (firstLine.match(/,/g) || []).length;

    // Return the most common delimiter
    if (tabCount > 0 && tabCount >= semicolonCount && tabCount >= commaCount) {
        return '\t';
    }
    if (semicolonCount > 0 && semicolonCount >= commaCount) {
        return ';';
    }
    return ',';
}

/**
 * Detect if the first row is a header row.
 * @param {Array<string>} row - First row of CSV
 * @returns {boolean} True if row looks like a header
 */
function detectHeader(row) {
    if (!row || row.length === 0) return false;

    // Common header patterns (case insensitive)
    const headerPatterns = ['name', 'sequence', 'seq', 'id', 'exon', 'header'];

    // Check if any cell matches header patterns
    for (const cell of row) {
        const lowerCell = cell.toLowerCase().trim();
        if (headerPatterns.some(pattern => lowerCell.includes(pattern))) {
            return true;
        }
    }

    // If first cell looks like a valid sequence (all ACGTU), probably not a header
    const firstCell = row[0].toUpperCase().trim();
    if (/^[ACGTU]+$/.test(firstCell) && firstCell.length > 20) {
        return false;
    }

    return false;
}

/**
 * Parse CSV content.
 * Supports:
 * - 2 columns: name, sequence (with or without header)
 * - 1 column: sequence only (with or without header)
 * - Auto-detects delimiter (comma, semicolon, tab)
 * @param {string} text - CSV file content
 * @returns {Array<{name: string, sequence: string}>}
 */
function parseCSV(text) {
    const delimiter = detectDelimiter(text);
    const lines = text.trim().split('\n');

    if (lines.length === 0) {
        return [];
    }

    // Parse all rows
    const rows = lines.map(line => {
        // Handle quoted fields properly
        const cells = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === delimiter && !inQuotes) {
                cells.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        cells.push(current.trim());
        return cells;
    });

    // Detect if first row is header
    const hasHeader = detectHeader(rows[0]);
    const dataRows = hasHeader ? rows.slice(1) : rows;

    // Determine format based on number of columns
    const numCols = rows[0].length;

    const sequences = [];
    for (let i = 0; i < dataRows.length; i++) {
        const row = dataRows[i];
        if (!row || row.length === 0 || (row.length === 1 && !row[0].trim())) {
            continue; // Skip empty rows
        }

        if (numCols >= 2 && row.length >= 2) {
            // Two or more columns: assume name, sequence
            const name = row[0].trim() || `Seq_${sequences.length + 1}`;
            const seq = row[1].trim().toUpperCase().replace(/\s/g, '');
            if (seq) {
                sequences.push({ name, sequence: seq });
            }
        } else {
            // Single column: sequence only
            const seq = row[0].trim().toUpperCase().replace(/\s/g, '');
            if (seq) {
                sequences.push({
                    name: `Seq_${sequences.length + 1}`,
                    sequence: seq
                });
            }
        }
    }

    return sequences;
}

/**
 * Read and parse a file (CSV or FASTA).
 * @param {File} file - File object to parse
 * @returns {Promise<Array<{name: string, sequence: string}>>}
 */
async function parseFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.onload = (event) => {
            const text = event.target.result;
            const fileName = file.name.toLowerCase();

            let sequences;
            if (fileName.endsWith('.fasta') || fileName.endsWith('.fa') || fileName.endsWith('.fna')) {
                sequences = parseFasta(text);
            } else if (fileName.endsWith('.csv') || fileName.endsWith('.tsv') || fileName.endsWith('.txt')) {
                // Try CSV first
                sequences = parseCSV(text);
                // If CSV parsing resulted in weird sequences, try FASTA
                if (sequences.length === 0 || (sequences.length === 1 && text.includes('>'))) {
                    sequences = parseFasta(text);
                }
            } else {
                // Unknown extension - try to auto-detect
                if (text.trim().startsWith('>')) {
                    sequences = parseFasta(text);
                } else {
                    sequences = parseCSV(text);
                }
            }

            resolve(sequences);
        };

        reader.onerror = () => {
            reject(new Error('Failed to read file'));
        };

        reader.readAsText(file);
    });
}

/**
 * Validate a single sequence.
 * @param {string} sequence - Sequence to validate
 * @param {number} expectedLength - Expected length (default 70)
 * @returns {{valid: boolean, error: string}}
 */
function validateSequence(sequence, expectedLength = 70) {
    const cleaned = sequence.toUpperCase().replace(/U/g, 'T').replace(/\s/g, '');

    if (cleaned.length !== expectedLength) {
        return {
            valid: false,
            error: `Must be exactly ${expectedLength} nucleotides (got ${cleaned.length})`
        };
    }

    const invalidChars = cleaned.match(/[^ACGT]/g);
    if (invalidChars) {
        const unique = [...new Set(invalidChars)];
        return {
            valid: false,
            error: `Contains invalid characters: ${unique.join(', ')}`
        };
    }

    return { valid: true, error: '' };
}

/**
 * Parse and validate sequences from text input or file.
 * @param {string} text - Text input to parse
 * @param {number} expectedLength - Expected sequence length
 * @returns {{sequences: Array<{name: string, sequence: string}>, validCount: number, invalidCount: number}}
 */
function parseAndValidate(text, expectedLength = 70) {
    const sequences = parseMultiSequenceText(text);
    let validCount = 0;
    let invalidCount = 0;

    for (const seq of sequences) {
        const validation = validateSequence(seq.sequence, expectedLength);
        seq.valid = validation.valid;
        seq.error = validation.error;
        if (validation.valid) {
            validCount++;
        } else {
            invalidCount++;
        }
    }

    return { sequences, validCount, invalidCount };
}

// Export functions for use in other scripts
window.FileParser = {
    parseFasta,
    parsePlainSequences,
    parseMultiSequenceText,
    parseCSV,
    parseFile,
    detectDelimiter,
    detectHeader,
    validateSequence,
    parseAndValidate,
};
