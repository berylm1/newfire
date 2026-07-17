# Reddit post draft: Codeep cannot render HTML files visually

**Suggested subreddits:** r/selfhosted, r/LocalLLaMA, r/docker, or a Codeep-specific community if one exists.

---

## Title options (pick one)

1. Codeep 2.1.1 in Docker returns raw HTML instead of a browser preview, anyone solved this?
2. How are you previewing HTML output from Codeep when it runs headless in a container?
3. Codeep TUI shows HTML source instead of rendering it, looking for the standard fix

---

## Body

Hey all,

Running into a wall with Codeep and hoping someone has hit this before.

**Setup**
* Codeep 2.1.1 running in Docker on a Minisforum box
* TUI only, I attach with `docker exec -it codeep ...`
* Model provider is a remote vLLM serving `qwen3-coder-30b`
* Workspace lives on CephFS, mounted into the container at `/mnt/cephfs-mgmt/codeep-workspaces`

**What I want**
When I ask Codeep to show an HTML file from the workspace, I want a rendered preview I can open in my browser, same loop I get from other coding agents that ship with a built in preview tool.

**What I get**
Codeep prints the raw HTML markup back into the TUI as text. No browser tab, no preview URL, no rendered output anywhere. The file itself is fine, the agent just hands me the source.

**What I think is happening**
1. The container is headless, so there is no browser context for Codeep to open into.
2. I have not exposed any port from the container that a static server could use.
3. I do not think Codeep 2.1.1 has a `browser_preview` style tool wired up by default, so the model falls back to printing file contents.

**What I am about to try**
Spin up a tiny static file server inside the container scoped to the active workspace, expose a single port, and route it through my existing reverse proxy with auth so it is not wide open. Then register it with Codeep so the agent can hand me a URL instead of source.

**Questions**
* Is there a first party HTML preview tool in Codeep 2.1.1 that I am missing in the config?
* If you run Codeep headless in Docker, what does your preview loop look like?
* Anyone wired Codeep up to an external preview service cleanly, and if so how did you scope it so it does not serve the entire workspace tree?

Happy to share the docker compose and the agent config once I land on something that works. Thanks in advance.
