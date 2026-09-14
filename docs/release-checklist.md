# v0.1.1 personal-MVP release checklist

This checklist prepares a local Git release only. Do not submit the project to
a public Plugin Directory or publish it as a hosted service.

## Code and package

- [ ] `git status --short` contains no unintended file, credential, fixture, or
      local tunnel configuration.
- [ ] `uv lock --check` passes.
- [ ] `uv sync --locked --all-groups` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `uv run mypy src tests` passes.
- [ ] `uv run pytest` passes with no network or live-account dependency.
- [ ] `uv build` produces the expected sdist and wheel.
- [ ] Package version is `0.1.1` in both `pyproject.toml` and `uv.lock`.

## Security and privacy

- [ ] No password, token, cookie, address, raw authenticated response, runtime
      API key, tunnel ID, or Chrome profile is tracked by Git.
- [ ] `uv run mercadona logout` removes the local Mercadona session when the
      release validation is complete.
- [ ] The tunnel runtime key remains in macOS Keychain and out of shell profiles
      and repository files.
- [ ] [SECURITY.md](../SECURITY.md), [THREAT_MODEL.md](../THREAT_MODEL.md), and
      [known limitations](known-limitations.md) match the shipped behavior.

## Optional personal acceptance

- [ ] Visible Chrome login succeeds without the CLI receiving a password.
- [ ] Bounded product search succeeds for a known warehouse. It uses a
      short-lived isolated headed Chrome window; it does not traverse catalog
      categories as a fallback.
- [ ] Catalog read and cart read succeed for the tester's own account.
- [ ] A controlled cart write uses an inexpensive selected product, an absolute
      final quantity, explicit confirmation, a new operation ID, and restores
      the original quantity.
- [ ] ChatGPT Web search and cart-read smoke tests pass through the private
      tunnel while the local companion remains running.

## Release decision

- [ ] Changelog entry is reviewed.
- [ ] Known limitations are accepted for a personal MVP.
- [ ] No checkout, order, payment, or delivery-slot behavior was added.
- [ ] Create a local Git tag only after all applicable checks pass.
