# ChemPredict v4.4.0 数据卡

## 1. 数据用途

公开数据用于复现目标反应的标签转录、结构/条件描述符、冠军-挑战者验证、适用域门控和前瞻盲测记录。只有目标 NHP 醚脱氧不对称氰化体系进入数值训练；相关反应文献不得与其直接合并。

## 2. 数据清单

| 文件 | 行数 | 角色 | 是否进入生产数值模型 |
| --- | ---: | --- | --- |
| `substrate_scope.csv` | 30 | 2a-2z 训练范围与 3a-3d 挑战范围 | 2a-2z 共 26 行 |
| `condition_screen.csv` | 33 | 单因素、对照与重复条件证据 | 否；仅作证据检索 |
| `mechanism_proxy_descriptors.csv` | 30 | 明确标注的二维经验代理 | 部分生产特征 |
| `rdkit_descriptors.csv` | 30 | 结构核验与挑战者特征 | 仅挑战者/质量控制 |
| `qmdesc_descriptors.csv` | 30 | ML 预测 B3LYP/def2-SVP 目标 | 仅挑战者 |
| `steric_descriptors.csv` | 30 | 产品骨架构象的 DBSTEP 代理 | 仅挑战者 |
| `external_gate_cases.csv` | 12 | 跨前体、自由基和反应体系门控测试 | 否 |
| `reaction_system_registry.*` | 9 个体系 | 定量、证据型和拒绝型注册 | 仅 1 个体系可定量 |
| `prospective_blind_test_template.csv` | 模板 | 独立实验冻结与回填 | 待新增前瞻数据 |

机器可读的实际行数、字段和状态由 `04_模型源码/data_pipeline/validate_data.py` 校验，不应仅依赖本表。

## 3. 来源与转录

- 目标标签来源：DOI `10.1021/acs.orglett.5c05116` 的主文和 Supporting Information。
- Hammett 常数来源：DOI `10.1021/cr00002a004`。
- PubChem 属性通过 PUG REST 记录，用于分子式与标识符交叉检查。
- RDKit、qmdesc 和 DBSTEP 的版本与语义见 `08_说明文档/THIRD_PARTY_NOTICES.md`。
- 每条参考文献的 DOI、用途、数值训练资格和访问日期见 `literature_registry.csv`；公开仓库不包含论文 PDF。

## 4. 标签与删失

产率与 ee 保持论文转录值，不为改善指标人工修改。条件筛选中的 `trace` 是删失观测，不等于精确的零；删失敏感性结果保存在 `07_验证结果/conditions/v4.4.0`。

## 5. 质量控制

- 30 个底物标识符唯一，标签限定在 0-100。
- 26 个训练样本按 10 个化学家族整组留出，避免同家族随机泄漏。
- RDKit 与 PubChem 对可注册化合物执行分子式交叉检查。
- qmdesc 与 DBSTEP 字段均记录真实计算语义，不将 ML 量子描述符称为现场 DFT，也不将产品骨架构象参数称为配体-过渡态参数。
- 挑战者只有通过预声明非退化标准才可晋级生产。

## 6. 已知偏差

数据来自单篇目标论文、单一协议和小样本化学空间。文献中的成功底物范围可能带有发表与选择偏差，低收率或失败组合覆盖不足。现有区间复用了同一论文的整组留出残差，不具备独立前瞻覆盖保证。

## 7. 权利边界

仓库许可证覆盖本项目原创代码、整理结构和原创注释，不改变论文、Supporting Information、数据库或第三方软件的原始权利。使用者应引用原始 DOI，并自行核对出版商和数据库的当前条款。

## 8. 外部数据贡献

建议使用 `prospective_blind_test_template.csv` 在实验前冻结协议、结构、预期适用域和预测版本，实验后再回填产率、ee、分析方法和失败原因。可识别个人、未公开专利或受限合作数据不得直接提交到公开 Issue。
