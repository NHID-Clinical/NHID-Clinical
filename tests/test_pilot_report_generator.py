"""5 deterministic tests for the pilot report generator."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.pilot_report_generator import load_results, summarize, generate_report


def _write_result(directory, name, conformant, cas_score, violations=None):
    payload = {
        "session_id": name,
        "conformant": conformant,
        "action": "ALLOW" if conformant else "DENY_DATA",
        "cas": {"score": cas_score, "tier": "Verified Trust" if cas_score >= 0.95 else "Review Required"},
        "violations": violations or [],
    }
    (directory / f"{name}.json").write_text(json.dumps(payload))


class TestPilotReportGenerator:
    def test_load_results_reads_json_files(self, tmp_path):
        _write_result(tmp_path, "call_001", True, 0.9)
        _write_result(tmp_path, "call_002", False, 0.2)
        results = load_results(tmp_path)
        assert len(results) == 2

    def test_load_results_skips_malformed_files(self, tmp_path):
        _write_result(tmp_path, "call_001", True, 0.9)
        (tmp_path / "broken.json").write_text("{not valid json")
        results = load_results(tmp_path)
        assert len(results) == 1

    def test_summarize_pass_rate_and_cas(self, tmp_path):
        _write_result(tmp_path, "c1", True, 0.8)
        _write_result(tmp_path, "c2", False, 0.4)
        s = summarize(load_results(tmp_path))
        assert s["calls_total"] == 2
        assert s["pass_rate"] == 0.5
        assert abs(s["cas_avg"] - 0.6) < 0.001

    def test_summarize_counts_violations_by_rule(self, tmp_path):
        _write_result(tmp_path, "c1", False, 0.0, [
            {"rule_id": "IDG-01", "severity": "critical"},
            {"rule_id": "PDX-01", "severity": "critical"},
        ])
        _write_result(tmp_path, "c2", False, 0.0, [
            {"rule_id": "IDG-01", "severity": "critical"},
        ])
        s = summarize(load_results(tmp_path))
        assert s["violations_by_rule"]["IDG-01"] == 2
        assert s["violations_by_rule"]["PDX-01"] == 1

    def test_generate_report_is_markdown_with_summary(self, tmp_path):
        _write_result(tmp_path, "c1", True, 0.95)
        report = generate_report(load_results(tmp_path), org_name="Test Org")
        assert report.startswith("# NHID-Clinical Shadow Pilot Report — Test Org")
        assert "| Total calls evaluated | 1 |" in report
        assert "IDG-01" in report  # controls table always lists the 5 controls
