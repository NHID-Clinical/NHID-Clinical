"""Safety evaluation test suite for NHID-Clinical.

Tests the safety framework in isolation from production policy engine.
Shadow mode ensures no impact on live behavior.

Test categories:
- test_failure_modes.py: Failure mode taxonomy validation
- test_safety_metrics.py: Metric collection and threshold evaluation
- test_adversarial_cases.py: Adversarial corpus stress testing
- test_shadow_mode.py: Non-blocking logging verification
- test_safety_case.py: Evidence-based claims validation
"""
