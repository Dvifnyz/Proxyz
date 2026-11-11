# Security Policy

## Reporting a vulnerability

**Do not report vulnerabilities via a public issue.**

Send the report to the repo owner via GitHub
([open a private issue / contact repo owner Dvifnyz](https://github.com/Dvifnyz))
with:

- a description of the vulnerability and its impact,
- reproduction steps (if any),
- the Proxyz version used (`proxyz --version`).

We will respond and fix it as soon as possible, then record it in the
CHANGELOG.

## What is already protected in Proxyz

- **Gateway only binds `127.0.0.1`** — not exposed to LAN/internet
  by default.
- **Optional token** (`PROXYZ_TOKEN`) for API & proxy usage;
  the token is never written to a config file.
- **API rate limit** (60/min per IP) + audit log
  (`output/gateway-audit.jsonl`).
- **TLS verification stays on** (system CA store); no
  `verify=False` / `ssl=False` anywhere.
- **Safe updater**: updates only via `pip` from GitHub releases —
  never runs commands from a server.
- **Webshare API key** stored locally with mode `0600` and never
  committed (`.gitignore`).
- **9Router sync** never deletes other people's data:
  insert-only, backup first, `--ganti` only deletes rows
  tagged Proxyz.

## Out of scope

- The free public proxies themselves (not owned by Proxyz; their
  quality and security are outside this tool's control). Don't send
  sensitive data through a public proxy you don't know.
- The user's Webshare / Cloudflare account (look after your own API key).
- Vulnerabilities in third-party dependencies — report them to the
  relevant project, or let us know so we can bump the version.

## What we will not build

Automatic captcha solvers, mass account farms, and anti-bot bypasses —
not because we can't, but because they get user accounts banned fast
and put this repo at risk of being taken down.
