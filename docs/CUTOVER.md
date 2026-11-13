# Cutover runbook (Phase 5, part B)

Everything here is done **by the owner on the server**. Claude prepared the files and
tested the stack locally; it has not connected to the server, changed DNS or run
`deploy/deploy.sh`. Nothing in this runbook has been executed yet.

Names assumed: `staging.neomortalsurv.net` and `legacy.neomortalsurv.net`. Replace
them everywhere if you choose others.

What was tested locally (2026-11-13) and what was not:

| Tested on the workstation | Not tested — first time is on the server |
|---|---|
| Both images build; API image has no torch | Let's Encrypt certificates for the real names |
| Stack starts, API healthy, 35 browser tests pass against it | Docker on the server's Ubuntu with 3.8 GiB RAM and no swap |
| Security headers, strict CSP, single-page fallback | Streamlit behind Caddy (websocket, its own paths) |
| Caddy proxies a second site to a process on the host | Streamlit listening on the Docker bridge address |
| Containers run as non-root, API file system read-only | Building the images on the server (memory) |

## 0. Before you start

- Pick a quiet time: steps 3–4 interrupt the live site for a few minutes.
- Have a second SSH session open the whole time.
- `TODO(owner)` still open from Phase 0: how does the renewed certificate reach
  Streamlit today? Run and note the output; it tells you whether a deploy hook exists
  that must be removed in step 5:

      ls /etc/letsencrypt/renewal-hooks/deploy
      grep -i hook /etc/letsencrypt/renewal/neomortalsurv.net.conf

## 1. DNS

Create two records pointing to the server's address, like the main domain:
`staging.neomortalsurv.net` and `legacy.neomortalsurv.net`. Wait until both resolve:

    dig +short staging.neomortalsurv.net legacy.neomortalsurv.net

## 2. Docker and the repository

