# 第三方材料与许可说明

本目录中的源代码、模型产物和文档与所附论文 PDF 的权利状态相互独立。下载的论文与补充信息仍由作者、出版商及其页面所示许可条款约束；本项目不改变、转授或扩大这些权利。

当前发布状态：v4.4.0 本轮不构建或分发 APK；历史 Android 文件不进入 v4.4 发布包。

## 运行时与开发依赖

- 网页运行时为原生 HTML/CSS/JavaScript，不调用云端推理服务，也不上传实验数据。
- 历史 Android 工程使用系统 WebView；本轮仅交付经过浏览器验收的静态网站。
- 结构核验使用 RDKit 2025.09.6。RDKit 项目采用 BSD 3-Clause 许可，详见 <https://github.com/rdkit/rdkit/blob/master/license.txt>。
- qmdesc 1.0.6 用于机器学习量子描述符预测，项目采用 MIT 许可：<https://github.com/yanfeiguan/qmdesc>。论文 DOI：<https://doi.org/10.1039/D0SC04823J>。
- DBSTEP 1.1.0 用于构象立体参数代理，项目采用 MIT 许可：<https://github.com/patonlab/DBSTEP>。论文 DOI：<https://doi.org/10.1021/acs.jcim.0c01367>。
- XGBoost 3.3.0 采用 Apache License 2.0：<https://github.com/dmlc/xgboost/blob/master/LICENSE>。
- PyTorch 2.13.0 用于 qmdesc 检查点推理，采用 BSD-style 许可：<https://github.com/pytorch/pytorch/blob/main/LICENSE>。
- scikit-learn 1.9.0 由 XGBoost Python 包装器使用，采用 BSD 3-Clause 许可：<https://github.com/scikit-learn/scikit-learn/blob/main/COPYING>。
- 公开化学属性通过 NCBI PubChem PUG REST 获取，访问接口和返回 URL 已逐行保存在 `pubchem_properties.csv`。使用时仍应遵守 NCBI/PubChem 的当前政策。
- 可选的 Word 和 Excel 构建工具不属于公开运行时，也不嵌入静态网站。

## 文献文件

- `背景_Kharasch_photoinduced_copper_catalysis.pdf` 首页标示 CC BY 4.0。
- ACS、Nature 及其他出版物的主文和 Supporting Information 许可可能不同，应以每个 PDF 首页、下载页或 DOI 页面为准。
- 发布到公开 GitHub 仓库前，建议仅提交可再分发的文件、书目信息、校验值和下载脚本；对许可不明确的 PDF 使用 DOI 链接替代二次上传。

完整书目、用途和是否进入数值训练见 `03_数据/整理数据/literature_registry.csv`。
