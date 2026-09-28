"""Small static Chinese entry page; all numbers come from the completed run."""

from html import escape


def render_index(summary: dict) -> str:
    cards = []
    for scenario in summary["scenarios"]:
        scores = scenario["quality"]
        bars = "".join(
            f'<div class="bar-row"><span>{escape(name)}</span><b>{value["psi"]:.4f}</b>'
            f'<meter min="0" max="4" value="{min(value["psi"], 4)}" aria-label="{name} PSI"></meter></div>'
            for name, value in scenario["columns"].items()
        )
        warning = "；".join(scenario["alerts"]) or "当前规则未触发告警，仍应持续观察。"
        cards.append(f'''<article class="scenario"><div class="eyebrow">{scenario["rows"]:,} 行当前数据</div>
<h2>{escape(scenario["title"])}</h2><p class="description">{escape(scenario["description"])}</p>
<div class="numbers"><div><strong>{scores["accuracy"]:.2%}</strong><span>准确率</span></div>
<div><strong>{scenario["drifted_count"]} / 5</strong><span>漂移特征</span></div></div>
<p class="secondary">F1 {scores["f1"]:.4f} · ROC AUC {scores["roc_auc"]:.4f}</p>
<div class="bars">{bars}</div><p class="notice">{escape(warning)}</p>
<a class="button" href="{scenario["id"]}.html">打开 Evidently 详细报告 →</a>
<a class="json" href="{scenario["id"]}.json" download>下载指标 JSON</a></article>''')
    ref = summary["reference_quality"]
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ModelWatch · 模型值班室</title><link rel="icon" href="data:,"><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f7;color:#182a3c;font-family:"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.7}}
header{{padding:21px max(5vw,20px);border-bottom:1px solid #dce3e9;background:white;display:flex;justify-content:space-between;gap:16px}}
header span{{color:#64778a;font-size:14px}}main{{max-width:1440px;margin:0 auto;padding:48px 32px 36px}}.eyebrow{{color:#536f89;font-size:12px;letter-spacing:.08em}}
h1{{font-size:42px;line-height:1.3;margin:12px 0}}.intro{{max-width:850px;color:#536578;margin-bottom:28px}}
.meta{{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0 32px}}.meta span{{border:1px solid #d5dfe7;background:white;border-radius:6px;padding:7px 13px;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}}.scenario{{padding:26px;background:white;border:1px solid #dbe3e9;border-top:4px solid #286895;border-radius:10px}}
h2{{font-size:24px;margin:8px 0}}.description{{min-height:58px;font-size:14px;color:#5b6c7e}}.numbers{{display:flex;justify-content:space-between;gap:10px;padding:15px 0;border-bottom:1px solid #e6ebef}}
.numbers strong{{font-size:30px;display:block;font-variant-numeric:tabular-nums}}.numbers span,.secondary{{font-size:13px;color:#647587}}.bar-row{{display:grid;grid-template-columns:1fr 64px;gap:4px 10px;margin:10px 0;font-size:12px}}.bar-row b{{text-align:right;font-variant-numeric:tabular-nums}}meter{{grid-column:1/-1;width:100%;height:10px}}.notice{{min-height:83px;background:#edf3f8;border-left:3px solid #5283a6;padding:11px;font-size:13px}}
a{{color:#245f8b}}.button{{display:block;background:#1f5d8b;color:white;text-align:center;padding:11px 8px;border-radius:5px;font-size:13px;text-decoration:none}}.json{{display:block;margin-top:12px;font-size:12px;text-align:center}}.lesson{{margin-top:24px;background:#e5edf4;padding:26px;border-radius:8px}}.lesson h2{{font-size:20px}}.lesson p{{margin:7px 0;font-size:14px}}footer{{color:#627487;font-size:12px;margin-top:25px}}@media(max-width:1050px){{.grid{{grid-template-columns:1fr}}.description,.notice{{min-height:0}}main{{padding:28px 20px}}h1{{font-size:30px}}header{{flex-direction:column;gap:0}}}}
</style></head><body><header><b>ModelWatch / 模型值班室</b><span>Evidently 0.7.23 · 开源复现与工程扩展</span></header>
<main><div class="eyebrow">AI ENGINEERING / MODEL MONITORING</div><h1>模型上线以后，怎么知道它变差了？</h1>
<p class="intro">在同一个模型上观察三种批次。输入分布变化与预测效果下降是两件事：既要观察特征，也要在真实标签到达后检查预测质量。此页使用原创合成数据演示，所有指标由本次程序实际计算。</p>
<div class="meta"><span>训练 6,000 行 · 参考 2,000 行</span><span>参考准确率 {ref["accuracy"]:.2%}</span><span>随机种子 {summary["seed"]}</span><span>PSI ≥ 0.2 判定单列漂移</span></div>
<section class="grid">{"".join(cards)}</section><section class="lesson"><h2>读报告时先回答这三个问题</h2>
<p>① 传感器偏移改变了哪些输入？点开报告中的特征分布图进行对照。</p>
<p>② 标签关系反转时，为什么输入漂移仍可能为零？输入监测看不到条件关系的变化。</p>
<p>③ 如果拿不到真实标签，哪些质量指标暂时无法计算？不要把漂移当作准确率的替代品。</p>
<p>告警规则：至少 2 / 5 个输入特征发生漂移，或准确率较参考批下降至少 5 个百分点。阈值用于教学，未经过真实业务校准。</p>
<p>PSI 条形图为方便比较在 4 截断，右侧数值保留真实结果。正常与两个异常场景共享同一批当前样本，是有意的配对实验，不是三批独立生产流量。</p></section>
<footer>生成于 {escape(summary["generated_at"])} · <a href="summary.json" download>下载汇总 JSON</a> · <a href="upstream/iris-drift.html">查看上游 Hello World 复现</a><br>
使用 Evidently 计算漂移与报告，scikit-learn 训练逻辑回归；本项目新增数据隔离、场景设计、规则与教学，未宣称自研这些底层算法。</footer></main></body></html>'''
