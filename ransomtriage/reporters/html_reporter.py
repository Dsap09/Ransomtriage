import os
import json
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Any

try:
    from jinja2 import Environment, FileSystemLoader, PackageLoader, ChoiceLoader, select_autoescape, TemplateNotFound
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False

try:
    import plotly.graph_objects as go
    import plotly.utils
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

logger = logging.getLogger("ransomtriage.reporters.html")


class HTMLReporter:
    """Generates an interactive, executive-ready standalone HTML report with Plotly Sankey & Timeline charts."""

    def __init__(self, events: List[Dict[str, Any]], target_dir: str):
        self.events = events
        self.target_dir = target_dir

    def _build_sankey_data(self) -> Dict[str, Any]:
        """Constructs Plotly Sankey Diagram JSON payload with sleek dark cyber styling."""
        if not HAS_PLOTLY:
            return {}

        nodes = []
        node_map = {}

        def get_node_index(label: str) -> int:
            if label not in node_map:
                node_map[label] = len(nodes)
                nodes.append(label)
            return node_map[label]

        sources = []
        targets = []
        values = []
        colors = []

        for ev in self.events:
            ref = ev.get("referrer_url") or "Direct / Unknown Source"
            if len(ref) > 40:
                ref = ref[:37] + "..."
            
            dl_file = f"Download: {ev.get('download_file', 'unknown')}"
            
            ref_idx = get_node_index(ref)
            dl_idx = get_node_index(dl_file)

            sources.append(ref_idx)
            targets.append(dl_idx)
            values.append(1)
            colors.append("rgba(56, 189, 248, 0.4)")

            if ev.get("executed_process"):
                exec_proc = f"Exec: {ev['executed_process']}"
                exec_idx = get_node_index(exec_proc)

                sources.append(dl_idx)
                targets.append(exec_idx)
                values.append(1)

                risk = ev.get("risk_level", "LOW")
                if risk == "CRITICAL":
                    colors.append("rgba(239, 68, 68, 0.5)")
                elif risk == "HIGH":
                    colors.append("rgba(249, 115, 22, 0.5)")
                elif risk == "MEDIUM":
                    colors.append("rgba(234, 179, 8, 0.5)")
                else:
                    colors.append("rgba(16, 185, 129, 0.5)")

        if not nodes:
            return {}

        node_colors = []
        for n in nodes:
            if n.startswith("Exec:"):
                node_colors.append("#ef4444")
            elif n.startswith("Download:"):
                node_colors.append("#6366f1")
            else:
                node_colors.append("#0284c7")

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=25,
                thickness=20,
                line=dict(color="#ffffff", width=1.5),
                label=nodes,
                color=node_colors
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=colors
            )
        )])

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff", size=13, family="Inter, sans-serif"),
            margin=dict(l=20, r=20, t=20, b=20)
        )

        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

    def _build_timeline_data(self) -> Dict[str, Any]:
        """Constructs Plotly Timeline Scatter Chart JSON payload."""
        if not HAS_PLOTLY:
            return {}

        x_times = []
        y_labels = []
        hover_texts = []
        marker_colors = []
        marker_sizes = []

        for ev in self.events:
            dl_time = ev.get("download_time")
            if dl_time and isinstance(dl_time, datetime.datetime):
                x_times.append(dl_time.isoformat())
                y_labels.append(f"Download: {ev.get('download_file')}")
                hover_texts.append(f"Download Completed<br>File: {ev.get('download_file')}<br>Referrer: {ev.get('referrer_url')}")
                marker_colors.append("#38bdf8")
                marker_sizes.append(12)

            exec_time = ev.get("execution_time")
            if exec_time and isinstance(exec_time, datetime.datetime):
                x_times.append(exec_time.isoformat())
                y_labels.append(f"Exec: {ev.get('executed_process')}")
                hover_texts.append(f"Process Executed<br>Proc: {ev.get('executed_process')}<br>Risk: {ev.get('risk_level')} ({ev.get('risk_score')}/100)")
                
                risk = ev.get("risk_level", "LOW")
                if risk == "CRITICAL":
                    marker_colors.append("#ef4444")
                    marker_sizes.append(18)
                elif risk == "HIGH":
                    marker_colors.append("#f97316")
                    marker_sizes.append(16)
                elif risk == "MEDIUM":
                    marker_colors.append("#eab308")
                    marker_sizes.append(14)
                else:
                    marker_colors.append("#10b981")
                    marker_sizes.append(12)

        if not x_times:
            return {}

        fig = go.Figure(data=[go.Scatter(
            x=x_times,
            y=y_labels,
            mode="markers+lines",
            marker=dict(size=marker_sizes, color=marker_colors, line=dict(width=1.5, color="#ffffff")),
            text=hover_texts,
            hoverinfo="text"
        )])

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ffffff", family="Inter, sans-serif"),
            xaxis=dict(title="Timestamp (UTC)", gridcolor="#334155", title_font=dict(color="#ffffff"), tickfont=dict(color="#f8fafc")),
            yaxis=dict(gridcolor="#334155", tickfont=dict(color="#f8fafc")),
            margin=dict(l=20, r=20, t=20, b=40)
        )

        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

    def generate(self, output_path: str):
        """Renders Jinja2 template or HTML generator fallback and writes file to output_path."""
        generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sankey_json = json.dumps(self._build_sankey_data())
        timeline_json = json.dumps(self._build_timeline_data())

        total_downloads = len(self.events)
        total_matched = sum(1 for e in self.events if e.get("matched"))
        total_critical = sum(1 for e in self.events if e.get("risk_level") in ("CRITICAL", "HIGH"))

        formatted_events = []
        for ev in self.events:
            e_copy = dict(ev)
            if isinstance(e_copy.get("download_time"), datetime.datetime):
                e_copy["download_time"] = e_copy["download_time"].strftime("%Y-%m-%d %H:%M:%S UTC")
            if isinstance(e_copy.get("execution_time"), datetime.datetime):
                e_copy["execution_time"] = e_copy["execution_time"].strftime("%Y-%m-%d %H:%M:%S UTC")
            formatted_events.append(e_copy)

        template_content = None

        # Tier 1: Try reading template file directly from package path
        current_file_path = Path(__file__).resolve()
        package_template_file = current_file_path.parent.parent / "templates" / "report_template.html"

        candidate_files = [
            package_template_file,
            Path(os.getcwd()) / "ransomtriage" / "templates" / "report_template.html",
            Path(os.getcwd()) / "templates" / "report_template.html",
        ]

        for c_file in candidate_files:
            if c_file.exists():
                try:
                    with open(c_file, "r", encoding="utf-8") as f:
                        template_content = f.read()
                    break
                except Exception:
                    pass

        rendered_html = None

        if HAS_JINJA2:
            try:
                if template_content:
                    template = Environment(autoescape=select_autoescape(["html", "xml"])).from_string(template_content)
                else:
                    env = Environment(
                        loader=FileSystemLoader(str(package_template_file.parent)),
                        autoescape=select_autoescape(["html", "xml"])
                    )
                    template = env.get_template("report_template.html")

                rendered_html = template.render(
                    generated_at=generated_at,
                    target_dir=self.target_dir,
                    total_downloads=total_downloads,
                    total_matched=total_matched,
                    total_critical=total_critical,
                    events=formatted_events,
                    sankey_json=sankey_json,
                    timeline_json=timeline_json
                )
            except Exception as e:
                logger.warning(f"Jinja2 rendering failed, falling back to direct builder: {e}")
                rendered_html = None

        if not rendered_html:
            rendered_html = self._render_fallback_html(
                formatted_events,
                generated_at,
                total_downloads,
                total_matched,
                total_critical,
                sankey_json,
                timeline_json
            )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        logger.info(f"HTML report successfully generated at '{output_path}'")

    def _render_fallback_html(
        self,
        formatted_events: List[Dict[str, Any]],
        generated_at: str,
        total_downloads: int,
        total_matched: int,
        total_critical: int,
        sankey_json: str,
        timeline_json: str
    ) -> str:
        """Full Executive UI HTML generator fallback (guarantees identical 10/10 styling without Jinja2 dependency)."""
        rows = []
        for ev in formatted_events:
            risk_level = ev.get("risk_level", "BENIGN")
            risk_score = ev.get("risk_score", 0)
            dl_file = ev.get("download_file", "")
            dl_path = ev.get("download_path", "")
            ref_url = ev.get("referrer_url", "")
            exec_proc = ev.get("executed_process")
            run_count = ev.get("run_count")
            delta_t = ev.get("delta_t_seconds")
            reasons = ev.get("risk_reasons", [])

            icon = "🚨" if risk_level == "CRITICAL" else ("⚠️" if risk_level == "HIGH" else ("⚡" if risk_level == "MEDIUM" else "ℹ️"))
            score_color = "var(--critical-red)" if risk_score >= 80 else ("var(--high-orange)" if risk_score >= 50 else "var(--low-blue)")

            exec_html = f'<div class="code-box" style="color: #a7f3d0;">⚡ {exec_proc}</div>' if exec_proc else '<span style="color: var(--text-muted); font-style: italic;">Tidak Dieksekusi</span>'
            if exec_proc and run_count:
                exec_html += f'<div class="path-sub">Run Count: {run_count}</div>'

            path_html = f'<div class="path-sub">{dl_path}</div>' if dl_path else ''
            
            delta_html = f'<span class="delta-t-tag {"delta-t-alert" if delta_t is not None and delta_t < 5 else ""}">{delta_t:.2f}s</span>' if delta_t is not None else '<span style="color: var(--text-muted);">-</span>'

            reasons_html = "".join(f"<li>{r}</li>" for r in reasons)

            rows.append(f"""
            <tr data-level="{risk_level}" data-matched="{'true' if ev.get('matched') else 'false'}">
                <td>
                    <span class="badge badge-{risk_level}">{icon} {risk_level}</span>
                </td>
                <td>
                    <span class="score-pill" style="color: {score_color};">{risk_score}</span>
                </td>
                <td>
                    <div class="code-box">{dl_file}</div>
                    {path_html}
                </td>
                <td>
                    <div class="path-sub" style="color: var(--text-secondary);">{ref_url}</div>
                </td>
                <td>
                    {exec_html}
                </td>
                <td>
                    {delta_html}
                </td>
                <td>
                    <ul class="risk-reasons-list">
                        {reasons_html}
                    </ul>
                </td>
            </tr>
            """)

        return f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RansomTriage - Forensic Execution Chain Report</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-body: #0b0f19;
            --bg-card: #111827;
            --bg-card-hover: #1f293d;
            --bg-table-header: #1e293b;
            --border-color: #1e293b;
            --border-highlight: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-indigo: #6366f1;
            --critical-red: #ef4444;
            --critical-bg: rgba(239, 68, 68, 0.12);
            --critical-border: rgba(239, 68, 68, 0.3);
            --high-orange: #f97316;
            --high-bg: rgba(249, 115, 22, 0.12);
            --high-border: rgba(249, 115, 22, 0.3);
            --medium-yellow: #eab308;
            --medium-bg: rgba(234, 179, 8, 0.12);
            --medium-border: rgba(234, 179, 8, 0.3);
            --low-blue: #3b82f6;
            --low-bg: rgba(59, 130, 246, 0.12);
            --low-border: rgba(59, 130, 246, 0.3);
            --benign-green: #10b981;
            --benign-bg: rgba(16, 185, 129, 0.12);
            --benign-border: rgba(16, 185, 129, 0.3);
        }}

        * {{ box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-primary);
            margin: 0;
            padding: 24px;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1350px;
            margin: 0 auto;
        }}

        .header-card {{
            background: linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(30, 41, 59, 0.7));
            border: 1px solid var(--border-highlight);
            border-radius: 12px;
            padding: 24px 32px;
            margin-bottom: 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}

        .header-brand {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .logo-icon {{
            font-size: 2.2rem;
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid var(--accent-indigo);
            padding: 8px 14px;
            border-radius: 10px;
        }}

        .header-title h1 {{
            margin: 0;
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #f8fafc 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .header-title p {{
            margin: 4px 0 0 0;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}

        .header-meta {{
            text-align: right;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}

        .meta-tag {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-color);
            padding: 4px 10px;
            border-radius: 6px;
            color: var(--accent-indigo);
            word-break: break-all;
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}

        .kpi-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
            transition: transform 0.2s, border-color 0.2s;
        }}

        .kpi-card:hover {{
            transform: translateY(-2px);
            border-color: var(--border-highlight);
        }}

        .kpi-label {{
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }}

        .kpi-value {{
            font-size: 2.4rem;
            font-weight: 700;
            line-height: 1.1;
        }}

        .kpi-sub {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 6px;
        }}

        .chart-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}

        .chart-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px 24px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
        }}

        .chart-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-color);
        }}

        .chart-header h2 {{
            margin: 0;
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .chart-header p {{
            margin: 4px 0 0 0;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}

        .filter-bar {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .search-box {{
            position: relative;
            flex: 1;
            min-width: 280px;
        }}

        .search-box input {{
            width: 100%;
            background-color: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 10px 14px 10px 38px;
            border-radius: 8px;
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.2s;
        }}

        .search-box input:focus {{
            border-color: var(--accent-indigo);
        }}

        .search-icon {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
        }}

        .filter-buttons {{
            display: flex;
            gap: 8px;
        }}

        .filter-btn {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .filter-btn:hover, .filter-btn.active {{
            background: var(--accent-indigo);
            color: #ffffff;
            border-color: var(--accent-indigo);
        }}

        .table-container {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            margin-bottom: 32px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }}

        th {{
            background-color: var(--bg-table-header);
            color: var(--text-secondary);
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-highlight);
        }}

        td {{
            padding: 16px 18px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: var(--bg-card-hover);
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }}

        .badge-CRITICAL {{ background: var(--critical-bg); color: var(--critical-red); border: 1px solid var(--critical-border); }}
        .badge-HIGH {{ background: var(--high-bg); color: var(--high-orange); border: 1px solid var(--high-border); }}
        .badge-MEDIUM {{ background: var(--medium-bg); color: var(--medium-yellow); border: 1px solid var(--medium-border); }}
        .badge-LOW {{ background: var(--low-bg); color: var(--low-blue); border: 1px solid var(--low-border); }}
        .badge-BENIGN {{ background: var(--benign-bg); color: var(--benign-green); border: 1px solid var(--benign-border); }}

        .score-pill {{
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 0.95rem;
            padding: 2px 8px;
            border-radius: 6px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-color);
        }}

        .code-box {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.83rem;
            color: #38bdf8;
            word-break: break-all;
        }}

        .path-sub {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 4px;
            word-break: break-all;
        }}

        .risk-reasons-list {{
            margin: 0;
            padding-left: 18px;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}

        .risk-reasons-list li {{
            margin-bottom: 4px;
        }}

        .delta-t-tag {{
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(15, 23, 42, 0.8);
        }}

        .delta-t-alert {{
            color: var(--critical-red);
            border: 1px solid var(--critical-border);
        }}

        footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            padding: 20px 0;
            border-top: 1px solid var(--border-color);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-card">
            <div class="header-brand">
                <div class="logo-icon">🛡️</div>
                <div class="header-title">
                    <h1>RansomTriage Forensic Execution Chain Report</h1>
                    <p>Automated Forensics & Attack Vector Analysis for CSIRT Incident Responders</p>
                </div>
            </div>
            <div class="header-meta">
                <div><strong>Waktu Analisa:</strong> {generated_at}</div>
                <div style="margin-top: 4px;"><strong>Target Directory:</strong> <span class="meta-tag">{self.target_dir}</span></div>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Total Artifact Downloads</div>
                <div class="kpi-value" style="color: var(--low-blue);">{total_downloads}</div>
                <div class="kpi-sub">Detected browser download events</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Execution Chain Matches</div>
                <div class="kpi-value" style="color: var(--high-orange);">{total_matched}</div>
                <div class="kpi-sub">Matched to Prefetch process execution</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Critical / High Threats</div>
                <div class="kpi-value" style="color: var(--critical-red);">{total_critical}</div>
                <div class="kpi-sub">Requiring immediate IR containment</div>
            </div>
        </div>

        <div class="chart-grid">
            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <h2>🔗 Attack Flow Diagram (Sankey Plot)</h2>
                        <p>Visualisasi rantai eksekusi serangan: Referrer URL ➔ Downloaded File ➔ Executed Process</p>
                    </div>
                </div>
                <div id="sankey-chart" style="width: 100%; height: 420px;"></div>
            </div>

            <div class="chart-card">
                <div class="chart-header">
                    <div>
                        <h2>⏱️ Incident Timeline Chart (Delta-T)</h2>
                        <p>Urutan kronologis waktu download artifact dan waktu eksekusi proses</p>
                    </div>
                </div>
                <div id="timeline-chart" style="width: 100%; height: 350px;"></div>
            </div>
        </div>

        <div class="filter-bar">
            <div class="search-box">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" placeholder="Cari nama file, process, URL referrer, atau indikator risiko..." onkeyup="filterTable()">
            </div>
            <div class="filter-buttons">
                <button class="filter-btn active" onclick="setFilter('ALL', this)">Semua Event</button>
                <button class="filter-btn" onclick="setFilter('CRITICAL', this)">Critical & High</button>
                <button class="filter-btn" onclick="setFilter('MATCHED', this)">Matched Only</button>
            </div>
        </div>

        <div class="table-container">
            <table id="eventsTable">
                <thead>
                    <tr>
                        <th style="width: 110px;">Level</th>
                        <th style="width: 80px;">Score</th>
                        <th style="width: 220px;">Download File</th>
                        <th style="width: 260px;">Referrer URL</th>
                        <th style="width: 200px;">Process Eksekusi</th>
                        <th style="width: 110px;">Delta-T</th>
                        <th>Analisa Risiko & Indikator</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>

        <footer>
            Dihasilkan secara otomatis oleh <strong>RansomTriage v1.0</strong> — Automated Forensic Execution Chain Analyzer
        </footer>
    </div>

    <script id="sankey-data" type="application/json">
        {sankey_json}
    </script>
    <script id="timeline-data" type="application/json">
        {timeline_json}
    </script>
    <script>
        const sankeyData = JSON.parse(document.getElementById('sankey-data').textContent || '{{}}');
        const timelineData = JSON.parse(document.getElementById('timeline-data').textContent || '{{}}');

        if (sankeyData && Object.keys(sankeyData).length > 0) {{
            Plotly.newPlot('sankey-chart', sankeyData.data, sankeyData.layout, {{responsive: true}});
        }}
        if (timelineData && Object.keys(timelineData).length > 0) {{
            Plotly.newPlot('timeline-chart', timelineData.data, timelineData.layout, {{responsive: true}});
        }}

        let activeFilter = 'ALL';

        function setFilter(filter, btn) {{
            activeFilter = filter;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterTable();
        }}

        function filterTable() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#eventsTable tbody tr');

            rows.forEach(row => {{
                const level = row.getAttribute('data-level');
                const matched = row.getAttribute('data-matched');
                const text = row.textContent.toLowerCase();

                let matchesFilter = true;
                if (activeFilter === 'CRITICAL') {{
                    matchesFilter = (level === 'CRITICAL' || level === 'HIGH');
                }} else if (activeFilter === 'MATCHED') {{
                    matchesFilter = (matched === 'true');
                }}

                let matchesSearch = text.includes(query);

                if (matchesFilter && matchesSearch) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>"""
