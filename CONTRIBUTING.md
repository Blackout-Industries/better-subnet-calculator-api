# Contributing

Thanks for considering a contribution. The project is small and the
workflow is intentionally minimal &mdash; no host toolchain required,
only Docker.

## Quick start

```sh
gh repo clone Blackout-Industries/better-subnet-calculator-api
cd better-subnet-calculator-api
make dev    # http://localhost:8000 with reload
```

## Local commands

| Command          | What it does                                              |
| ---------------- | --------------------------------------------------------- |
| `make dev`       | uvicorn with reload (Docker) at <http://localhost:8000>   |
| `make test`      | Run pytest with coverage in a one-shot container          |
| `make lint`      | ruff check                                                |
| `make typecheck` | mypy in strict mode                                       |
| `make build`     | Build the production image                                |
| `make up`        | Run the production image at <http://localhost:8000>       |
| `make down`      | Stop the production container                             |
| `make lockfile`  | Regenerate `uv.lock` without host Python                  |
| `make clean`     | Remove the local container and its images                 |

Do not run `pip`, `uv`, or `python` directly on the host. Everything
builds and tests inside Docker so the project stays reproducible.

## Code style

- ruff and mypy (strict) must pass. No `Any`, no unused imports.
- Pure functions over `ipaddress.IPv4Network` live in
  [src/subnet_api/core.py](src/subnet_api/core.py) and
  [src/subnet_api/allocator.py](src/subnet_api/allocator.py). These
  modules **must not** import FastAPI or Pydantic. Keep them pure so
  they remain trivially testable and reusable from a CLI or a Lambda
  handler.
- Pydantic v2 models in [src/subnet_api/models.py](src/subnet_api/models.py)
  use strict mode for inputs. Reject coercions; fail loud on malformed
  payloads.
- Routes in [src/subnet_api/routes.py](src/subnet_api/routes.py) stay
  thin: parse input, call core/allocator, shape the response. No
  business logic in the route layer.
- Default to no comments. Only add a comment when the *why* is
  non-obvious (a spec reference, a workaround, a hidden invariant).
- No trailing whitespace, four-space indent, double-quoted strings.

## Tests

All math, allocation, and route handlers should have a pytest case
under [tests/](tests/). Run:

```sh
make test
```

This runs `pytest` with coverage. Pull requests must not regress
coverage. CI runs the same command on every push and pull request, and
PRs must be green before merging.

## Branching and pull requests

Trunk-based development. `main` is always releasable.

1. Branch from `main` with the prefix `feature/`:

   ```sh
   git switch -c feature/short-description main
   ```

2. Make focused changes &mdash; one fix or feature per PR.
3. Run `make test`, `make lint`, and `make typecheck` locally.
4. Open a PR from `feature/*` into `main`. Describe what changed and why.
5. The pipeline runs the `Test and validate build` status check on every
   PR (pytest + ruff + mypy + amd64 build, no push). Branch protection
   requires it to be green before merge. The publish job only runs after
   a merge to `main`.

Direct pushes to `main` are blocked by branch protection. All changes
flow through PRs.

## Versioning and releases

Versions are derived automatically from git history by
[GitVersion](https://gitversion.net/). Configuration lives in
[GitVersion.yml](GitVersion.yml).

- Each merge to `main` increments the patch version by default.
- To bump minor or major, include `+semver: minor` or `+semver: major`
  in the commit message.
- After publishing, the workflow tags the commit on GitHub with `vX.Y.Z`.

The published image at
`ghcr.io/blackout-industries/better-subnet-calculator-api` is tagged
with:

- `X.Y.Z` &mdash; the exact version
- `X.Y` &mdash; the latest patch in this minor line
- `X` &mdash; the latest minor in this major line
- `latest` &mdash; the most recent main build

## Reporting issues

Open an issue at
<https://github.com/Blackout-Industries/better-subnet-calculator-api/issues>.
Include:

- The endpoint and request body that reproduces it.
- The response you got and the response you expected.
- Whether `make test` passes locally.
