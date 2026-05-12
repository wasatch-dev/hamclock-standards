#!/usr/bin/env python3
# Copyright 2026 Open HamClock Standards
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may find a copy of the License in the LICENSE file at the repo root.

"""
generate_docs.py
Reads hamclock-openapi.yaml and writes hamclock-api-docs.html —
a fully self-contained Swagger UI page with the spec embedded inline.

Usage:
    python3 generate_docs.py
    python3 generate_docs.py --spec my-spec.yaml --out my-docs.html
    python3 generate_docs.py --serve          # generate then serve on :8080
    python3 generate_docs.py --serve --port 9000
"""

import argparse
import http.server
import json
import os
import sys
import threading
import webbrowser

# ── Try to load PyYAML; fall back to stdlib json if the spec is JSON ──────────
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ─────────────────────────────────────────────────────────────────────────────
# HTML template — {spec_json} is replaced with the spec as a JS object literal
# ─────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HamClock API Docs</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow:wght@300;400;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.min.css" />
  <style>
    :root {{
      --bg:        #0b0f14;
      --surface:   #111820;
      --border:    #1e2d3d;
      --accent:    #00d4aa;
      --accent2:   #ff7043;
      --text:      #c9d8e8;
      --muted:     #4a6278;
      --font-mono: 'Share Tech Mono', monospace;
      --font-body: 'Barlow', sans-serif;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-body);
      min-height: 100vh;
    }}
    header {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 18px 32px;
      display: flex;
      align-items: center;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 100;
    }}
    .logo-icon {{
      width: 36px; height: 36px;
      border: 2px solid var(--accent);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
      animation: pulse 3s ease-in-out infinite;
    }}
    .logo-icon svg {{ width: 18px; height: 18px; fill: var(--accent); }}
    @keyframes pulse {{
      0%, 100% {{ box-shadow: 0 0 0 0 rgba(0,212,170,.4); }}
      50%       {{ box-shadow: 0 0 0 8px rgba(0,212,170,0); }}
    }}
    header h1 {{
      font-family: var(--font-mono);
      font-size: 1.1rem;
      letter-spacing: .12em;
      color: var(--accent);
    }}
    header h1 span {{ color: var(--muted); font-size: .8rem; margin-left: 10px; letter-spacing: 0; }}
    .header-badge {{
      margin-left: auto;
      font-family: var(--font-mono);
      font-size: .7rem;
      letter-spacing: .08em;
      color: var(--accent2);
      border: 1px solid var(--accent2);
      padding: 3px 10px;
      border-radius: 2px;
    }}
    #swagger-ui {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 24px 16px 60px;
    }}
    .swagger-ui .topbar {{ display: none !important; }}
    .swagger-ui .info .title {{
      font-family: var(--font-mono) !important;
      color: var(--accent) !important;
      font-size: 1.6rem !important;
    }}
    .swagger-ui .info .description p,
    .swagger-ui .info p {{ color: var(--text) !important; font-family: var(--font-body) !important; }}
    .swagger-ui .info a {{ color: var(--accent) !important; }}
    .swagger-ui .info .version {{
      background: var(--accent) !important;
      color: #000 !important;
      font-family: var(--font-mono) !important;
      font-size: .7rem !important;
    }}
    .swagger-ui .scheme-container {{
      background: var(--surface) !important;
      border: 1px solid var(--border) !important;
      box-shadow: none !important;
      padding: 12px 16px !important;
    }}
    .swagger-ui .scheme-container .schemes > label {{
      color: var(--muted) !important;
      font-family: var(--font-mono) !important;
      font-size: .75rem !important;
    }}
    .swagger-ui select {{
      background: var(--bg) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
      font-family: var(--font-mono) !important;
    }}
    .swagger-ui .opblock-tag {{
      font-family: var(--font-mono) !important;
      color: var(--accent) !important;
      border-bottom: 1px solid var(--border) !important;
      font-size: .85rem !important;
      letter-spacing: .1em !important;
    }}
    .swagger-ui .opblock-tag:hover {{ background: rgba(0,212,170,.04) !important; }}
    .swagger-ui .opblock-tag svg {{ fill: var(--muted) !important; }}
    .swagger-ui .opblock {{
      background: var(--surface) !important;
      border: 1px solid var(--border) !important;
      border-radius: 4px !important;
      box-shadow: none !important;
      margin-bottom: 6px !important;
    }}
    .swagger-ui .opblock.is-open {{ border-color: var(--accent) !important; }}
    .swagger-ui .opblock .opblock-summary {{
      border: none !important;
      background: transparent !important;
    }}
    .swagger-ui .opblock .opblock-summary:hover {{ background: rgba(255,255,255,.02) !important; }}
    .swagger-ui .opblock-summary-method {{
      font-family: var(--font-mono) !important;
      font-size: .72rem !important;
      border-radius: 3px !important;
      min-width: 52px !important;
      text-align: center !important;
    }}
    .swagger-ui .opblock.opblock-get .opblock-summary-method,
    .swagger-ui .opblock.opblock-get {{
      background: rgba(0,212,170,.08) !important;
      border-color: rgba(0,212,170,.25) !important;
    }}
    .swagger-ui .opblock.opblock-get .opblock-summary-method {{
      background: rgba(0,212,170,.2) !important;
      color: var(--accent) !important;
    }}
    .swagger-ui .opblock-summary-path {{
      font-family: var(--font-mono) !important;
      font-size: .8rem !important;
      color: var(--text) !important;
    }}
    .swagger-ui .opblock-summary-path .nostyle {{ color: var(--text) !important; }}
    .swagger-ui .opblock-summary-description {{
      color: var(--muted) !important;
      font-family: var(--font-body) !important;
      font-size: .8rem !important;
    }}
    .swagger-ui .opblock-body {{ background: rgba(0,0,0,.25) !important; }}
    .swagger-ui .opblock-description-wrapper p,
    .swagger-ui .opblock-section-header h4,
    .swagger-ui table thead tr th,
    .swagger-ui .parameter__name,
    .swagger-ui .parameter__in,
    .swagger-ui .parameter__type,
    .swagger-ui .response-col_status,
    .swagger-ui .response-col_description,
    .swagger-ui .responses-inner h4,
    .swagger-ui .responses-inner h5,
    .swagger-ui label {{ color: var(--text) !important; }}
    .swagger-ui .parameter__name {{ font-family: var(--font-mono) !important; font-size: .8rem !important; }}
    .swagger-ui .parameter__in {{ font-family: var(--font-mono) !important; color: var(--muted) !important; font-size: .72rem !important; }}
    .swagger-ui .parameter__type {{ font-family: var(--font-mono) !important; color: var(--accent2) !important; font-size: .72rem !important; }}
    .swagger-ui table {{ background: transparent !important; }}
    .swagger-ui table thead tr {{ background: rgba(0,0,0,.2) !important; border: none !important; }}
    .swagger-ui table tbody tr {{ background: transparent !important; border-top: 1px solid var(--border) !important; }}
    .swagger-ui table tbody tr:hover {{ background: rgba(255,255,255,.02) !important; }}
    .swagger-ui table tbody tr td {{ border: none !important; color: var(--text) !important; }}
    .swagger-ui .btn.execute {{
      background: var(--accent) !important;
      color: #000 !important;
      border: none !important;
      font-family: var(--font-mono) !important;
      font-size: .75rem !important;
      letter-spacing: .08em !important;
      border-radius: 3px !important;
    }}
    .swagger-ui .btn.execute:hover {{ background: #00ffcc !important; }}
    .swagger-ui .btn {{
      background: var(--surface) !important;
      color: var(--text) !important;
      border: 1px solid var(--border) !important;
      font-family: var(--font-mono) !important;
      font-size: .75rem !important;
      border-radius: 3px !important;
    }}
    .swagger-ui .highlight-code,
    .swagger-ui .microlight,
    .swagger-ui pre {{
      background: #060a0e !important;
      border: 1px solid var(--border) !important;
      border-radius: 3px !important;
      color: var(--accent) !important;
      font-family: var(--font-mono) !important;
      font-size: .78rem !important;
    }}
    .swagger-ui input[type=text],
    .swagger-ui textarea {{
      background: var(--bg) !important;
      border: 1px solid var(--border) !important;
      color: var(--text) !important;
      font-family: var(--font-mono) !important;
      border-radius: 3px !important;
    }}
    .swagger-ui input[type=text]:focus,
    .swagger-ui textarea:focus {{
      border-color: var(--accent) !important;
      outline: none !important;
    }}
    .swagger-ui .response-col_status {{ font-family: var(--font-mono) !important; }}
    .swagger-ui .responses-table .response-col_status {{ color: var(--accent) !important; }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--muted); }}
    .swagger-ui .auth-wrapper {{ display: none; }}
    .swagger-ui section.models {{ display: none; }}
  </style>
