"""8 deterministic tests for the vendor conformance metrics store."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import nhid_event_store as store


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Each test gets its own fresh in-memory-like SQLite file."""
    db_file = tmp_path / "test_nhid.db"
    monkeypatch.setattr(store, "DB_PATH", db_file)
    yield


class TestRecordConformanceResult:
    def test_record_inserts_row(self):
        store.record_conformance_result("vendor_a", "sess_001", 0.85, True)
        metrics = store.get_vendor_metrics("vendor_a")
        assert metrics["calls_total"] == 1

    def test_record_multiple_rows_same_vendor(self):
        store.record_conformance_result("vendor_b", "sess_01", 0.90, True)
        store.record_conformance_result("vendor_b", "sess_02", 0.50, False)
        store.record_conformance_result("vendor_b", "sess_03", 0.75, True)
        metrics = store.get_vendor_metrics("vendor_b")
        assert metrics["calls_total"] == 3

    def test_missing_vendor_id_raises(self):
        with pytest.raises(ValueError, match="vendor_id"):
            store.record_conformance_result("", "sess_x", 0.80, True)

    def test_missing_session_id_raises(self):
        with pytest.raises(ValueError, match="session_id"):
            store.record_conformance_result("vendor_c", "", 0.80, True)


class TestGetVendorMetrics:
    def test_pass_rate_calculation(self):
        store.record_conformance_result("v1", "s1", 0.9, True)
        store.record_conformance_result("v1", "s2", 0.4, False)
        metrics = store.get_vendor_metrics("v1")
        assert metrics["pass_rate"] == 0.5

    def test_cas_avg_calculation(self):
        store.record_conformance_result("v2", "s1", 0.8, True)
        store.record_conformance_result("v2", "s2", 0.6, False)
        metrics = store.get_vendor_metrics("v2")
        assert abs(metrics["cas_avg"] - 0.7) < 0.001

    def test_vendor_isolation(self):
        store.record_conformance_result("vendor_x", "sx1", 0.95, True)
        store.record_conformance_result("vendor_y", "sy1", 0.10, False)
        mx = store.get_vendor_metrics("vendor_x")
        my = store.get_vendor_metrics("vendor_y")
        assert mx["calls_total"] == 1
        assert my["calls_total"] == 1
        assert mx["cas_avg"] > my["cas_avg"]

    def test_empty_vendor_returns_zero_metrics(self):
        metrics = store.get_vendor_metrics("vendor_none")
        assert metrics["calls_total"] == 0
        assert metrics["pass_rate"] == 0.0
        assert metrics["cas_avg"] == 0.0
