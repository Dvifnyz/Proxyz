# Changelog

All notable changes to Proxyz are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/).

## [2.1.4] - 2026-11-11

### Changed

- English is now the primary language of all documentation. The main
  README is English; the other 13 languages (including Indonesian)
  are optional translations in `docs/translations/`.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, issue/PR templates, `docs/API.md`,
  `docs/ARSITEKTUR.md`, and `RENCANA_KERJA.md` are now in English.

### Removed

- All thanks/credits to other projects and all README-structure
  references (itzluthfi, petani-proxy, FastAPI, uv) — removed from
  every markdown file in the project.
- `docs/STUDI_PETANI_PROXY.md` deleted.

## [2.1.3] - 2026-11-11

### Added

- README fully translated into 12 languages in `docs/translations/`:
  English, 中文 (Simplified), 한국어, 日本語, Русский, العربية,
  Afrikaans, Español, Português, Deutsch, Français, हिन्दी.
  The main README now has a language links row at the top.
- Literal error messages in the first column of the Troubleshooting
  table are deliberately NOT translated in any language — the program
  prints them in Indonesian, so users need to be able to match them.

### Fixed

- `docs/` listing in the README project structure: `MIGRASI` removed
  (the file was already deleted in v2.1.2).

## [2.1.2] - 2026-11-11

### Removed

- Compatibility shim `proxyx` removed entirely: the `proxyx/`
  package, the `proxyx` command, `python -m proxyx`, `import proxyx`,
  the `PROXYX_TOKEN` env fallback, the `X-Proxyx-Token` header, and
  cleanup of 9Router rows tagged `Proxyx`. There is only one name
  now: Proxyz. `docs/MIGRASI-2.1.md` was removed along with it
  (nothing left to migrate).
- The `.coverage` file that had been committed was also removed
  from git (it is already in `.gitignore`).

## [2.1.1] - 2026-11-11

### Fixed

- Full code audit (ruff, vulture, pylint, coverage): 139 ruff
  findings cleaned down to 0, duplicate code removed, dead code
  removed.
- The duplicated aiohttp `try/except ImportError` blocks in checker.py
  and harvester.py were moved to `proxyz/compat.py` (shared).
- 11 unused imports removed, 14 `try/except/pass` replaced with
  `contextlib.suppress`, 3 `try/except/continue` now log (debug)
  so failed sources/keys can be traced.
- `subprocess.run` in the updater & tests is now explicitly
  `check=False` (the return code is checked manually).
- Broken link in CHANGELOG: `docs/MIGRASI-3.0.md` -> `docs/MIGRASI-2.1.md`.

### Added

- New tests: CLI smoke test — all 15 subcommand `--help` run
  (previously cli.py was at 7% coverage). Total tests 83 -> 100.
- Ruff config moved into `pyproject.toml` (with a reason for each
  disabled rule), ruff + vulture added to the `dev` extra.

## [2.1.0] - 2026-11-11

> Note: this version was briefly published as v3.0.0, then withdrawn —
> a rename only, not a major change, so the version was corrected
> to v2.1.0. The v3.0.0 tag & release were deleted.

### Changed (breaking)

- **Tool renamed from Proxyx to Proxyz** (package, CLI,
  config, env, header). The old `proxyx` command was kept briefly
  as a deprecated shim, then removed in v2.1.2.
- `config/proxyx.json` -> `config/proxyz.json`.
- Env `PROXYX_TOKEN` -> `PROXYZ_TOKEN`.
- Header `X-Proxyx-Token` -> `X-Proxyz-Token`.
- 9Router rows are now tagged `Proxyz`.

### Added

- Big-repo standard README, CHANGELOG, CONTRIBUTING, SECURITY,
  Code of Conduct, issue/PR templates.
- GitHub repo description & topics.

## [2.0.0] - 2026-11-11

### Added

- Public API frozen & documented (`docs/API.md`).
- Automatic migration of `config/webshare.json` from the old
  `{"api_key"}` format to `{"api_keys"}`.

## [1.9.0] - 2026-11-11

### Added

- `proxyz doctor`: installation diagnostics (Python, config, sources,
  pool, Webshare key, blacklist, output, disk, gateway).

## [1.8.0] - 2026-11-11

### Added

- `proxyz laporan` (`output/laporan.md`) + `/api/report` endpoint.

## [1.7.0] - 2026-11-11

### Added

- `proxyz blacklist add|remove|list`; blacklist used during harvest & check.
- `proxyz panen --tier cepat|sedang|lambat`.

## [1.6.0] - 2026-11-11

### Added

- `proxyz auto`: periodic harvest -> check -> export cycle; `--sekali`
  for cron.

## [1.5.0] - 2026-11-11

### Added

- API rate limit (60/min per IP, 429 + Retry-After) + JSONL audit.
- SOCKS5 listener (`gateway --socks 1080`); UDP ASSOCIATE rejected.

## [1.4.0] - 2026-11-11

### Added

- `proxyz sync-9router` (safe: insert-only, backup, dedup).
- Gateway profiles `scraper` / `cepat` / `hemat`.
- Automatic pool backup (max 5) on every export.

## [1.3.0] - 2026-11-11

### Added

- `proxyz bench` + `/api/bench` endpoint.
- Dashboard v2 (leak test + speed test buttons, score colors).
- `proxyz install-service` (systemd + Windows Task).

## [1.2.0] - 2026-11-11

### Added

- `config/proxyz.json` actually read by the code.
- `/api/leak-test` + `proxyz test`; `/api/clash.yaml`.
- `proxyz update` (safe, via pip, falls back to tags).

## [1.1.0] - 2026-11-11

### Added

- Source health score + 1-hour backoff; `proxyz sources`.
- Multi-account residential; semi-automatic signup (live key validation).
- Real HTTP healer probe (not just TCP).

## [1.0.0] - 2026-11-11

### Added

- First release: 35-source harvester, async checker, rotating gateway
  + REST API + dashboard + PAC, WARP, TXT/JSON/CSV/Clash export,
  residential via the official Webshare API, Docker + CI.
