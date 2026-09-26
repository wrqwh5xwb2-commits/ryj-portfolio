# 纸境 ScanLab · OpenCV 文档扫描实验室

把拍歪的平面纸张拉正，比较彩色、灰度增强与黑白扫描结果。这个项目把传统计算机视觉算法做成了能操作、能观察中间结果、能复现评测的本机工作台。

**技术栈：Python · OpenCV · NumPy · FastAPI · 原生 JavaScript / Canvas**

基础版本采用 AI 辅助开发，面向学习和实习作品展示。没有使用深度学习模型、OCR 或外部推理 API；尚未通过真实手机照片集验证。

![工作台实际截图](output/playwright/workspace.png)

## 能做什么

- 自动寻找文档四角；找错时拖动角点，或输入百分比坐标重新校正。
- 用四点透视变换拉正纸张，支持自动估计、A4 竖向和横向比例。
- 比较彩色校正、局部光照归一化与 CLAHE 灰度增强、自适应二值化。
- 查看 Canny 边缘图、候选数、区域占比、清晰度提示与处理时间。
- 下载 PNG 或导出包含角点、单应矩阵和参数的 JSON。
- 浏览固定合成评测集的逐条结果，保留自动定位失败案例。

## 第一次运行（Windows）

1. 安装 Python。本机验证版本为 **Python 3.14 / OpenCV 5.0.0**，完整版本见 `requirements-lock.txt`。安装 Python 时勾选 Add Python to PATH。
2. 下载完整作品集并解压，进入 `10-ScanLab` 文件夹。不要单独下载 HTML 文件。
3. 双击 `setup.cmd` 安装依赖。首次需要联网；完成后示例与处理均可离线使用。
4. 双击 `启动项目.cmd`，浏览器会打开 **http://127.0.0.1:8770**，优先使用 Edge。
5. 点击「倾斜文档」，切换输出模式并下载结果。停止时在服务窗口按 `Ctrl+C`，或者双击 `停止项目.cmd`。

命令行等价操作：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe launch.py
```

端口冲突可运行 `python launch.py --port 8771`（需使用已安装依赖的 Python）。默认只监听本机，不是公网网站；GitHub 展示源码、截图与文档，不会执行 Python 后端。

## 验证与测量

双击 `check.cmd`，或运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m app.evaluate
```

当前基线：**15 项自动测试通过**。覆盖四点映射、角点排序、非法几何、空白图回退、二值结果、A4 比例、EXIF 旋转、透明背景、API 参数与本机访问限制。

| 固定合成开发评测 | 结果 |
| --- | --- |
| 找到某个四边形 | 24 / 24 |
| 定位通过：平均角点误差 ≤ 对角线 2.5%，且区域 IoU ≥ 0.90 | **20 / 24** |
| 纯色负例转入手动定位 | 4 / 4 |
| 失败场景 | 4 张边缘遮挡图 |

**找到四边形不等于找对文档。** 数据来自同一合成生成器，不能解释成实拍准确率、OCR 识别率或独立测试集性能。检测时间仅反映本机运行，不含解码、增强和网络传输；详细时延及逐条结果见 [benchmark.json](docs/benchmark.json)。没有量化增强后的文字可读性。

评测集使用 6 种场景 × 4 个固定种子；内置演示图片使用另一种子。生成器与原始角点均随项目提供。重新生成示例：`python -m app.synthetic`。

## 学习与面试

- [第一课与循序练习](docs/01-从零上手.md)
- [架构、算法与数据流](docs/02-技术说明.md)
- [演示、面试问题与贡献记录](docs/03-面试演示.md)
- [验证记录与已知边界](docs/04-验证记录.md)

## 使用边界

适合背景相对简单、边缘完整的单张平面纸。曲面书页、纸张出框、遮挡、反光、复杂背景、多张文档可能导致选错区域；应人工检查四角。不会纠正文字阅读方向，不会恢复失焦或被遮住的文字。

自动宽高比按图中边长估计，不是物理尺寸测量。清晰度阈值是启发式提示，不是识别置信度。工作图和输出最长边上限 1800 像素；文件上限 12 MiB、解码前像素上限 2000 万、宽高至少 64 像素。支持 JPG、PNG、WebP。

应用不建立扫描历史、不向第三方发送图片；框架处理较大上传时可能使用系统临时文件，请求结束关闭上传句柄。下载文件由浏览器保存。本地服务仅供个人演示，没有公网服务的鉴权、配额或多人任务队列。

## 参考

- [OpenCV：几何与透视变换](https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html)
- [OpenCV：轮廓特征与多边形逼近](https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html)
- [OpenCV：图像阈值与自适应阈值](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html)
