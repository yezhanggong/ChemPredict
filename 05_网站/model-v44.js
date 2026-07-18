(function () {
  'use strict';

  const artifact = window.CHEMPREDICT_ARTIFACT;
  const reactionSystems = window.CHEMPREDICT_REACTION_SYSTEMS || [];
  const termRows = window.CHEMPREDICT_TERMS || [];
  const termMap = Object.fromEntries(termRows.map((row) => [row.key, row]));
  const R_KCAL = 1.98720425864083e-3;
  const T_K = artifact.temperature_k_for_ee_transform || 298.15;

  const anchors = {
    solvent: 'SOLV-02',
    photocatalyst: 'PC-01',
    copper_source: 'CU-07',
    ligand: 'LIG-01',
    temperature: 'TEMP-01',
  };

  const text = {
    zh: {
      solvent: '溶剂', photocatalyst: '光催化剂', copper_source: '铜源', ligand: '手性配体', temperature: '温度',
      missing: '缺少描述符', unsupported: '不支持的模型算法',
      precursor: '前体必须是目标协议中的仲苄醇来源 NHP 醚。',
      radical: '自由基类别不属于训练域中的碳-芳基仲苄基自由基。',
      family: '反应路径与目标脱氧不对称氰化催化循环不一致。',
      multi: '同时改变的条件因素超过已验证上限。',
      incomplete: '描述符不完整',
      sparse: '样本位于训练域稀疏边界。',
      median: '距离高于训练域中位密度。',
      cyclicOverride: '该已知环状单例家族超过 q95；按预声明规则仅降级为 D 级边界参考。',
      fallback: '当前输入缺少预计算结构描述符，产率使用手工特征回退模型。',
      interval: '区间来自嵌套整组留出残差；只有家族 n≥4 且区间更窄时才采用家族校准，尚无独立前瞻覆盖保证。',
    },
    en: {
      solvent: 'Solvent', photocatalyst: 'Photocatalyst', copper_source: 'Copper source', ligand: 'Chiral ligand', temperature: 'Temperature',
      missing: 'Missing descriptor', unsupported: 'Unsupported model algorithm',
      precursor: 'The precursor must be a secondary benzylic NHP ether from the target protocol.',
      radical: 'The radical class is outside the carbon-aryl secondary-benzylic training domain.',
      family: 'The reaction pathway differs from the target deoxygenative asymmetric cyanation cycle.',
      multi: 'The number of simultaneous condition changes exceeds the validated limit.',
      incomplete: 'Incomplete descriptors',
      sparse: 'The sample lies in a sparse boundary region.',
      median: 'The distance is above the median training-domain density.',
      cyclicOverride: 'This known cyclic singleton exceeds q95 and is retained only as a predeclared grade-D boundary reference.',
      fallback: 'Precomputed structure descriptors are unavailable; yield uses the manual-feature fallback model.',
      interval: 'Intervals use nested grouped-holdout residuals. A family interval is used only at n≥4 when narrower; independent prospective coverage is unavailable.',
    },
  };

  function tr(lang, key) { return (text[lang] || text.zh)[key]; }
  function number(value) {
    if (value === '' || value === null || value === undefined) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  function clamp(value, low, high) { return Math.max(low, Math.min(high, value)); }

  function formatTerm(value, lang = 'zh') {
    const record = termMap[String(value)];
    if (!record) return String(value ?? '');
    if (lang === 'en') return record.en;
    if (record.key === 'none') return record.zh;
    return `${record.en}（${record.zh}）`;
  }

  function axisLabel(axis, lang = 'zh') { return tr(lang, axis); }
  function conditionLabel(record, axis, lang = 'zh') {
    if (axis === 'temperature') return `${record.temp_c} °C`;
    return formatTerm(record[axis], lang);
  }
  function conditionRows(axis) { return artifact.condition_screen.filter((row) => row.screen_axis === axis); }
  function conditionEvidence(recordId, lang = 'zh') {
    const record = artifact.condition_screen.find((row) => row.record_id === recordId);
    if (!record) return null;
    const axis = record.screen_axis;
    const anchor = artifact.condition_screen.find((row) => row.record_id === anchors[axis]);
    const y = number(record.yield_pct);
    const ee = number(record.ee_pct);
    const anchorYield = anchor ? number(anchor.yield_pct) : null;
    const anchorEe = anchor ? number(anchor.ee_pct) : null;
    return {
      record, axis, axisLabel: axisLabel(axis, lang), candidate: conditionLabel(record, axis, lang), yield: y, ee,
      deltaYield: y !== null && anchorYield !== null ? y - anchorYield : null,
      deltaEe: ee !== null && anchorEe !== null ? ee - anchorEe : null,
      anchor, isCensored: record.yield_status !== 'measured',
    };
  }

  function knownSubstrate(id) { return artifact.known_scope.find((row) => row.id === id) || null; }
  function virtualCandidates() { return artifact.virtual_candidates || []; }
  function systemById(id) { return reactionSystems.find((row) => row.system_id === id) || null; }
  function eeToDdg(eePct) {
    const ee = clamp(Number(eePct) / 100, -0.999999, 0.999999);
    return R_KCAL * T_K * Math.log((1 + ee) / (1 - ee));
  }
  function inverseTarget(model, value) {
    if (model.target_transform === 'ee_to_ddg_kcal_mol') {
      const ratio = Math.exp(value / (R_KCAL * T_K));
      return clamp(100 * (ratio - 1) / (ratio + 1), 0, 100);
    }
    if (model.target_transform === 'yield_logit') {
      const probability = 1 / (1 + Math.exp(-value));
      return clamp(101 * probability - 0.5, 0, 100);
    }
    return clamp(value, 0, 100);
  }
  function hasFeatures(features, names) { return names.every((name) => Number.isFinite(Number(features[name]))); }
  function featureVector(features, names, lang = 'zh') {
    return names.map((name) => {
      const value = Number(features[name]);
      if (!Number.isFinite(value)) throw new Error(`${tr(lang, 'missing')}: ${name}`);
      return value;
    });
  }

  function xgboostNodeValue(node, vector, featureNames) {
    if (Object.prototype.hasOwnProperty.call(node, 'leaf')) return Number(node.leaf);
    const split = String(node.split);
    const index = /^f\d+$/.test(split) ? Number(split.slice(1)) : featureNames.indexOf(split);
    if (index < 0) throw new Error(`Unknown XGBoost split feature: ${split}`);
    const value = Number(vector[index]);
    const nextId = Number.isFinite(value)
      ? (value < Number(node.split_condition) ? Number(node.yes) : Number(node.no))
      : Number(node.missing);
    const child = (node.children || []).find((item) => Number(item.nodeid) === nextId);
    if (!child) throw new Error(`Missing XGBoost child node ${nextId}`);
    return xgboostNodeValue(child, vector, featureNames);
  }

  function modelPrediction(model, features, lang = 'zh') {
    const vector = featureVector(features, model.features, lang);
    if (model.algorithm === 'xgboost') {
      const transformed = Number(model.base_score) + model.trees.reduce(
        (sum, tree) => sum + xgboostNodeValue(tree, vector, model.features), 0,
      );
      return inverseTarget(model, transformed);
    }
    const scaled = vector.map((value, index) => (value - model.mean[index]) / model.scale[index]);
    if (model.algorithm === 'ridge') {
      const transformed = model.intercept + scaled.reduce(
        (sum, value, index) => sum + value * model.coefficients[index], 0,
      );
      return inverseTarget(model, transformed);
    }
    if (model.algorithm === 'knn') {
      const distances = model.training_x_scaled.map((row, rowIndex) => ({
        rowIndex,
        distance: Math.sqrt(row.reduce((sum, value, index) => sum + ((value - scaled[index]) ** 2), 0) / row.length),
      })).sort((a, b) => a.distance - b.distance);
      const selected = distances.slice(0, Math.min(Number(model.parameter), distances.length));
      let weighted = 0; let totalWeight = 0;
      selected.forEach(({ rowIndex, distance }) => {
        const weight = 1 / Math.max(distance, 0.05);
        weighted += weight * model.training_y[rowIndex]; totalWeight += weight;
      });
      const value = weighted / totalWeight;
      return model.knn_uses_target_transform ? inverseTarget(model, value) : clamp(value, 0, 100);
    }
    if (model.algorithm === 'rbf_kernel_ridge') {
      const transformed = model.intercept + model.training_x_scaled.reduce((sum, row, rowIndex) => {
        const squared = row.reduce((total, value, index) => total + ((value - scaled[index]) ** 2), 0) / row.length;
        return sum + (Math.exp(-Number(model.gamma) * squared) * model.dual_coefficients[rowIndex]);
      }, 0);
      return inverseTarget(model, transformed);
    }
    throw new Error(`${tr(lang, 'unsupported')}: ${model.algorithm}`);
  }

  function chooseModel(target, features) {
    const primary = artifact.models[target];
    if (hasFeatures(features, primary.features)) return { model: primary, source: 'production_primary' };
    const fallback = artifact.fallback_models && artifact.fallback_models[target];
    if (fallback && hasFeatures(features, fallback.features)) return { model: fallback, source: 'manual_fallback' };
    throw new Error(`${target}: missing model features`);
  }
  function applicabilityDistance(features, lang = 'zh') {
    const domain = artifact.applicability;
    const vector = featureVector(features, domain.features, lang);
    const scaled = vector.map((value, index) => (value - domain.mean[index]) / domain.scale[index]);
    return Math.min(...domain.training_x.map((row) => {
      const rowScaled = row.map((value, index) => (value - domain.mean[index]) / domain.scale[index]);
      return Math.sqrt(rowScaled.reduce((sum, value, index) => sum + ((value - scaled[index]) ** 2), 0) / rowScaled.length);
    }));
  }
  function highRiskMatch(features, rule) {
    return Object.entries(rule.minimum || {}).every(([name, minimum]) => Number(features[name]) >= Number(minimum))
      && Object.entries(rule.maximum || {}).every(([name, maximum]) => Number(features[name]) <= Number(maximum));
  }

  function gateCheck(input, lang = 'zh') {
    const domain = artifact.applicability;
    const config = domain.gate_config;
    const reasons = [];
    const ruleIds = [];
    const intervalFloor = {};
    let warningGrade = null;
    let overrideDistanceRefusal = false;
    if (!config.allowed_precursor_types.includes(input.precursorType)) reasons.push(tr(lang, 'precursor'));
    if (!config.allowed_radical_classes.includes(input.radicalClass)) reasons.push(tr(lang, 'radical'));
    if (!config.allowed_reaction_families.includes(input.reactionFamily)) reasons.push(tr(lang, 'family'));
    const changes = [...new Set((input.conditionChanges || []).filter(Boolean))];
    if (changes.length > Number(config.max_condition_changes)) reasons.push(tr(lang, 'multi'));
    if (reasons.length) return { status: 'REFUSE', grade: 'R', reasons, ruleIds, intervalFloor, distance: null };

    for (const rule of config.high_risk_rules || []) {
      if (!highRiskMatch(input.features, rule)) continue;
      const message = lang === 'en' ? (rule.message_en || rule.message) : (rule.message_zh || rule.message);
      if (rule.action === 'REFUSE') return { status: 'REFUSE', grade: 'R', reasons: [message], ruleIds: [rule.id], intervalFloor, distance: null };
      reasons.push(message); ruleIds.push(rule.id); warningGrade = rule.grade || 'D';
      overrideDistanceRefusal = overrideDistanceRefusal || Boolean(rule.override_distance_refusal);
      Object.assign(intervalFloor, rule.interval_floor || {});
    }

    let distance;
    try { distance = applicabilityDistance(input.features, lang); }
    catch (error) { return { status: 'REFUSE', grade: 'R', reasons: [`${tr(lang, 'incomplete')}: ${error.message}`], ruleIds, intervalFloor, distance: null }; }
    const thresholds = config.distance_thresholds;
    if (distance > thresholds.q95_refuse) {
      if (overrideDistanceRefusal) return { status: 'WARN', grade: 'D', distance, reasons: [...reasons, tr(lang, 'cyclicOverride')], ruleIds, intervalFloor };
      return { status: 'REFUSE', grade: 'R', distance, reasons: [...reasons, `q95: ${distance.toFixed(3)} > ${Number(thresholds.q95_refuse).toFixed(3)}`], ruleIds, intervalFloor };
    }
    if (distance > thresholds.q90_warn) return { status: 'WARN', grade: 'D', distance, reasons: [...reasons, tr(lang, 'sparse')], ruleIds, intervalFloor };
    if (distance > thresholds.q50_typical) return { status: 'WARN', grade: warningGrade === 'D' ? 'D' : 'C', distance, reasons: [...reasons, tr(lang, 'median')], ruleIds, intervalFloor };
    if (ruleIds.length) return { status: 'WARN', grade: warningGrade || 'D', distance, reasons, ruleIds, intervalFloor };
    return { status: 'ACCEPT', grade: 'B', distance, reasons, ruleIds, intervalFloor };
  }

  function calibratedInterval(model, point, scopeGroup) {
    const calibration = model.cross_conformal || {};
    const globalWidth = Number(calibration.half_width);
    const group = calibration.group_calibration && calibration.group_calibration[scopeGroup];
    const selectedWidth = group ? Number(group.selected_half_width) : globalWidth;
    const source = group ? group.source : 'global_fallback';
    const empiricalWidth = Number(calibration.empirical_q80_half_width || globalWidth);
    return {
      point,
      low: clamp(point - selectedWidth, 0, 100), high: clamp(point + selectedWidth, 0, 100),
      selectedWidth, source, groupN: group ? Number(group.n) : 0,
      globalLow: clamp(point - globalWidth, 0, 100), globalHigh: clamp(point + globalWidth, 0, 100), globalWidth,
      empiricalLow: clamp(point - empiricalWidth, 0, 100), empiricalHigh: clamp(point + empiricalWidth, 0, 100), empiricalWidth,
    };
  }

  function predictCustom(input, lang = 'zh') {
    const system = systemById(input.systemId || 'nhp_deoxygenative_asymmetric_cyanation');
    if (!system || system.status !== 'quantitative') {
      return { status: 'SYSTEM_EVIDENCE_ONLY', grade: 'R', reasons: [system ? system[`boundary_${lang}`] : tr(lang, 'family')], system };
    }
    const gate = gateCheck(input, lang);
    if (gate.status === 'REFUSE') return gate;
    let yChoice; let eeChoice;
    try { yChoice = chooseModel('yield', input.features); eeChoice = chooseModel('ee', input.features); }
    catch (error) { return { status: 'REFUSE', grade: 'R', reasons: [error.message], distance: gate.distance }; }
    const yPoint = modelPrediction(yChoice.model, input.features, lang);
    const eePoint = modelPrediction(eeChoice.model, input.features, lang);
    const yInterval = calibratedInterval(yChoice.model, yPoint, input.scopeGroup);
    const eeInterval = calibratedInterval(eeChoice.model, eePoint, input.scopeGroup);
    if (Number.isFinite(Number(gate.intervalFloor.ee))) eeInterval.low = Math.min(eeInterval.low, Number(gate.intervalFloor.ee));
    const warnings = [...gate.reasons];
    if (yChoice.source === 'manual_fallback') warnings.push(tr(lang, 'fallback'));
    return {
      status: 'PREDICT', gateStatus: gate.status, grade: gate.grade, distance: gate.distance,
      distanceThreshold: artifact.applicability.gate_config.distance_thresholds.q95_refuse,
      scopeGroup: input.scopeGroup || 'unassigned', ruleIds: gate.ruleIds, yield: { ...yInterval, modelSource: yChoice.source },
      ee: { ...eeInterval, modelSource: eeChoice.source }, warnings,
      modelDetails: {
        yield: `${yChoice.model.algorithm}/${yChoice.model.feature_set} · v${yChoice.model.model_origin_version || artifact.model_version}`,
        ee: `${eeChoice.model.algorithm}/${eeChoice.model.feature_set} · v${eeChoice.model.model_origin_version || artifact.model_version}`,
      },
      intervalNote: tr(lang, 'interval'), productionVersions: artifact.production_model_version_by_target,
    };
  }

  window.ChemPredictModel = {
    artifact, reactionSystems, termRows, axisLabel, formatTerm, conditionRows, conditionLabel, conditionEvidence,
    knownSubstrate, virtualCandidates, systemById, eeToDdg, gateCheck, predictCustom, modelPrediction,
  };
}());
