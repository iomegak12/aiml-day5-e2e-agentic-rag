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
- **Change the REST API:** keep the layers. Routes stay thin in `api/app/controllers/`, logic goes in `services/`, and data access goes in `repositories/`. DTOs live in `schemas/`, and errors are raised as `ProblemException` (RFC 9457).
- **Change the database schema:** edit `api/app/models/`, then add a migration with `uv run alembic -c api/alembic.ini revision --autogenerate -m "..."` and review it before `make db-migrate`.
- **Add a dependency:** `uv add <pkg>` for the runtime (it goes into the API image), or `uv add --group kb <pkg>` for KB generation and notebook-only packages.
- **Containers:** test with Docker, and with Podman if you can (`make api-up ENGINE=podman`). Keep image names fully qualified and volumes named.

## Before Opening a PR

1. `make generate && make verify` must pass (KB changes), and `make api-test` must pass (API or agent changes). New API behaviour needs a unit test, with external services faked as in `api/tests/conftest.py`.
2. Keep all content fictional: no real vendor or product names.
3. Never commit `.env` or API keys.
4. Add an entry under a new version heading in [CHANGELOG.md](CHANGELOG.md).
5. Use small, focused commits with clear messages.

By contributing you agree that your work is licensed under the [MIT License](LICENSE) and that you will follow the [Code of Conduct](CODE_OF_CONDUCT.md).
