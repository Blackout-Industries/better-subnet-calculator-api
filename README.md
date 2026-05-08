# better-subnet-calculator-api

[![Build and publish](https://github.com/Blackout-Industries/better-subnet-calculator-api/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Blackout-Industries/better-subnet-calculator-api/actions/workflows/docker-publish.yml)
[![CodeQL](https://github.com/Blackout-Industries/better-subnet-calculator-api/actions/workflows/codeql.yml/badge.svg)](https://github.com/Blackout-Industries/better-subnet-calculator-api/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/Blackout-Industries/better-subnet-calculator-api/badge)](https://scorecard.dev/viewer/?uri=github.com/Blackout-Industries/better-subnet-calculator-api)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A small, stateless HTTP service that does IPv4 subnet allocation math and
exposes it as JSON. Built with FastAPI and Python's stdlib `ipaddress`.
Intended to be called from Terraform's `http` data source, OpenTofu,
Pulumi, or `curl` in a build pipeline &mdash; anywhere uniform
`cidrsubnet` math is not enough.

The service is request/response only. It holds no state; the caller owns
the ledger of allocated subnets.

If you want a UI, see the frontend project:
<https://github.com/Blackout-Industries/better-subnet-calculator>.

## Features

- `POST /v1/calculate` &mdash; subnet metadata for a single CIDR.
- `POST /v1/subdivide` &mdash; split a parent into N equal children or to a target prefix.
- `POST /v1/free` &mdash; maximal free CIDR blocks inside a parent given the allocated children.
- `POST /v1/allocate` &mdash; best-fit-decreasing VLSM allocator over named requests.
- `POST /v1/overlap` &mdash; pairwise overlap detection plus a summarized, deduplicated view.
- Auto-generated OpenAPI at `/openapi.json`, Swagger UI at `/docs`, Redoc at `/redoc`.

## Run with Docker

Pull the published image:

```sh
docker run -d -p 8000:8000 \
  ghcr.io/blackout-industries/better-subnet-calculator-api:latest
```

Open <http://localhost:8000/docs> for the auto-generated Swagger UI.

Or with compose, from a clone of this repository:

```sh
docker compose up -d --build app
```

Stop:

```sh
docker compose down
```

## Develop

The project requires no host toolchain. Python, `uv`, pytest, ruff, and
mypy all run inside containers.

```sh
make dev       # uvicorn with reload on http://localhost:8000
make test      # pytest with coverage in a one-shot container
make lint      # ruff check
make typecheck # mypy strict
make lockfile  # regenerate uv.lock without installing on the host
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow.

## Endpoints

All endpoints live under `/v1`. Versioning lets the API evolve without
breaking pipelines that already exist.

| Method | Path             | Purpose                                                      |
| ------ | ---------------- | ------------------------------------------------------------ |
| `POST` | `/v1/calculate`  | Return network, broadcast, netmask, host range for a CIDR    |
| `POST` | `/v1/subdivide`  | Split a parent into N equal children or to a target prefix   |
| `POST` | `/v1/free`       | Maximal free CIDR blocks in a parent given allocated children |
| `POST` | `/v1/allocate`   | Best-fit-decreasing VLSM allocator over named requests       |
| `POST` | `/v1/overlap`    | Overlap pairs and a deduplicated, summarized list            |

See `/docs` for the live schema, and [BRD.md](BRD.md) for the full
request/response shapes and rationale.

## Terraform usage

Call the API from Terraform's built-in `http` data source &mdash; no
custom provider required.

```hcl
data "http" "free" {
  url    = "http://subnet-api.internal:8000/v1/free"
  method = "POST"
  request_headers = {
    Content-Type = "application/json"
  }
  request_body = jsonencode({
    parent    = "10.10.0.0/16"
    allocated = ["10.10.0.0/24", "10.10.5.0/24"]
  })
}

locals {
  next_free = jsondecode(data.http.free.response_body).free[0].cidr
  app_subnet = cidrsubnet(local.next_free, 2, 0)
}
```

## Layout

```text
better-subnet-calculator-api/
  pyproject.toml
  uv.lock
  README.md
  CONTRIBUTING.md
  SECURITY.md
  LICENSE
  BRD.md
  Dockerfile
  docker-compose.yml
  Makefile
  GitVersion.yml
  .gitignore
  .dockerignore
  .github/
    workflows/docker-publish.yml
    workflows/codeql.yml
    workflows/dependency-review.yml
    workflows/scorecard.yml
    dependabot.yml
    CODEOWNERS
  src/subnet_api/
    __init__.py
    main.py        # FastAPI app, router wiring, lifespan
    routes.py      # /v1/* endpoints
    models.py      # Pydantic request/response schemas
    core.py        # pure functions over ipaddress.IPv4Network
    allocator.py   # best-fit-decreasing VLSM
    errors.py      # API error envelope
  tests/
    conftest.py
    test_core.py
    test_allocator.py
    test_routes.py
```

## License

MIT. See [LICENSE](LICENSE).
