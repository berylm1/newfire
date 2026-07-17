# Bug Report: Codeep cannot render HTML files visually

**Reported:** 2026-05-22
**Reporter:** chisoba.9090@gmail.com
**Component:** Codeep 2.1.1 (dockerized, Minisforum)
**Severity:** Medium (blocks visual review of agent-generated HTML)
**Status:** Open

## Summary
Codeep returns the raw HTML markup as text instead of opening a browser preview when asked to display an HTML file from its workspace. There is no rendered visual output, only the source code.

## Environment
| Item | Value |
|---|---|
| Codeep version | 2.1.1 |
| Host | Minisforum (america) |
| Runtime | Docker container, TUI accessed via `docker exec` |
| Model provider | Custom provider, DGX vLLM, `qwen3-coder-30b` |
| Workspace path | `/mnt/cephfs-mgmt/codeep-workspaces` |
| Deployment date | 2026-05-20 |

## Expected behavior
When the user asks Codeep to show an HTML file located in the workspace, Codeep should open or serve that file in a browser so the user can see the rendered page (styles, layout, images applied).

## Actual behavior
Codeep prints the raw HTML/markup back into the TUI as plain text. No browser tab is opened, no preview URL is produced, and no rendered output is shown anywhere.

## Steps to reproduce
1. SSH into Minisforum as `newwaveclaw`.
2. Attach to the Codeep TUI: `docker exec -it codeep <codeep TUI entrypoint>`.
3. Inside a workspace under `/mnt/cephfs-mgmt/codeep-workspaces`, create or open an `.html` file with valid markup (for example a small page with a heading and inline CSS).
4. Ask Codeep to preview or display the HTML file.
5. Observe that the response is the HTML source code rendered as text in the TUI.

## Impact
* Users cannot visually verify HTML output produced by the agent.
* Front-end iteration loops (generate, preview, refine) are broken inside Codeep.
* Forces the user to manually copy files out of the container to view them, which defeats the purpose of running Codeep as the coding agent.

## Root cause (confirmed 2026-05-22)
Inspection of `/usr/local/lib/node_modules/codeep/dist/utils/tools.js` shows Codeep 2.1.1 ships with this tool catalog only:

`read_file, write_file, edit_file, delete_file, list_files, create_directory, execute_command, search_code, find_files, fetch_url, web_search, web_read, github_read, minimax_web_search, zai_analyze_image, minimax_understand_image`

No `browser_preview`, `open_url`, or `serve_static` tool exists. The model picks `read_file` as the closest fallback when asked to "show" an HTML file, which is why the raw markup comes back in the TUI.

Supporting findings:
* Container publishes only `127.0.0.1:7681` (ttyd). No other port reaches the host, so even if a static server were spawned, the browser could not reach it.
* MCP support is wired in. Codeep loads servers from `~/.codeep/mcp_servers.json` (global) and `<workspace>/.codeep/mcp_servers.json` (project). Both files are absent, so zero external tools are registered.
* `tmux` plus `ttyd` keep the runtime fully headless, so any libraries like the bundled `open` npm module cannot launch a real browser from inside the container.

## Proposed next steps
1. Publish a second port from the Codeep container, bound to `127.0.0.1` on Minisforum, dedicated to preview traffic.
2. Build a small MCP server that exposes a `preview_html` tool. It must validate the requested path stays inside the active workspace (no `..` escapes), serve only that workspace subtree, and return a URL the user can open.
3. Register the MCP server in `/home/node/.codeep/mcp_servers.json` so the Codeep agent loads the new tool on next start. Confirm it appears in the tool catalog.
4. Route `codeep-preview.newfire.app` through the existing reverse proxy with auth in front, and keep the static server bound to localhost so the only public path is via the proxy.
5. Security checks before exposure: enforce per workspace scoping, require auth on the public hostname, log every preview hit, and never serve the whole `/mnt/cephfs-mgmt/codeep-workspaces` tree.

## Workaround
Copy the HTML file out of the container to the Mac (`scp` from Minisforum) and open it locally in a browser. This is manual and breaks the agent loop, so it is only acceptable as a stopgap.

## Acceptance criteria for the fix
* Asking Codeep to preview an HTML file inside `/mnt/cephfs-mgmt/codeep-workspaces` produces a URL that opens a rendered page in the user's browser.
* The preview reflects edits made by the agent without requiring a container restart.
* The preview endpoint is not publicly exposed without auth, and is scoped to the active workspace only.
