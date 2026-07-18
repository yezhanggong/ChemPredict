from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_模型源码" / "model"))

from applicability_gate import gate_check  # noqa: E402


class ApplicabilityGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        artifact_path = ROOT / "04_模型源码" / "model" / "artifacts" / "model_artifact_v44.json"
        cls.artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        cls.applicability = cls.artifact["applicability"]
        cls.config = cls.applicability["gate_config"]
        scope = pd.read_csv(ROOT / "03_数据" / "整理数据" / "substrate_scope.csv")
        cls.control = scope[scope["id"] == "2d"].iloc[0].to_dict()

    def check(self, **overrides):
        values = {
            "input_features": self.control,
            "precursor_type": "secondary_benzylic_nhp_ether",
            "radical_class": "carbon_aryl_benzylic",
            "condition_changes": [],
            "reaction_family": "nhp_ether_deoxygenative_asymmetric_cyanation",
        }
        values.update(overrides)
        return gate_check(
            values["input_features"],
            values["precursor_type"],
            values["radical_class"],
            values["condition_changes"],
            reaction_family=values["reaction_family"],
            gate_config=self.config,
            applicability=self.applicability,
        )

    def test_valid_in_domain_control_is_accepted(self):
        result = self.check()
        self.assertEqual(result.status, "ACCEPT")
        self.assertAlmostEqual(result.distance or 0.0, 0.0, places=12)

    def test_non_nhp_precursor_is_refused(self):
        self.assertEqual(self.check(precursor_type="alkyl_arene").status, "REFUSE")

    def test_non_benzylic_radical_is_refused(self):
        self.assertEqual(self.check(radical_class="allylic").status, "REFUSE")

    def test_wrong_reaction_family_is_refused(self):
        self.assertEqual(self.check(reaction_family="c_h_radical_relay_asymmetric_cyanation").status, "REFUSE")

    def test_multiple_condition_changes_are_refused(self):
        self.assertEqual(self.check(condition_changes=["solvent", "ligand"]).status, "REFUSE")

    def test_strong_para_ewg_subdomain_warns_and_expands_interval(self):
        features = dict(self.control)
        features.update({"hammett_sigma_mp": 0.66, "para_sub_count": 1})
        result = self.check(input_features=features)
        self.assertEqual(result.status, "WARN")
        self.assertEqual(result.grade, "D")
        self.assertEqual(result.interval_floor, {"ee": 35.0})
        self.assertIn("strong_para_ewg_low_ee_warning", result.rule_ids)

    def test_cyclic_singleton_is_grade_d_instead_of_distance_refusal(self):
        features = dict(self.control)
        features.update({"cyclic_center": 1, "alpha_chain_carbons": 20})
        result = self.check(input_features=features)
        self.assertEqual(result.status, "WARN")
        self.assertEqual(result.grade, "D")
        self.assertIn("cyclic_benzylic_singleton_warning", result.rule_ids)

    def test_large_descriptor_distance_is_refused(self):
        features = dict(self.control)
        features["alpha_chain_carbons"] = 20
        self.assertEqual(self.check(input_features=features).status, "REFUSE")

    def test_external_gate_fixture(self):
        cases = pd.read_csv(ROOT / "03_数据" / "整理数据" / "external_gate_cases.csv").fillna("")
        for row in cases.to_dict(orient="records"):
            with self.subTest(case=row["case_id"]):
                changes = [value for value in str(row["condition_changes"]).split("|") if value]
                result = self.check(
                    precursor_type=row["precursor_type"],
                    radical_class=row["radical_class"],
                    reaction_family=row["reaction_family"],
                    condition_changes=changes,
                )
                self.assertEqual(result.status, row["expected_decision"])


if __name__ == "__main__":
    unittest.main()
