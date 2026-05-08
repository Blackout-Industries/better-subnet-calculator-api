---
name: Bug report
about: Something doesn't work as documented
title: ''
labels: [bug]
assignees: []
---

## What happened

A short, factual description of the bug.

## What you expected

What you thought the API would do, and where that expectation came from
(BRD section, OpenAPI schema, or just intuition).

## How to reproduce

The smallest possible request that triggers the bug:

```sh
curl -sX POST http://localhost:8000/v1/<endpoint> \
  -H 'content-type: application/json' \
  -d '{ ... }'
```

If it only reproduces in a multi-step flow, list the steps in order.

## Environment

- Image tag: `ghcr.io/blackout-industries/better-subnet-calculator-api:<tag>`
- How you ran it: `docker run` / `docker compose` / Kubernetes / something else
- OS / arch:

## Logs

Attach the response body and any relevant container logs.
