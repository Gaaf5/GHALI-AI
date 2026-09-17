# GHALI AI — Cloud Deployment

## Target architecture

The laptop is a development machine only. Production runs the web application and AI provider on an always-on server.

Production uses `GHALI_LLM_PROVIDER=openai`; Ollama remains available only for local development.

## Required server secrets

Set these in the cloud provider secret/environment manager, never in Git:

- `OPENAI_API_KEY`
- `OPENAI_MODEL=gpt-5.6-luna`
- `GHALI_LLM_PROVIDER=openai`
- `GHALI_ADMIN_USER`
- `GHALI_ADMIN_PASSWORD`

The database and knowledge base should live on persistent storage mounted at `/app/data`.

## Docker

Build:

```bash
docker build -t ghali-ai .
```

Run:

```bash
docker run -d --name ghali-ai --restart unless-stopped \
  -p 8765:8765 \
  -v ghali_data:/app/data \
  -e GHALI_LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=YOUR_SERVER_SECRET \
  -e OPENAI_MODEL=gpt-5.6-luna \
  ghali-ai
```

## Important

Do not expose the SQLite database, `.env`, Git repository, or admin credentials through the web server.

For the final production setup, place TLS/reverse-proxy protection in front of GHALI and keep the application port private to the server/network.
