# 知答 SupportLab

**面向 AI 应用开发实习的本地作品：把客户问题分类、找到处理依据，并把人工处理过程记录成工单。**

技术：Python · FastAPI · scikit-learn · SQLite · 原生 HTML/CSS/JavaScript。

这是可运行的教学作品集基线，采用 AI 辅助开发。业务规范和语料均为原创模拟数据，不代表真实商家政策。目前没有接入生成式大模型、BERT、向量数据库或真实订单服务。

## 界面预览

![问题分析、原文依据与工单入口](output/playwright/05-answer.png)

[查看效果评测截图](output/playwright/02-evaluation.png) · [查看移动布局](output/playwright/04-mobile-workspace.png)

此仓库提供源码与演示截图，尚未部署在线体验地址。

## 现在开始

1. 首次下载：安装 Python 3.14，在本项目目录双击 `setup.cmd` 安装依赖。然后双击 **启动项目.cmd**（或 `start.cmd`）；已安装环境可直接启动。
2. 等待 Edge 自动打开 `http://127.0.0.1:8765`。
3. 点击“退款进度”，再点击“分析并查找依据”。
4. 按 [第一课](docs/01-第一课与学习路线.md) 完成一次工单闭环。

依赖安装需要网络；安装完成后的本地运行不需要 GPU、网络或 API Key。启动时会训练96条小样本。窗口中按 Ctrl+C，或双击“停止项目.cmd”可停止服务，数据会保留。若本地服务已启动，入口会直接打开页面。

GitHub版本不包含运行数据库。首次启动会初始化12篇模拟规范，问题与工单记录为空；截图中的问题、工单与额外规范来自本机验收演示，不是真实客户数据。

## 你能演示什么

| 功能 | 实现 | 如何观察 |
|---|---|---|
| 6类问题自动分诊 | 字符 TF-IDF + 逻辑回归 | 提问后看建议分类与模型分数 |
| 规范检索对比 | TF-IDF、BM25、RRF 融合 | 工作台切换方法，评测页看指标 |
| 回答依据可查 | 展示最相关规范完整原文 | 右侧展开来源，核对摘录 |
| 依据不足处理 | 相似度阈值，小分数转人工 | 问“明天天气怎么样” |
| 人工确认与工单流转 | SQLite事务、状态校验、事件记录 | 创建、接单、关闭、重新打开 |
| 导入新知识 | TXT/Markdown、查重、原子更新索引 | 导入 examples/member-policy.md |
| 反馈闭环 | 正负反馈保存，重复反馈更新 | 点击“有帮助”或“不够相关” |
| 可复现评测 | 固定语料、随机种子、数据摘要、逐条结果 | 评测页下载 JSON |

## 本机验证结果

2026-09-18，Windows / Python 3.14，固定模拟开发评测集：

- 自动测试：**16项通过**。
- 分类：24题中23题正确，准确率 **95.83%**，Macro-F1 **0.9577**。
- 检索：三种方法的 Recall@3 均为 **100%（24/24）**。
- MRR@3：TF-IDF **0.9583**；BM25 **0.9792**；RRF **0.9583**。
- 相似度阈值：24个已知问题中19个提供原文依据，覆盖率 **79.17%**；6个简单无关问题全部暂不回答。

**这些不是商业效果或上线指标。** 数据量小、问题由开发者编写、词汇与规范接近；没有独立盲测，也没有真实客户验证。已经看过的评测集应视为开发集，下一阶段须另外建立盲测集。检索进入前三名不等于第一条答案正确，相似度和分类分数也不是正确率。

## 文件地图

```text
app/
  dataset.py       训练语料、评测语料、模拟规范
  engine.py        分类器、两种检索、融合、依据阈值
  main.py          HTTP接口、输入验证、工单状态流转
  storage.py       SQLite表、事务、文档初始化
  evaluation.py    训练并评测、逐条报告
static/            浏览器界面、交互和样式
tests/             自动测试，使用独立临时数据库
docs/              第一课、代码导读、面试指南、验收记录
examples/          可以亲手导入的练习资料
data/              本机数据库与评测报告，不提交Git
launch.py          启动服务并打开Edge
requirements-lock.txt  本机验证过的依赖版本
```

## 自己运行检查

双击 `check.cmd`；或在项目文件夹空白处右键“在终端中打开”，复制：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m app.evaluation
```

第二条命令保存 `data/evaluation.json`。已验证的基线报告随源码保存在 [docs/benchmark-v1.json](docs/benchmark-v1.json)。页面重新运行的结果保存在服务内存中，可点击下载；CLI生成的报告会在下次启动时载入。训练数据改动后需要重启服务；文档导入则立即生效。

## 换一台电脑

需要 Python 3.14（当前已验证版本），建议使用相同版本复现。复制项目源码后双击 `setup.cmd`，再双击 `start.cmd`。`.venv` 不可直接跨电脑复制。若下载慢，可在项目终端使用：

```powershell
.\.venv\Scripts\python.exe -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-lock.txt
```

## 当前边界与升级顺序

1. 单机、单进程、只监听127.0.0.1；没有登录、权限隔离、多人协作和生产运维。不能直接暴露到公网。
2. 中文字符匹配不能真正理解所有同义表达、否定和多意图问题；分类强制在6类中选一类，因此未知输入应结合低分提醒和人工判断。
3. 风险优先级使用明确关键词规则，有漏报可能；没有训练优先级模型，也不会自动退款、封号或发消息。
4. 导入单位是一篇规范，没有长文分块、PDF/OCR和文档版本管理。每篇最多12,000字，最多300篇。
5. 反馈只是保存，尚无自动再训练。分类确认也未形成独立标注工作流。
6. 第一阶段先学懂并改好基线；第二阶段增加更多独立语料、同义改写和多意图评测；第三阶段再实测语义向量与重排；确有需要时接生成模型并验证引用忠实度。

## 学习资料

- [第一课与六阶段路线](docs/01-第一课与学习路线.md)
- [架构和代码导读](docs/02-架构与代码导读.md)
- [三分钟演示与面试准备](docs/03-演示与面试准备.md)
- [交付验收与真实问题](docs/04-验收记录.md)
- [scikit-learn TF-IDF 官方文档](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [训练、验证和测试的划分](https://scikit-learn.org/stable/modules/cross_validation.html)
- [FastAPI 测试官方文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [语义检索升级方向：Sentence Transformers](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
