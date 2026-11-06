# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/).

## [0.1.0] - 2026-11-06

### Added
- `scripts/generate_kb.py`: hybrid (seed catalog + LLM) generator for 20 synthetic NetCore Systems KB articles in two domains (networking, meetings), rendered as PDF, HTML and Markdown, with embedded metadata and a `manifest.json` per domain.
- `scripts/verify_kb.py`: smoke test that uses LangChain document loaders.
- `Makefile` targets: `help`, `install`, `generate*`, `regenerate`, `verify`, `clean`, `clean-data`.
- `.env.example`, README, TROUBLESHOOTING, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, MIT LICENSE.

### Security
- `.env` added to `.gitignore`.
