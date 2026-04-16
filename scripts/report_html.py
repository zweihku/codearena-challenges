#!/usr/bin/env python3
"""
CodeArena HTML 报告生成器
把 evaluate.py 的 JSON 报告转成 DESIGN.md 风格的 HTML 页面。

用法：
    python report_html.py --input report.json --output report.html
    python report_html.py --input report.json --output report.html --open
"""

import argparse
import json
import math
import os
import sys
import webbrowser
from pathlib import Path
from datetime import datetime


def score_color(score: float) -> str:
    if score >= 7:
        return "#16a34a"
    elif score >= 5:
        return "#ca8a04"
    else:
        return "#dc2626"


def score_label(score: float) -> str:
    if score >= 8:
        return "优秀"
    elif score >= 7:
        return "良好"
    elif score >= 5:
        return "合格"
    elif score >= 3:
        return "待提升"
    else:
        return "不足"


def radar_svg(scores: dict, size: int = 280) -> str:
    """生成 SVG 雷达图"""
    cx, cy = size // 2, size // 2
    r = size // 2 - 40
    labels = list(scores.keys())
    values = list(scores.values())
    n = len(labels)
    angle_step = 2 * math.pi / n

    # 背景网格
    grid_lines = []
    for level in [2, 4, 6, 8, 10]:
        points = []
        for i in range(n):
            angle = -math.pi / 2 + i * angle_step
            x = cx + (r * level / 10) * math.cos(angle)
            y = cy + (r * level / 10) * math.sin(angle)
            points.append(f"{x:.1f},{y:.1f}")
        grid_lines.append(f'<polygon points="{" ".join(points)}" fill="none" stroke="#d4d4d4" stroke-width="1"/>')

    # 轴线
    axis_lines = []
    label_elems = []
    short_labels = {
        "结果正确性": "结果",
        "工程质量": "质量",
        "工程习惯": "习惯",
        "AI工具运用": "AI运用",
        "问题拆解": "拆解",
        "时间效率": "效率",
    }
    for i in range(n):
        angle = -math.pi / 2 + i * angle_step
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        axis_lines.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#d4d4d4" stroke-width="1"/>')

        lx = cx + (r + 24) * math.cos(angle)
        ly = cy + (r + 24) * math.sin(angle)
        label = short_labels.get(labels[i], labels[i][:4])
        anchor = "middle"
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        label_elems.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" fill="#525252" font-size="12" '
            f'font-family="Geist, sans-serif" text-anchor="{anchor}" dominant-baseline="central">{label}</text>'
        )

    # 数据多边形
    data_points = []
    dot_elems = []
    for i in range(n):
        angle = -math.pi / 2 + i * angle_step
        v = values[i]
        x = cx + (r * v / 10) * math.cos(angle)
        y = cy + (r * v / 10) * math.sin(angle)
        data_points.append(f"{x:.1f},{y:.1f}")
        dot_elems.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#0d9488"/>'
        )

    data_polygon = f'<polygon points="{" ".join(data_points)}" fill="rgba(13,148,136,0.15)" stroke="#0d9488" stroke-width="2"/>'

    svg = f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
    {"".join(grid_lines)}
    {"".join(axis_lines)}
    {data_polygon}
    {"".join(dot_elems)}
    {"".join(label_elems)}
    </svg>'''
    return svg


def generate_html(report: dict, participant: str) -> str:
    composite = report.get("composite_score", 0)
    color = score_color(composite)
    label = score_label(composite)

    dimensions = [
        ("result_score", "结果正确性"),
        ("engineering_quality_score", "工程质量"),
        ("engineering_habits_score", "工程习惯"),
        ("tool_usage_score", "AI工具运用"),
        ("problem_decomposition_score", "问题拆解"),
        ("efficiency_score", "时间效率"),
    ]

    # 分数条 HTML
    bars_html = ""
    radar_scores = {}
    for key, label_name in dimensions:
        d = report.get(key, {})
        s = d.get("score", 0) if isinstance(d, dict) else 0
        reason = d.get("reason", "") if isinstance(d, dict) else ""
        c = score_color(s)
        sl = score_label(s)
        pct = s * 10
        radar_scores[label_name] = s

        bars_html += f'''
        <div class="dim-row">
            <div class="dim-header">
                <span class="dim-name">{label_name}</span>
                <span class="dim-score" style="color:{c}">{s:.1f}</span>
                <span class="dim-label" style="color:{c}">{sl}</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width:{pct}%;background:{c}"></div>
            </div>
            <div class="dim-reason">{reason}</div>
        </div>'''

    # 雷达图
    radar = radar_svg(radar_scores)

    # 时间线
    moments = report.get("key_moments", [])
    timeline_html = ""
    for m in moments:
        timeline_html += f'''
        <div class="moment">
            <div class="moment-time">{m.get("time", "")}</div>
            <div class="moment-dot"></div>
            <div class="moment-body">
                <div class="moment-desc">{m.get("description", "")}</div>
                <div class="moment-sig">{m.get("significance", "")}</div>
            </div>
        </div>'''

    # 数据完整性
    dc = report.get("data_completeness", report.get("data_quality", {}))
    commits_n = dc.get("commit_count", "?")
    ai_n = dc.get("ai_interaction_count", "?")
    data_flags = []
    if not dc.get("has_commit_history") or commits_n in (0, 1):
        data_flags.append("无有效 commit")
    if not dc.get("has_ai_logs"):
        data_flags.append("无 AI 日志")
    if not dc.get("has_test_results"):
        data_flags.append("未运行测试")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeArena 评测报告 - {participant}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

  :root {{
    --bg: #ffffff;
    --surface: #f5f5f5;
    --subtle: #e5e5e5;
    --border: #d4d4d4;
    --text: #0a0a0a;
    --text2: #525252;
    --muted: #a3a3a3;
    --accent: #0d9488;
    --green: #16a34a;
    --yellow: #ca8a04;
    --red: #dc2626;
  }}

  * {{ margin:0; padding:0; box-sizing:border-box; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Geist', -apple-system, 'Segoe UI', sans-serif;
    font-size: 16px;
    line-height: 1.6;
    min-height: 100vh;
  }}

  .container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 48px 24px;
  }}

  /* Header */
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 48px;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border);
  }}
  .header-left {{}}
  .brand {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .participant-name {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 30px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.2;
  }}
  .meta {{
    font-size: 14px;
    color: var(--muted);
    margin-top: 8px;
  }}

  /* Composite Score */
  .composite {{
    text-align: right;
  }}
  .composite-score {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 64px;
    font-weight: 700;
    line-height: 1;
    color: {color};
  }}
  .composite-max {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 24px;
    color: var(--muted);
  }}
  .composite-label {{
    font-size: 14px;
    color: {color};
    margin-top: 4px;
  }}

  /* Score + Radar Row */
  .score-section {{
    display: grid;
    grid-template-columns: 1fr 300px;
    gap: 48px;
    margin-bottom: 48px;
  }}
  .radar {{
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  /* Dimension Bars */
  .dim-row {{
    margin-bottom: 20px;
  }}
  .dim-header {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 6px;
  }}
  .dim-name {{
    font-size: 14px;
    font-weight: 500;
    color: var(--text2);
    min-width: 90px;
  }}
  .dim-score {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px;
    font-weight: 600;
  }}
  .dim-label {{
    font-size: 12px;
  }}
  .bar-track {{
    height: 6px;
    background: var(--subtle);
    border-radius: 3px;
    overflow: hidden;
  }}
  .bar-fill {{
    height: 100%;
    border-radius: 3px;
    animation: fillBar 0.8s ease-out forwards;
    transform-origin: left;
  }}
  @keyframes fillBar {{
    from {{ width: 0 !important; }}
  }}
  .dim-reason {{
    font-size: 13px;
    color: var(--muted);
    margin-top: 4px;
    line-height: 1.5;
  }}

  /* Sections */
  .section {{
    margin-bottom: 40px;
  }}
  .section-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}

  /* Timeline */
  .timeline {{
    position: relative;
    padding-left: 24px;
  }}
  .timeline::before {{
    content: '';
    position: absolute;
    left: 7px;
    top: 4px;
    bottom: 4px;
    width: 2px;
    background: var(--border);
  }}
  .moment {{
    display: flex;
    gap: 16px;
    margin-bottom: 20px;
    position: relative;
  }}
  .moment-time {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--muted);
    min-width: 50px;
    flex-shrink: 0;
  }}
  .moment-dot {{
    position: absolute;
    left: -20px;
    top: 6px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent);
    border: 2px solid #ffffff;
  }}
  .moment-body {{}}
  .moment-desc {{
    font-size: 15px;
    color: var(--text);
    margin-bottom: 2px;
  }}
  .moment-sig {{
    font-size: 13px;
    color: var(--muted);
  }}

  /* Text Blocks */
  .text-block {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px;
    font-size: 14px;
    color: var(--text2);
    line-height: 1.7;
  }}
  .text-block.highlight {{
    border-left: 3px solid var(--accent);
  }}
  .text-block.improve {{
    border-left: 3px solid var(--yellow);
  }}

  /* Data Bar */
  .data-bar {{
    display: flex;
    gap: 24px;
    padding: 12px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--muted);
  }}
  .data-item {{
    display: flex;
    gap: 8px;
    align-items: center;
  }}
  .data-value {{
    color: var(--text2);
    font-weight: 500;
  }}
  .data-warn {{
    color: var(--red);
    font-size: 12px;
  }}

  /* Footer */
  .footer {{
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--muted);
    display: flex;
    justify-content: space-between;
  }}

  @media (max-width: 768px) {{
    .header {{ flex-direction: column; gap: 24px; }}
    .composite {{ text-align: left; }}
    .score-section {{ grid-template-columns: 1fr; }}
    .radar {{ order: -1; }}
  }}

  @media print {{
    .container {{ padding: 24px 0; }}
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="header-left">
      <div class="brand">CodeArena 评测报告</div>
      <div class="participant-name">{participant}</div>
      <div class="meta">生成时间: {now}</div>
    </div>
    <div class="composite">
      <div class="composite-score">{composite:.1f}<span class="composite-max"> / 10</span></div>
      <div class="composite-label">{label}</div>
    </div>
  </div>

  <div class="score-section">
    <div class="dimensions">
      {bars_html}
    </div>
    <div class="radar">
      {radar}
    </div>
  </div>

  <div class="section">
    <div class="section-title">关键时刻</div>
    <div class="timeline">
      {timeline_html}
    </div>
  </div>

  <div class="section">
    <div class="section-title">亮点</div>
    <div class="text-block highlight">{report.get("highlights", "")}</div>
  </div>

  <div class="section">
    <div class="section-title">提升空间</div>
    <div class="text-block improve">{report.get("improvements", "")}</div>
  </div>

  <div class="section">
    <div class="section-title">数据来源</div>
    <div class="data-bar">
      <div class="data-item">Commits <span class="data-value">{commits_n}</span></div>
      <div class="data-item">AI 对话 <span class="data-value">{ai_n}</span></div>
      <div class="data-item">测试 <span class="data-value">{"通过" if dc.get("has_test_results") else "未运行"}</span></div>
      {f'<div class="data-warn">{"  |  ".join(data_flags)}</div>' if data_flags else ""}
    </div>
  </div>

  <div class="footer">
    <span>CodeArena Internal Test</span>
    <span>Powered by GLM-5.1</span>
  </div>

</div>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description="CodeArena HTML 报告")
    parser.add_argument("--input", required=True, help="JSON 报告文件")
    parser.add_argument("--output", default=None, help="HTML 输出路径")
    parser.add_argument("--participant", default=None, help="参赛者名称")
    parser.add_argument("--open", action="store_true", help="生成后自动打开浏览器")
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    participant = args.participant or Path(args.input).stem.replace("_report", "")

    output = args.output or str(Path(args.input).with_suffix(".html"))
    html = generate_html(report, participant)
    Path(output).write_text(html, encoding="utf-8")
    print(f"HTML 报告: {output}")

    if args.open:
        webbrowser.open(f"file://{os.path.abspath(output)}")


if __name__ == "__main__":
    main()
