"""Test suite for synthetic healthcare workflow evaluation (Phase 3).

Tests synthetic scenario generation, workflow simulation, and integration
with Phase 1 & Phase 2 safety evaluation frameworks.
"""

import pytest
from datetime import datetime

from src.safety_evaluation.synthetic_scenarios import (
    SyntheticWorkflow,
    SyntheticScenarioBuilder,
    SyntheticScenarioGenerator,
    WorkflowType,
    ParticipantRole,
    ConversationTurn,
)
from src.safety_evaluation.workflow_simulator import (
    WorkflowSimulator,
    WorkflowOutcome,
    ConversationTurnResult,
    WorkflowExecutionResult,
)


class TestSyntheticScenarioGeneration:
    """Test synthetic healthcare workflow scenario generation."""

    def test_compliant_prior_auth_scenario(self):
        """Test generation of compliant prior authorization workflow."""
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        assert workflow.workflow_type == WorkflowType.PRIOR_AUTH
        assert len(workflow.conversation_turns) > 0
        assert workflow.expected_violations == []
        assert workflow.expected_policy_decision == "ALLOW"
        assert "IDG-01" in workflow.target_rules

    def test_delayed_disclosure_scenario(self):
        """Test generation of delayed disclosure violation scenario."""
        workflow = SyntheticScenarioBuilder.prior_auth_delayed_disclosure()

        assert "IDG-01" in workflow.expected_violations
        assert workflow.expected_policy_decision == "DENY_DATA"
        assert workflow.severity == "critical"
        assert len(workflow.conversation_turns) > 0

    def test_ambiguous_disclosure_scenario(self):
        """Test generation of ambiguous disclosure scenario."""
        workflow = SyntheticScenarioBuilder.eligibility_ambiguous_disclosure()

        assert workflow.workflow_type == WorkflowType.ELIGIBILITY
        assert "IDG-01" in workflow.expected_violations
        assert workflow.difficulty == "intermediate"

    def test_escalation_ignored_scenario(self):
        """Test generation of escalation ignored scenario."""
        workflow = SyntheticScenarioBuilder.member_escalation_ignored()

        assert workflow.workflow_type == WorkflowType.ESCALATION
        assert "EIT-01" in workflow.expected_violations
        assert workflow.severity == "critical"
        # Verify escalation request appears in conversation
        escalation_turn = [t for t in workflow.conversation_turns if t.ai_action == "escalation_requested"]
        assert len(escalation_turn) > 0

    def test_social_engineering_scenario(self):
        """Test generation of social engineering violation scenario."""
        workflow = SyntheticScenarioBuilder.provider_social_engineering()

        assert "DBC-01" in workflow.expected_violations
        assert workflow.difficulty == "advanced"
        # Verify false authority claim appears
        false_authority_turn = [t for t in workflow.conversation_turns if t.ai_action == "false_clinical_authority"]
        assert len(false_authority_turn) > 0

    def test_audit_trail_failure_scenario(self):
        """Test generation of audit trail tampering scenario."""
        workflow = SyntheticScenarioBuilder.identity_verification_failure()

        assert workflow.workflow_type == WorkflowType.IDENTITY_VERIFY
        assert "ATR-01" in workflow.expected_violations

    def test_scenario_has_uuid(self):
        """Test that generated scenarios have unique IDs."""
        workflow1 = SyntheticScenarioBuilder.prior_auth_compliant()
        workflow2 = SyntheticScenarioBuilder.prior_auth_compliant()

        # Should generate new UUIDs each time
        assert workflow1.workflow_id != workflow2.workflow_id

    def test_scenario_has_timestamp(self):
        """Test that scenarios have ISO 8601 timestamp."""
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        # Should be parseable as ISO 8601
        assert workflow.created_at.endswith("Z")
        datetime.fromisoformat(workflow.created_at.replace("Z", "+00:00"))

    def test_conversation_turns_ordered(self):
        """Test that conversation turns are in proper order."""
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        for i, turn in enumerate(workflow.conversation_turns):
            assert turn.turn_number == i + 1

    def test_conversation_turns_have_timestamps(self):
        """Test that turns have monotonically increasing timestamps."""
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        prev_timestamp = -1
        for turn in workflow.conversation_turns:
            assert turn.timestamp_ms >= prev_timestamp
            prev_timestamp = turn.timestamp_ms

    def test_pdx_violation_scenarios_generated(self):
        """Test that PDX-01 scenarios are generated."""
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()

        pdx_scenarios = [s for s in scenarios if "PDX-01" in s.expected_violations]
        assert len(pdx_scenarios) > 0
        assert any(s.description.startswith("Eligibility - premature SSN") for s in pdx_scenarios)

    def test_escalation_variant_scenarios_generated(self):
        """Test that escalation variant scenarios are generated."""
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()

        escalation_scenarios = [s for s in scenarios if s.workflow_type == WorkflowType.ESCALATION]
        assert len(escalation_scenarios) > 0

    def test_edge_case_scenarios_generated(self):
        """Test that edge case scenarios with multiple violations are generated."""
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()

        multi_violation_scenarios = [s for s in scenarios if len(s.expected_violations) > 1]
        assert len(multi_violation_scenarios) > 0

    def test_full_corpus_generation(self):
        """Test full synthetic corpus generation meets minimum requirements."""
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()

        # Minimum 20 scenarios (targeting 25+)
        assert len(scenarios) >= 20

        # Coverage of all 5 rules
        all_rules = set()
        for scenario in scenarios:
            all_rules.update(scenario.target_rules)

        required_rules = {"IDG-01", "PDX-01", "DBC-01", "EIT-01", "ATR-01"}
        assert required_rules.issubset(all_rules)

        # Distribution across workflow types
        workflow_types = set(s.workflow_type for s in scenarios)
        assert len(workflow_types) > 1

    def test_scenario_has_required_fields(self):
        """Test that all scenarios have required fields."""
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        assert workflow.workflow_id
        assert workflow.workflow_type
        assert workflow.description
        assert workflow.scenario_narrative
        assert workflow.participants
        assert workflow.conversation_turns
        assert isinstance(workflow.expected_violations, list)
        assert isinstance(workflow.target_rules, list)
        assert workflow.severity in ["critical", "major", "minor"]
        assert workflow.difficulty in ["basic", "intermediate", "advanced"]


