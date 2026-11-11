# Contributing to Proxyz

Thank you for wanting to contribute! This short guide will help get
your PR accepted quickly.

## Getting started

```bash
git clone https://github.com/Dvifnyz/Proxyz.git
cd Proxyz
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python -m proxyz doctor
```

## Ground rules

1. **One PR, one change.** Don't mix a new feature with a large
   refactor.
2. **Test first.** Every new feature/bugfix must come with tests in
   `tests/` and `pytest -q` must be green.
3. **Don't break the public API** (see `docs/API.md`) without
   discussing it in an issue first.
4. **Don't commit secrets**: API keys, tokens, passwords, private keys,
   the `config/webshare.json` file, `output/`, or `.env`.
5. **Write clear commits**, format: `type: short summary`
   (`feat:`, `fix:`, `docs:`, `test:`, `chore:`). Example:
   `feat: add country filter for SOCKS5`.

## Adding a new harvest source

1. Add the URL to `config/sources.json` (the `http` / `socks4` /
   `socks5` group).
2. Make sure the format is one `ip:port` per line (or JSON `proxies` —
   see `proxyz/sources.py`).
3. Run `pytest -q` and one live harvest to confirm the source
   returns results.

## Adding a new CLI command

1. Write the function in `proxyz/cli.py` + register it in `build_parser()`.
2. Add a row to the commands table in `README.md`.
3. Add tests in `tests/test_*.py`.

## What will not be accepted

- Automatic captcha solvers, mass account farms, Turnstile /
  anti-bot bypasses, and any form of automated account creation.
- Code that disables TLS verification, executes commands from
  a server, or stores hardcoded credentials.
- Changes that delete user data without confirmation
  (e.g. `DELETE` without a backup).

## Lint & audit

Before sending a PR, run this (ruff and vulture are in the `dev` extra):

```bash
ruff check proxyz/ tests/     # must be 0 errors; rules are in pyproject.toml
python -m vulture proxyz/ --min-confidence 80   # must be empty
pytest -q                     # must be green
```

Two rules are deliberately disabled in the config (read the reasons in pyproject):
`BLE001`/`S110` (a network error = dead proxy, not a bug) and
`S101` (asserts are how pytest works).

## Reporting bugs

Use the "Bug report" issue template: include your Proxyz version
(`proxyz --version`), the command you ran, the output of
`proxyz doctor`, and any relevant logs — **without API keys/tokens**.

## License

By submitting a PR, you agree that your contribution is licensed
under the same MIT license as this project.
