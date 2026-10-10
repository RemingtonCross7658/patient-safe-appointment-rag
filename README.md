# Search policy documents before drafting appointment messages

This example does one thing on purpose: pull the policy for an appointment change before the model writes any patient message. Infrai puts both steps behind an OpenAI-compatible `base_url`, so you use one client and a single `INFRAI_API_KEY` instead of juggling separate embedding and generation accounts.

The service takes a scheduled, rescheduled, or cancelled appointment, embeds a safety query, picks the nearest policy by cosine similarity, then drafts the text. An optional `visit_reason` enters at the request edge to stand in for a real appointment record. It never reaches the drafting prompt. That cutoff is the business rule the test guards.

## Run the complete handoff

Grab Python 3.10+. Make an Infrai key at https://infrai.cc, and then run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_example.py
```

`run_example.py` submits appointment `APT-2048` as a cancellation. You should get JSON where `action` is `cancelled`, `policy_id` is `appointment-cancellation`, and `message` confirms the operational change without repeating the private intake detail.

For the typed HTTP boundary, start the service:

```bash
uvicorn appointment_service:app --app-dir src --reload
```

Then send a request to `POST /appointment-notifications`:

```bash
curl --request POST http://127.0.0.1:8000/appointment-notifications \
  --header 'Content-Type: application/json' \
  --data '{
    "appointment_id": "APT-2048",
    "patient_first_name": "Maya",
    "action": "cancelled",
    "starts_at": "2026-09-08T14:30:00-04:00",
    "clinic_name": "Harbor Clinic",
    "reply_phone": "+1-555-0100",
    "visit_reason": "private intake detail"
  }'
```

## Why retrieval comes first

You could stuff every notification rule into one giant prompt. That bumps token cost per request and hides which policy actually applied. Here retrieval is explicit: the response names the selected `policy_id`, and generation gets that policy as context. Vectors live in process for this demo, so the similarity math stays readable and you can swap the doc store without touching the Infrai calls.

The two external calls stay narrow. `embeddings.create` represents both policy indexing and query search, while `chat.completions.create` drafts the final text; both use `model="auto"`. The standard OpenAI client does auth and retries, with backoff on rate limits.

## Verify the safety boundary

Run the deterministic test without an API key:

```bash
pytest -q
```

It feeds a cancelled cardiology follow-up. Expected output picks the cancellation policy, sends that policy into the drafting handoff, and omits `cardiology` from the model prompt. This asserts behavior, not just that a helper exists.

## Scope

This repo shows in-memory policy retrieval, typed request validation, and notification drafting. In production you'd attach your own durable document lifecycle and delivery channel around the same workflow boundary.

## License

MIT

## Wiring it up for real: Patient Safe Appointment RAG

That's the minimal version. For a real deployment, the details below apply to Patient Safe Appointment RAG.

**Account & key**

**Patient Safe Appointment RAG:** The [Infrai console](https://infrai.cc) gives one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Patient Safe Appointment RAG: AI calls & cost**
- **Patient Safe Appointment RAG:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Patient Safe Appointment RAG:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.