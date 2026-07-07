"""引文图谱可视化 — D3.js 力导向图 HTML 生成

参考: ScholarFlow (D3 force-directed graph), Biblio Infinity
"""
from __future__ import annotations
import json
import logging
from typing import List, Optional

from article_check.literature.citation import CitationNode, CitationGraph

logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>引文网络图谱</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ font-family: "Microsoft YaHei", sans-serif; margin: 0; background: #f8f9fa; }}
  .graph-container {{ width: 100vw; height: 100vh; position: relative; }}
  svg {{ width: 100%; height: 100%; }}
  .node circle {{ stroke: #fff; stroke-width: 2px; cursor: pointer; }}
  .node text {{ font-size: 12px; pointer-events: none; }}
  .link {{ stroke: #999; stroke-opacity: 0.6; stroke-width: 1.5; }}
  .tooltip {{
    position: absolute; background: rgba(0,0,0,0.8); color: #fff;
    padding: 8px 12px; border-radius: 6px; font-size: 13px;
    pointer-events: none; max-width: 300px;
  }}
  .legend {{ position: absolute; bottom: 20px; left: 20px; background: #fff;
    padding: 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
  .color-bar {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; }}
  .color-sample {{ width: 16px; height: 16px; border-radius: 50%; }}
  h3 {{ margin: 0 0 8px; font-size: 14px; }}
</style>
</head>
<body>
<div class="graph-container">
  <svg></svg>
  <div class="tooltip" style="display:none"></div>
  <div class="legend"></div>
</div>
<script>
const DATA = {data_json};

const width = window.innerWidth, height = window.innerHeight;
const svg = d3.select("svg"), tooltip = d3.select(".tooltip");

const color = d3.scaleOrdinal(d3.schemeTableau10);

const simulation = d3.forceSimulation(DATA.nodes)
  .force("link", d3.forceLink(DATA.links).id(d => d.id).distance(150))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2));

const link = svg.append("g").selectAll("line")
  .data(DATA.links).join("line").attr("class", "link");

const node = svg.append("g").selectAll("g")
  .data(DATA.nodes).join("g").attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end", (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }})
  );

node.append("circle")
  .attr("r", d => Math.max(5, Math.min(20, (d.citations || 5) * 1.5)))
  .attr("fill", d => color(d.group || 0))
  .on("mouseover", (e, d) => {{
    tooltip.style("display", "block")
      .html(`<b>${{d.title}}</b><br>${{d.year || '?'}} | 被引: ${{d.citations || 0}}`)
      .style("left", (e.pageX + 12) + "px").style("top", (e.pageY - 12) + "px");
  }})
  .on("mouseout", () => tooltip.style("display", "none"));

node.append("text")
  .text(d => d.title?.substring(0, 20) || "")
  .attr("x", d => Math.max(5, Math.min(20, (d.citations || 5) * 1.5)) + 6)
  .attr("y", 4);

simulation.on("tick", () => {{
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});

const legend = d3.select(".legend");
legend.html("<h3>📊 引文网络</h3>");
DATA.groups?.forEach((g, i) => {{
  legend.append("div").attr("class", "color-bar")
    .html(`<span class="color-sample" style="background:${{color(i)}}"></span> ${{g}}`);
}});
</script>
</body>
</html>"""


def generate_citation_html(
    papers: List[CitationNode],
    graph: Optional[CitationGraph] = None,
    output_path: str = "citation_graph.html",
) -> str:
    """
    生成 D3 引文网络 HTML

    Args:
        papers: 核心文献列表
        graph: 引文网络图（可选）
        output_path: 输出路径

    Returns:
        HTML 内容
    """
    nodes = []
    links = []
    groups = set()

    for p in papers:
        group = str(p.year // 5 * 5) + "s" if p.year else "unknown"
        groups.add(group)
        nodes.append({
            "id": p.paper_id or p.title[:30],
            "title": p.title[:50] if p.title else "",
            "year": p.year,
            "citations": p.citations_count or 0,
            "group": group,
        })

    if graph:
        for from_id, to_ids in graph.edges_forward.items():
            for to_id in to_ids:
                links.append({"source": from_id, "target": to_id})

    data = {
        "nodes": nodes,
        "links": links,
        "groups": sorted(groups),
    }

    html = HTML_TEMPLATE.replace("{data_json}", json.dumps(data, ensure_ascii=False))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"引文图谱已生成: {output_path} ({len(nodes)} 节点, {len(links)} 边)")
    return html


def generate_trend_chart(
    papers: List[CitationNode],
    output_path: str = "citation_trend.html",
) -> str:
    """生成引用趋势图"""
    from collections import Counter
    years = Counter(p.year for p in papers if p.year)
    sorted_years = sorted(years.items())

    chart_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>引用年度分布</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>body {{ font-family: sans-serif; padding: 20px; }}
.bar {{ fill: #4dabf7; transition: fill 0.2s; }}
.bar:hover {{ fill: #1971c2; }}
.axis text {{ font-size: 11px; }}
.label {{ font-size: 13px; text-anchor: middle; }}
</style></head><body>
<h2>📈 文献发表年度分布</h2>
<svg width="700" height="400"></svg>
<script>
const data = {json.dumps([{"year": y, "count": c} for y, c in sorted_years], ensure_ascii=False)};
const margin = {{top: 20, right: 20, bottom: 40, left: 40}};
const w = 660, h = 360;
const x = d3.scaleBand().domain(data.map(d => d.year)).range([0, w]).padding(0.2);
const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count)]).range([h, 0]);
const svg = d3.select("svg").append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
svg.selectAll(".bar").data(data).join("rect").attr("class", "bar")
  .attr("x", d => x(d.year)).attr("y", d => y(d.count))
  .attr("width", x.bandwidth()).attr("height", d => h - y(d.count));
svg.append("g").call(d3.axisLeft(y));
svg.append("g").attr("transform", `translate(0,${{h}})`).call(d3.axisBottom(x))
  .selectAll("text").attr("transform", "rotate(-45)").style("text-anchor", "end");
</script></body></html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(chart_html)
    logger.info(f"趋势图已生成: {output_path}")
    return chart_html
