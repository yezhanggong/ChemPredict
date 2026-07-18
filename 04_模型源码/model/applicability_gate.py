"""Authoritative applicability gate for ChemPredict v4.4 inference."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GateResult:
    status: str
    reasons: tuple[str, ...]
    distance: float | None
    grade: str
    rule_ids: tuple[str, ...] = ()
    interval_floor: Mapping[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        value["rule_ids"] = list(self.rule_ids)
        return value


def standardized_nearest_distance(
    input_features: Mapping[str, float], applicability: Mapping[str, Any]
) -> float:
    names = applicability["features"]
    mean = applicability["mean"]
    scale = applicability["scale"]
    training_x = applicability["training_x"]
    vector = []
    for name in names:
        if name not in input_features:
            raise ValueError(f"missing applicability feature: {name}")
        value = float(input_features[name])
        if not math.isfinite(value):
            raise ValueError(f"non-finite applicability feature: {name}")
        vector.append(value)
    scaled = [(value - center) / width for value, center, width in zip(vector, mean, scale, strict=True)]
    distances = []
    for row in training_x:
        row_scaled = [
            (value - center) / width
            for value, center, width in zip(row, mean, scale, strict=True)
        ]
        distances.append(
            math.sqrt(sum((left - right) ** 2 for left, right in zip(scaled, row_scaled, strict=True)) / len(scaled))
        )
    return min(distances)


def _high_risk_match(features: Mapping[str, float], rule: Mapping[str, Any]) -> bool:
    for name, minimum in rule.get("minimum", {}).items():
        if float(features.get(name, float("-inf"))) < float(minimum):
            return False
    for name, maximum in rule.get("maximum", {}).items():
        if float(features.get(name, float("inf"))) > float(maximum):
            return False
    return True


def gate_check(
    input_features: Mapping[str, float],
    precursor_type: str,
    radical_class: str,
    condition_changes: Sequence[str],
    *,
    gate_config: Mapping[str, Any],
    applicability: Mapping[str, Any],
    reaction_family: str = "nhp_ether_deoxygenative_asymmetric_cyanation",
) -> GateResult:
    """Apply mechanism, protocol, high-risk-subdomain and distance gates."""
    reasons: list[str] = []
    matched_rule_ids: list[str] = []
    interval_floor: dict[str, float] = {}
    warning_grade: str | None = None
    override_distance_refusal = False
    if precursor_type not in gate_config["allowed_precursor_types"]:
        reasons.append("前体必须是目标协议中的仲苄醇来源 N-烷氧基邻苯二甲酰亚胺（NHP 醚）。")
    if radical_class not in gate_config["allowed_radical_classes"]:
        reasons.append("自由基类别不属于训练域中的碳-芳基仲苄基自由基。")
    if reaction_family not in gate_config["allowed_reaction_families"]:
        reasons.append("反应路径与目标脱氧不对称氰化催化循环不一致。")
    distinct_changes = sorted({str(value).strip() for value in condition_changes if str(value).strip()})
    if len(distinct_changes) > int(gate_config["max_condition_changes"]):
        reasons.append(
            f"同时改变 {len(distinct_changes)} 个条件因素，超过已验证上限 {gate_config['max_condition_changes']}。"
        )
    if reasons:
        return GateResult("REFUSE", tuple(reasons), None, "R")

    for rule in gate_config.get("high_risk_rules", []):
        if _high_risk_match(input_features, rule):
            action = rule.get("action", "WARN")
            message = str(rule.get("message", rule.get("id", "high-risk subdomain")))
            rule_id = str(rule.get("id", "high-risk subdomain"))
            if action == "REFUSE":
                return GateResult("REFUSE", (message,), None, "R", (rule_id,))
            reasons.append(message)
            matched_rule_ids.append(rule_id)
            warning_grade = str(rule.get("grade", warning_grade or "D"))
            override_distance_refusal = override_distance_refusal or bool(rule.get("override_distance_refusal", False))
            interval_floor.update({key: float(value) for key, value in rule.get("interval_floor", {}).items()})

    try:
        distance = standardized_nearest_distance(input_features, applicability)
    except (KeyError, TypeError, ValueError) as exc:
        return GateResult("REFUSE", (f"描述符不完整：{exc}",), None, "R", tuple(matched_rule_ids), interval_floor)
    thresholds = gate_config["distance_thresholds"]
    if distance > float(thresholds["q95_refuse"]):
        if override_distance_refusal:
            reasons.append(
                f"最近邻距离 {distance:.3f} 超过 q95，但该已知单例家族按预声明规则降级为 D 级而不硬拒绝。"
            )
            return GateResult(
                "WARN", tuple(reasons), distance, "D", tuple(matched_rule_ids), interval_floor
            )
        return GateResult(
            "REFUSE",
            tuple(reasons + [f"最近邻标准化距离 {distance:.3f} 超过拒绝阈值 {thresholds['q95_refuse']:.3f}。"]),
            distance,
            "R",
            tuple(matched_rule_ids),
            interval_floor,
        )
    if distance > float(thresholds["q90_warn"]):
        reasons.append(f"距离 {distance:.3f} 位于稀疏边界区，输出仅可用于低优先级排序。")
        return GateResult("WARN", tuple(reasons), distance, "D", tuple(matched_rule_ids), interval_floor)
    if distance > float(thresholds["q50_typical"]):
        reasons.append("距离高于训练域中位密度，需安排前瞻验证。")
        grade = "D" if warning_grade == "D" else "C"
        return GateResult("WARN", tuple(reasons), distance, grade, tuple(matched_rule_ids), interval_floor)
    if matched_rule_ids:
        return GateResult(
            "WARN", tuple(reasons), distance, warning_grade or "D", tuple(matched_rule_ids), interval_floor
        )
    return GateResult("ACCEPT", tuple(reasons), distance, "B")
