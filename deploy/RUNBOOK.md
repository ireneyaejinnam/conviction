# Runbook

Day-to-day operations for the EC2 deployment. All `docker compose` commands
run from the repo directory on the instance (`cd ~/conviction`).

The instance's `.env` (mode 600) holds `OPENAI_API_KEY`, `EDGAR_USER_AGENT`,
`DOMAIN`, and `DATA_HOST_DIR=/srv/conviction-data`. The container runs as
uid 1000, so the data dir must be owned by it:

```bash
sudo mkdir -p /srv/conviction-data
sudo chown 1000:1000 /srv/conviction-data
```

## First-time seed

Run once, by hand, after the stack is up. It ingests the watchlist and caches
the risk diffs (calls EDGAR and OpenAI). If the index
already has chunks it prints "already seeded" and the stats instead.

```bash
docker compose up -d
docker compose exec app python -m scripts.seed
docker compose exec app python -m scripts.stats   # check counts
```

## Redeploy

```bash
git pull && docker compose up -d --build
```

Data in `/srv/conviction-data` and Caddy's certificates (the `caddy_data`
volume) survive rebuilds.

## Logs

On the instance:

```bash
docker compose logs -f app          # or: caddy
docker compose logs --tail 100 app
```

In CloudWatch: region **us-east-1**, log group **`conviction`**, streams
`app` and `caddy` (Console → CloudWatch → Logs → Log groups → `conviction`).
From a machine with the AWS CLI:

```bash
aws logs tail conviction --region us-east-1 --log-stream-names app --follow
```

## API keys

Placeholder: key management arrives in Phase 3 (`scripts/create_key.py`).
Not built yet.

## Stop and start the stack

```bash
docker compose stop      # stop containers, keep them
docker compose start     # start them again
docker compose down      # remove containers (data and certificates are kept)
docker compose up -d     # recreate
```

Never run `docker compose down -v`: it deletes the `caddy_data` volume, and
Caddy would have to request new certificates.

`restart: unless-stopped` brings the containers back after a reboot, unless
they were stopped with `docker compose stop` beforehand.

## Stop the EC2 instance when idle

Console: EC2 → Instances → select the instance → Instance state → **Stop**
(not Terminate). Start it the same way. Or with the AWS CLI:

```bash
aws ec2 stop-instances  --region us-east-1 --instance-ids <instance-id>
aws ec2 start-instances --region us-east-1 --instance-ids <instance-id>
```

A stopped instance stops compute billing, but the EBS volume and the Elastic
IP still bill. The Elastic IP keeps the address stable, so DNS needs no change
after a start. Docker starts on boot and the containers come back on their own;
check with `docker compose ps`.
