import json
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import translation


def _mock_llm_response(text):
    response = MagicMock()
    response.content = text
    return response


def test_translate_to_language_is_noop_for_english(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("should not call the LLM for English")

    monkeypatch.setattr(translation, "_llm", fail)

    assert translation.translate_to_language("Hello", "en") == "Hello"


def test_translate_to_english_is_noop_for_english(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("should not call the LLM for English")

    monkeypatch.setattr(translation, "_llm", fail)

    assert translation.translate_to_english("Hello", "en") == "Hello"


def test_translate_to_language_calls_llm_and_caches_result(tmp_path, monkeypatch):
    monkeypatch.setattr(translation, "CACHE_PATH", str(tmp_path / "translation_cache.json"))
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("Hola")
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    result = translation.translate_to_language("Hello", "es")

    assert result == "Hola"
    mock_llm.invoke.assert_called_once()
    cache = json.loads((tmp_path / "translation_cache.json").read_text())
    assert cache["es:Hello"] == "Hola"


def test_translate_to_language_reuses_cache_without_calling_llm_again(tmp_path, monkeypatch):
    monkeypatch.setattr(translation, "CACHE_PATH", str(tmp_path / "translation_cache.json"))
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("Hola")
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    translation.translate_to_language("Hello", "es")
    translation.translate_to_language("Hello", "es")

    assert mock_llm.invoke.call_count == 1


def test_translate_to_language_cache_is_keyed_by_language_and_text(tmp_path, monkeypatch):
    monkeypatch.setattr(translation, "CACHE_PATH", str(tmp_path / "translation_cache.json"))
    responses = iter(["Hola", "Bonjour"])
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = lambda prompt: _mock_llm_response(next(responses))
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    es_result = translation.translate_to_language("Hello", "es")
    fr_result = translation.translate_to_language("Hello", "fr")

    assert es_result == "Hola"
    assert fr_result == "Bonjour"
    assert mock_llm.invoke.call_count == 2


def test_translate_to_english_does_not_use_the_cache(tmp_path, monkeypatch):
    # Answers are per-client and rarely repeat -- no cache file should even
    # be touched.
    cache_path = tmp_path / "translation_cache.json"
    monkeypatch.setattr(translation, "CACHE_PATH", str(cache_path))
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("March 15, 2024")
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    result = translation.translate_to_english("15 de marzo de 2024", "es")

    assert result == "March 15, 2024"
    assert not cache_path.exists()


def test_detect_case_type_and_language_parses_json_response(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response('{"case_type": "change_of_status", "language": "es"}')
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    case_type, language = translation.detect_case_type_and_language("mensaje", ["change_of_status", "asylum"])

    assert case_type == "change_of_status"
    assert language == "es"


def test_detect_case_type_and_language_defaults_to_english_when_missing(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response('{"case_type": "asylum"}')
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    _case_type, language = translation.detect_case_type_and_language("message", ["asylum"])

    assert language == "en"


def test_detect_case_type_and_language_returns_none_for_unknown_case_type(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response('{"case_type": "unclear", "language": "en"}')
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    case_type, _language = translation.detect_case_type_and_language("message", ["asylum"])

    assert case_type is None


def test_detect_case_type_and_language_handles_unparseable_response(monkeypatch):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _mock_llm_response("not json at all")
    monkeypatch.setattr(translation, "_llm", lambda: mock_llm)

    case_type, language = translation.detect_case_type_and_language("message", ["asylum"])

    assert case_type is None
    assert language == "en"
