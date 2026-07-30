#!/usr/bin/env python3
"""
Test live VAPI adapter endpoint with noncompliant scenario.

Run from repo root: python scripts/test_vapi_live.py
"""

import json
import sys
import time
from pathlib import Path

import requests


ENDPOINT = "https://gfvq4swdtf.execute-api.us-east-1.amazonaws.com/prod/v1/adapters/vapi/check"
SCENARIO_PATH = "tests/demo_scenarios/vapi_noncompliant.json"


def main():
    print("━" * 60)
    print("Testing Live VAPI Adapter Endpoint")
    print("━" * 60)
    print()

    # Check if scenario file exists
    scenario_file = Path(SCENARIO_PATH)
    if not scenario_file.exists():
        print(f"ERROR: Scenario file not found: {SCENARIO_PATH}")
        return 1

    print(f"Endpoint: {ENDPOINT}")
    print(f"Scenario: {SCENARIO_PATH}")
    print()

    # Load the JSON payload
    print("Loading scenario...")
    with open(scenario_file) as f:
        payload = json.load(f)

    messages = payload.get("messages", [])
    call_id = payload["call"]["id"]
    print(f"Scenario loaded: {len(messages)} messages in call {call_id}")
    for i, msg in enumerate(messages):
        role = msg["role"].upper()
        text = msg["message"][:60] + ("..." if len(msg["message"]) > 60 else "")
        ts = msg["secondsFromStart"]
        print(f"  - {role} ({ts}s): {text}")
    print()

    # Expected behavior
    print("Expected Result:")
    print("  ✓ conformant: false (rejection)")
    print("  ✓ violations: IDG-01 (no early disclosure) + PDX-01 (PHI before disclosure)")
    print("  ✓ action: DENY_DATA or LOG_ONLY")
    print()

    # Call the endpoint
    print("Calling live endpoint...")
    try:
        start = time.time()
        resp = requests.post(
            ENDPOINT,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        elapsed_ms = (time.time() - start) * 1000

        print(f"✓ Success ({elapsed_ms:.0f}ms)")
        print()

        # Parse response
        try:
            result = resp.json()
        except:
            print(f"✗ Response is not valid JSON (status {resp.status_code}):")
            print(resp.text)
            return 1

        # Display response
        print("Response:")
        print(json.dumps(result, indent=2))
        print()

        # Validate
        print("Validation:")
        if result.get("conformant") is False:
            print("✓ conformant is FALSE (correct rejection)")
        else:
            print(f"✗ conformant is {result.get('conformant')} (unexpected — should reject)")

        violations = result.get("violations", [])
        if violations:
            print(f"✓ Violations present: {len(violations)} found")
            rule_ids = []
            for v in violations:
                rule_id = v.get("rule_id", "?")
                desc = v.get("description", "")
                print(f"  - {rule_id}: {desc}")
                rule_ids.append(rule_id)

            # Check for expected rule IDs
            if "IDG-01" in rule_ids:
                print("✓ IDG-01 (early disclosure required) present")
            else:
                print("✗ IDG-01 missing from violations")

            if "PDX-01" in rule_ids:
                print("✓ PDX-01 (PHI before disclosure) present")
            else:
                print("✗ PDX-01 missing from violations")
        else:
            print("✗ No violations found (expected IDG-01 + PDX-01)")

        print()
        print("━" * 60)
        print("Test Complete")
        print("━" * 60)
        return 0

    except requests.exceptions.Timeout:
        print("✗ Timeout: endpoint did not respond within 30 seconds")
        return 1
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {e}")
        print("  Check: endpoint URL, internet connectivity, firewall")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
