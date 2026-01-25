"""Tests for the prediction API."""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webapp.app.main import app
from webapp.app.database import init_db


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    init_db()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check(self, client):
        """Test health check returns OK."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data


class TestExampleEndpoint:
    """Tests for /api/example endpoint."""

    def test_get_examples(self, client):
        """Test getting example sequences."""
        response = client.get("/api/example")
        assert response.status_code == 200
        data = response.json()
        assert "sequences" in data
        assert len(data["sequences"]) >= 1

        # Check structure of first example
        example = data["sequences"][0]
        assert "name" in example
        assert "sequence" in example
        assert "description" in example
        assert len(example["sequence"]) == 70


class TestPredictEndpoint:
    """Tests for /api/predict endpoint."""

    def test_predict_valid_sequence(self, client):
        """Test prediction with valid sequence."""
        # Use a real example sequence
        sequence = "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT"

        response = client.post(
            "/api/predict",
            json={"sequence": sequence},
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "finished"
        assert "result_url" in data

    def test_predict_invalid_length(self, client):
        """Test prediction rejects wrong length."""
        response = client.post(
            "/api/predict",
            json={"sequence": "ACGT"},  # Too short
        )
        assert response.status_code == 422  # Validation error

    def test_predict_invalid_characters(self, client):
        """Test prediction rejects invalid characters."""
        # 70 characters but with invalid ones
        sequence = "X" * 70

        response = client.post(
            "/api/predict",
            json={"sequence": sequence},
        )
        assert response.status_code == 422  # Validation error


class TestResultEndpoint:
    """Tests for /api/result endpoint."""

    def test_get_result_not_found(self, client):
        """Test getting result for non-existent job."""
        response = client.get("/api/result/nonexistent-id")
        assert response.status_code == 404

    def test_get_result_after_prediction(self, client):
        """Test getting result after prediction."""
        # First submit a prediction
        sequence = "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT"
        predict_response = client.post(
            "/api/predict",
            json={"sequence": sequence},
        )
        job_id = predict_response.json()["job_id"]

        # Then get the result
        response = client.get(f"/api/result/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert "psi" in data
        assert 0 <= data["psi"] <= 1
        assert "interpretation" in data


class TestBatchEndpoint:
    """Tests for /api/batch endpoint."""

    def test_batch_predict(self, client):
        """Test batch prediction."""
        sequences = [
            {"name": "seq1", "sequence": "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT"},
            {"name": "seq2", "sequence": "CTACCACCTCCCAAGCTTACACACTGTTTGATGAAAGGTCGCCACAACGTTCCCTCACCCCTAGTCTCGC"},
        ]

        response = client.post(
            "/api/batch",
            json={"sequences": sequences},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "finished"

    def test_batch_empty_list(self, client):
        """Test batch rejects empty list."""
        response = client.post(
            "/api/batch",
            json={"sequences": []},
        )
        assert response.status_code == 422


class TestExportEndpoint:
    """Tests for /api/export endpoint."""

    def test_export_csv_basic(self, client):
        """Test exporting results as CSV."""
        # First create a prediction
        sequence = "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT"
        predict_response = client.post(
            "/api/predict",
            json={"sequence": sequence},
        )
        job_id = predict_response.json()["job_id"]

        # Export as CSV
        response = client.get(f"/api/export/{job_id}/csv")
        assert response.status_code == 200

    def test_export_csv_content(self, client):
        """Test exporting results as CSV with proper content."""
        # First create a prediction
        sequence = "GGTAGTACGCCAATTCGCCGGTGCCGCGAGCCAGAGGCTACCAAAACTTGACAAGCCTACATATACTACT"
        predict_response = client.post(
            "/api/predict",
            json={"sequence": sequence},
        )
        job_id = predict_response.json()["job_id"]

        # Export as CSV
        response = client.get(f"/api/export/{job_id}/csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        csv_content = response.text
        assert "sequence" in csv_content  # CSV header should include sequence
        assert "psi" in csv_content  # CSV header should include psi
