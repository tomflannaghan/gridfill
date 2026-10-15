---
name: this-healthcheck
description: Health check for the deployed gridfill webapp (https://gridfill.flannaghan.com), run by the global healthcheck skill. Checks the editor loads and grid detection works end to end. Reports problems; never redeploys or restarts anything.
---

# gridfill healthcheck

This check only reports. Don't redeploy, restart the service or change anything on the server. If something needs fixing, say what under "Needs attention", pointing at the relevant part of `deploy/README.md`.

## 1. The editor loads

```bash
B=https://gridfill.flannaghan.com
curl -s -w '\n%{http_code}\n' $B/
# Every asset the page references (the Vite build's hashed JS, CSS and icon)
curl -s $B/ | grep -oE '(src|href)="/[^"]+"' | sed 's/.*="//;s/"$//' | while read p; do
  curl -s -o /dev/null -w "%{http_code} $p\n" "$B$p"
done
# HTTP redirects to HTTPS
curl -sI http://gridfill.flannaghan.com | head -1
# Certificate expiry
echo | openssl s_client -connect gridfill.flannaghan.com:443 -servername gridfill.flannaghan.com 2>/dev/null | openssl x509 -noout -enddate
```

- The page must return 200 with `<title>Gridfill Editor</title>`, and every asset must return 200. A missing asset leaves a blank page, typically after a half-finished `make frontend`. Either is a **FAIL**.
- HTTP not returning a 301 to HTTPS is a **WARN**.
- A certificate that has expired is a **FAIL**; one expiring within 14 days is a **WARN**, because the snap certbot should have renewed it.

## 2. Grid detection works

Upload a test fixture to the live API, from the repo root:

```bash
curl -s -F file=@python/tests/fixtures/barred.png -w '\n%{http_code}\n' $B/api/detect
```

It should return 200 within a few seconds with a `.cwd` document: JSON with `"format": "gridfill"`, a `version` equal to `_FORMAT_VERSION` in `python/src/gridfill/document.py`, and one grid of 144 cells. Count the grids and cells with a short Python one-liner rather than printing the response, which contains a large base64 image.

- A 502 or 504 means nginx is up but the backend isn't: **FAIL**.
- A 429 means the rate limit was hit (20 requests a minute, shared with real users). Wait a minute and retry once; if it persists, it's a **WARN**.
- Any other error, a different format or version, or a different grid or cell count is a **FAIL**. A version mismatch means the backend and the repo are out of step, so a redeploy is probably missing.

Only send one request (plus the one retry); the server is shared and detection is CPU heavy.

## 3. The service on the server

Over SSH to `coultershaw_server` (read-only; give up after a timeout rather than hang):

```bash
timeout 30 ssh -o BatchMode=yes coultershaw_server '
  systemctl is-active gridfill
  systemctl show gridfill -p NRestarts -p ActiveEnterTimestamp
  journalctl -u gridfill --since "-24h" -p warning --no-pager | tail -20
'
```

- The service not `active` is a **FAIL**.
- Restarts (`NRestarts` above 0) or warnings and errors in the last day are a **WARN**: summarise them.

If SSH isn't available, say so and mark the run **WARN**; steps 1 and 2 still show whether the site works.

## Status

**OK** if every check passed, **WARN** if anything above was marked WARN, **FAIL** if the editor or detection is broken.
