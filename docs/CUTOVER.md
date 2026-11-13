# Cutover runbook (Phase 5, part B)

Everything here is done **by the owner on the server**. Claude prepared the files and
tested the stack locally; it has not connected to the server, changed DNS or run
`deploy/deploy.sh`. Nothing in this runbook has been executed yet.

**Addresses (decided 2026-11-13).** The owner cannot get into the Cloudflare account
that holds the DNS zone, so no subdomains are used. Both stacks share the host name;
the one that does not hold the main address sits on a port:

| | new calculator | old Streamlit app |
|---|---|---|
| before cutover | `https://neomortalsurv.net:8443` | `https://neomortalsurv.net` |
| after cutover | `https://neomortalsurv.net` | `https://neomortalsurv.net:8444` |

If Cloudflare access comes back, `staging.` / `legacy.` names can replace the ports by
editing `deploy/.env` only.

What was tested locally (2026-11-13) and what was not:

| Tested on the workstation | Not tested — first time is on the server |
|---|---|
| Both images build; API image has no torch | Let's Encrypt certificates for the real names |
| Stack starts, API healthy, 35 browser tests pass against it | Docker on the server's Ubuntu with 3.8 GiB RAM and no swap |
| Security headers, strict CSP, single-page fallback | Streamlit behind Caddy (websocket, its own paths) |
| Caddy proxies a second site to a process on the host; port-based staging, cutover swap and rollback (with `localhost`) | Streamlit listening on the Docker bridge address; ports 8443 / 8444 reachable from outside |
| Containers run as non-root, API file system read-only | Building the images on the server (memory) |

## 0. Before you start

- Pick a quiet time: steps 3–4 interrupt the live site for a few minutes.
- Have a second SSH session open the whole time.
- Certificate hooks, checked on 2026-11-13: none exist (the deploy-hook directory is
  empty, the renewal file has no hook lines). Step 5 has no hook to remove.
- The server reports "System restart required" and pending security updates. If you
  want to restart it, do it just before step 3, which interrupts the site anyway.

## 1. Open the two extra ports

No DNS change. Ports 8443 and 8444 must be reachable from outside, next to 80 and 443.

    sudo ufw status                 # if "inactive", the server itself blocks nothing

If ufw is active: `sudo ufw allow 8443/tcp && sudo ufw allow 8444/tcp`. If a firewall is
switched on in the Hostinger control panel for this server, allow both ports there as
well. (Reachability can only be confirmed in step 4, once Caddy listens.)

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
`https://neomortalsurv.net:8443` and the old app, unchanged, on
`https://neomortalsurv.net`, with a fresh certificate from Caddy. Check, **from a
computer outside the server** as well (this is the firewall test of step 1):

    curl -s https://neomortalsurv.net:8443/api/v1/health
    curl -sI https://neomortalsurv.net | head -1
    curl -sI http://neomortalsurv.net | head -3       # now redirects to https

Open both in a browser. On the old app run one calculation (this exercises the
websocket through Caddy).

**If the old site does not come back:** stop the stack and restore Streamlit —

    docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.legacy.yml --env-file deploy/.env down
    # put the saved run.sh back, remove the two lines from the unit file
    sudo systemctl daemon-reload && sudo systemctl restart streamlit

## 5. Switch certbot's schedule off (done 2026-11-13)

Caddy now renews the certificate. Two ACME clients for one name must not both run, so
certbot's schedule is off; its certificate files are **kept** until step 9, because the
full undo of step 3 (Streamlit alone on port 443) needs them. They are valid until
2027-02-05.

    sudo systemctl disable --now certbot.timer
    sudo mv /etc/cron.d/certbot /etc/cron.d/certbot.disabled

To switch it back on: `sudo mv /etc/cron.d/certbot.disabled /etc/cron.d/certbot` and
`sudo systemctl enable --now certbot.timer`.

## 6. Compare cases on the staging address

Owner and a clinical co-author enter the same cases on both sites. The old app (since
the hot-fix of 2026-11-12) and the new one use the same model in the same order, so
log-risk and percentages must agree: old site two decimals, new site one decimal in
"Details" and whole percent in the headline.

| # | Case | Expected log-risk | Day 7 / 28 / 100, % |
|---|---|---|---|
| 1 | Article Figure 8: BOH yes, 900 g, Apgar 3, GA 27, RF III, HR 80, SpO2 55, all four diagnoses yes | 1.210 | 65.22 / 39.52 / 5.63 |
| 2 | 400 g, Apgar 0, GA 20, HR 60, SpO2 40, BOH no, RF II, **RDS yes only** | 0.647 | 78.39 / 58.93 / 19.41 |
| 3 | same as 2, but **NEC yes only** | −0.681 | 93.76 / 86.93 / 64.78 |
| | *Cases 1–3 on the new calculator were checked through its API on staging on 2026-11-13 and match; the old app gave the same numbers on 2026-11-12 after the hot-fix. They still need entering by hand on both sites for the sign-off.* | | |
| 4–10 | `TODO(owner)` / `TODO(clinical-review)`: seven realistic cases chosen by the clinical co-author; write the old site's numbers here and compare | | |

Also check on the staging address: both languages, the printed report, a phone, the
ward PC. Some hospital networks block unusual ports; if `:8443` does not open there,
compare from another network.
Record the sign-off in `docs/DECISIONS.md` (who, when, which cases).

## 7. Cutover

In `deploy/.env`:

    SITE_NEW=neomortalsurv.net
    SITE_LEGACY=neomortalsurv.net:8444

then `deploy/deploy.sh`. The main address now opens the new calculator; the old app is
on `https://neomortalsurv.net:8444`. Port 8443 stops answering.

Check `https://neomortalsurv.net/api/v1/health` and case 1 again.

## 8. Rollback (rehearse once, right after step 7)

Put the two lines back —

    SITE_NEW=neomortalsurv.net:8443
    SITE_LEGACY=neomortalsurv.net

— and run `deploy/deploy.sh`. The main address shows the old app again within a
minute; no DNS is involved, so there is nothing to wait for. Then repeat step 7. Note
the rehearsal in `docs/PROGRESS.md`.

## 9. After 30 days

Set `LEGACY=off` in `deploy/.env`, run `deploy/deploy.sh`, stop and disable
`streamlit.service`. Close ports 8443 and 8444 in the firewall again. Then remove certbot's
old certificate: `sudo certbot delete --cert-name neomortalsurv.net`. Keep the old directory or
archive it; the code is in git (`legacy-streamlit` branch).

## Later deploys

    cd ~/neomortalsurv && git pull && deploy/deploy.sh

## Still to decide (`TODO(owner)`)

- External uptime check on `https://neomortalsurv.net/api/v1/health` (spec Section 9).
- Whether the site shows a notice about the feature-order correction
  (`docs/ERRATUM_feature_order.md`).
- HSTS is sent with one year from the first response. If you want to be able to go
  back to plain HTTP during the trial, lower `max-age` in `deploy/Caddyfile` first.
