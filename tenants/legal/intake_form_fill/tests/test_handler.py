import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import handler
import translation


def _reset_state(tmp_path, monkeypatch):
    monkeypatch.setattr(handler, "STATE_PATH", str(tmp_path / "conversation_state.json"))


def _stub_classifier(monkeypatch, case_type, language="en"):
    monkeypatch.setattr(handler, "detect_case_type_and_language", lambda message, known_case_types: (case_type, language))


def _stub_case_creation(monkeypatch):
    created = {}
    logged = []
    monkeypatch.setattr(handler, "create_case", lambda **kwargs: created.update(kwargs) or {**kwargs, "id": "case-1"})
    monkeypatch.setattr(handler, "log_event", lambda **kwargs: logged.append(kwargs))
    return created, logged


def _no_translation(monkeypatch):
    # Runs the *real* translate_to_language/translate_to_english (so their
    # own "return text unchanged for English" fast path is what's under
    # test), but fails loudly if either ever reaches an actual LLM call --
    # confirming an English conversation makes zero LLM/translation calls,
    # same behavior as before Phase 7 existed.
    def fail(*args, **kwargs):
        raise AssertionError("translation should not call the LLM for an English conversation")

    monkeypatch.setattr(translation, "_llm", fail)


# --- English-language behavior (regression coverage for Phase 4) ---


