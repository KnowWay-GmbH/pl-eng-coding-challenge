# Platform Engineering Challenge

A small "agent runs" API behind an nginx reverse proxy, with Postgres as the datastore, all running locally in Docker via Terraform (or OpenTofu).

## Requirements

- Docker (Docker Desktop, or Docker Engine in WSL2)
- Terraform >= 1.5 or OpenTofu >= 1.6
- Python 3.9+ (only for the load generator, no extra packages needed)

## Run

```sh
cd terraform
terraform init   # or: tofu init
terraform apply  # or: tofu apply
```

The proxy listens on http://localhost:8080 and Postgres on 5432, so both ports must be free.

```sh
curl localhost:8080/healthz
curl -X POST localhost:8080/runs -H 'Content-Type: application/json' -d '{"agent": "coder"}'
curl localhost:8080/runs
```

## Load generator

```sh
python3 loadgen/loadgen.py --requests 200 --concurrency 4
```

## Logs

```sh
docker logs proxy
docker logs api-1
```

## Tear down

```sh
cd terraform
terraform destroy  # or: tofu destroy
```

If Docker is not reachable at the default socket, set `DOCKER_HOST` (for example `unix://$HOME/.docker/run/docker.sock`).
