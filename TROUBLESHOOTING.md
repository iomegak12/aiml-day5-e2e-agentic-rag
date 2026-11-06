# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'OPENAI_MODEL'` | `.env` is missing or incomplete | `cp .env.example .env`, then set both variables |
| `AuthenticationError` / 401 | Invalid or expired API key | Update `OPENAI_API_KEY` in `.env` |
| `[fail] KB-…` in the output | Rate limit, timeout or schema error for that article | Re-run `make generate`. Only missing articles are regenerated |
| `make generate` does nothing | Every file already exists (skip-existing behaviour) | `make regenerate`, or delete specific files and re-run |
| `make: command not found` | GNU make isn't installed | Windows: `choco install make`. macOS: `xcode-select --install` |
| `BSHTMLLoader … uses the 'lxml' package` | `lxml` isn't installed | Use `make verify`, which supplies it. In your own code: `uv add lxml` |
| Garbled characters (`›`) in loaded HTML | Windows default encoding (cp1252) | Pass `open_encoding="utf-8"` to `BSHTMLLoader` |
| `DeprecationWarning: langchain-community is being sunset` | Upstream LangChain change | Harmless for now. See [langchain-community #674](https://github.com/langchain-ai/langchain-community/issues/674) |
| PDF page text starts with "NetCore Systems \| KB-… \| Page n" | The page footer is extracted as text | Expected. Strip it during chunk cleaning if you want |
| Frontmatter / `<meta>` missing from `Document.metadata` | `TextLoader` / `BSHTMLLoader` don't parse them | Join on `manifest.json` by file name, or parse them yourself |
| Articles differ between runs | LLM output is non-deterministic | Expected. The seeds and domain facts keep key values consistent |
