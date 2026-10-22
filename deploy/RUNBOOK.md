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

If the Caddyfile changes, run `docker compose up -d --force-recreate caddy`
(a `git pull` does not reload it).

## Logs

On the instance:

```bash
docker compose logs -f app          # or: api, caddy
docker compose logs --tail 100 app
```

In CloudWatch: region **us-east-2**, log group **`conviction`**, streams
`app`, `api` and `caddy` (Console → CloudWatch → Logs → Log groups →
`conviction`). The `api` stream has one JSON line per request.
From a machine with the AWS CLI:

```bash
aws logs tail conviction --region us-east-2 --log-stream-names api --follow
```

## API keys

Keys live in `app.db` in the data dir. The plaintext is printed once at
creation; only its SHA-256 hash is stored, so a lost key can't be recovered,
only revoked and replaced.

```bash
# Create (defaults: --rph 30, --daily-tokens 200000)
docker compose exec api python -m scripts.create_key --name alice

# Revoke
docker compose exec api python -m scripts.revoke_key --name alice
```

Names are unique and stay taken after a revoke, so a replacement key needs a
new name.

### Demo key

The public page uses `DEMO_API_KEY` when a visitor doesn't enter a key.

1. Create it, passing `--rph` and `--daily-tokens` lower than the defaults
   since anyone on the page shares it:
   `docker compose exec api python -m scripts.create_key --name demo --rph <n> --daily-tokens <n>`
2. Put the printed key in `.env` as `DEMO_API_KEY=cv_...`.
3. Recreate the app so it reads the new value:
   `docker compose up -d --force-recreate app`

To rotate it, revoke `demo`, create a key under a new name, and repeat
steps 2 and 3.

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
aws ec2 stop-instances  --region us-east-2 --instance-ids <instance-id>
aws ec2 start-instances --region us-east-2 --instance-ids <instance-id>
```

A stopped instance stops compute billing, but the EBS volume and the Elastic
IP still bill. The Elastic IP keeps the address stable, so DNS needs no change
after a start. Docker starts on boot and the containers come back on their own;
check with `docker compose ps`.
