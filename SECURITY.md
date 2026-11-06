# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Reporting a Vulnerability

Please **do not** open a public issue. Email **jd.ramkumar@gmail.com** with:

- a description of the issue and its impact
- steps to reproduce it
- any suggested fix

You will receive an acknowledgement within 5 business days.

## Handling Secrets

- Keep API keys only in `.env`. It is git-ignored, and `.env.example` holds placeholders only.
- If you commit a key by accident, **rotate it immediately** in the OpenAI dashboard. Removing it from git history is not enough.
- The generated KB content is synthetic and fictional, so it contains no real customer or product data.
