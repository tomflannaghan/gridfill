# Deploying gridfill

gridfill is hosted at **https://gridfill.flannaghan.com**, alongside the
coultershaw-hydro project on the same Lightsail server. Two pieces get
deployed:

- **backend** — the `gridfill-server` FastAPI service (grid detection),
  running under systemd as the `gridfill` user, bound to `127.0.0.1:8420`.
- **frontend** — the React web editor, built to static files and served by
  nginx.

nginx serves the SPA and reverse-proxies `/api/` to the backend, with rate
limiting to protect the shared box.

Everything is done with Ansible except issuing the TLS certificate (a one-time
`certbot` run) and the DNS record — see [Manual steps](#manual-steps).

> **Nothing secret is needed or checked in.** All Python dependencies come from
> public PyPI (no private index, so no `pip.conf`), and the backend needs no
> config file or credentials.

## Requirements on the local machine

The machine you deploy *from* needs:

- `ansible` (ansible-core is enough — only built-in modules are used, no extra
  collections).
- `uv` — used to build the backend wheel (`cd python && uv build`).
- `node` + `npm` — used to build the frontend.
- SSH access to the server as host `coultershaw_server`. As in the
  coultershaw-hydro project, `~/.ssh/config` should contain:

  ```
  Host coultershaw_server
  HostName <static ip assigned in AWS>
  User ubuntu
  ```

The server is assumed to already have nginx installed (it hosts
coultershaw-hydro too).

## Deploy

A [Makefile](Makefile) wraps the three playbooks below — each target just
`cd`s into the matching subfolder and runs `ansible-playbook`. Run these from
`deploy/`, in order the first time (subsequent redeploys are safe to re-run in
any order/combination):

```bash
make backend    # just the backend
make nginx      # just nginx
make frontend   # just the frontend
make backend frontend   # both, one after the other
make all        # backend, nginx, frontend, in that order
```

### 1. Backend (`make backend`)

Builds a wheel locally, uploads it, installs it into a venv owned by the
`gridfill` user, and starts the systemd service.

Check it: `ssh coultershaw_server systemctl status gridfill`, or
`curl -F file=@some-scan.png http://127.0.0.1:8420/api/detect` from an SSH
session on the server.

### 2. nginx (`make nginx`) — HTTP only, first pass

Installs the rate-limit zones and the site config. On this first run no
certificate exists yet, so it serves HTTP only and prepares the ACME challenge
path. It also installs `certbot`.

### 3. Issue the TLS certificate (manual, one-time)

See [Manual steps](#manual-steps) below — point DNS at the server and run
`certbot`. Then **re-run `make nginx`** so it detects the certificate and
switches to HTTPS (with an HTTP→HTTPS redirect).

### 4. Frontend (`make frontend`)

Builds the web editor (with the API URL baked in) and uploads the static files.

Visit https://gridfill.flannaghan.com — open a `.cwd`, or upload a scan/PDF to
have the backend detect a grid.

## Manual steps

Only two things are not automated:

### DNS

Point `gridfill.flannaghan.com` (an A record) at the server's static IP,
wherever `flannaghan.com`'s DNS is managed. Wait for it to propagate before
running certbot.

### TLS certificate

certbot is installed by the nginx playbook and run in **webroot** mode, so it
only issues/renews the certificate and never edits the Ansible-managed nginx
config. Once DNS resolves and the HTTP site is up (steps 1–2), run once on the
server:

```bash
ssh coultershaw_server
sudo certbot certonly --webroot \
  -w /var/www/gridfill.flannaghan.com/html \
  -d gridfill.flannaghan.com
```

certbot installs a systemd timer that auto-renews. Verify with
`sudo certbot renew --dry-run`. After the certificate exists, re-run the nginx
playbook (step 3) to enable HTTPS.

## How it fits together

```
                 gridfill.flannaghan.com  (nginx, TLS)
                 ├── /                     -> static SPA (/var/www/.../html)
                 └── /api/  (rate limited) -> 127.0.0.1:8420  (gridfill.service)
```

- **Rate limiting** ([nginx/gridfill_ratelimit.conf](nginx/gridfill_ratelimit.conf)):
  the `/api/` location is capped at 20 requests/minute per IP (burst 10) and 4
  concurrent connections per IP, returning `429` when exceeded. Uploads are
  capped at 25 MB (`client_max_body_size`). Detection is CPU/memory heavy, so
  these are deliberately conservative — adjust the `rate`/`burst` there if
  needed.
- **Backend hardening** ([backend/gridfill.service](backend/gridfill.service)):
  runs as an unprivileged user with `ProtectSystem=strict`, `PrivateTmp`, and a
  `MemoryMax` cap so a large detection can't take down the shared 1 GB box.
- **Redeploys**: re-running a playbook picks up new code. The backend force-
  reinstalls the app even at the same version number; the frontend clears old
  hashed assets before uploading.

## Files

| Path | What it does |
| --- | --- |
| [Makefile](Makefile) | `make backend` / `make nginx` / `make frontend` / `make all` |
| [backend/playbook_backend.yaml](backend/playbook_backend.yaml) | Build wheel, install into venv, run systemd service |
| [backend/gridfill.service](backend/gridfill.service) | systemd unit for `gridfill-server` |
| [frontend/playbook_frontend.yaml](frontend/playbook_frontend.yaml) | Build the SPA and upload static files |
| [nginx/playbook_nginx.yaml](nginx/playbook_nginx.yaml) | Site config, rate-limit zones, certbot install |
| [nginx/templates/gridfill.flannaghan.com.conf.j2](nginx/templates/gridfill.flannaghan.com.conf.j2) | nginx site (HTTP-only until cert exists, then HTTPS) |
| [nginx/gridfill_ratelimit.conf](nginx/gridfill_ratelimit.conf) | `limit_req` / `limit_conn` zones |
