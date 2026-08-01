import os
import json
import datetime
import logging
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
    """Generates an interactive, standalone HTML report with Plotly Sankey & Timeline charts."""

    def __init__(self, events: List[Dict[str, Any]], target_dir: str):
        self.events = events
        self.target_dir = target_dir

    def _build_sankey_data(self) -> Dict[str, Any]:
        """Constructs Plotly Sankey Diagram JSON payload."""
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
            colors.append("#58a6ff")

            if ev.get("executed_process"):
                exec_proc = f"Exec: {ev['executed_process']}"
                exec_idx = get_node_index(exec_proc)

                sources.append(dl_idx)
                targets.append(exec_idx)
                values.append(1)

                risk = ev.get("risk_level", "LOW")
                if risk == "CRITICAL":
                    colors.append("#ff7b72")
                elif risk == "HIGH":
                    colors.append("#ffa657")
                elif risk == "MEDIUM":
                    colors.append("#d29922")
                else:
                    colors.append("#3fb950")

        if not nodes:
            return {}

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="#30363d", width=0.5),
                label=nodes,
                color="#21262d"
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
            font=dict(color="#c9d1d9", size=12),
            margin=dict(l=10, r=10, t=10, b=10)
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
                marker_colors.append("#58a6ff")
                marker_sizes.append(12)

            exec_time = ev.get("execution_time")
            if exec_time and isinstance(exec_time, datetime.datetime):
                x_times.append(exec_time.isoformat())
                y_labels.append(f"Exec: {ev.get('executed_process')}")
                hover_texts.append(f"Process Executed<br>Proc: {ev.get('executed_process')}<br>Risk: {ev.get('risk_level')} ({ev.get('risk_score')}/100)")
                
                risk = ev.get("risk_level", "LOW")
                if risk == "CRITICAL":
                    marker_colors.append("#ff7b72")
                    marker_sizes.append(18)
                elif risk == "HIGH":
                    marker_colors.append("#ffa657")
                    marker_sizes.append(16)
                elif risk == "MEDIUM":
                    marker_colors.append("#d29922")
                    marker_sizes.append(14)
                else:
                    marker_colors.append("#3fb950")
                    marker_sizes.append(12)

        if not x_times:
            return {}

        fig = go.Figure(data=[go.Scatter(
            x=x_times,
            y=y_labels,
            mode="markers+lines",
            marker=dict(size=marker_sizes, color=marker_colors, line=dict(width=1, color="#ffffff")),
            text=hover_texts,
            hoverinfo="text"
        )])

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c9d1d9"),
            xaxis=dict(title="Timestamp (UTC)", gridcolor="#30363d"),
            yaxis=dict(gridcolor="#30363d"),
            margin=dict(l=10, r=10, t=10, b=40)
        )

        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

    def generate(self, output_path: str):
        """Renders Jinja2 template or string fallback and writes file to output_path."""
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        template_dir = os.path.join(base_dir, "templates")

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

        if HAS_JINJA2:
            candidate_dirs = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
                os.path.abspath(os.path.join(os.getcwd(), "ransomtriage", "templates")),
                os.path.abspath(os.path.join(os.getcwd(), "templates")),
            ]

            loaders = [FileSystemLoader(d) for d in candidate_dirs if os.path.isdir(d)]
            try:
                loaders.append(PackageLoader("ransomtriage", "templates"))
            except Exception:
                pass
            try:
                loaders.append(PackageLoader("ransomtriage", "."))
            except Exception:
                pass

            env = Environment(
                loader=ChoiceLoader(loaders) if loaders else FileSystemLoader(template_dir),
                autoescape=select_autoescape(["html", "xml"])
            )

            template = None
            for t_name in ["report_template.html", "templates/report_template.html"]:
                try:
                    template = env.get_template(t_name)
                    if template:
                        break
                except Exception:
                    continue

            # Fallback to direct file read if loaders fail
            if template is None:
                for c_dir in candidate_dirs:
                    t_file = os.path.join(c_dir, "report_template.html")
                    if os.path.exists(t_file):
                        try:
                            with open(t_file, "r", encoding="utf-8") as f:
                                template = Environment(autoescape=select_autoescape(["html", "xml"])).from_string(f.read())
                            break
                        except Exception:
                            pass

            if template is not None:
                rendered_html = template.render(
                    generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    target_dir=self.target_dir,
                    total_downloads=total_downloads,
                    total_matched=total_matched,
                    total_critical=total_critical,
                    events=formatted_events,
                    sankey_json=sankey_json,
                    timeline_json=timeline_json
                )
            else:
                rendered_html = self._render_fallback_html(formatted_events)
        else:
            rendered_html = self._render_fallback_html(formatted_events)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        logger.info(f"HTML report successfully generated at '{output_path}'")

    def _render_fallback_html(self, formatted_events: List[Dict[str, Any]]) -> str:
        """Basic HTML string fallback if Jinja2 template is missing."""
        rows = []
        for ev in formatted_events:
            reasons = "".join(f"<li>{r}</li>" for r in ev.get("risk_reasons", []))
            rows.append(f"""
            <tr>
                <td>{ev.get('risk_level')}</td>
                <td>{ev.get('risk_score')}</td>
                <td>{ev.get('download_file')}</td>
                <td>{ev.get('referrer_url')}</td>
                <td>{ev.get('executed_process') or 'Unexecuted'}</td>
                <td>{ev.get('delta_t_seconds', '-')}</td>
                <td><ul>{reasons}</ul></td>
            </tr>
            """)
        return f"""<!DOCTYPE html>
<html>
<head><title>RansomTriage Report</title></head>
<body style="font-family: sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px;">
    <h1>RansomTriage Forensic Execution Chain Report</h1>
    <p>Target: {self.target_dir}</p>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <thead>
            <tr><th>Level</th><th>Score</th><th>File</th><th>Referrer</th><th>Process</th><th>Delta-T</th><th>Risk Analysis</th></tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
</body>
</html>"""

