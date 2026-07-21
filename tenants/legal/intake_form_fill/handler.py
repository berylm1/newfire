"""Conversational form-fill — requirement #4 from Mr. Patrick's product-
direction meeting. `handle_message` is called once per inbound message,
same calling shape as `shared/whatsapp_intake_handler.py`: OpenClaw invokes
it synchronously with the client's identity and latest message text, and
gets back a reply string to relay over WhatsApp. This is deliberately a
plain script, not a LangGraph graph with an interrupt/resume pause — that
pattern exists for pausing a run until a human decides something later
(see approval_service + resume_approvals.py); here, each turn already
arrives as its own separate invocation whenever the client replies, so
there's nothing to pause. The conversation's progress just needs to be
read, advanced by one step, and written back — a small JSON file keyed by
the client's phone number, same simplicity level as every other JSON-file
store in this tenant.

No human_approval_interrupt for the completed intake either: creating a
case record from a client's own stated facts and notifying the attorney it
happened is exactly the "low-stakes/routine" tier from the autonomy-
tiering direction — nothing here resembles legal judgment. The attorney
still reviews the new case; this just means they aren't the bottleneck for
a client answering four questions.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from activity_log_service.client import log_event
from case_service.client import create_case
from form_schemas import FORM_SCHEMAS

DEFAULT_MODEL = "glm4:9b"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"

TENANT_ID = "hawthorn-pell"
STATE_PATH = os.environ.get(
    "INTAKE_FORM_STATE_PATH", os.path.join(os.path.dirname(__file__), "conversation_state.json")
)

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%B %d %Y")
CLARIFYING_QUESTION = "Sorry, could you tell me a bit more about what kind of application this is for?"


def _load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _classify_case_type(message: str) -> str | None:
    from langchain_openai import ChatOpenAI

    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    llm = ChatOpenAI(api_key=api_key, base_url=base_url, model=model)

    case_types = ", ".join(FORM_SCHEMAS.keys())
    prompt = (
        "Classify what kind of immigration matter this message is about. Respond with ONLY one of "
        f'these exact strings, no other text: {case_types}, or "unclear" if you can\'t tell.\n\n'
        f"Message: {message}"
    )
    response = llm.invoke(prompt)
    case_type = str(response.content).strip().strip('"').strip("'")
    return case_type if case_type in FORM_SCHEMAS else None


def _parse_date_answer(text: str) -> str | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _set_nested(target: dict, field_path: str, value) -> None:
    parts = field_path.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def _field_kind(field_path: str) -> str:
    if field_path.startswith("key_dates."):
        return "date"
    if field_path == "contact.email":
        return "email"
    return "text"


def _next_question(case_type: str, step: int) -> str | None:
    schema = FORM_SCHEMAS[case_type]
    return schema[step][1] if step < len(schema) else None


def _complete_intake(phone: str, convo: dict) -> str:
    answers = convo["answers"]
    contact = answers.get("contact", {})
    contact["whatsapp"] = phone
    case = create_case(
        tenant_id=TENANT_ID,
        client_name=answers.get("client_name", "Unknown"),
        contact=contact,
        case_type=convo["case_type"],
        key_dates=answers.get("key_dates", {}),
    )
    log_event(
        event_type="intake_completed",
        urgency="low",
        summary=f"New {convo['case_type']} intake completed via conversational form-fill: {case['client_name']}.",
    )
    return (
        f"Thanks, {case['client_name']} — we've got everything we need to get started. "
        "Someone from the firm will follow up with you soon."
    )


def handle_message(phone: str, message: str) -> str:
    all_state = _load_state()
    convo = all_state.get(phone)

    if convo is None:
        case_type = _classify_case_type(message)
        if case_type is None:
            return CLARIFYING_QUESTION
        convo = {"case_type": case_type, "answers": {}, "step": 0}
        all_state[phone] = convo
        _save_state(all_state)
        return _next_question(case_type, 0)

    field_path, _question = FORM_SCHEMAS[convo["case_type"]][convo["step"]]
    kind = _field_kind(field_path)

    if kind == "date":
        parsed = _parse_date_answer(message)
        if parsed is None:
            return "I didn't quite catch that date — could you send it as YYYY-MM-DD?"
        value = parsed
    elif kind == "email":
        if "@" not in message:
            return "That doesn't look like a valid email — could you double check it?"
        value = message.strip()
    else:
        value = message.strip()

    _set_nested(convo["answers"], field_path, value)
    convo["step"] += 1
    next_question = _next_question(convo["case_type"], convo["step"])

    if next_question is not None:
        all_state[phone] = convo
        _save_state(all_state)
        return next_question

    reply = _complete_intake(phone, convo)
    del all_state[phone]
    _save_state(all_state)
    return reply


def main() -> None:
    if len(sys.argv) < 3:
        print("Sorry, I couldn't process that — could you try again?")
        return
    phone, message = sys.argv[1], sys.argv[2]
    print(handle_message(phone, message))


if __name__ == "__main__":
    main()
