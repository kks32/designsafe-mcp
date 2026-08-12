"""Local interactive playground for the MCP server.

Serves one page that lists every tool with a form generated from its
schema; submitting a form executes the real tool (in mock mode unless
DESIGNSAFE_MCP_MOCK=0) and shows the JSON result. No dependencies
beyond the package itself; no Inspector, no proxy.

Run: .venv/bin/python scripts/playground.py  ->  http://localhost:8787
"""

import asyncio
import html
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault("DESIGNSAFE_MCP_MOCK", "1")

from designsafe_mcp.server import mcp  # noqa: E402

PORT = 8787


def _tools() -> list:
    return asyncio.run(mcp.list_tools())


def _call(name: str, args: dict) -> str:
    async def run():
        return await mcp.call_tool(name, args)

    try:
        result = asyncio.run(run())
    except Exception as e:  # noqa: BLE001 - surface any tool error to the page
        return json.dumps({"error": str(e)}, indent=1)
    content = getattr(result, "content", None)
    if content:
        texts = [c.text for c in content if getattr(c, "text", None)]
        if texts:
            return "\n".join(texts)
    if isinstance(result, tuple):
        result = result[1] if len(result) > 1 else result[0]
    try:
        return json.dumps(result, indent=1, default=str)
    except TypeError:
        return str(result)


def _page() -> str:
    blocks = ""
    for t in _tools():
        raw = getattr(t, "input_schema", None) or {}
        props = raw.get("properties", {}) if isinstance(raw, dict) else {}
        required = set(raw.get("required", []))
        fields = ""
        for pname, spec in props.items():
            ptype = spec.get("type", "any")
            mark = " *" if pname in required else ""
            fields += (
                f"<label>{html.escape(pname)}{mark} "
                f"<span class='t'>{html.escape(str(ptype))}</span>"
                f"<input name='{html.escape(pname)}' "
                f"placeholder='{html.escape(str(spec.get('default', '')))}'>"
                "</label>")
        desc = html.escape((t.description or "").strip())
        blocks += f"""
<details id="{t.name}"><summary><code>{t.name}</code></summary>
<p class="d">{desc}</p>
<form onsubmit="return call(event, '{t.name}')">{fields}
<button>call</button></form>
<pre class="out" id="out-{t.name}"></pre></details>"""

    mode = os.environ.get("DESIGNSAFE_MCP_MOCK") == "1"
    badge = ("mock mode: canned Tapis, real approval gate, no SUs" if mode
             else "LIVE mode: real Tapis calls")
    return f"""<!doctype html><meta charset="utf-8">
<title>designsafe-mcp playground</title>
<style>
:root {{ --bg:#FAFAF8; --ink:#1A1D21; --mut:#5A6069; --line:#E3E2DD;
  --acc:#0E7C7B; --panel:#fff; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14171A; --ink:#E8EAED; --mut:#9AA1AA; --line:#2C3238;
    --acc:#3FB8B6; --panel:#1C2025; }} }}
body {{ background:var(--bg); color:var(--ink); margin:0;
  font:15px/1.5 ui-sans-serif,system-ui; }}
main {{ max-width:52rem; margin:0 auto; padding:2rem 1rem 4rem; }}
h1 {{ font-size:1.3rem; }} .badge {{ color:var(--acc); font-size:.85rem; }}
details {{ border:1px solid var(--line); border-radius:8px;
  background:var(--panel); padding:.5rem .9rem; margin:.5rem 0; }}
summary {{ cursor:pointer; }} code {{ color:var(--acc);
  font:.9em ui-monospace,Menlo,monospace; }}
.d {{ color:var(--mut); font-size:.85rem; white-space:pre-wrap; }}
label {{ display:block; margin:.35rem 0; font-size:.85rem; }}
.t {{ color:var(--mut); }}
input {{ display:block; width:100%; box-sizing:border-box; margin-top:2px;
  padding:.35rem .5rem; border:1px solid var(--line); border-radius:6px;
  background:var(--bg); color:var(--ink);
  font:.85rem ui-monospace,Menlo,monospace; }}
button {{ margin-top:.5rem; padding:.35rem 1rem; border:none;
  border-radius:6px; background:var(--acc); color:#fff; cursor:pointer; }}
pre.out {{ overflow-x:auto; font-size:.78rem; color:var(--mut);
  max-height:24rem; overflow-y:auto; }}
</style>
<main>
<h1>designsafe-mcp playground</h1>
<p class="badge">{badge}</p>
<p class="d">JSON typed into a field is parsed as JSON (e.g. true, 3,
["a"], {{"k": 1}}); anything else is a string. Empty fields are omitted.</p>
{blocks}
</main>
<script>
async function call(ev, name) {{
  ev.preventDefault();
  const args = {{}};
  for (const el of ev.target.elements) {{
    if (!el.name || el.value === "") continue;
    try {{ args[el.name] = JSON.parse(el.value); }}
    catch {{ args[el.name] = el.value; }}
  }}
  const out = document.getElementById("out-" + name);
  out.textContent = "...";
  const r = await fetch("/call/" + name, {{method: "POST",
    headers: {{"content-type": "application/json"}},
    body: JSON.stringify(args)}});
  out.textContent = await r.text();
  return false;
}}
</script>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, ctype: str = "text/html") -> None:
        data = body.encode()
        self.send_response(200)
        self.send_header("content-type", f"{ctype}; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        self._send(_page())

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        if not self.path.startswith("/call/"):
            self._send("{}", "application/json")
            return
        name = self.path.split("/call/", 1)[1]
        length = int(self.headers.get("content-length", 0))
        args = json.loads(self.rfile.read(length) or b"{}")
        self._send(_call(name, args), "application/json")

    def log_message(self, *a: object) -> None:
        pass


if __name__ == "__main__":
    print(f"playground: http://localhost:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
