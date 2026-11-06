# Contributing

Thanks for helping improve the course material.

## Setup

```bash
cp .env.example .env   # add your own OpenAI key
make install
```

## Common Changes

- **Add or edit an article:** update `SEEDS` in [scripts/generate_kb.py](scripts/generate_kb.py), then run `make generate`.
- **Change shared facts** (thresholds, error codes): edit `DOMAIN_FACTS`, then run `make regenerate` so every article stays consistent.
- **Change layout or styling:** edit the `render_md`, `render_html` or `render_pdf` functions.

## Before Opening a PR

1. `make generate && make verify` must pass.
2. Keep all content fictional: no real vendor or product names.
3. Never commit `.env` or API keys.
4. Add an entry under a new version heading in [CHANGELOG.md](CHANGELOG.md).
5. Use small, focused commits with clear messages.

By contributing you agree that your work is licensed under the [MIT License](LICENSE) and that you will follow the [Code of Conduct](CODE_OF_CONDUCT.md).
