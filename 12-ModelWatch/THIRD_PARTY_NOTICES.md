# 第三方来源与复用边界

## Evidently

- 项目：https://github.com/evidentlyai/evidently
- 示例固定 commit：`34771fe41c08ca074d96a52aaf4a45cd640cbaf5`。
- 文件：README.md 的 “Data and ML evals” 示例。
- 许可证：Apache License 2.0，原文保留在 [LICENSE-Evidently.txt](upstream/LICENSE-Evidently.txt)。
- 原始 README 快照：[README-Evidently.md](upstream/README-Evidently.md)。其中链接按上游仓库解释，快照不是本项目入口。
- 本地变更：示例代码包装成可执行函数，新增输出路径、运行摘要和遥测关闭。核心数据切片、PSI 预设和报告调用未替换。
- 运行版本：PyPI `evidently==0.7.23`，安装项见 requirements-lock.txt。
- `reports/*.html` 使用 Evidently 提供的嵌入式可视化资源。本项目没有声称自研该前端或漂移算法。

## scikit-learn

- 项目：https://github.com/scikit-learn/scikit-learn
- 实际运行：`scikit-learn==1.9.1`。
- 许可证：BSD 3-Clause，来自已安装发行包的原文保留在 [LICENSE-scikit-learn.txt](upstream/LICENSE-scikit-learn.txt)。
- 用途：StandardScaler、LogisticRegression、评价指标；官方复现使用 `datasets.load_iris()`。

## Iris 数据（仅官方示例复现）

- 归属：R. A. Fisher，Iris (1936)。UCI 标识：https://doi.org/10.24432/C56C76。
- [UCI 数据页面](https://archive.ics.uci.edu/dataset/53/iris) 标注 CC BY 4.0：[许可说明](https://creativecommons.org/licenses/by/4.0/)。
- 本次实际加载的是 scikit-learn 内置版本。[官方说明](https://scikit-learn.org/stable/datasets/toy_dataset.html#iris-plants-dataset) 指出它与 Fisher/R 版本一致，和 UCI 原始文件存在两个数据点的校正差别。未下载或声称它是 UCI 文件的逐字节副本。
- 本项目不单独打包原始 Iris CSV；复现 HTML/JSON 包含该数据的统计衍生结果，保留上述作者、版本差异和许可链接。

## ModelWatch 合成数据与新增内容

模型值班室自己的三个场景完全由 `modelwatch/data.py` 生成，分布、标签规则和种子公开，不使用他人私有设备、客户或个人资料。新增代码与文档采用 Apache-2.0；第三方组件仍适用各自许可证。

来源核验日期：2026-09-28（北京时间）。锁文件记录传递依赖版本；未将整个虚拟环境或第三方二进制包复制进仓库。
