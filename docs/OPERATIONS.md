# Operations

## Public/private split

This repo is the generic, shareable deployment baseline — no domain,
provider accounts, or personal state. Keep that in a separate private "ops"
repo instead, structured as:

```text
your-ops-repo/
  stack/                 # this repo, as a git submodule
  CLAUDE.md / AGENTS.md   # entry point for whichever repo an agent opens
  docs/PROJECT_STATE.md   # what's actually deployed, where, as of when
  docs/VALIDATION.md      # what has actually been tested on your VPS
  scripts/github-bootstrap.py (or equivalent)  # if you automate repo creation
```

Add this repo as a submodule from the ops repo:

```bash
git submodule add <this-repo-url> stack
```

Run `scripts/deploy.sh` etc. from inside `stack/`, with `.env` placed at
`stack/.env` (never committed, in either repo).

## Deploying behind an existing reverse proxy on the host

Two modes, chosen by whether `standalone` is in `COMPOSE_PROFILES` (see
`.env.example`):

- **Standalone** (`COMPOSE_PROFILES=standalone`, the default): the bundled
  Caddy container owns host ports 80/443 and handles TLS itself. Use this
  on a host with nothing else listening on those ports.
- **Shared host** (`standalone` omitted from `COMPOSE_PROFILES`): the
  bundled Caddy never starts. `librechat` is always published to
  `127.0.0.1:3080` regardless of this setting — point the host's existing
  reverse proxy at that address instead. For an existing Caddy install,
  add a new site-block (don't edit the existing one) so it's the import
  pattern that survives the existing config's own changes:

  ```caddyfile
  # /etc/caddy/sites-enabled/ai.example.com (adjust to match how the
  # existing Caddyfile imports this directory)
  ai.example.com {
      reverse_proxy 127.0.0.1:3080 {
          flush_interval -1   # LibreChat streams SSE; don't buffer it
      }
  }
  ```

  Then reload the existing Caddy (`systemctl reload caddy` or
  `caddy reload --config /etc/caddy/Caddyfile`), not restart — a reload
  picks up the new site-block without dropping connections to sites
  already being served.

## Backups

`scripts/backup.py` is a **cold** backup: it stops `librechat` and `rag_api`
(not the databases) long enough to take a consistent `mongodump` and
`pg_dump`, tars the upload volume, then pushes everything to the restic
repository in `RESTIC_REPOSITORY`/`RESTIC_PASSWORD`. This implies a brief
maintenance window — schedule it accordingly.

```bash
python3 scripts/backup.py
```

Restic deduplicates and encrypts; keep `RESTIC_PASSWORD` somewhere other
than this server (a password manager, not another file on the same VPS).

## Restore drill

Before trusting backups in production, actually restore one on a disposable
host:

```bash
restic -r "$RESTIC_REPOSITORY" snapshots
restic -r "$RESTIC_REPOSITORY" restore latest --target /tmp/restore-test
# then: mongorestore the archive, pg_restore the dump, verify the app starts
# against the restored data before calling the drill complete.
```

## Monitoring

Nothing in this baseline pages anyone. `docker compose ps` and the health
checks in `docker-compose.yml` tell you current state only. For anything
beyond that:

- `docker compose logs --tail 200 <service>` for recent output.
- Consider forwarding container logs or `docker compose ps` output to an
  external uptime check (e.g. a simple HTTPS probe of `/health` from
  outside the VPS) if you need alerting.
- `unless-stopped` restarts a crashed container; it does not detect a
  hung-but-running process. A healthcheck failure alone does not trigger a
  restart in base Docker — add an external watcher if you need that.

## Upgrades

1. Review each image's release notes/security advisories (see
   [SOURCES.md](SOURCES.md)).
2. Test on a staging copy of this stack first.
3. `python3 scripts/pin-images.py` to resolve and lock the new digests.
4. `./scripts/deploy.sh` on staging, run the acceptance checks in
   README.md section 10.
5. Take a backup, then repeat on production.

Never point an unattended image-updater (Watchtower, etc.) at this stack —
MongoDB and pgvector are stateful and a bad auto-update can corrupt data
with no one watching.

## Rollback

`image-lock.json` and `docker-compose.override.yml` from the previous
deploy are your rollback target. Keep the prior versions (e.g. a git tag or
copied files) before resolving new digests, so you can restore the old
override file and `docker compose up -d` to go back. Restoring from a
backup is the fallback if a rollback alone isn't enough (e.g. a migration
already ran against the data).

## Reindexing after an embedding model change

Changing `EMBEDDINGS_PROVIDER`/`EMBEDDINGS_MODEL` does not retroactively
re-embed existing documents. Plan a deliberate reindex (delete and
re-upload, or a scripted pass through the RAG API) rather than mixing
embedding spaces in the same pgvector table.
