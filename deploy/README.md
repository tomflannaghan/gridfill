# Deploying gridfill

gridfill is hosted at **https://gridfill.flannaghan.com** on `metatron`, a
server shared with other services. Two pieces get deployed from this repo:

- **backend** — the `gridfill-server` FastAPI service (grid detection), running
  under systemd as the `gridfill` user, bound to `127.0.0.1:3001`.
- **frontend** — the React web editor, built to static files that
  `gridfill-server` serves at `/`.

The public side belongs to the separate `metatron` repo, which owns nginx, TLS
(a wildcard certificate) and DNS. Its `nginx_sites` entry for gridfill proxies
the whole site to port 3001 and caps uploads at 25 MB. This repo doesn't touch
any of that; see `docs/deploying-apps.md` there.

> **Nothing secret is needed or checked in.** All Python dependencies come from
> public PyPI (no private index, so no `pip.conf`), and the backend needs no
> config file or credentials.

## Requirements on the local machine

The machine you deploy *from* needs:

- `ansible` (ansible-core is enough — only built-in modules are used, no extra
  collections).
- `uv` — used to build the backend wheel (`cd python && uv build`).
- `node` + `npm` — used to build the frontend.
- SSH access to the server as host `metatron`, with passwordless sudo.

## Deploy

A [Makefile](Makefile) wraps the two playbooks below — each target just `cd`s
into the matching subfolder and runs `ansible-playbook`. Run these from
`deploy/`, in any order or combination:

```bash
make backend    # just the backend
make frontend   # just the frontend
make all        # backend, then frontend
```

Until both have been deployed, the site returns 502 (no backend) or 404 (no
frontend).

### Backend (`make backend`)

Builds a wheel locally, uploads it, installs it into a venv owned by the
`gridfill` user, and starts the systemd service.

Check it: `ssh metatron systemctl status gridfill`, or
`curl -F file=@some-scan.png http://127.0.0.1:3001/api/detect` from an SSH
session on the server. `systemd-analyze security gridfill` should score about
1.5 ("OK").

### Frontend (`make frontend`)

Builds the web editor (with the API URL baked in) and uploads the static files.
No restart is needed.

Visit https://gridfill.flannaghan.com — open a `.cwd`, or upload a scan/PDF to
have the backend detect a grid.

## How it fits together

```
gridfill.flannaghan.com  (metatron's nginx, TLS, 25 MB upload cap)
└── /  -> 127.0.0.1:3001  (gridfill.service)
          ├── POST /api/detect  (rate limited)
          └── everything else   -> static SPA (/var/www/.../html)
```

- **Rate limiting** ([server.py](../python/src/gridfill/server.py)): the backend
  allows 20 detections/minute per client IP (burst 10), returning `429` with a
  `Retry-After` when exceeded, and runs one detection at a time, queueing the
  rest (`--max-concurrency`). Detection is CPU/memory heavy, so these are
  deliberately conservative — adjust `_rate_limiter` there if needed. The client
  IP comes from nginx's `X-Forwarded-For`. The state is per-process, so run a
  single worker.
- **Sandbox** ([backend/gridfill.service](backend/gridfill.service)): metatron's
  standard systemd hardening, plus a `MemoryMax` cap so a large detection can't
  affect the rest of the box.
- **Redeploys**: re-running a playbook picks up new code. The backend force-
  reinstalls the app even at the same version number; the frontend clears old
  hashed assets before uploading.

## Files

| Path | What it does |
| --- | --- |
| [Makefile](Makefile) | `make backend` / `make frontend` / `make all` |
| [backend/playbook_backend.yaml](backend/playbook_backend.yaml) | Build wheel, install into venv, run systemd service |
| [backend/gridfill.service](backend/gridfill.service) | systemd unit for `gridfill-server` |
| [frontend/playbook_frontend.yaml](frontend/playbook_frontend.yaml) | Build the SPA and upload static files |
