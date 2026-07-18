(function () {
  'use strict';

  const model = window.ChemPredictModel;
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  let lang = localStorage.getItem('chempredict-v44-language') === 'en' ? 'en' : 'zh';
  let plan = loadPlan();
  let currentCondition = null;
  let currentLiterature = null;
  let currentVirtual = null;
  let currentCustom = null;

  const i18n = {
    zh: {
      subtitle: '多反应体系证据与预测工作台', offline: '完全离线', reactionSystem: '反应体系', workspace: '预测工作台', systemEvidence: '体系证据', audit: '模型审计', planner: '实验计划',
      activeModel: '当前定量模型', targetTitle: 'NHP 醚脱氧不对称氰化', championBadge: 'v4.3 生产冠军 + v4.4 门控', conditionMode: '条件证据', literatureMode: '文献复现', virtualMode: '候选库', customMode: '新底物估计',
      screenAxis: '筛选维度', candidateCondition: '候选条件', readEvidence: '读取实验结果', addPlan: '加入计划', conditionBoundary: '只返回论文实测的一次单因素变化；不学习任意溶剂/催化剂组合。',
      sameAxisRanking: '同维度证据排序', censorNote: 'trace/n.d. 保留为删失结果', candidate: '候选', yield: '产率', deltaAnchor: '相对锚点', source: '来源', paperSubstrate: '论文底物', readObservation: '读取原始观测',
      precomputedCandidate: '预计算候选', screenCandidate: '读取候选结果', virtualNote: '候选结构描述符已离线预计算；结果是排序依据，不是实验保证。', precursor: '前体类型', radical: '自由基类型', arylTemplate: '芳基模板', substituent: '芳环取代', sidechain: '另一取代基', familyAssignment: '校准家族',
      advancedDescriptors: '高级描述符', orthoCount: '邻位数', metaCount: '间位数', paraCount: '对位数', halogenCount: '卤素数', edgCount: '给电子基数', ewgCount: '吸电子基数', polarCount: '侧链极性基数', calculate: '检查适用域并计算', customNote: '结果按家族/全局区间分层显示；只有同体系固定协议可输出数值。',
      transferGuard: '跨体系迁移防护', registeredSystems: '已注册反应体系', oneQuantitative: '1 个定量体系', traceability: '可追溯性', validationTitle: '验证、晋级与描述符语义', promotionTitle: '冠军-挑战者决策', openTools: '开源工具状态', validationDesign: '验证设计', modelFeatures: '生产模型特征', auditWarning: '尚无独立前瞻盲测。内部区间只能辅助排序，不能替代实验重复、风险评估或放大决策。',
      prospective: '前瞻检验', planTitle: '实验计划与盲测记录', exportCsv: '导出 CSV', clear: '清空', safety: 'TMSCN（三甲基氰硅烷）及氰化物具有急性毒性；工具不替代机构 SOP、导师审批、通风监测和废物处置要求。', subject: '底物/用途', condition: '条件', expected: '预期', evidenceLevel: '证据级别', emptyPlan: '尚未加入候选。', footerClaim: 'ChemPredict v4.4 · 证据检索与候选排序，不是实验保证', auditDate: '审计日期：2026-07-18',
      quantitative: '定量预测', evidence_only: '仅证据', refusal_only: '仅拒绝验证', doi: '文献 DOI', boundary: '适用边界', reactionClass: '反应类别', records: '定量记录', openDoi: '打开 DOI',
      measured: '论文观测', censored: '删失/定性观测', isolatedYield: '分离产率', enantiomericExcess: '对映体过量', notReported: '未报告', relativeAnchor: '相对匹配锚点', fullCombination: '完整组合', setup: '反应设置', sourcePage: '来源页', noFakeNumber: '原文未给出 trace/n.d. 的数值检测限，本工具不换算为伪点值。',
      fixedProtocol: '固定优化协议', originalObservation: 'A级：原始观测', radicalClass: '自由基类别', smiles: '人工核对 SMILES', dataRole: '数据角色', trainingDomain: '训练域样本', challengeOnly: '跨类型挑战样本；仅查表', originalEnglishName: '原文英文名',
      prediction: '模型估计，不是论文实测', refuse: '拒绝预测', noPoint: '未输出点预测。', gradeDomain: '级适用域', yieldInterval: '产率筛选区间', eeInterval: 'ee 经验区间', centre: '中心', selectedInterval: '所用区间', globalInterval: '全局区间', empiricalInterval: '经验 q80 区间', intervalSource: '区间来源', group: '校准家族', distance: '最近邻距离', yieldModel: '产率模型', eeModel: 'ee 模型', intervalMeaning: '区间含义', globalFallback: '全局回退', groupCalibration: '家族校准',
      productionModel: '生产模型', challengerModel: 'v4.4 挑战者', retained: '保留冠军', promoted: '挑战者晋级', target: '目标', championMae: '冠军嵌套 MAE', challengerMae: '挑战者嵌套 MAE', decision: '决策',
      trainingRows: '训练底物', conditionRows: '条件证据', yieldMae: '生产产率嵌套 MAE', eeMae: '生产 ee 嵌套 MAE', allScope: '2a–2z，同协议 26 条', evidenceRows: '论文单因素与对照记录', targetTransform: 'ee 先变换为 ΔΔG‡', groupedHoldout: '10 个化学家族整组留出', noExternal: '无独立外部盲测',
      integratedResearch: '已集成；研究性挑战者', notPromoted: '未晋级生产', productionUsed: '生产使用', remove: '删除', planEvidenceA: 'A级论文观测', modelEstimate: '模型估计', fixedCondition: '固定条件',
    },
    en: {
      subtitle: 'Multi-system evidence and prediction workbench', offline: 'Fully offline', reactionSystem: 'Reaction system', workspace: 'Prediction workspace', systemEvidence: 'System evidence', audit: 'Model audit', planner: 'Experiment plan',
      activeModel: 'Active quantitative model', targetTitle: 'NHP-ether deoxygenative asymmetric cyanation', championBadge: 'v4.3 production champion + v4.4 gate', conditionMode: 'Condition evidence', literatureMode: 'Literature lookup', virtualMode: 'Candidate library', customMode: 'New-substrate estimate',
      screenAxis: 'Screening axis', candidateCondition: 'Candidate condition', readEvidence: 'Read experiment', addPlan: 'Add to plan', conditionBoundary: 'Returns one-factor literature observations only; arbitrary solvent/catalyst combinations are not learned.',
      sameAxisRanking: 'Evidence ranking within axis', censorNote: 'trace/n.d. remain censored', candidate: 'Candidate', yield: 'Yield', deltaAnchor: 'Delta vs anchor', source: 'Source', paperSubstrate: 'Paper substrate', readObservation: 'Read observation',
      precomputedCandidate: 'Precomputed candidate', screenCandidate: 'Read candidate result', virtualNote: 'Structure descriptors are precomputed offline. Results rank candidates and do not guarantee experiments.', precursor: 'Precursor type', radical: 'Radical class', arylTemplate: 'Aryl template', substituent: 'Aryl substituent', sidechain: 'Other substituent', familyAssignment: 'Calibration family',
      advancedDescriptors: 'Advanced descriptors', orthoCount: 'Ortho count', metaCount: 'Meta count', paraCount: 'Para count', halogenCount: 'Halogen count', edgCount: 'EDG count', ewgCount: 'EWG count', polarCount: 'Side-chain polar count', calculate: 'Check domain and calculate', customNote: 'Family/global intervals are shown separately; numerical output is limited to the fixed protocol in the same system.',
      transferGuard: 'Cross-system transfer guard', registeredSystems: 'Registered reaction systems', oneQuantitative: '1 quantitative system', traceability: 'Traceability', validationTitle: 'Validation, promotion, and descriptor semantics', promotionTitle: 'Champion-challenger decision', openTools: 'Open-source tool status', validationDesign: 'Validation design', modelFeatures: 'Production-model features', auditWarning: 'No independent prospective blind set is available. Internal intervals support ranking only and do not replace replication, risk assessment, or scale-up decisions.',
      prospective: 'Prospective validation', planTitle: 'Experiment plan and blind-test record', exportCsv: 'Export CSV', clear: 'Clear', safety: 'TMSCN and cyanides are acutely toxic. This tool does not replace institutional SOPs, supervisor approval, ventilation monitoring, or waste controls.', subject: 'Substrate/purpose', condition: 'Condition', expected: 'Expected', evidenceLevel: 'Evidence level', emptyPlan: 'No candidates added.', footerClaim: 'ChemPredict v4.4 · Evidence lookup and candidate ranking, not an experimental guarantee', auditDate: 'Audit date: 2026-07-18',
      quantitative: 'Quantitative', evidence_only: 'Evidence only', refusal_only: 'Refusal test only', doi: 'Literature DOI', boundary: 'Applicability boundary', reactionClass: 'Reaction class', records: 'Quantitative rows', openDoi: 'Open DOI',
      measured: 'Paper observation', censored: 'Censored/qualitative', isolatedYield: 'Isolated yield', enantiomericExcess: 'Enantiomeric excess', notReported: 'Not reported', relativeAnchor: 'Relative to matched anchor', fullCombination: 'Full combination', setup: 'Reaction setup', sourcePage: 'Source page', noFakeNumber: 'The paper gives no numerical detection limit for trace/n.d.; no pseudo-point value is created.',
      fixedProtocol: 'Fixed optimized protocol', originalObservation: 'Grade A: observation', radicalClass: 'Radical class', smiles: 'Manually audited SMILES', dataRole: 'Data role', trainingDomain: 'Training-domain sample', challengeOnly: 'Cross-class challenge; lookup only', originalEnglishName: 'Paper name',
      prediction: 'Model estimate, not a paper observation', refuse: 'Prediction refused', noPoint: 'No point prediction was emitted.', gradeDomain: ' domain grade', yieldInterval: 'Yield screening interval', eeInterval: 'ee empirical interval', centre: 'Point', selectedInterval: 'Selected interval', globalInterval: 'Global interval', empiricalInterval: 'Empirical q80 interval', intervalSource: 'Interval source', group: 'Calibration family', distance: 'Nearest-neighbour distance', yieldModel: 'Yield model', eeModel: 'ee model', intervalMeaning: 'Interval meaning', globalFallback: 'Global fallback', groupCalibration: 'Family calibration',
      productionModel: 'Production model', challengerModel: 'v4.4 challenger', retained: 'Champion retained', promoted: 'Challenger promoted', target: 'Target', championMae: 'Champion nested MAE', challengerMae: 'Challenger nested MAE', decision: 'Decision',
      trainingRows: 'Training substrates', conditionRows: 'Condition evidence', yieldMae: 'Production yield nested MAE', eeMae: 'Production ee nested MAE', allScope: '2a–2z, 26 rows under one protocol', evidenceRows: 'Paper one-factor and control records', targetTransform: 'ee transformed to ΔΔG‡ first', groupedHoldout: '10 chemical families held out by group', noExternal: 'No independent blind test',
      integratedResearch: 'Integrated; research challenger', notPromoted: 'Not promoted', productionUsed: 'Used in production', remove: 'Remove', planEvidenceA: 'Grade-A paper observation', modelEstimate: 'Model estimate', fixedCondition: 'Fixed condition',
    },
  };

  const substrateZh = {
    '2a': '(S)-2-(萘-2-基)丙腈', '2b': '(S)-2-(萘-1-基)丙腈', '2c': '(S)-2-(6-甲氧基萘-2-基)丙腈',
    '2d': '(S)-2-苯基丙腈', '2e': '(S)-2-苯基庚腈', '2f': '(S)-5-溴-2-苯基戊腈', '2g': '(S)-5-氰基-5-苯基戊酸甲酯',
    '2h': '(S)-2-(对甲苯基)丙腈', '2i': '(S)-2-(4-甲氧基苯基)丙腈', '2j': '(S)-2-([1,1′-联苯]-4-基)丙腈',
    '2k': '(S)-2-(2-氟-[1,1′-联苯]-4-基)丙腈', '2l': '(S)-4-(1-氰乙基)苯甲酸甲酯', '2m': '(S)-2-[4-(三氟甲基)苯基]丙腈',
    '2n': '(S)-4-(1-氰乙基)苯甲腈', '2o': '(S)-2-(4-氟苯基)丙腈', '2p': '(S)-2-(4-氯苯基)丙腈', '2q': '(S)-2-(4-溴苯基)丙腈',
    '2r': '(S)-2-(3-氯苯基)丙腈', '2s': '(S)-2-(3-溴苯基)丙腈', '2t': '(S)-2-(2-氯苯基)丙腈', '2u': '(S)-2-(2-溴苯基)丙腈',
    '2v': '(S)-2-(2-氟苯基)丙腈', '2w': '(S)-2-(2,4-二氯苯基)丙腈', '2x': '(S)-2-(2,6-二氯苯基)丙腈', '2y': '(S)-2-(4-溴-3-氟苯基)丙腈',
    '2z': '(S)-1,2,3,4-四氢萘-1-甲腈', '3a': '(R)-2-(噻吩-2-基)丙腈', '3b': '(S)-2-氯-5,6,7,8-四氢喹啉-5-甲腈',
    '3c': '(R)-1-氧代-1,2,3,4-四氢萘-2-甲腈', '3d': '(R)-2-苯乙基-4-(三甲基硅基)丁-3-炔腈',
  };

  const choiceSets = {
    precursor: [
      ['secondary_benzylic_nhp_ether', '仲苄基 NHP 醚', 'Secondary benzylic NHP ether'],
      ['tertiary_nhp_ether', '三级 NHP 醚', 'Tertiary NHP ether'],
      ['unactivated_alcohol', '非活化脂肪醇衍生物', 'Unactivated aliphatic-alcohol derivative'],
    ],
    radical: [
      ['carbon_aryl_benzylic', '碳-芳基仲苄基自由基', 'Carbon-aryl secondary-benzylic radical'],
      ['heteroaryl', '杂芳基自由基', 'Heteroaryl radical'], ['alpha_carbonyl', 'α-羰基自由基', 'Alpha-carbonyl radical'], ['propargylic', '炔丙基自由基', 'Propargylic radical'],
    ],
    aryl: [['phenyl', '苯基', 'Phenyl'], ['naphthyl2', '萘-2-基', 'Naphthalen-2-yl'], ['naphthyl1', '萘-1-基', 'Naphthalen-1-yl'], ['cyclic', '四氢萘型环状中心', 'Tetralin-type cyclic centre']],
    substituent: [
      ['none', '无取代', 'Unsubstituted'], ['p_me', '对甲基', 'para-Methyl'], ['p_ome', '对甲氧基', 'para-Methoxy'], ['p_ph', '对苯基', 'para-Phenyl'],
      ['p_co2me', '对甲氧羰基', 'para-Methoxycarbonyl'], ['p_cf3', '对三氟甲基', 'para-Trifluoromethyl'], ['p_cn', '对氰基', 'para-Cyano'],
      ['p_f', '对氟', 'para-Fluoro'], ['p_cl', '对氯', 'para-Chloro'], ['p_br', '对溴', 'para-Bromo'], ['m_cl', '间氯', 'meta-Chloro'], ['m_br', '间溴', 'meta-Bromo'],
      ['o_f', '邻氟', 'ortho-Fluoro'], ['o_cl', '邻氯', 'ortho-Chloro'], ['o_br', '邻溴', 'ortho-Bromo'], ['dicl_24', '2,4-二氯', '2,4-Dichloro'], ['dicl_26', '2,6-二氯', '2,6-Dichloro'],
    ],
    sidechain: [['methyl', '甲基', 'Methyl'], ['pentyl', '正戊基', 'n-Pentyl'], ['bromopropyl', '3-溴丙基', '3-Bromopropyl'], ['ester_chain', '3-甲氧羰基丙基', '3-Methoxycarbonylpropyl'], ['cyclic', '环内连接', 'Cyclic linkage']],
    groups: [['alkyl_series', '烷基侧链系列', 'Alkyl series'], ['biphenyl', '联苯系列', 'Biphenyl'], ['cyclic_benzylic', '环状苄基系列', 'Cyclic benzylic'], ['meta_halogen', '间位卤素系列', 'meta-Halogen'], ['naphthyl', '萘基系列', 'Naphthyl'], ['ortho_halogen', '邻位卤素系列', 'ortho-Halogen'], ['para_edg', '对位给电子系列', 'para-EDG'], ['para_ewg', '对位吸电子系列', 'para-EWG'], ['para_halogen', '对位卤素系列', 'para-Halogen'], ['polyhalogen', '多卤代系列', 'Polyhalogen']],
  };

  const substituents = {
    none: { ortho: 0, meta: 0, para: 0, sigma: 0, halogen: 0, edg: 0, ewg: 0, polar: 0, ringDelta: 0 }, p_me: { ortho: 0, meta: 0, para: 1, sigma: -0.17, halogen: 0, edg: 1, ewg: 0, polar: 0, ringDelta: 0 },
    p_ome: { ortho: 0, meta: 0, para: 1, sigma: -0.27, halogen: 0, edg: 1, ewg: 0, polar: 1, ringDelta: 0 }, p_ph: { ortho: 0, meta: 0, para: 1, sigma: -0.01, halogen: 0, edg: 0, ewg: 0, polar: 0, ringDelta: 1 },
    p_co2me: { ortho: 0, meta: 0, para: 1, sigma: 0.45, halogen: 0, edg: 0, ewg: 1, polar: 2, ringDelta: 0 }, p_cf3: { ortho: 0, meta: 0, para: 1, sigma: 0.54, halogen: 3, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
    p_cn: { ortho: 0, meta: 0, para: 1, sigma: 0.66, halogen: 0, edg: 0, ewg: 1, polar: 1, ringDelta: 0 }, p_f: { ortho: 0, meta: 0, para: 1, sigma: 0.06, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
    p_cl: { ortho: 0, meta: 0, para: 1, sigma: 0.23, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 }, p_br: { ortho: 0, meta: 0, para: 1, sigma: 0.23, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
    m_cl: { ortho: 0, meta: 1, para: 0, sigma: 0.37, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 }, m_br: { ortho: 0, meta: 1, para: 0, sigma: 0.39, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
    o_f: { ortho: 1, meta: 0, para: 0, sigma: 0, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 }, o_cl: { ortho: 1, meta: 0, para: 0, sigma: 0, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
    o_br: { ortho: 1, meta: 0, para: 0, sigma: 0, halogen: 1, edg: 0, ewg: 1, polar: 0, ringDelta: 0 }, dicl_24: { ortho: 1, meta: 0, para: 1, sigma: 0.23, halogen: 2, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
    dicl_26: { ortho: 2, meta: 0, para: 0, sigma: 0, halogen: 2, edg: 0, ewg: 1, polar: 0, ringDelta: 0 },
  };
  const sidechains = { methyl: { carbons: 1, polar: 0, extraHalogen: 0, cyclic: 0 }, pentyl: { carbons: 5, polar: 0, extraHalogen: 0, cyclic: 0 }, bromopropyl: { carbons: 3, polar: 1, extraHalogen: 1, cyclic: 0 }, ester_chain: { carbons: 3, polar: 2, extraHalogen: 0, cyclic: 0 }, cyclic: { carbons: 0, polar: 0, extraHalogen: 0, cyclic: 1 } };

  function t(key) { return (i18n[lang] || i18n.zh)[key] || key; }
  function escapeHtml(value) { return String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;'); }
  function formatNumber(value, digits = 0) { return Number(value).toFixed(digits); }
  function signed(value) { if (value === null || value === undefined) return '—'; return `${value > 0 ? '+' : ''}${formatNumber(value)}`; }
  function optionHtml(value, zh, en) { return `<option value="${escapeHtml(value)}">${escapeHtml(lang === 'zh' ? zh : en)}</option>`; }
  function fillChoices(selector, rows) { const selected = $(selector).value; $(selector).innerHTML = rows.map((row) => optionHtml(...row)).join(''); if (rows.some((row) => row[0] === selected)) $(selector).value = selected; }
  function outcome(label, value, detail) { return `<div class="outcome"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`; }

  function translateStatic() { $$('[data-i18n]').forEach((node) => { node.textContent = t(node.dataset.i18n); }); document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'; $$('.language-switch button').forEach((button) => button.classList.toggle('is-active', button.dataset.language === lang)); }
  function populateChoiceControls() {
    fillChoices('#precursor-type', choiceSets.precursor); fillChoices('#radical-class', choiceSets.radical); fillChoices('#aryl-template', choiceSets.aryl);
    fillChoices('#substituent-template', choiceSets.substituent); fillChoices('#sidechain-template', choiceSets.sidechain); fillChoices('#scope-group', choiceSets.groups);
    const axes = [['solvent', '溶剂', 'Solvent'], ['photocatalyst', '光催化剂', 'Photocatalyst'], ['copper_source', '铜源', 'Copper source'], ['ligand', '手性配体', 'Chiral ligand'], ['temperature', '温度', 'Temperature']];
    fillChoices('#condition-axis', axes);
  }

  function statusLabel(status) { return t(status); }
  function renderSystems() {
    const selected = $('#system-selector').value || 'nhp_deoxygenative_asymmetric_cyanation';
    $('#system-selector').innerHTML = model.reactionSystems.map((row) => `<option value="${escapeHtml(row.system_id)}">${escapeHtml(row[lang === 'zh' ? 'title_zh' : 'title_en'])}</option>`).join('');
    $('#system-selector').value = model.reactionSystems.some((row) => row.system_id === selected) ? selected : model.reactionSystems[0].system_id;
    renderSelectedSystem(); renderSystemGrid();
  }
  function renderSelectedSystem() {
    const system = model.systemById($('#system-selector').value);
    if (!system) return;
    $('#system-summary').innerHTML = `<p>${escapeHtml(system[lang === 'zh' ? 'reaction_class_zh' : 'reaction_class_en'])}<br>${escapeHtml(system[lang === 'zh' ? 'boundary_zh' : 'boundary_en'])}</p><span class="status-chip ${escapeHtml(system.status)}">${escapeHtml(statusLabel(system.status))}</span>`;
    const quantitative = system.status === 'quantitative';
    $('#quantitative-workspace').hidden = !quantitative; $('#system-boundary').hidden = quantitative;
    if (!quantitative) {
      $('#system-boundary').innerHTML = `<h2>${escapeHtml(system[lang === 'zh' ? 'title_zh' : 'title_en'])}</h2><p>${escapeHtml(system[lang === 'zh' ? 'boundary_zh' : 'boundary_en'])}</p><dl><dt>${t('reactionClass')}</dt><dd>${escapeHtml(system[lang === 'zh' ? 'reaction_class_zh' : 'reaction_class_en'])}</dd><dt>${t('doi')}</dt><dd><a href="https://doi.org/${escapeHtml(system.doi)}" target="_blank" rel="noreferrer">${escapeHtml(system.doi)}</a></dd><dt>${t('condition')}</dt><dd>${escapeHtml(system[lang === 'zh' ? 'condition_summary_zh' : 'condition_summary_en'])}</dd></dl>`;
    }
  }
  function renderSystemGrid() {
    $('#system-grid').innerHTML = model.reactionSystems.map((system) => `<article class="system-card"><header><h3>${escapeHtml(system[lang === 'zh' ? 'title_zh' : 'title_en'])}</h3><span class="status-chip ${escapeHtml(system.status)}">${escapeHtml(statusLabel(system.status))}</span></header><p>${escapeHtml(system[lang === 'zh' ? 'boundary_zh' : 'boundary_en'])}</p><footer><span>${t('records')}: ${system.quantitative_rows}</span><a href="https://doi.org/${escapeHtml(system.doi)}" target="_blank" rel="noreferrer">${t('openDoi')}</a></footer></article>`).join('');
  }

  function statusYield(record) {
    if (record.yield_status === 'measured') return `${formatNumber(record.yield_pct)}%`;
    if (record.yield_status === 'trace') return 'trace'; if (record.yield_status === 'not_detected') return 'n.d.';
    if (record.yield_status === 'less_than_50') return '<50%'; if (record.yield_status === 'not_obtained') return lang === 'zh' ? '未获得' : 'not obtained';
    return String(record.yield_status);
  }
  function fullCondition(record) { return `${model.formatTerm(record.photocatalyst, lang)} ${record.pc_mol_pct} mol%; ${model.formatTerm(record.copper_source, lang)} ${record.cu_mol_pct} mol%; ${model.formatTerm(record.ligand, lang)} ${record.ligand_mol_pct} mol%; ${model.formatTerm(record.solvent, lang)}; ${record.temp_c} °C`; }
  function populateConditionCandidates() {
    const axis = $('#condition-axis').value; const rows = model.conditionRows(axis);
    $('#condition-candidate').innerHTML = rows.map((row) => `<option value="${escapeHtml(row.record_id)}">${escapeHtml(model.conditionLabel(row, axis, lang))}</option>`).join('');
    renderConditionTable(axis); renderCondition(rows[0] && rows[0].record_id);
  }
  function renderCondition(recordId) {
    const evidence = model.conditionEvidence(recordId, lang); currentCondition = evidence; if (!evidence) return;
    const r = evidence.record; const eeText = evidence.ee === null ? t('notReported') : `${formatNumber(evidence.ee)}%`;
    $('#condition-result').innerHTML = `<div class="result-header"><div><h3>${escapeHtml(evidence.candidate)}</h3><p>${escapeHtml(evidence.axisLabel)}</p></div><span class="evidence-badge ${evidence.isCensored ? 'grade-d' : 'grade-b'}">${evidence.isCensored ? t('censored') : t('measured')}</span></div><div class="outcome-grid">${outcome(t('isolatedYield'), statusYield(r), evidence.isCensored ? t('censored') : t('measured'))}${outcome('ee', eeText, evidence.ee === null ? t('notReported') : `${model.formatTerm('HPLC', lang)}`)}</div><dl class="detail-list"><div><dt>${t('relativeAnchor')}</dt><dd>${evidence.deltaYield === null ? '—' : `${t('yield')} ${signed(evidence.deltaYield)}; ee ${signed(evidence.deltaEe)}`}</dd></div><div><dt>${t('fullCombination')}</dt><dd>${escapeHtml(fullCondition(r))}</dd></div><div><dt>${t('setup')}</dt><dd>${r.scale_mmol} mmol · ${r.time_h} h · ${escapeHtml(r.light_nm)} nm · ${escapeHtml(model.formatTerm('N2', lang))}</dd></div><div><dt>${t('sourcePage')}</dt><dd>${escapeHtml(r.source_table)} · PDF p.${escapeHtml(r.source_pdf_page)} · ${escapeHtml(r.source_doi)}</dd></div></dl>${evidence.isCensored ? `<div class="warning-box">${t('noFakeNumber')}</div>` : ''}`;
  }
  function renderConditionTable(axis) {
    const rows = model.conditionRows(axis).slice().sort((a, b) => (Number(b.yield_pct) || -1) - (Number(a.yield_pct) || -1));
    $('#condition-table-body').innerHTML = rows.map((r) => { const e = model.conditionEvidence(r.record_id, lang); return `<tr data-condition-id="${escapeHtml(r.record_id)}"><td><button class="text-button" type="button">${escapeHtml(model.conditionLabel(r, axis, lang))}</button></td><td>${escapeHtml(statusYield(r))}</td><td>${e.ee === null ? '—' : `${formatNumber(e.ee)}%`}</td><td>${e.deltaYield === null ? '—' : `${signed(e.deltaYield)} / ${signed(e.deltaEe)}`}</td><td>${escapeHtml(r.source_table)} · p.${escapeHtml(r.source_pdf_page)}</td></tr>`; }).join('');
    $$('[data-condition-id]').forEach((row) => row.addEventListener('click', () => { $('#condition-candidate').value = row.dataset.conditionId; renderCondition(row.dataset.conditionId); }));
  }

  function substrateLabel(row) { return lang === 'zh' ? `${row.id} · ${row.product_name}（${substrateZh[row.id] || '原文结构'}）` : `${row.id} · ${row.product_name}`; }
  function populateLiterature() { $('#literature-substrate').innerHTML = model.artifact.known_scope.map((row) => `<option value="${escapeHtml(row.id)}">${escapeHtml(substrateLabel(row))}</option>`).join(''); renderLiterature(model.artifact.known_scope[0].id); renderFixedCondition(); }
  function renderFixedCondition() { $('#fixed-condition').innerHTML = `<strong>${t('fixedCondition')}</strong><span>${escapeHtml(model.formatTerm('fac-Ir(ppy)3', lang))} 1 mol%</span><span>${escapeHtml(model.formatTerm('CuCN', lang))} 2 mol% · ${escapeHtml(model.formatTerm('L1', lang))} 3 mol%</span><span>${escapeHtml(model.formatTerm('DCM', lang))} · ${escapeHtml(model.formatTerm('N2', lang))} · 450–465 nm · 12 h</span>`; }
  function renderLiterature(id) {
    const row = model.knownSubstrate(id); currentLiterature = row; if (!row) return;
    const name = substrateLabel(row); const role = String(row.id).startsWith('2') ? t('trainingDomain') : t('challengeOnly');
    $('#literature-result').innerHTML = `<div class="result-header"><div><h3>${escapeHtml(name)}</h3><p>${t('fixedProtocol')}</p></div><span class="evidence-badge grade-b">${t('originalObservation')}</span></div><div class="outcome-grid">${outcome(t('isolatedYield'), `${formatNumber(row.yield_pct)}%`, 'Table 2 / SI')}${outcome('ee', `${formatNumber(row.ee_pct)}%`, `ΔΔG‡ = ${formatNumber(model.eeToDdg(row.ee_pct), 3)} kcal/mol`)}</div><dl class="detail-list"><div><dt>${t('radicalClass')}</dt><dd>${escapeHtml(row.radical_class)}</dd></div><div><dt>${t('smiles')}</dt><dd>${escapeHtml(row.manual_smiles)}</dd></div><div><dt>${t('sourcePage')}</dt><dd>Table 2 · SI PDF p.${escapeHtml(row.source_pdf_page)} · ${escapeHtml(row.source_doi)}</dd></div><div><dt>${t('dataRole')}</dt><dd>${escapeHtml(role)}</dd></div></dl>`;
  }

  function normalizeVirtualGroup(group) { if (String(group).startsWith('alkyl')) return 'alkyl_series'; return choiceSets.groups.some((row) => row[0] === group) ? group : undefined; }
  function virtualInput(record) { return { systemId: 'nhp_deoxygenative_asymmetric_cyanation', precursorType: 'secondary_benzylic_nhp_ether', radicalClass: 'carbon_aryl_benzylic', reactionFamily: 'nhp_ether_deoxygenative_asymmetric_cyanation', conditionChanges: [], scopeGroup: normalizeVirtualGroup(record.scope_group), label: `${record.id} · ${record.label}`, features: record }; }
  function populateVirtual() { const rows = model.virtualCandidates(); $('#virtual-candidate').innerHTML = rows.map((row) => `<option value="${escapeHtml(row.id)}">${escapeHtml(row.id)} · ${escapeHtml(row.label)}</option>`).join(''); if (rows.length) renderVirtual(rows[0].id); }
  function renderVirtual(id) { const record = model.virtualCandidates().find((row) => row.id === id); if (!record) return; const input = virtualInput(record); const result = model.predictCustom(input, lang); currentVirtual = { record, input, result }; renderPrediction(input, result, '#virtual-result', '#add-virtual'); }

  function inferredGroup(aryl, sub, side) {
    if (aryl.startsWith('naphthyl')) return 'naphthyl'; if (aryl === 'cyclic' || side === 'cyclic') return 'cyclic_benzylic'; if (side !== 'methyl') return 'alkyl_series';
    if (sub === 'p_ph') return 'biphenyl'; if (['p_me', 'p_ome'].includes(sub)) return 'para_edg'; if (['p_co2me', 'p_cf3', 'p_cn'].includes(sub)) return 'para_ewg';
    if (['p_f', 'p_cl', 'p_br'].includes(sub)) return 'para_halogen'; if (sub.startsWith('m_')) return 'meta_halogen'; if (sub.startsWith('o_')) return 'ortho_halogen'; if (sub.startsWith('dicl')) return 'polyhalogen'; return 'alkyl_series';
  }
  function syncDescriptors() {
    const aryl = $('#aryl-template').value; const subKey = $('#substituent-template').value; const sideKey = $('#sidechain-template').value; const sub = substituents[subKey]; const side = sidechains[sideKey];
    $('#f-ortho').value = sub.ortho; $('#f-meta').value = sub.meta; $('#f-para').value = sub.para; $('#f-sigma').value = sub.sigma; $('#f-halogen').value = sub.halogen + side.extraHalogen; $('#f-edg').value = sub.edg; $('#f-ewg').value = sub.ewg; $('#f-polar').value = Math.max(sub.polar, side.polar);
    $('#custom-form').dataset.arylRings = (aryl.startsWith('naphthyl') ? 2 : 1) + sub.ringDelta; $('#custom-form').dataset.fused = aryl.startsWith('naphthyl') || aryl === 'cyclic' ? 1 : 0; $('#custom-form').dataset.cyclic = aryl === 'cyclic' || side.cyclic ? 1 : 0; $('#custom-form').dataset.alphaCarbons = side.carbons;
    $('#scope-group').value = inferredGroup(aryl, subKey, sideKey); currentCustom = null; $('#add-custom').disabled = true;
  }
  function selectedText(selector) { return $(selector).selectedOptions[0] ? $(selector).selectedOptions[0].textContent : ''; }
  function customInput() {
    const form = $('#custom-form'); const para = Number($('#f-para').value); const sigma = Number($('#f-sigma').value);
    return { systemId: $('#system-selector').value, precursorType: $('#precursor-type').value, radicalClass: $('#radical-class').value, reactionFamily: 'nhp_ether_deoxygenative_asymmetric_cyanation', conditionChanges: [], scopeGroup: $('#scope-group').value, label: `${selectedText('#aryl-template')} / ${selectedText('#substituent-template')} / ${selectedText('#sidechain-template')}`, features: { aryl_rings: Number(form.dataset.arylRings), fused_aromatic: Number(form.dataset.fused), cyclic_center: Number(form.dataset.cyclic), alpha_chain_carbons: Number(form.dataset.alphaCarbons), ortho_sub_count: Number($('#f-ortho').value), meta_sub_count: Number($('#f-meta').value), para_sub_count: para, hammett_sigma_mp: sigma, hammett_sigma_mp_x_para_sub_count: sigma * para, halogen_count: Number($('#f-halogen').value), edg_count: Number($('#f-edg').value), ewg_count: Number($('#f-ewg').value), sidechain_polar_count: Number($('#f-polar').value) } };
  }
  function intervalText(interval) { return `${formatNumber(interval.low)}–${formatNumber(interval.high)}%`; }
  function renderPrediction(input, result, targetSelector, buttonSelector) {
    const target = $(targetSelector); const button = $(buttonSelector);
    if (result.status !== 'PREDICT') { target.innerHTML = `<div class="result-header"><div><h3>${escapeHtml(input.label)}</h3><p>${t('boundary')}</p></div><span class="evidence-badge grade-r">${t('refuse')}</span></div><div class="refusal-box"><strong>${t('noPoint')}</strong><br>${(result.reasons || []).map(escapeHtml).join('<br>')}</div>`; button.disabled = true; return; }
    const gradeClass = result.grade === 'B' ? 'grade-b' : (result.grade === 'C' ? 'grade-c' : 'grade-d'); const sourceName = result.ee.source === 'group' ? t('groupCalibration') : t('globalFallback');
    target.innerHTML = `<div class="result-header"><div><h3>${escapeHtml(input.label)}</h3><p>${t('prediction')}</p></div><span class="evidence-badge ${gradeClass}">${escapeHtml(result.grade)}${t('gradeDomain')}</span></div><div class="outcome-grid">${outcome(t('yieldInterval'), intervalText(result.yield), `${t('centre')} ${formatNumber(result.yield.point, 1)}%`)}${outcome(t('eeInterval'), intervalText(result.ee), `${t('centre')} ${formatNumber(result.ee.point, 1)}%`)}</div><dl class="detail-list"><div><dt>${t('globalInterval')}</dt><dd>${t('yield')} ${formatNumber(result.yield.globalLow)}–${formatNumber(result.yield.globalHigh)}%; ee ${formatNumber(result.ee.globalLow)}–${formatNumber(result.ee.globalHigh)}%</dd></div><div><dt>${t('empiricalInterval')}</dt><dd>${t('yield')} ${formatNumber(result.yield.empiricalLow)}–${formatNumber(result.yield.empiricalHigh)}%; ee ${formatNumber(result.ee.empiricalLow)}–${formatNumber(result.ee.empiricalHigh)}%</dd></div><div><dt>${t('intervalSource')}</dt><dd>${escapeHtml(sourceName)} · ${escapeHtml(result.scopeGroup)} · n=${result.ee.groupN}</dd></div><div><dt>${t('distance')}</dt><dd>${formatNumber(result.distance, 3)} / q95 ${formatNumber(result.distanceThreshold, 3)}</dd></div><div><dt>${t('yieldModel')}</dt><dd>${escapeHtml(result.modelDetails.yield)}</dd></div><div><dt>${t('eeModel')}</dt><dd>${escapeHtml(result.modelDetails.ee)}</dd></div><div><dt>${t('intervalMeaning')}</dt><dd>${escapeHtml(result.intervalNote)}</dd></div></dl>${result.warnings.length ? `<div class="warning-box">${result.warnings.map(escapeHtml).join('<br>')}</div>` : ''}`;
    button.disabled = false;
  }

  function renderAudit() {
    const production = model.artifact.production_validation_metrics; const y = production.yield; const e = production.ee;
    const cards = [[t('trainingRows'), model.artifact.training_count, t('allScope')], [t('conditionRows'), model.artifact.condition_screen.length, t('evidenceRows')], [t('yieldMae'), formatNumber(y.mae, 2), `RMSE ${formatNumber(y.rmse, 2)}`], [t('eeMae'), formatNumber(e.mae, 2), `RMSE ${formatNumber(e.rmse, 2)}`]];
    $('#metric-cards').innerHTML = cards.map(([label, value, detail]) => `<div class="metric-card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><small>${escapeHtml(detail)}</small></div>`).join('');
    $('#promotion-table').innerHTML = `<table><thead><tr><th>${t('target')}</th><th>${t('championMae')}</th><th>${t('challengerMae')}</th><th>${t('decision')}</th></tr></thead><tbody>${model.artifact.promotion_audit.map((row) => `<tr><td>${escapeHtml(row.target)}</td><td>${formatNumber(row.champion_nested_mae, 3)}</td><td>${formatNumber(row.challenger_nested_mae, 3)}</td><td>${row.promoted ? t('promoted') : t('retained')}</td></tr>`).join('')}</tbody></table>`;
    const tools = [['qmdesc 1.0.6', t('integratedResearch'), t('notPromoted')], ['DBSTEP 1.1.0', t('integratedResearch'), t('notPromoted')], ['XGBoost 3.3.0', t('integratedResearch'), t('notPromoted')], ['RDKit 2025.09.6', lang === 'zh' ? '结构解析与分化描述符' : 'Structure parsing and discriminating descriptors', t('productionUsed')]];
    $('#tool-status').innerHTML = tools.map((row) => `<div class="tool-row"><strong>${escapeHtml(row[0])}</strong><span>${escapeHtml(row[1])}</span><b>${escapeHtml(row[2])}</b></div>`).join('');
    const design = [[lang === 'zh' ? '外层切分' : 'Outer split', t('groupedHoldout')], [lang === 'zh' ? '目标变换' : 'Target transform', t('targetTransform')], [lang === 'zh' ? '区间' : 'Intervals', lang === 'zh' ? '嵌套留组残差；家族 n≥4 才可收窄' : 'Nested grouped residuals; family narrowing only at n≥4'], [lang === 'zh' ? '外部验证' : 'External validation', t('noExternal')]];
    $('#validation-design').innerHTML = design.map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');
    $('#model-features').innerHTML = Object.entries(model.artifact.models).flatMap(([targetName, item]) => item.features.map((feature) => `<div class="feature-row"><strong>${escapeHtml(targetName)}</strong><span>${escapeHtml(feature)}</span><b>${escapeHtml(item.algorithm)}</b></div>`)).join('');
  }

  function loadPlan() { try { return JSON.parse(localStorage.getItem('chempredict-v44-plan') || '[]'); } catch (_) { return []; } }
  function savePlan() { localStorage.setItem('chempredict-v44-plan', JSON.stringify(plan)); renderPlan(); }
  function addPlan(item) { plan.push({ ...item, uid: `${Date.now()}-${Math.random().toString(16).slice(2)}` }); savePlan(); }
  function renderPlan() { $('#plan-count').textContent = String(plan.length); $('#plan-empty').hidden = plan.length > 0; $('#plan-table-body').innerHTML = plan.map((item, index) => `<tr><td>${index + 1}</td><td>${escapeHtml(item.subject)}</td><td>${escapeHtml(item.condition)}</td><td>${escapeHtml(item.expected)}</td><td>${escapeHtml(item.evidence)}</td><td><button type="button" class="text-button" data-remove="${escapeHtml(item.uid)}">${t('remove')}</button></td></tr>`).join(''); $$('[data-remove]').forEach((button) => button.addEventListener('click', () => { plan = plan.filter((item) => item.uid !== button.dataset.remove); savePlan(); })); }
  function fixedConditionText() { return `${model.formatTerm('fac-Ir(ppy)3', lang)} 1%; ${model.formatTerm('CuCN', lang)} 2%; ${model.formatTerm('L1', lang)} 3%; ${model.formatTerm('DCM', lang)}; 25 °C; 12 h`; }

  function refreshLanguage() { translateStatic(); populateChoiceControls(); renderSystems(); populateConditionCandidates(); populateLiterature(); populateVirtual(); syncDescriptors(); renderAudit(); renderPlan(); }

  $$('.language-switch button').forEach((button) => button.addEventListener('click', () => { lang = button.dataset.language; localStorage.setItem('chempredict-v44-language', lang); refreshLanguage(); }));
  $$('.primary-tabs button').forEach((button) => button.addEventListener('click', () => { $$('.primary-tabs button').forEach((item) => item.classList.toggle('is-active', item === button)); $$('.page').forEach((page) => page.classList.toggle('is-active', page.id === button.dataset.page)); window.scrollTo({ top: 0, behavior: 'smooth' }); }));
  $$('.mode-tabs button').forEach((button) => button.addEventListener('click', () => { $$('.mode-tabs button').forEach((item) => item.classList.toggle('is-active', item === button)); $$('.mode-panel').forEach((panel) => panel.classList.toggle('is-active', panel.id === `mode-${button.dataset.mode}`)); }));
  $('#system-selector').addEventListener('change', renderSelectedSystem); $('#condition-axis').addEventListener('change', populateConditionCandidates);
  $('#condition-form').addEventListener('submit', (event) => { event.preventDefault(); renderCondition($('#condition-candidate').value); });
  $('#literature-form').addEventListener('submit', (event) => { event.preventDefault(); renderLiterature($('#literature-substrate').value); });
  $('#virtual-form').addEventListener('submit', (event) => { event.preventDefault(); renderVirtual($('#virtual-candidate').value); });
  ['#aryl-template', '#substituent-template', '#sidechain-template'].forEach((selector) => $(selector).addEventListener('change', syncDescriptors));
  $('#custom-form').addEventListener('submit', (event) => { event.preventDefault(); const input = customInput(); const result = model.predictCustom(input, lang); currentCustom = { input, result }; renderPrediction(input, result, '#custom-result', '#add-custom'); });
  $('#add-condition').addEventListener('click', () => { if (!currentCondition) return; addPlan({ subject: `${currentCondition.axisLabel}: ${currentCondition.candidate}`, condition: fullCondition(currentCondition.record), expected: `${statusYield(currentCondition.record)}; ee ${currentCondition.ee === null ? '—' : `${currentCondition.ee}%`}`, evidence: t('planEvidenceA') }); });
  $('#add-literature').addEventListener('click', () => { if (!currentLiterature) return; addPlan({ subject: substrateLabel(currentLiterature), condition: fixedConditionText(), expected: `${currentLiterature.yield_pct}% ${t('yield')}; ${currentLiterature.ee_pct}% ee`, evidence: t('planEvidenceA') }); });
  $('#add-virtual').addEventListener('click', () => { if (!currentVirtual || currentVirtual.result.status !== 'PREDICT') return; addPlan({ subject: currentVirtual.input.label, condition: fixedConditionText(), expected: `${t('yield')} ${intervalText(currentVirtual.result.yield)}; ee ${intervalText(currentVirtual.result.ee)}`, evidence: `${currentVirtual.result.grade} · ${t('modelEstimate')}` }); });
  $('#add-custom').addEventListener('click', () => { if (!currentCustom || currentCustom.result.status !== 'PREDICT') return; addPlan({ subject: currentCustom.input.label, condition: fixedConditionText(), expected: `${t('yield')} ${intervalText(currentCustom.result.yield)}; ee ${intervalText(currentCustom.result.ee)}`, evidence: `${currentCustom.result.grade} · ${t('modelEstimate')}` }); });
  $('#clear-plan').addEventListener('click', () => { plan = []; savePlan(); });
  $('#export-plan').addEventListener('click', () => { if (!plan.length) return; const headers = lang === 'zh' ? ['run_id', '底物或用途', '条件', '预期', '证据级别', '实测产率', '实测ee', '备注'] : ['run_id', 'subject', 'condition', 'expected', 'evidence', 'observed_yield', 'observed_ee', 'notes']; const cell = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`; const rows = [headers, ...plan.map((item, index) => [index + 1, item.subject, item.condition, item.expected, item.evidence, '', '', ''])]; const blob = new Blob([`\ufeff${rows.map((row) => row.map(cell).join(',')).join('\r\n')}`], { type: 'text/csv;charset=utf-8' }); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `ChemPredict_v4.4_plan_${new Date().toISOString().slice(0, 10)}.csv`; link.click(); URL.revokeObjectURL(url); });

  refreshLanguage();
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});
}());
