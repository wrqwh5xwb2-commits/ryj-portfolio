# 上游与复现记录

- 原项目：[RapidAI/RapidOCR](https://github.com/RapidAI/RapidOCR)
- 选取版本：`v3.9.2`，PyPI `rapidocr==3.9.2`
- Git commit：`095232a4c94f7f0e6600ba5bba1177010ad696d4`
- 参考示例：[该版本 README 的 Usage](https://github.com/RapidAI/RapidOCR/blob/095232a4c94f7f0e6600ba5bba1177010ad696d4/README.md)
- 上游许可证：[Apache-2.0 原文](RapidOCR-LICENSE)，保留版权声明。
- 查询日期：2026-09-28。

`quickstart.py` 改编官方入门调用，保留 `RapidOCR()` 与 `engine(image)`；用自制中文图片替换远端图片，增加结果 JSON 序列化，省略需要字体文件的 `vis()`。运行 `python upstream/quickstart.py`，实际输出存于 `docs/upstream-run.json`，成功识别9行。

本项目通过锁定 PyPI 包调用上游能力，没有复制整套上游实现，也没有重新训练模型。源代码和许可证固定到上面的 Git 提交；PyPI 安装包版本与实际模型校验和另行记录。上游 Git 仓库直接 clone 在本机超时，因此通过 GitHub 连接器读取固定提交、许可证与示例，并从 PyPI 安装同版本发行包完成复现。

该提交 README 的许可说明明确：OCR模型版权归百度，上游工程脚本版权归仓库作者，项目采用Apache-2.0。当前主分支网页曾显示模型许可链接，但对应文件API返回404，因此本项目不把该缺失文件当作许可依据，而保留实际固定版本说明。权重通过上游发行包安装，不在此仓库重新发布。

## 实际运行使用的模型

- `PP-OCRv6_det_small.onnx`：文本区域检测。
- `ch_ppocr_mobile_v2.0_cls_mobile.onnx`：文本行方向分类。
- `PP-OCRv6_rec_small.onnx`：文字识别。

三个文件的大小和SHA-256见 `docs/model-manifest.json`。ONNX Runtime执行推理；不需要GPU或API Key。

## 新增内容

| 上游提供 | OCRDesk新增 |
| --- | --- |
| 检测、方向分类、识别与模型文件 | 本机API、图片格式和尺寸校验 |
| Python推理接口及模型分数 | 文字框联动、逐行校对、核对状态 |
| 原始OCR结果 | TXT、JSON、CSV导出，CSV公式保护 |
| 工程库 | 中文操作页、合成评测与关键行为测试 |

新增基础版本使用AI辅助开发；用户后续独立改进应另外记录。此项目不是RapidAI官方产品，不宣称模型为自研。