def test_first_message_with_clear_case_type_asks_first_question(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    _no_translation(monkeypatch)

    reply = handler.handle_message("+15551234567", "I want to change from a visitor visa to a student visa")

    assert reply == "What's your full legal name?"


def test_first_message_unclear_asks_clarifying_question_without_saving_state(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, None)
    _no_translation(monkeypatch)

    reply = handler.handle_message("+15551234567", "hi")

    assert reply == handler.CLARIFYING_QUESTION
    assert handler._load_state() == {}


def test_second_message_advances_to_next_question(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    _no_translation(monkeypatch)
    handler.handle_message("+15551234567", "change of status question")

    reply = handler.handle_message("+15551234567", "Priya Raman")

    assert reply == "What's the best email address to reach you at?"
    state = handler._load_state()["+15551234567"]
    assert state["answers"]["client_name"] == "Priya Raman"
    assert state["step"] == 1


def test_invalid_email_is_reprompted_without_advancing_step(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    _no_translation(monkeypatch)
    handler.handle_message("+15551234567", "change of status question")
    handler.handle_message("+15551234567", "Priya Raman")

    reply = handler.handle_message("+15551234567", "not-an-email")

    assert "valid email" in reply
    state = handler._load_state()["+15551234567"]
    assert state["step"] == 1
    assert "email" not in state["answers"].get("contact", {})


def test_invalid_date_is_reprompted_without_advancing_step(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    monkeypatch.setattr(handler, "translate_to_english", lambda text, language: text)
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: text)
    handler.handle_message("+15551234567", "change of status question")
    handler.handle_message("+15551234567", "Priya Raman")
    handler.handle_message("+15551234567", "priya@example.com")

    reply = handler.handle_message("+15551234567", "sometime last spring")

    assert "YYYY-MM-DD" in reply
    state = handler._load_state()["+15551234567"]
    assert state["step"] == 2
    assert "us_entry_date" not in state["answers"].get("key_dates", {})


def test_date_accepts_several_common_formats(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    monkeypatch.setattr(handler, "translate_to_english", lambda text, language: text)
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: text)
    handler.handle_message("+15551234567", "change of status question")
    handler.handle_message("+15551234567", "Priya Raman")
    handler.handle_message("+15551234567", "priya@example.com")

    handler.handle_message("+15551234567", "03/15/2024")

    state = handler._load_state()["+15551234567"]
    assert state["answers"]["key_dates"]["us_entry_date"] == "2024-03-15"


def test_completed_conversation_creates_case_and_clears_state(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    monkeypatch.setattr(handler, "translate_to_english", lambda text, language: text)
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: text)
    created, logged = _stub_case_creation(monkeypatch)

    handler.handle_message("+15551234567", "change of status question")
    handler.handle_message("+15551234567", "Priya Raman")
    handler.handle_message("+15551234567", "priya@example.com")
    handler.handle_message("+15551234567", "2024-03-15")
    reply = handler.handle_message("+15551234567", "2026-08-01")

    assert "Priya Raman" in reply
    assert created["tenant_id"] == "hawthorn-pell"
    assert created["client_name"] == "Priya Raman"
    assert created["case_type"] == "change_of_status"
    assert created["contact"] == {
        "email": "priya@example.com",
        "whatsapp": "+15551234567",
        "preferred_language": "en",
    }
    assert created["key_dates"] == {"us_entry_date": "2024-03-15", "visa_expiration": "2026-08-01"}
    assert logged[0]["event_type"] == "intake_completed"
    assert "Priya Raman" in logged[0]["summary"]
    assert handler._load_state() == {}


def test_different_phone_numbers_have_independent_conversations(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "asylum")
    _no_translation(monkeypatch)

    handler.handle_message("+15551111111", "asylum question")
    handler.handle_message("+15552222222", "asylum question")
    handler.handle_message("+15551111111", "First Client")

    state = handler._load_state()
    assert state["+15551111111"]["answers"]["client_name"] == "First Client"
    assert state["+15552222222"]["answers"] == {}
    assert state["+15552222222"]["step"] == 0


def test_set_nested_creates_intermediate_dicts():
    target = {}
    handler._set_nested(target, "contact.email", "a@b.com")
    assert target == {"contact": {"email": "a@b.com"}}


def test_field_kind_classification():
    assert handler._field_kind("key_dates.us_entry_date") == "date"
    assert handler._field_kind("contact.email") == "email"
    assert handler._field_kind("client_name") == "text"


# --- Multi-language behavior (Phase 7) ---


def test_first_message_in_spanish_stores_language_and_translates_first_question(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status", language="es")
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: f"[{language}] {text}")

    reply = handler.handle_message("+15559990000", "Quiero cambiar mi estatus de visitante a estudiante")

    assert reply == "[es] What's your full legal name?"
    state = handler._load_state()["+15559990000"]
    assert state["language"] == "es"


def test_unclear_case_type_in_non_english_still_translates_clarifying_question(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, None, language="fr")
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: f"[{language}] {text}")

    reply = handler.handle_message("+15559990000", "Bonjour")

    assert reply == f"[fr] {handler.CLARIFYING_QUESTION}"
    assert handler._load_state() == {}


def test_name_and_email_answers_are_never_translated_to_english(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status", language="es")
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: text)

    def fail_if_translating_answer(text, language):
        raise AssertionError("name/email answers must not be translated")

    monkeypatch.setattr(handler, "translate_to_english", fail_if_translating_answer)

    handler.handle_message("+15559990000", "cambio de estatus")
    handler.handle_message("+15559990000", "Sofía Ramírez")
    handler.handle_message("+15559990000", "sofia@example.com")

    state = handler._load_state()["+15559990000"]
    assert state["answers"]["client_name"] == "Sofía Ramírez"
    assert state["answers"]["contact"]["email"] == "sofia@example.com"


def test_date_answer_is_translated_to_english_before_parsing(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status", language="es")
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: text)
    seen = {}

    def fake_translate_to_english(text, language):
        seen["text"] = text
        seen["language"] = language
        return "2024-03-15"  # pretend the LLM normalized "15 de marzo de 2024"

    monkeypatch.setattr(handler, "translate_to_english", fake_translate_to_english)

    handler.handle_message("+15559990000", "cambio de estatus")
    handler.handle_message("+15559990000", "Sofía Ramírez")
    handler.handle_message("+15559990000", "sofia@example.com")
    handler.handle_message("+15559990000", "15 de marzo de 2024")

    assert seen == {"text": "15 de marzo de 2024", "language": "es"}
    state = handler._load_state()["+15559990000"]
    assert state["answers"]["key_dates"]["us_entry_date"] == "2024-03-15"


def test_unparseable_translated_date_reprompts_in_client_language(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status", language="es")
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: f"[{language}] {text}")
    monkeypatch.setattr(handler, "translate_to_english", lambda text, language: "not a real date")

    handler.handle_message("+15559990000", "cambio de estatus")
    handler.handle_message("+15559990000", "Sofía Ramírez")
    handler.handle_message("+15559990000", "sofia@example.com")

    reply = handler.handle_message("+15559990000", "quien sabe")

    assert reply == f"[es] {handler.DATE_REPROMPT}"


def test_confirmation_message_prepends_name_untranslated(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status", language="es")
    monkeypatch.setattr(handler, "translate_to_english", lambda text, language: text)
    seen_confirmation_calls = []

    def fake_translate_to_language(text, language):
        seen_confirmation_calls.append(text)
        return f"[{language}] {text}"

    monkeypatch.setattr(handler, "translate_to_language", fake_translate_to_language)
    _stub_case_creation(monkeypatch)

    handler.handle_message("+15559990000", "cambio de estatus")
    handler.handle_message("+15559990000", "Sofía Ramírez")
    handler.handle_message("+15559990000", "sofia@example.com")
    handler.handle_message("+15559990000", "2024-03-15")
    reply = handler.handle_message("+15559990000", "2026-08-01")

    assert reply == f"Thanks, Sofía Ramírez — [es] {handler.CONFIRMATION_TEMPLATE}"
    # The client's name was never handed to the translation call.
    assert all("Sofía" not in call for call in seen_confirmation_calls)


def test_completed_case_records_preferred_language(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status", language="es")
    monkeypatch.setattr(handler, "translate_to_english", lambda text, language: text)
    monkeypatch.setattr(handler, "translate_to_language", lambda text, language: text)
    created, _logged = _stub_case_creation(monkeypatch)

    handler.handle_message("+15559990000", "cambio de estatus")
    handler.handle_message("+15559990000", "Sofía Ramírez")
    handler.handle_message("+15559990000", "sofia@example.com")
    handler.handle_message("+15559990000", "2024-03-15")
    handler.handle_message("+15559990000", "2026-08-01")

    assert created["contact"]["preferred_language"] == "es"
