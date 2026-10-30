# Agent workflow

- Discover repository-local skills in `.agents/skills/` and follow every skill that matches the request.
- Use `using-superpowers` as the entry point for software-development work.
- Use `thermonuclear` for an explicitly strict, adversarial maintainability review.
- Use `persist` for work that must survive a session or after three failed attempts at the same fix.
- Use `obc` for research in the Open Bibliographies for China Studies collection.
- Use `gh-project` when creating a GitHub repository.
- Direct user instructions override skill instructions.

## GitHub workflow

- Use `gh` for GitHub repository, Issue, pull request, Actions, and Projects operations; use `git` for local history, branches, fetch, and push.
- Before remote work, verify the target with `git remote -v` and authentication with `gh auth status`.
- Work in a dedicated branch or worktree. Never push changes directly to `main` or `master`.
- Agents may create or update Issues and open draft pull requests when that is part of the requested workflow.
- Link pull requests to their Issue with `Closes #N` when the pull request should close that Issue after merge.
- Do not merge pull requests, close Issues, delete branches or repositories, or change repository visibility without explicit user approval.
- Never print, copy into chat, or commit GitHub tokens, credentials, SSH private keys, or other secrets.
- Before pushing or opening a pull request, run the relevant tests and follow `verification-before-completion`.
