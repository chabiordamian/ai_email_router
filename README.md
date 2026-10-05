# AI Email Router

A small FastAPI service that uses a local Ollama model to route incoming messages
to a department mailbox. The model selects a department and calls the email tool;
Mailpit captures the resulting message.

## Run

Docker with Compose is the only requirement.

```bash
docker compose up -d
```

The first start downloads and warms up the `qwen3:1.7b` model, so it can take a
few minutes. The API starts after the model is ready.

- Swagger UI: http://127.0.0.1:8000/api/v1/docs
- Mailpit: http://127.0.0.1:8025
- Health check: http://127.0.0.1:8000/health

Send a message:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "jan.nowak@example.com",
    "message": "Chciałbym zgłosić urlop na jutro."
  }'
```

The response contains the selected department. Open Mailpit to inspect the
forwarded message and its `Reply-To` header.

Stop the services with:

```bash
docker compose down
```

## Design

- Department descriptions, examples and addresses live in
  [`config/departments.yaml`](config/departments.yaml). The file is validated at
  application startup.
- The tool schema is built from that configuration, so Ollama receives the current
  list of allowed department identifiers.
- The agent must call `send_email` exactly once. Missing, repeated or malformed tool
  calls are rejected without sending a message.
- The original request is kept outside the model's tool arguments. The model chooses
  a department; the application controls the message body and `Reply-To` value.
- Routing and email delivery are synchronous. This keeps the PoC small and makes a
  successful HTTP response mean that SMTP accepted the message.

Runtime settings can be overridden with the variables listed in `.env.example`.

## Checks

```bash
python -m pip install -r requirements-dev.txt
pytest
ruff check .
ruff format --check .
mypy app
docker compose config --quiet
```
