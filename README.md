# smartbaseai

This project provides a minimal API and test suite used for evaluation.

## Environment setup

Before running the API create a `.env` file in the project root. You can start by copying the provided example:

```bash
cp .env.example .env
```

Edit the file and set `SECRET_KEY` to a secure value that will be used for signing JWT tokens. Any variables defined in `.env` are read by the backend on startup.

## Backend setup

Install Python dependencies and run the API server:

```bash
pip install -r requirements.txt
python scripts/run_server.py --reload
```

The server listens on port `8000` by default.

## Frontend setup

Two Next.js applications are provided. Each must be started separately.

### Chat interface

```bash
cd ui/web
npm install
npm run dev
```

### Admin panel

```bash
cd ui/admin_panel
npm install
npm run dev
```

## Utility scripts

### Create a tenant

```bash
python scripts/setup_tenant.py tenant1 --name "Tenant 1" --db-type postgres \
    --db-config '{"host": "localhost", "user": "app"}'
    --model-type ollama --model-name llama3
```

### Build embeddings

```bash
python scripts/build_embeddings.py --source docs/ --output embeddings.json \
    --embedder local
```

## Example API usage

### Authenticate

```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "ChangeThis123!"}' \
     http://localhost:8000/auth/login
```

Use the `access_token` returned above when calling other endpoints.

### Send a chat message

```bash
curl -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -X POST http://localhost:8000/chat/message \
     -d '{"session_id": "s1", "tenant_id": "t1", "message": "hello"}'
```

### Tenant operations

```bash
# list tenants
curl -H "Authorization: Bearer <token>" http://localhost:8000/admin/tenants

# get configuration for a tenant
curl -H "Authorization: Bearer <token>" http://localhost:8000/admin/tenants/t1
```

## Testing

Install the Python dependencies before running the test suite:

```bash
pip install -r requirements.txt
```

Run all unit tests with:

```bash
pytest -q
```

## Extending the response generator

The `ResponseGenerator` combines conversation history, structured data from a
tenant database and unstructured context from the vector store. Additional data
sources can be integrated by implementing new helper methods that fetch and
format their results before calling the language model. Each source should be
encapsulated in its own method and added to the prompt in
`chatbot/response_generator.py`.

