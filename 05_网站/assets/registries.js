window.CHEMPREDICT_REACTION_SYSTEMS = [
  {
    "system_id": "nhp_deoxygenative_asymmetric_cyanation",
    "title_zh": "NHP 醚脱氧不对称氰化",
    "title_en": "NHP-ether deoxygenative asymmetric cyanation",
    "reaction_class_zh": "光氧化还原/铜协同催化不对称自由基氰化",
    "reaction_class_en": "Cooperative photoredox/copper asymmetric radical cyanation",
    "status": "quantitative",
    "model_id": "production_champion_v4.3_with_v4.4_gate",
    "quantitative_rows": 26,
    "condition_rows": 33,
    "outputs": [
      "yield_pct",
      "ee_pct"
    ],
    "doi": "10.1021/acs.orglett.5c05116",
    "condition_summary_zh": "fac-Ir(ppy)3（面式三(2-苯基吡啶)合铱(III)）/CuCN（氰化亚铜）/L1（原文手性配体编号）/DCM（二氯甲烷），450–465 nm",
    "condition_summary_en": "fac-Ir(ppy)3/CuCN/L1/DCM, 450–465 nm",
    "boundary_zh": "只对固定优化协议下的仲苄基 NHP 醚输出定量结果；条件变化仅查阅原文单因素证据。",
    "boundary_en": "Quantitative output is restricted to secondary benzylic NHP ethers under the fixed optimized protocol; condition changes are literature evidence only."
  },
  {
    "system_id": "alkoxycarbonyl_cyanation_styrenes",
    "title_zh": "苯乙烯不对称烷氧羰基氰化",
    "title_en": "Asymmetric alkoxycarbonyl-cyanation of styrenes",
    "reaction_class_zh": "烯烃加成型光氧化还原/铜协同催化",
    "reaction_class_en": "Alkene-addition photoredox/copper catalysis",
    "status": "evidence_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1021/acscatal.5c04002",
    "condition_summary_zh": "反应物、自由基生成与成键顺序均不同；未与目标训练集数值合并。",
    "condition_summary_en": "Different reactants, radical generation, and bond-forming sequence; no numerical pooling.",
    "boundary_zh": "仅用于机理对照和实验因素清单，不输出产率或 ee 点预测。",
    "boundary_en": "Mechanistic reference and factor inventory only; no yield or ee point prediction."
  },
  {
    "system_id": "electrochemical_cyanoesterification_vinylarenes",
    "title_zh": "乙烯基芳烃电化学不对称氰酯化",
    "title_en": "Electrochemical asymmetric cyanoesterification of vinylarenes",
    "reaction_class_zh": "电化学铜催化烯烃双官能团化",
    "reaction_class_en": "Electrochemical copper-catalyzed alkene difunctionalization",
    "status": "evidence_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1038/s41467-025-62137-7",
    "condition_summary_zh": "电极、电流/电位和电解质是额外决定因素，不能映射到光催化固定协议。",
    "condition_summary_en": "Electrode, current/potential, and electrolyte are additional determinants not mapped to the fixed photochemical protocol.",
    "boundary_zh": "证据浏览模式；不进行跨电化学/光化学迁移。",
    "boundary_en": "Evidence browser only; no electrochemical-to-photochemical transfer."
  },
  {
    "system_id": "tertiary_radical_cyanation",
    "title_zh": "三级自由基不对称氰化",
    "title_en": "Asymmetric tertiary-radical cyanation",
    "reaction_class_zh": "铜催化三级自由基对映汇聚氰化",
    "reaction_class_en": "Copper-catalyzed enantioconvergent tertiary-radical cyanation",
    "status": "refusal_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1021/acs.orglett.4c03914",
    "condition_summary_zh": "自由基级别和配体空间口袋与仲苄基 NHP 醚体系不同。",
    "condition_summary_en": "Radical substitution and ligand pocket differ from the secondary-benzylic NHP-ether system.",
    "boundary_zh": "作为硬拒绝压力测试；不输出数值。",
    "boundary_en": "Hard-refusal stress test; no numerical output."
  },
  {
    "system_id": "propargylic_radical_cyanation",
    "title_zh": "炔丙基自由基不对称氰化",
    "title_en": "Asymmetric propargylic-radical cyanation",
    "reaction_class_zh": "丙二烯/炔烃来源炔丙基自由基氰化",
    "reaction_class_en": "Propargylic-radical cyanation from allenes/alkynes",
    "status": "refusal_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1002/anie.202505939",
    "condition_summary_zh": "涉及炔丙基自由基与氢原子转移路径，反应中心定义不同。",
    "condition_summary_en": "A propargylic radical/HAT pathway uses a different reaction-centre definition.",
    "boundary_zh": "仅作反应类别拒绝验证。",
    "boundary_en": "Reaction-class refusal validation only."
  },
  {
    "system_id": "sulfonylcyanation_vinylarenes",
    "title_zh": "乙烯基芳烃不对称磺酰氰化",
    "title_en": "Asymmetric sulfonylcyanation of vinylarenes",
    "reaction_class_zh": "磺酰自由基烯烃加成/铜捕获",
    "reaction_class_en": "Sulfonyl-radical alkene addition/copper capture",
    "status": "evidence_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1002/cctc.202500258",
    "condition_summary_zh": "自由基来源和烯烃加成序列不同。",
    "condition_summary_en": "Different radical source and alkene-addition sequence.",
    "boundary_zh": "仅显示文献边界，不进行数值迁移。",
    "boundary_en": "Literature boundary only; no numerical transfer."
  },
  {
    "system_id": "allenic_ch_cyanation",
    "title_zh": "联烯 C(sp2)-H 键不对称氰化",
    "title_en": "Enantioselective cyanation of allenic C(sp2)-H bonds",
    "reaction_class_zh": "联烯 C-H 活化与轴手性构建",
    "reaction_class_en": "Allenic C-H activation and axial-chirality construction",
    "status": "refusal_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1021/acscatal.5c01796",
    "condition_summary_zh": "轴手性终点与目标中心手性终点不同。",
    "condition_summary_en": "Axial-chirality endpoint differs from the target central-chirality endpoint.",
    "boundary_zh": "硬拒绝体系。",
    "boundary_en": "Hard-refusal system."
  },
  {
    "system_id": "carbocyanation_dienes_vinylarenes",
    "title_zh": "二烯/乙烯基芳烃不对称碳氰化",
    "title_en": "Asymmetric carbocyanation of dienes/vinylarenes",
    "reaction_class_zh": "HAT 产生酰基/烷基自由基的烯烃碳氰化",
    "reaction_class_en": "HAT-derived acyl/alkyl-radical carbocyanation",
    "status": "evidence_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1021/acscatal.5c04586",
    "condition_summary_zh": "HAT 自由基生成和烯烃加成网络不同。",
    "condition_summary_en": "Different HAT radical-generation and alkene-addition network.",
    "boundary_zh": "只作机理压力测试，不合并标签。",
    "boundary_en": "Mechanistic stress test only; labels are not pooled."
  },
  {
    "system_id": "kharasch_haloalkylation",
    "title_zh": "光诱导铜催化 Kharasch 型卤烷基化",
    "title_en": "Photoinduced copper-catalyzed Kharasch-type haloalkylation",
    "reaction_class_zh": "非对称自由基卤烷基化",
    "reaction_class_en": "Non-asymmetric radical haloalkylation",
    "status": "evidence_only",
    "model_id": null,
    "quantitative_rows": 0,
    "condition_rows": 0,
    "outputs": [],
    "doi": "10.1021/jacs.5c05699",
    "condition_summary_zh": "成键步骤和目标函数不同，且不以 ee 为终点。",
    "condition_summary_en": "Different bond-forming step and objective; ee is not an endpoint.",
    "boundary_zh": "作为光诱导铜催化背景，不输出不对称预测。",
    "boundary_en": "Photochemical copper-catalysis background only; no asymmetric prediction."
  }
];
window.CHEMPREDICT_TERMS = [
  {
    "key": "DCM",
    "category": "solvent",
    "en": "DCM",
    "zh": "二氯甲烷"
  },
  {
    "key": "DCE",
    "category": "solvent",
    "en": "DCE",
    "zh": "1,2-二氯乙烷"
  },
  {
    "key": "CH3CN",
    "category": "solvent",
    "en": "CH3CN",
    "zh": "乙腈"
  },
  {
    "key": "CHCl3",
    "category": "solvent",
    "en": "CHCl3",
    "zh": "氯仿（三氯甲烷）"
  },
  {
    "key": "PhCl",
    "category": "solvent",
    "en": "PhCl",
    "zh": "氯苯"
  },
  {
    "key": "acetone",
    "category": "solvent",
    "en": "acetone",
    "zh": "丙酮"
  },
  {
    "key": "MTBE",
    "category": "solvent",
    "en": "MTBE",
    "zh": "甲基叔丁基醚"
  },
  {
    "key": "fac-Ir(ppy)3",
    "category": "photocatalyst",
    "en": "fac-Ir(ppy)3",
    "zh": "面式三(2-苯基吡啶)合铱(III)"
  },
  {
    "key": "[Ir(dFCF3ppy)2(bpy)]PF6",
    "category": "photocatalyst",
    "en": "[Ir(dFCF3ppy)2(bpy)]PF6",
    "zh": "六氟磷酸双(二氟三氟甲基苯基吡啶)(联吡啶)合铱(III)"
  },
  {
    "key": "4CzIPN",
    "category": "photocatalyst",
    "en": "4CzIPN",
    "zh": "2,4,5,6-四(9H-咔唑-9-基)间苯二腈"
  },
  {
    "key": "Eosin Y",
    "category": "photocatalyst",
    "en": "Eosin Y",
    "zh": "曙红 Y"
  },
  {
    "key": "5,7,12,14-Pentacenetetrone",
    "category": "photocatalyst",
    "en": "5,7,12,14-pentacenetetrone",
    "zh": "5,7,12,14-并五苯四酮"
  },
  {
    "key": "9,10-Diphenylanthracene",
    "category": "photocatalyst",
    "en": "9,10-diphenylanthracene",
    "zh": "9,10-二苯基蒽"
  },
  {
    "key": "none",
    "category": "generic",
    "en": "none",
    "zh": "无"
  },
  {
    "key": "Cu(CH3CN)4PF6",
    "category": "copper_source",
    "en": "Cu(CH3CN)4PF6",
    "zh": "六氟磷酸四(乙腈)合铜(I)"
  },
  {
    "key": "Cu(CH3CN)4BF4",
    "category": "copper_source",
    "en": "Cu(CH3CN)4BF4",
    "zh": "四氟硼酸四(乙腈)合铜(I)"
  },
  {
    "key": "CuCN",
    "category": "copper_source",
    "en": "CuCN",
    "zh": "氰化亚铜"
  },
  {
    "key": "CuCl",
    "category": "copper_source",
    "en": "CuCl",
    "zh": "氯化亚铜"
  },
  {
    "key": "CuBr",
    "category": "copper_source",
    "en": "CuBr",
    "zh": "溴化亚铜"
  },
  {
    "key": "CuCl2",
    "category": "copper_source",
    "en": "CuCl2",
    "zh": "氯化铜(II)"
  },
  {
    "key": "CuBr2",
    "category": "copper_source",
    "en": "CuBr2",
    "zh": "溴化铜(II)"
  },
  {
    "key": "L1",
    "category": "ligand",
    "en": "L1",
    "zh": "手性配体 L1（原文编号，结构见 SI）"
  },
  {
    "key": "L2",
    "category": "ligand",
    "en": "L2",
    "zh": "手性配体 L2（原文编号，结构见 SI）"
  },
  {
    "key": "L3",
    "category": "ligand",
    "en": "L3",
    "zh": "手性配体 L3（原文编号，结构见 SI）"
  },
  {
    "key": "L4",
    "category": "ligand",
    "en": "L4",
    "zh": "手性配体 L4（原文编号，结构见 SI）"
  },
  {
    "key": "L5",
    "category": "ligand",
    "en": "L5",
    "zh": "手性配体 L5（原文编号，结构见 SI）"
  },
  {
    "key": "L6",
    "category": "ligand",
    "en": "L6",
    "zh": "手性配体 L6（原文编号，结构见 SI）"
  },
  {
    "key": "NHP ether",
    "category": "reactant",
    "en": "NHP ether",
    "zh": "N-羟基邻苯二甲酰亚胺醚"
  },
  {
    "key": "P(OEt)3",
    "category": "reagent",
    "en": "P(OEt)3",
    "zh": "亚磷酸三乙酯"
  },
  {
    "key": "TMSCN",
    "category": "reagent",
    "en": "TMSCN",
    "zh": "三甲基氰硅烷"
  },
  {
    "key": "N2",
    "category": "atmosphere",
    "en": "N2",
    "zh": "氮气"
  },
  {
    "key": "HPLC",
    "category": "analysis",
    "en": "HPLC",
    "zh": "高效液相色谱"
  },
  {
    "key": "ee",
    "category": "endpoint",
    "en": "ee",
    "zh": "对映体过量"
  },
  {
    "key": "yield",
    "category": "endpoint",
    "en": "yield",
    "zh": "分离产率"
  },
  {
    "key": "qmdesc",
    "category": "software",
    "en": "qmdesc",
    "zh": "机器学习量子描述符预测器"
  },
  {
    "key": "DBSTEP",
    "category": "software",
    "en": "DBSTEP",
    "zh": "分子立体参数计算工具"
  },
  {
    "key": "XGBoost",
    "category": "software",
    "en": "XGBoost",
    "zh": "极端梯度提升树"
  },
  {
    "key": "RDKit",
    "category": "software",
    "en": "RDKit",
    "zh": "开源化学信息学工具包"
  }
];