class TestWorkflowSimulation:
    """Test healthcare workflow simulation and execution."""

    def test_simulator_initialization(self):
        """Test workflow simulator initialization."""
        simulator = WorkflowSimulator()

        assert simulator.execution_results == []
        assert simulator.start_time is None
        assert simulator.end_time is None

    def test_execute_compliant_workflow(self):
        """Test executing compliant workflow."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        result = simulator.execute_workflow(workflow)

        assert result.workflow_id == workflow.workflow_id
        assert result.workflow_outcome == WorkflowOutcome.SAFE
        assert result.total_violations_detected == 0
        assert result.violations_missed == []

    def test_execute_idg01_violation_workflow(self):
        """Test executing workflow with IDG-01 violation."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_delayed_disclosure()

        result = simulator.execute_workflow(workflow)

        # Violation is detected in the scenario, so outcome is DEGRADED (detected but present)
        # UNSAFE would be if violation was expected but not detected
        assert result.workflow_outcome in (WorkflowOutcome.DEGRADED, WorkflowOutcome.UNSAFE)
        assert "IDG-01" in result.unique_violated_rules
        assert result.severity_score > 0.0

    def test_execute_eit01_violation_workflow(self):
        """Test executing workflow with EIT-01 violation."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.member_escalation_ignored()

        result = simulator.execute_workflow(workflow)

        assert "EIT-01" in result.expected_violations
        assert result.workflow_outcome in (WorkflowOutcome.UNSAFE, WorkflowOutcome.DEGRADED)

    def test_execute_dbc01_violation_workflow(self):
        """Test executing workflow with DBC-01 violation."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.provider_social_engineering()

        result = simulator.execute_workflow(workflow)

        assert "DBC-01" in result.expected_violations
        assert result.severity_score > 0.0

    def test_turn_result_phi_detection(self):
        """Test that PHI handling is detected in turn results."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        result = simulator.execute_workflow(workflow)

        # Should have some turns where PHI was handled
        phi_turns = [t for t in result.turn_results if t.phi_handled]
        assert len(phi_turns) > 0

    def test_turn_result_escalation_handling(self):
        """Test that escalation requests are tracked in turns."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.member_escalation_ignored()

        result = simulator.execute_workflow(workflow)

        # Should have escalation request turn
        escalation_request_turns = [t for t in result.turn_results if t.escalation_requested]
        assert len(escalation_request_turns) > 0

    def test_multiple_violations_in_workflow(self):
        """Test workflow with multiple violations detected."""
        simulator = WorkflowSimulator()
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()
        multi_violation = [s for s in scenarios if len(s.expected_violations) > 1][0]

        result = simulator.execute_workflow(multi_violation)

        assert len(result.expected_violations) > 1
        assert result.workflow_outcome == WorkflowOutcome.UNSAFE

    def test_workflow_execution_timestamp(self):
        """Test that execution timestamp is recorded."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        result = simulator.execute_workflow(workflow)

        assert result.execution_timestamp.endswith("Z")
        # Verify it's a valid ISO 8601 timestamp
        datetime.fromisoformat(result.execution_timestamp.replace("Z", "+00:00"))

    def test_campaign_execution(self):
        """Test executing full campaign of workflows."""
        simulator = WorkflowSimulator()
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()[:5]  # Test subset

        simulator.execute_campaign(scenarios)

        assert len(simulator.execution_results) == len(scenarios)
        assert simulator.start_time is not None
        assert simulator.end_time is not None

    def test_campaign_summary_statistics(self):
        """Test campaign summary generation."""
        simulator = WorkflowSimulator()
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()[:10]

        simulator.execute_campaign(scenarios)
        summary = simulator.campaign_summary()

        assert summary["total_workflows"] == len(scenarios)
        assert "outcomes" in summary
        assert "violations" in summary
        assert summary["outcomes"]["safe"] + summary["outcomes"]["unsafe"] + summary["outcomes"]["degraded"] > 0

    def test_remediation_generation_idg01(self):
        """Test remediation recommendation generation for IDG-01."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_delayed_disclosure()

        result = simulator.execute_workflow(workflow)

        # Should have remediation for disclosure
        assert any("disclosure" in item.lower() for item in result.remediation_items)

    def test_remediation_generation_eit01(self):
        """Test remediation recommendation generation for EIT-01."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.member_escalation_ignored()

        result = simulator.execute_workflow(workflow)

        # Should have remediation for escalation
        assert any("escalation" in item.lower() for item in result.remediation_items)

    def test_export_results_json(self, tmp_path):
        """Test exporting results to JSON."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()
        simulator.execute_workflow(workflow)

        output_file = tmp_path / "results.json"
        simulator.export_results_json(str(output_file))

        assert output_file.exists()
        import json
        with open(output_file) as f:
            data = json.load(f)
        assert data["total_workflows"] == 1
        assert "workflows" in data
        assert "summary" in data

    def test_export_results_markdown(self, tmp_path):
        """Test exporting results to Markdown report."""
        simulator = WorkflowSimulator()
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()[:5]
        simulator.execute_campaign(scenarios)

        output_file = tmp_path / "report.md"
        simulator.export_results_markdown(str(output_file))

        assert output_file.exists()
        content = output_file.read_text()
        assert "Synthetic Workflow Safety Evaluation Report" in content
        assert "Campaign Summary" in content
        assert "Rule Coverage" in content

    def test_deterministic_workflow_execution(self):
        """Test that workflow execution is deterministic."""
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()

        simulator1 = WorkflowSimulator()
        result1 = simulator1.execute_workflow(workflow)

        simulator2 = WorkflowSimulator()
        result2 = simulator2.execute_workflow(workflow)

        # Same workflow should produce same violations
        assert result1.unique_violated_rules == result2.unique_violated_rules
        assert result1.workflow_outcome == result2.workflow_outcome

    def test_workflow_result_immutability(self):
        """Test that workflow execution results are immutable."""
        simulator = WorkflowSimulator()
        workflow = SyntheticScenarioBuilder.prior_auth_compliant()
        result = simulator.execute_workflow(workflow)

        # Should be frozen dataclass
        with pytest.raises((AttributeError, Exception)):
            result.workflow_outcome = WorkflowOutcome.UNSAFE

    def test_empty_campaign_summary(self):
        """Test campaign summary on empty campaign."""
        simulator = WorkflowSimulator()
        summary = simulator.campaign_summary()

        assert summary["total_workflows"] == 0
        assert summary["outcomes"]["safe"] == 0

    def test_multiple_violation_detection(self):
        """Test detection of multiple violations in single workflow."""
        simulator = WorkflowSimulator()
        scenarios = SyntheticScenarioGenerator.generate_all_scenarios()

        # Find scenario with multiple expected violations
        multi_violation_scenario = next(
            (s for s in scenarios if len(s.expected_violations) > 1),
            None
        )

        if multi_violation_scenario:
            result = simulator.execute_workflow(multi_violation_scenario)
            assert len(result.expected_violations) > 1

    def test_control_failure_tracking(self):
        """Test that control failures are properly tracked."""
        simulator = WorkflowSimulator()
        # Use a scenario where violation is marked as expected but not marked as detected
        # Create a synthetic scenario with expected violations but no detected_violations
        workflow = SyntheticScenarioBuilder.member_escalation_ignored()

        result = simulator.execute_workflow(workflow)

        # Escalation ignored should create control failures
        assert len(result.control_failures) > 0
        assert any("escalation" in item.lower() or "control" in item.lower() for item in result.control_failures)