Install Docker Engine and the compose plugin from Docker's own Ubuntu repository
(https://docs.docker.com/engine/install/ubuntu/). Then:

    docker --version && docker compose version
    ip -4 addr show docker0        # note the address, normally 172.17.0.1

With no swap and 3.8 GiB RAM, add swap before building images (the frontend build is
the hungry step):

    sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
    sudo mkswap /swapfile && sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

Get the code (a new directory; the old `/home/AuE/MortralCombat` stays as it is):

    git clone -b rebuild https://github.com/allminer1/MortralCombat.git ~/neomortalsurv
    cd ~/neomortalsurv
    cp deploy/.env.example deploy/.env      # then edit: ACME_EMAIL

The branch must be pushed first (owner's decision; nothing has been pushed since
Phase 0).

## 3. Move Streamlit off port 443 (short interruption starts)

Caddy needs ports 80 and 443. Streamlit moves to plain HTTP on the Docker bridge
address, reachable from containers and from the server itself, not from the internet.

Keep a copy of the current start script, then change the Streamlit command in
`/home/AuE/MortralCombat/run.sh`: remove the two `--server.sslCertFile` /
`--server.sslKeyFile` options and set

    --server.port 8501 --server.address 172.17.0.1

(use the `docker0` address from step 2). Because that address exists only once Docker
is running, make the service start after Docker: in
`/etc/systemd/system/streamlit.service`, under `[Unit]`, add

    After=docker.service
    Requires=docker.service

then

    sudo systemctl daemon-reload && sudo systemctl restart streamlit
    curl -sI http://172.17.0.1:8501 | head -1        # expect HTTP/1.1 200 OK
    curl -sI --max-time 5 http://<public address>:8501 | head -1   # expect no answer

If the last command does answer, a firewall rule is needed before going on.

## 4. Start the new stack (interruption ends)

    cd ~/neomortalsurv && deploy/deploy.sh

With the example `.env` this serves the new calculator on
`https://staging.neomortalsurv.net` and the old app, unchanged, on
`https://neomortalsurv.net`, both with fresh certificates from Caddy. Check:

    curl -s https://staging.neomortalsurv.net/api/v1/health
    curl -sI https://neomortalsurv.net | head -1
    curl -sI http://neomortalsurv.net | head -3       # now redirects to https

Open both in a browser. On the old app run one calculation (this exercises the
websocket through Caddy).

**If the old site does not come back:** stop the stack and restore Streamlit —

    docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.legacy.yml --env-file deploy/.env down
    # put the saved run.sh back, remove the two lines from the unit file
    sudo systemctl daemon-reload && sudo systemctl restart streamlit

## 5. Switch certbot off for this domain

Caddy now renews the certificates. Two ACME clients for one name must not both run.

    sudo certbot certificates                 # confirm what exists
    sudo certbot delete --cert-name neomortalsurv.net

Remove any deploy hook found in step 0. If certbot manages no other certificate on
this server: `sudo systemctl disable --now certbot.timer` and remove
`/etc/cron.d/certbot`.

## 6. Compare cases on staging

Owner and a clinical co-author enter the same cases on both sites. The old app (since
the hot-fix of 2026-11-12) and the new one use the same model in the same order, so
log-risk and percentages must agree: old site two decimals, new site one decimal in
"Details" and whole percent in the headline.

| # | Case | Expected log-risk | Day 7 / 28 / 100, % |
|---|---|---|---|
| 1 | Article Figure 8: BOH yes, 900 g, Apgar 3, GA 27, RF III, HR 80, SpO2 55, all four diagnoses yes | 1.210 | 65.22 / 39.52 / 5.63 |
| 2 | 400 g, Apgar 0, GA 20, HR 60, SpO2 40, BOH no, RF II, **RDS yes only** | 0.647 | 78.39 / 58.93 / 19.41 |
| 3 | same as 2, but **NEC yes only** | −0.681 | 93.76 / 86.93 / 64.78 |
| 4–10 | `TODO(owner)` / `TODO(clinical-review)`: seven realistic cases chosen by the clinical co-author; write the old site's numbers here and compare | | |

Also check on staging: both languages, the printed report, a phone, the ward PC.
Record the sign-off in `docs/DECISIONS.md` (who, when, which cases).

## 7. Cutover

In `deploy/.env`:

    SITE_NEW=neomortalsurv.net
    SITE_LEGACY=legacy.neomortalsurv.net

then `deploy/deploy.sh`. The main domain now opens the new calculator; the old app is
on `https://legacy.neomortalsurv.net`. `staging.` stops answering; delete its DNS
record or keep it for later tests by listing both names:
`SITE_NEW="neomortalsurv.net, staging.neomortalsurv.net"`.

Check `https://neomortalsurv.net/api/v1/health` and case 1 again.

## 8. Rollback (rehearse once, right after step 7)

Swap the two lines back —

    SITE_NEW=staging.neomortalsurv.net
    SITE_LEGACY=neomortalsurv.net

— and run `deploy/deploy.sh`. The main domain shows the old app again within a
minute; no DNS change is involved, so there is nothing to wait for. Then repeat step
7. Note the rehearsal in `docs/PROGRESS.md`.

## 9. After 30 days

Set `LEGACY=off` in `deploy/.env`, run `deploy/deploy.sh`, stop and disable
`streamlit.service`, delete the `legacy.` DNS record. Keep the old directory or
archive it; the code is in git (`legacy-streamlit` branch).

## Later deploys

    cd ~/neomortalsurv && git pull && deploy/deploy.sh

## Still to decide (`TODO(owner)`)

- External uptime check on `https://neomortalsurv.net/api/v1/health` (spec Section 9).
- Whether the site shows a notice about the feature-order correction
  (`docs/ERRATUM_feature_order.md`).
- HSTS is sent with one year from the first response. If you want to be able to go
  back to plain HTTP during the trial, lower `max-age` in `deploy/Caddyfile` first.
