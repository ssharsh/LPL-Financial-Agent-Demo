# LPL-Financial-Agent-Demo
# Team 20
# Authors: Harsh Sheth, Ben Witham, Isaiah Hames, Hayden Fallon

## Running the demo

Two terminals: the Python backend on 127.0.0.1:8000 and the Vite frontend on localhost:5173.
Vite proxies `/api` to the backend, so no CORS setup is needed.

Prerequisites (once):

```sh
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env   # set DATA_BACKEND=memory, AUDIT_BACKEND=memory, AWS_REGION, BEDROCK_MODEL_ID
cd ..
npm install
```

Chat calls Amazon Bedrock, so you need AWS credentials with access to `BEDROCK_MODEL_ID` in the default
credential chain (`~/.aws`, `AWS_PROFILE`, or env vars). Check with `aws sts get-caller-identity`.
Without them the portfolio panel still works and chat shows the AWS error.

```sh
npm run backend   # terminal 1
npm run dev       # terminal 2, then open http://localhost:5173
```

Pick a client with the Client account dropdown (populated from `/api/clients`); it resets the conversation and keeps `?client=N` in the URL in sync, so `?client=N` also opens that client directly (default 1, or `DEMO_CLIENT_ID`).

Endpoints (`backend/src/advisor/server.py`):

- `GET /api/health`: status and whether chat is configured
- `POST /api/chat` `{message, conversation_id, client_id?}`: the response envelope, unchanged
- `GET /api/portfolio?client_id=N`: totals, accounts, holdings, performance, and two chart specs for the side panel
- `GET /api/clients`: `{clients: [{client_id, name}], default_client_id}` for the demo client picker

Errors are always `{"error": "..."}`. Conversation history lives in server memory (lost on restart).

### How graphs work

The backend fills the envelope's `chart` field in code from the turn's tool results (`advisor/charts.py`):
performance → line, holdings → pie, transactions → bar, accounts → bar. The model never produces chart data.
The frontend draws any spec `{type, x, y, series, rows}` with one component,
`src/components/chat/ChartRenderer.jsx` (line, stacked_area, bar, pie, table). Only line, bar, and pie are
emitted today; stacked_area and table are ready for a later explore tool. Unknown or malformed specs render nothing.

### Security note

Demo only: the API is unauthenticated and uses dev-mode identity (any caller can pick a client ID).
It binds to 127.0.0.1. Do not expose it on a network.

## Tests

```sh
npm test
cd backend && .venv/bin/pytest
```
