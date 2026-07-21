import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import handler


def _reset_state(tmp_path, monkeypatch):
    monkeypatch.setattr(handler, "STATE_PATH", str(tmp_path / "conversation_state.json"))


def _stub_classifier(monkeypatch, case_type):
    monkeypatch.setattr(handler, "_classify_case_type", lambda message: case_type)


def _stub_case_creation(monkeypatch):
    created = {}
    logged = []
    monkeypatch.setattr(handler, "create_case", lambda **kwargs: created.update(kwargs) or {**kwargs, "id": "case-1"})
    monkeypatch.setattr(handler, "log_event", lambda **kwargs: logged.append(kwargs))
    return created, logged


def test_first_message_with_clear_case_type_asks_first_question(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")

    reply = handler.handle_message("+15551234567", "I want to change from a visitor visa to a student visa")

    assert reply == "What's your full legal name?"


def test_first_message_unclear_asks_clarifying_question_without_saving_state(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, None)

    reply = handler.handle_message("+15551234567", "hi")

    assert reply == handler.CLARIFYING_QUESTION
    assert handler._load_state() == {}


def test_second_message_advances_to_next_question(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
    handler.handle_message("+15551234567", "change of status question")

    reply = handler.handle_message("+15551234567", "Priya Raman")

    assert reply == "What's the best email address to reach you at?"
    state = handler._load_state()["+15551234567"]
    assert state["answers"]["client_name"] == "Priya Raman"
    assert state["step"] == 1


def test_invalid_email_is_reprompted_without_advancing_step(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
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
    handler.handle_message("+15551234567", "change of status question")
    handler.handle_message("+15551234567", "Priya Raman")
    handler.handle_message("+15551234567", "priya@example.com")

    handler.handle_message("+15551234567", "03/15/2024")

    state = handler._load_state()["+15551234567"]
    assert state["answers"]["key_dates"]["us_entry_date"] == "2024-03-15"


def test_completed_conversation_creates_case_and_clears_state(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "change_of_status")
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
    assert created["contact"] == {"email": "priya@example.com", "whatsapp": "+15551234567"}
    assert created["key_dates"] == {"us_entry_date": "2024-03-15", "visa_expiration": "2026-08-01"}
    assert logged[0]["event_type"] == "intake_completed"
    assert "Priya Raman" in logged[0]["summary"]
    assert handler._load_state() == {}


def test_different_phone_numbers_have_independent_conversations(tmp_path, monkeypatch):
    _reset_state(tmp_path, monkeypatch)
    _stub_classifier(monkeypatch, "asylum")

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