</head>
<body>
<header>
  <div class="logo-icon">
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
    </svg>
  </div>
  <h1>HAMCLOCK API <span>OpenAPI 3.1 Reference</span></h1>
  <div class="header-badge">73 DE HamClock</div>
</header>

<div id="swagger-ui"></div>

<script>
const SPEC = {spec_json};
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-standalone-preset.min.js"></script>
<script>
  window.onload = () => {{
    SwaggerUIBundle({{
      spec: SPEC,
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      layout: 'StandaloneLayout',
      defaultModelsExpandDepth: -1,
      defaultModelExpandDepth: 1,
      docExpansion: 'list',
      filter: true,
      tryItOutEnabled: false,
    }});
  }};
</script>
</body>
</html>
"""


def load_spec(spec_path: str) -> dict:
    """Load an OpenAPI spec from a YAML or JSON file."""
    if not os.path.exists(spec_path):
        sys.exit(f"ERROR: spec file not found: {spec_path}")

    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()

    if spec_path.endswith((".yaml", ".yml")):
        if not HAS_YAML:
            sys.exit(
                "ERROR: PyYAML is not installed.\n"
                "Run:  pip install pyyaml\n"
                "Or supply a JSON spec file instead."
            )
        return yaml.safe_load(content)
    else:
        return json.loads(content)


def generate(spec_path: str, out_path: str) -> None:
    """Read the spec and write the HTML file."""
    print(f"Reading spec : {spec_path}")
    spec = load_spec(spec_path)

    spec_json = json.dumps(spec, indent=2)
    html = HTML_TEMPLATE.format(spec_json=spec_json)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Written      : {out_path}  ({os.path.getsize(out_path):,} bytes)")


def serve(out_path: str, port: int) -> None:
    """Serve the output directory over HTTP and open the browser."""
    directory = os.path.dirname(os.path.abspath(out_path))
    filename  = os.path.basename(out_path)
    url       = f"http://localhost:{port}/{filename}"

    os.chdir(directory)

    handler = http.server.SimpleHTTPRequestHandler
    # Silence request logs — remove the next two lines to see them
    handler.log_message = lambda *args: None

    server = http.server.HTTPServer(("", port), handler)
    print(f"Serving on   : {url}")
    print("Press Ctrl+C to stop.\n")

    threading.Timer(0.5, webbrowser.open, args=[url]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Swagger UI HTML page from an OpenAPI YAML/JSON spec."
    )
    parser.add_argument(
        "--spec", default="hamclock-openapi.yaml",
        help="Path to the OpenAPI spec file (YAML or JSON). Default: hamclock-openapi.yaml"
    )
    parser.add_argument(
        "--out", default="hamclock-api-docs.html",
        help="Output HTML file path. Default: hamclock-api-docs.html"
    )
    parser.add_argument(
        "--serve", action="store_true",
        help="After generating, serve the file over HTTP and open the browser."
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port for the built-in HTTP server (default: 8080). Implies --serve."
    )
    args = parser.parse_args()

    generate(args.spec, args.out)

    if args.serve or args.port != 8080:
        serve(args.out, args.port)


if __name__ == "__main__":
    main()
