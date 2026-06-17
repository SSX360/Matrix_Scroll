import unittest

from qa import release_evidence


def fake_report(workspace: str, *, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "workspace_kind": workspace,
        "duration_ms": 123,
        "gates": [
            {"name": "chat_offline_project_answer", "passed": passed},
            {"name": "redacted_diagnostics", "passed": passed},
            {"name": "launch_readiness_static_validation", "passed": passed},
            {"name": "project_secret_redaction", "passed": passed},
            {"name": "no_stale_workspace_leak", "passed": True},
        ],
    }


def fake_supply_chain(*, inventory_ready: bool = True) -> dict:
    return {
        "status": "inventory_ready" if inventory_ready else "review",
        "inventory_ready": inventory_ready,
        "component_count": 12,
        "manifest_count": 2,
        "warning_count": 1,
        "field_evidence_needed": [
            "Dependency vulnerability review",
            "Signed installer provenance",
            "Release artifact attestation",
        ],
    }


class ReleaseEvidenceTests(unittest.TestCase):
    def test_summarize_gate_reports_calculates_rates(self):
        summary = release_evidence.summarize_gate_reports(
            {
                "empty": fake_report("empty"),
                "python": fake_report("python"),
                "notebook": fake_report("notebook", passed=False),
            }
        )

        self.assertEqual(summary["workspace_count"], 3)
        self.assertEqual(summary["workspace_pass_count"], 2)
        self.assertEqual(summary["fresh_project_qa_pass_rate"], 66.7)
        self.assertEqual(summary["degraded_chat_success_rate"], 66.7)
        self.assertEqual(summary["diagnostics_redaction_rate"], 66.7)
        self.assertEqual(summary["launch_readiness_validation_rate"], 66.7)
        self.assertEqual(summary["project_secret_redaction_rate"], 66.7)
        self.assertEqual(summary["stale_workspace_leak_count"], 0)

    def test_build_kpis_marks_local_passes_and_field_data_gaps(self):
        kpis = release_evidence.build_kpis(
            {
                "fresh_project_qa_pass_rate": 100.0,
                "degraded_chat_success_rate": 100.0,
                "diagnostics_redaction_rate": 100.0,
                "launch_readiness_validation_rate": 100.0,
                "project_secret_redaction_rate": 100.0,
                "stale_workspace_leak_count": 0,
            },
            fake_supply_chain(),
        )

        statuses = {item["id"]: item["status"] for item in kpis}
        self.assertEqual(statuses["fresh_project_qa_pass_rate"], "pass")
        self.assertEqual(statuses["chat_degraded_mode_success"], "pass")
        self.assertEqual(statuses["diagnostics_redaction"], "pass")
        self.assertEqual(statuses["launch_readiness_validation"], "pass")
        self.assertEqual(statuses["project_secret_redaction"], "pass")
        self.assertEqual(statuses["stale_workspace_leaks"], "pass")
        self.assertEqual(statuses["supply_chain_inventory"], "pass")
        self.assertEqual(statuses["install_success_rate"], "needs_field_data")
        self.assertEqual(statuses["first_week_retention"], "needs_field_data")

    def test_release_decision_separates_software_and_device_readiness(self):
        kpis = release_evidence.build_kpis(
            {
                "fresh_project_qa_pass_rate": 100.0,
                "degraded_chat_success_rate": 100.0,
                "diagnostics_redaction_rate": 100.0,
                "launch_readiness_validation_rate": 100.0,
                "project_secret_redaction_rate": 100.0,
                "stale_workspace_leak_count": 0,
            }
        )

        decision = release_evidence.release_decision(
            [{"name": "unit_tests", "passed": True}],
            {"empty": fake_report("empty")},
            kpis,
            fake_supply_chain(),
        )

        self.assertTrue(decision["software_release_candidate"])
        self.assertFalse(decision["device_gtm_ready"])
        self.assertIn("Install success rate", decision["field_evidence_needed"])
        self.assertIn("Signed installer provenance", decision["field_evidence_needed"])

    def test_build_experiment_matrix_adds_local_pros_cons(self):
        experiments = release_evidence.build_experiment_matrix(
            {
                "empty": fake_report("empty"),
                "python": fake_report("python"),
                "typescript": fake_report("typescript"),
                "monorepo": fake_report("monorepo"),
                "notebook": fake_report("notebook"),
                "security": fake_report("security"),
            }
        )

        by_workspace = {item["workspace"]: item for item in experiments}
        self.assertEqual(by_workspace["empty"]["build_style"], "first-run/offline-first")
        self.assertIn("pros", by_workspace["python"])
        self.assertEqual(by_workspace["typescript"]["build_style"], "modern web app")
        self.assertEqual(by_workspace["monorepo"]["build_style"], "multi-service repo")
        self.assertTrue(by_workspace["notebook"]["optimization"])
        self.assertEqual(by_workspace["security"]["build_style"], "secret-redaction and local-trust workflow")
        self.assertIn("redacted_diagnostics", by_workspace["empty"]["validated_gates"])

    def test_summary_markdown_contains_kpi_table(self):
        manifest = {
            "run_id": "release-evidence-test",
            "generated_at": "2026-06-17T00:00:00Z",
            "release_decision": {
                "software_release_candidate": True,
                "device_gtm_ready": False,
                "blockers": [],
                "field_evidence_needed": ["Install success rate"],
            },
            "commands": [{"name": "unit_tests", "passed": True, "duration_ms": 1}],
            "qa_reports": {"empty": fake_report("empty")},
            "supply_chain": fake_supply_chain(),
            "local_experiments": [
                {
                    "scenario": "Brand-new empty project",
                    "build_style": "first-run/offline-first",
                    "passed": True,
                    "optimization": "keep first-run prompts visible",
                }
            ],
            "kpis": [
                {
                    "label": "Fresh-project QA pass rate",
                    "target": ">=95%",
                    "actual": "100.0%",
                    "status": "pass",
                }
            ],
        }

        markdown = release_evidence.build_summary_markdown(manifest)

        self.assertIn("# Digital Rain Release Evidence", markdown)
        self.assertIn("| Fresh-project QA pass rate | >=95% | 100.0% | pass |", markdown)
        self.assertIn("Supply Chain Evidence", markdown)
        self.assertIn("| SBOM/dependency inventory | inventory_ready | 12 components |", markdown)
        self.assertIn("Local Experiment Matrix", markdown)
        self.assertIn("Install success rate", markdown)


if __name__ == "__main__":
    unittest.main()
