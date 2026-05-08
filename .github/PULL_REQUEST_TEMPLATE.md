## Summary

One paragraph: what changed and why.

## Changes

- Bullet list of concrete changes.

## Test plan

- [ ] `make test` passes locally
- [ ] `make build` produces a runnable image
- [ ] Manual smoke test: `curl` the endpoints touched by this PR

## Notes for reviewers

Anything that needs explicit attention &mdash; tradeoffs you considered,
follow-ups deferred to another PR, things that look weird but are
deliberate.

## Versioning

If this PR is a new feature or breaking change, include the appropriate
GitVersion message in the squash commit:

- Patch (default): no marker needed
- Minor: append `+semver: minor` to the merge commit
- Major: append `+semver: major` to the merge commit
