"""Generate a self-contained HTML preview of the MCP server.

Introspects the live server object (tools, schemas, resources) plus the
capability map, snippet corpus, and latest eval results, and writes one
dependency-free HTML file. The page is the shareable answer to "what do
we support here, and what tools are available in which domain".

Run: .venv/bin/python scripts/preview_server.py  -> preview.html
"""

import asyncio
import base64
import html
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent

LAYERS = {
    "Scope and planning": ["supported_capabilities", "plan_simulation",
                           "plan_calibration", "calibration_options",
                           "opensees_matrix", "describe_material"],
    "Grounding and retrieval": ["search_snippets", "search_community",
                                "reindex", "describe_app"],
    "Job lifecycle and safety spine": ["stage_inputs", "build_job_request",
                                       "validate_job", "estimate_cost",
                                       "approve_submission", "submit_job",
                                       "job_status", "get_results"],
    "Workflows and provenance": ["build_workflow_preview", "write_manifest"],
}

STATUS_CLASS = {"tested": "ok", "candidate": "warn", "untested": "off"}


def esc(s: object) -> str:
    return html.escape(str(s))


async def introspect() -> tuple[list, list]:
    from designsafe_mcp.server import mcp

    return await mcp.list_tools(), await mcp.list_resources()


def main() -> None:
    tools, resources = asyncio.run(introspect())
    tool_map = {t.name: t for t in tools}
    from designsafe_mcp.capabilities import supported_capabilities

    caps = supported_capabilities()
    snippets = yaml.safe_load(
        (ROOT / "designsafe_mcp" / "snippets.yaml").read_text())
    img_b64 = base64.b64encode(
        (ROOT / "assets" / "opensees-decision-matrix.png").read_bytes()
    ).decode()

    domain_html = ""
    for d in caps["domains"]:
        rows = "".join(
            f"<tr><td>{esc(c['what'])}</td><td>{esc(c['served_by'])}</td>"
            f"<td><code>{esc(c['snippet'] or '—')}</code></td>"
            f"<td><span class='pill {STATUS_CLASS[c['status']]}'>"
            f"{esc(c['status'])}</span></td></tr>"
            for c in d["capabilities"])
        domain_html += (
            f"<section><h3>{esc(d['domain'])}</h3>"
            f"<p class='science'>{esc(d['science'])}</p>"
            "<div class='scroll'><table><thead><tr><th>capability</th>"
            "<th>served by</th><th>snippet</th><th>status</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div></section>")

    oos = "".join(f"<li>{esc(x)}</li>" for x in caps["out_of_scope"])

    tools_html = ""
    for layer, names in LAYERS.items():
        items = ""
        for n in names:
            t = tool_map.get(n)
            if t is None:
                continue
            desc = (t.description or "").strip().split("\n\n")[0]
            raw = (getattr(t, "input_schema", None)
                   or getattr(t, "inputSchema", None) or {})
            props = raw.get("properties", {}) if isinstance(raw, dict) else {}
            schema = json.dumps(props, indent=1) if props else "(no arguments)"
            items += (
                f"<details><summary><code>{esc(n)}</code> "
                f"<span class='d'>{esc(desc[:160])}</span></summary>"
                f"<pre>{esc(schema)}</pre></details>")
        tools_html += f"<section><h3>{esc(layer)}</h3>{items}</section>"

    listed = ", ".join(f"<code>{esc(str(r.uri))}</code>" for r in resources)
    snip_rows = "".join(
        f"<tr><td><code>{esc(s['id'])}</code></td><td>{esc(s['title'])}</td>"
        f"<td><code>{esc(s['app_id'])}</code></td></tr>"
        for s in snippets["snippets"])

    page = f"""<title>DesignSafe MCP — capability sheet</title>
<style>
:root {{
  --bg: #FAFAF8; --panel: #FFFFFF; --ink: #1A1D21; --mut: #5A6069;
  --line: #E3E2DD; --acc: #0E7C7B; --ok: #2E7D46; --warn: #B07D22;
  --off: #6B7280;
}}
:root:not([data-theme="light"]) {{}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #14171A; --panel: #1C2025; --ink: #E8EAED; --mut: #9AA1AA;
    --line: #2C3238; --acc: #3FB8B6; --ok: #57B87A; --warn: #D9A34A;
    --off: #8B939E;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #14171A; --panel: #1C2025; --ink: #E8EAED; --mut: #9AA1AA;
  --line: #2C3238; --acc: #3FB8B6; --ok: #57B87A; --warn: #D9A34A;
  --off: #8B939E;
}}
body {{ background: var(--bg); color: var(--ink); margin: 0;
  font: 16px/1.55 ui-sans-serif, system-ui, sans-serif; }}
main {{ max-width: 60rem; margin: 0 auto; padding: 2.5rem 1.25rem 5rem; }}
h1 {{ font-size: 1.65rem; letter-spacing: -0.01em; margin: 0 0 .3rem;
  text-wrap: balance; }}
h2 {{ font-size: 1.15rem; margin: 2.8rem 0 .4rem; color: var(--acc);
  text-transform: uppercase; letter-spacing: .06em; }}
h3 {{ font-size: 1.02rem; margin: 1.6rem 0 .3rem; }}
.sub {{ color: var(--mut); max-width: 46rem; }}
.science {{ color: var(--mut); font-size: .92rem; margin: .1rem 0 .6rem; }}
table {{ border-collapse: collapse; width: 100%; font-size: .88rem; }}
th {{ text-align: left; color: var(--mut); font-weight: 600;
  padding: .35rem .6rem; border-bottom: 1px solid var(--line);
  white-space: nowrap; }}
td {{ padding: .42rem .6rem; border-bottom: 1px solid var(--line);
  vertical-align: top; }}
.scroll {{ overflow-x: auto; }}
code {{ font: .85em ui-monospace, Menlo, monospace; color: var(--acc); }}
.pill {{ font-size: .74rem; font-weight: 600; padding: .1rem .55rem;
  border-radius: 99px; white-space: nowrap; }}
.pill.ok {{ background: color-mix(in srgb, var(--ok) 14%, transparent);
  color: var(--ok); }}
.pill.warn {{ background: color-mix(in srgb, var(--warn) 16%, transparent);
  color: var(--warn); }}
.pill.off {{ background: color-mix(in srgb, var(--off) 14%, transparent);
  color: var(--off); }}
details {{ border: 1px solid var(--line); border-radius: 8px;
  padding: .5rem .8rem; margin: .4rem 0; background: var(--panel); }}
summary {{ cursor: pointer; }}
summary .d {{ color: var(--mut); font-size: .85rem; margin-left: .4rem; }}
pre {{ overflow-x: auto; font-size: .78rem; line-height: 1.45;
  color: var(--mut); margin: .6rem 0 .2rem; }}
ul {{ padding-left: 1.2rem; }} li {{ margin: .25rem 0; }}
img {{ max-width: 100%; border: 1px solid var(--line); border-radius: 8px; }}
.gate {{ border-left: 3px solid var(--acc); padding: .1rem 0 .1rem .9rem;
  color: var(--mut); }}
</style>
<main>
<h1>DesignSafe MCP</h1>
<p class="sub">{esc(caps["scope"])}. Nothing reaches HPC without a
human-minted approval token, and every compute action ends in a
provenance manifest.</p>

<h2>What we support</h2>
{domain_html}
<section><h3>Out of scope</h3><ul>{oos}</ul></section>

<h2>Tools by layer ({len(tools)})</h2>
{tools_html}
<p class="gate">The safety spine is fixed: validate → estimate cost →
human approval (sha256 token over the exact job) → submit → manifest.
An edited job invalidates its token.</p>

<h2>Tested snippet corpus</h2>
<div class="scroll"><table><thead><tr><th>id</th><th>title</th>
<th>app</th></tr></thead><tbody>{snip_rows}</tbody></table></div>

<h2>Resources</h2>
<p>{listed}</p>
<p>The OpenSees decision matrix agents plan against, as taught in the
training deck:</p>
<img src="data:image/png;base64,{img_b64}"
  alt="Decision matrix for OpenSees on DesignSafe cyberinfrastructure">
</main>
"""
    out = ROOT / "preview.html"
    out.write_text(page)
    print(f"{out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
