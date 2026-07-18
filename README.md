# ChemPredict v4.4.0

[English](README.en.md) | 中文

[![CI](https://github.com/yezhanggong/ChemPredict/actions/workflows/ci.yml/badge.svg)](https://github.com/yezhanggong/ChemPredict/actions/workflows/ci.yml)
[![Pages](https://github.com/yezhanggong/ChemPredict/actions/workflows/pages.yml/badge.svg)](https://yezhanggong.github.io/ChemPredict/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

ChemPredict 是面向不对称自由基氰化研究的离线证据检索、适用域判断与候选排序工具。v4.4.0 以 Yu 等人在 *Organic Letters* 2026 报道的 NHP 醚脱氧不对称氰化为唯一可定量体系；另外 8 个相关体系仅用于证据检索或跨体系拒绝，不进行数值合并。

> 本项目是可审计的研究原型，不是任意不对称反应的通用预测器。预测不能替代前瞻实验、风险评估或实测表征。

## 在线使用

- 在线工作台：[https://yezhanggong.github.io/ChemPredict/](https://yezhanggong.github.io/ChemPredict/)
- 本地离线：直接打开 `05_网站/index.html`
- 本地服务器：在 PowerShell 中运行 `./05_网站/run-local.ps1 -Port 8788`

网站只在浏览器本地运行，不调用远程推理 API，也不上传结构或实验计划。

## 当前能力

| 层级 | 数据基础 | 输出 | 限制 |
| --- | ---: | --- | --- |
| NHP 醚脱氧不对称氰化 | 26 条同协议训练记录 | 产率、ee、经验区间、适用域等级 | 仅固定协议和仲苄基 NHP 醚 |
| 条件证据 | 33 条单因素/对照记录 | 溶剂、光催化剂、铜源、配体和温度的文献观测 | 不对任意多因素组合做加和外推 |
| 相关反应体系 | 8 个体系注册项 | 证据摘要或拒绝理由 | 不输出跨体系数值预测 |
| 虚拟候选库 | 预计算结构特征 | 候选排序与实验计划导出 | 只用于优先级，不等同于反应成功概率 |

## 生产模型与验证

v4.4.0 使用预声明的冠军-挑战者规则。qmdesc、DBSTEP、结构分化特征和 XGBoost 挑战者均完成训练与序列化，但没有同时满足“嵌套整组留出 MAE 至少改善 0.30，且 RMSE、最大绝对误差不变差”，因此生产模型继续使用 v4.3 冠军。

| 目标 | 生产模型 | 嵌套 MAE | RMSE | 最大绝对误差 | R2 | Spearman |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 产率 | Ridge | 8.029 | 10.948 | 30.275 | -0.343 | 0.015 |
| ee | RBF kernel ridge，先变换为 ΔΔG‡ | 6.180 | 10.993 | 45.207 | 0.065 | 0.620 |

产率的 R2 为负且排序相关性接近零，因此只能作为低风险候选的弱排序信号。ee 在多数化学家族中更有排序信息，但仍存在 45.207 点的单样本最大误差。完整定义、异常点和区间策略见 [模型卡](08_说明文档/模型卡_v4.4.0.md)。

## 适用域

只有同时满足以下条件时才允许定量输出：

1. 前体为目标协议中的仲苄基 NHP 醚。
2. 自由基为碳-芳基仲苄基自由基。
3. 反应家族为目标脱氧不对称氰化。
4. 条件改变不超过一个因素。
5. 描述符距离和预声明高风险规则允许输出。

强对位吸电子底物和环状苄基单例会进入 D 级警告或拒绝；其他前体、自由基类别和反应网络拒绝数值外推。

## 快速复现

最小测试环境只需要 Python 3.12、Node.js 22.13+：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-ci.txt
corepack enable
pnpm install --frozen-lockfile
python -m unittest discover -s "04_模型源码/tests" -p "test_*.py" -v
```

浏览器验收：

```bash
pnpm exec playwright install chromium
python -m http.server 8788 --directory "05_网站"
# 另开终端
pnpm test:ui
```

完整描述符生成和挑战者训练依赖 RDKit、qmdesc、DBSTEP、XGBoost 与 PyTorch，步骤见 [工具搭建流程](08_说明文档/工具搭建流程_v4.4.0.md)。

## 数据与文献

- 数值标签来自 DOI [`10.1021/acs.orglett.5c05116`](https://doi.org/10.1021/acs.orglett.5c05116) 的主文与 Supporting Information 转录。
- 其他论文只用于方法设计、机理边界或外部拒绝案例，不与目标体系数值合并。
- 仓库不重新分发论文 PDF；DOI、数据用途和访问日期记录在 `03_数据/整理数据/literature_registry.csv`。
- 数据字段、来源、权利边界和完整性检查见 [数据卡](DATA_CARD.md)。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| `03_数据/整理数据` | 文献转录、描述符、反应体系注册表、双语词典和前瞻盲测模板 |
| `04_模型源码` | 数据管线、训练、推理、适用域、测试和发布工具 |
| `05_网站` | 中英文离线工作台和序列化生产模型 |
| `07_验证结果` | v4.4 指标、留出预测、晋级决策、门控与界面验证证据 |
| `08_说明文档` | 模型卡、构建流程、语义审计和版本对比 |

## 持续改进与参与

后续版本将继续优化模型结构、特征参数、适用域与不确定性校准，并优先引入预注册的独立前瞻数据。欢迎化学、化学信息学和机器学习研究者通过 [GitHub Discussions](https://github.com/yezhanggong/ChemPredict/discussions) 讨论方法，通过 [Issues](https://github.com/yezhanggong/ChemPredict/issues) 提交复现实验、外部验证、数据纠错或功能建议。贡献标准见 [CONTRIBUTING.md](CONTRIBUTING.md)，阶段目标见 [ROADMAP.md](ROADMAP.md)。

## 引用与许可

引用信息见 [`CITATION.cff`](CITATION.cff)。代码与原创文档按 [Apache License 2.0](LICENSE) 发布；文献、第三方数据和软件仍受各自权利与许可约束，详见 [第三方说明](08_说明文档/THIRD_PARTY_NOTICES.md)。

氰化物与 TMSCN 相关实验必须遵循所在机构的 SOP、风险评估、通风监测和废物处置要求。本仓库不提供具体投料、放大或安全替代建议。
