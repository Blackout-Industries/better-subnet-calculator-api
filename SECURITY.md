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

- Accompanied by a SLSA v1 build provenance attestation, viewable on
  the package page or via:

  ```sh
  gh attestation verify oci://ghcr.io/blackout-industries/better-subnet-calculator-api:latest \
    -R Blackout-Industries/better-subnet-calculator-api
  ```

- Embedded with a SBOM via Buildx `sbom: true`. Inspect with:

  ```sh
  docker buildx imagetools inspect \
    ghcr.io/blackout-industries/better-subnet-calculator-api:latest \
    --format '{{ json .SBOM }}'
  ```

- Scanned with Trivy on every push to `main`. Results are uploaded to
  the GitHub Security tab as SARIF; the publish run also fails on any
  HIGH or CRITICAL finding with a fix available, so vulnerable images
  never reach `latest`.

## Static analysis

- **CodeQL** runs on every push, every pull request, and weekly. Findings
  appear in the Security tab.
- **Dependency Review** gates pull requests, blocking any new direct or
  transitive dependency with a HIGH or CRITICAL advisory.
- **OpenSSF Scorecard** runs weekly, results in SARIF + the public
  Scorecard badge in `README.md`.
- **GitHub secret scanning** + **push protection** are enabled on the
  repository.

## Runtime hardening

GitHub Actions workflows use
[step-security/harden-runner](https://github.com/step-security/harden-runner)
in audit mode at the start of every job, monitoring runner egress
endpoints. Findings are visible at <https://app.stepsecurity.io>.
