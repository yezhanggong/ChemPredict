from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_模型源码" / "model"))

from predict_v44 import model_prediction, predict  # noqa: E402


class InferenceParityTests(unittest.TestCase):
    def test_python_and_javascript_match_for_virtual_candidate(self):
        artifact_path = ROOT / "04_模型源码" / "model" / "artifacts" / "model_artifact_v44.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        candidate = pd.read_csv(ROOT / "03_数据" / "整理数据" / "virtual_candidate_library.csv").iloc[0].to_dict()
        python_result = predict(
            artifact,
            {
                "features": candidate,
                "precursor_type": "secondary_benzylic_nhp_ether",
                "radical_class": "carbon_aryl_benzylic",
                "reaction_family": "nhp_ether_deoxygenative_asymmetric_cyanation",
                "condition_changes": [],
                "scope_group": "alkyl_series",
            },
        )
        node = os.environ.get("NODE_EXE") or shutil.which("node")
        if not node:
            self.skipTest("Node.js not available")
        output = subprocess.check_output(
            [
                node,
                str(ROOT / "07_验证结果" / "browser" / "js-inference-json.cjs"),
                str(ROOT / "05_网站" / "assets" / "registries.js"),
                str(ROOT / "05_网站" / "assets" / "model_artifact.js"),
                str(ROOT / "05_网站" / "model-v44.js"),
                "V01",
            ],
            text=True,
            encoding="utf-8",
        )
        javascript_result = json.loads(output)
        self.assertEqual(python_result["status"], javascript_result["gateStatus"])
        self.assertAlmostEqual(
            python_result["targets"]["yield"]["point"], javascript_result["yield"]["point"], places=10
        )
        self.assertAlmostEqual(
            python_result["targets"]["ee"]["point"], javascript_result["ee"]["point"], places=10
        )

    def test_xgboost_challenger_serialization_matches_javascript(self):
        artifact_path = (
            ROOT / "04_模型源码" / "model" / "artifacts" / "model_artifact_v44_manual_policy_audit.json"
        )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["models"]["ee"]["algorithm"], "xgboost")
        record = dict(next(row for row in artifact["known_scope"] if row["id"] == "2m"))
        record["hammett_sigma_mp_x_para_sub_count"] = (
            float(record["hammett_sigma_mp"]) * float(record["para_sub_count"])
        )
        python_value = model_prediction(
            artifact["models"]["ee"], record, float(artifact["temperature_k_for_ee_transform"])
        )
        node = os.environ.get("NODE_EXE") or shutil.which("node")
        if not node:
            self.skipTest("Node.js not available")
        output = subprocess.check_output(
            [
                node,
                str(ROOT / "07_验证结果" / "browser" / "xgb-inference-json.cjs"),
                str(artifact_path),
                str(ROOT / "05_网站" / "assets" / "registries.js"),
                str(ROOT / "05_网站" / "model-v44.js"),
                "ee",
                "2m",
            ],
            text=True,
            encoding="utf-8",
        )
        javascript_value = json.loads(output)["prediction"]
        self.assertAlmostEqual(python_value, javascript_value, places=10)


if __name__ == "__main__":
    unittest.main()
