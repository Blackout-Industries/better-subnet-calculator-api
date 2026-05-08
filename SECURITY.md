# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[security advisory form](https://github.com/Blackout-Industries/better-subnet-calculator-api/security/advisories/new).

Do not open a public issue for suspected vulnerabilities.

We aim to respond within 7 days and to ship a fix within 30 days for
confirmed high-severity issues.

## Supported versions

Only the latest minor on `main` is supported. Older container tags
remain published but receive no security backports.

## Supply chain

Container images are:

- Built reproducibly via the multi-stage `Dockerfile` in this repository.
- Published to `ghcr.io/blackout-industries/better-subnet-calculator-api`
  for `linux/amd64` and `linux/arm64`.
- Signed with [cosign](https://github.com/sigstore/cosign) using keyless
  GitHub OIDC. Verify with:

  ```sh
  cosign verify ghcr.io/blackout-industries/better-subnet-calculator-api:latest \
    --certificate-identity-regexp 'https://github.com/Blackout-Industries/better-subnet-calculator-api/.+' \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com
  ```

- Embedded with SLSA build provenance via `docker buildx`'s
  `provenance: true`. Inspect with `docker buildx imagetools inspect`.
- Scanned with Trivy on every push to `main`. The publish job fails on
  any critical or high severity finding with a fix available, so
  vulnerable images never reach `latest`.

GitHub Advanced Security features (CodeQL, Dependency Review, build
attestations published via the GitHub API, the Security tab SARIF feed,
OpenSSF Scorecard) are not enabled while this repository is private on
a free plan. They will start working automatically if the repository
becomes public or the organization upgrades.
