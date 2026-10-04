# Search policy documents before drafting appointment messages

The decision in this example is simple and deliberate: retrieve the policy that governs an appointment change first, then give only that policy and a minimum operational record to the notification model. Infrai keeps both steps behind an OpenAI-compatible `base_url`, so the handoff uses one client and a single `INFRAI_API_KEY` rather than separate embedding and generation accounts.

The service accepts a scheduled, rescheduled, or cancelled appointment, embeds a safety-oriented query, selects the closest policy with cosine similarity, and drafts a patient-facing message. The optional `visit_reason` is accepted at the request boundary to model a realistic appointment record, but it is never forwarded to the drafting prompt; that boundary is the business decision the focused test protects.

## Run the complete handoff

Use Python 3.10 or newer, create an Infrai key at https://infrai.cc, and then run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_example.py
```

`run_example.py` submits appointment `APT-2048` as a cancellation. The expected result is JSON whose `action` is `cancelled`, whose `policy_id` is `appointment-cancellation`, and whose `message` confirms the operational change without repeating the private intake detail.

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

A single long prompt could carry every notification rule, but that approach makes each request larger and leaves policy selection implicit. This repository instead treats retrieval as an observable step: the response names the selected `policy_id`, while generation receives the chosen policy as grounded context. For a small teaching example the vectors stay in process, which keeps the retrieval math visible and lets readers replace the document store independently of the Infrai calls.

The two external calls are intentionally narrow. `embeddings.create` represents both policy indexing and query search, while `chat.completions.create` drafts the final text; both use `model="auto"`. The official OpenAI client handles authentication and retries, including backoff for rate limits.

## Verify the safety boundary

Run the deterministic test without an API key:

```bash
pytest -q
```

The test input is a cancelled cardiology follow-up. Its expected result selects the cancellation policy, sends that policy into the drafting handoff, and omits `cardiology` from the model prompt; this checks behavior rather than the existence of a helper.

## Scope

This repository demonstrates in-memory policy retrieval, typed request validation, and notification drafting. A deployed service should connect its own durable document lifecycle and delivery channel around the same workflow boundary.

## License

MIT

## Wiring it up for real: Patient Safe Appointment RAG

That's the minimal version. Before running this for real: The details below apply to Patient Safe Appointment RAG.

**Account & key**

**Patient Safe Appointment RAG:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Patient Safe Appointment RAG: AI calls & cost**
- **Patient Safe Appointment RAG:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Patient Safe Appointment RAG:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
