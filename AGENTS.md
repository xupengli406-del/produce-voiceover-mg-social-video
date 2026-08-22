# Repository instructions

These instructions apply to the whole repository.

- Preserve this Skill as a portable package. Do not add usernames, drive letters, absolute local paths, fixed OS-only dependencies, browser cookies, API keys, voice credentials, user media, rendered videos, or task-specific output folders.
- The repository owner has explicitly requested GitHub synchronization after every successful Skill update. After making an in-scope change, run `python scripts/repo_check.py`, then run `python scripts/sync_github.py --message "<concise change summary>"`.
- A successful local edit is not a successful sync. Confirm that the sync script reports matching local and remote commit SHAs.
- Do not push when validation fails. Never force-push, rewrite history, change repository visibility, publish releases, or upload user source media without a separate explicit request.
- Keep runtime secrets in environment variables. Examples and tests must use placeholders or synthetic data.
