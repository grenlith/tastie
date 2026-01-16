# tastie

a personal bookmark repository with optional sharing, inspired by early [del.icio.us](https://en.wikipedia.org/wiki/Delicious_(website)).

you can visit the reference implementation at [tast.ie](https://tast.ie).

## features

- **multi-user support** open or invite-based registration
- **bookmark visibility** - supports private, logged-in only, and public bookmark visibility
- **tagging** - organize bookmarks with space-separated tags
- **full-text search** - easy to find what you're looking for

## development

requires [uv](https://docs.astral.sh/uv/), and [just](https://github.com/casey/just).

see the `justfile` for up-to-date commands

## configuration

via environment variables or `.env` file.

see `.env.example` for configuration settings

## invite generation

if you turn on invite-only registration, each user will need an invite to sign up. invites can be generated with:

```bash
uv run cli.py -c tastie create-invite
```

if our application is running in a container, `-c tastie` here is telling the script which container the application lives in.

## deployment

a dockerfile, docker-compose.yml, and caddyfile are provided for containerized deployment. the compose file includes caddy as a reverse proxy with automatic https.

```bash
mv .env.example .env # you will want to edit this
mv Dockerfile.example Dockerfile
mv docker-compose.yml.example docker-compose.yml
mv Caddyfile.example Caddyfile
```

```bash
docker compose up -d
```

for production, ensure `TASTIE_SECRET_KEY` in the environment variable configuration is set to a secure random value:

```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
