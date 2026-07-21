"""Translation support for intake_form_fill — requirement #7 from Mr.
Patrick's product-direction meeting: "a large share of immigration clients
aren't native English speakers." Layered on top of Phase 4's conversational
form-fill rather than a rewrite of it: every outgoing message (questions,
reprompts, the confirmation) gets translated into the client's detected
language, and only the one field kind where language actually affects
parsing — a date — gets translated back to English before validation.

Names and email addresses are never passed through translation at all:
neither is natural-language content, and running either through an LLM
risks it "helpfully" altering something that must stay exactly as given —
a mistranslated or "corrected" name is a real, visible quality problem in
a legal context, not a cosmetic one.

Self-hosted only, same DGX/Ollama endpoint every other agent in this
tenant already uses — no external translation API, per the self-hosted
mandate.

Outgoing question/reprompt text is a small, fixed set repeated across
every conversation in the same language, so those translations are cached
(translation_cache.json, keyed by language + source text) to avoid
re-translating the identical string for the tenth Spanish-speaking client
in a row. Incoming answers aren't cached — they're per-client and rarely
repeat verbatim.
"""

import json
import os
import re

DEFAULT_MODEL = "glm4:9b"
DEFAULT_BASE_URL = "http://100.88.112.5:11434/v1"

CACHE_PATH = os.environ.get(
    "TRANSLATION_CACHE_PATH", os.path.join(os.path.dirname(__file__), "translation_cache.json")
)

ENGLISH = "en"


def _llm():
    from langchain_openai import ChatOpenAI

    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    api_key = os.environ.get("LLM_API_KEY", "ollama")
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    return ChatOpenAI(api_key=api_key, base_url=base_url, model=model)


def _load_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {}
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_cache(cache: dict) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def detect_case_type_and_language(message: str, known_case_types: list) -> tuple:
    """One combined LLM call, same "single JSON extraction" pattern as
    intake_conflict_check's extract_node — returns (case_type or None,
    ISO 639-1 language code, defaulting to "en" if detection is unclear)."""
    case_types = ", ".join(known_case_types)
    prompt = (
        "Read this message from a prospective client. Respond with ONLY a JSON object, no other text:\n"
        '{"case_type": "...", "language": "..."}\n\n'
        f'"case_type" must be exactly one of: {case_types}, or "unclear" if you can\'t tell.\n'
        '"language" is the ISO 639-1 code (e.g. "en", "es", "zh") of the language the message is written in.\n\n'
        f"Message: {message}"
    )
    response = _llm().invoke(prompt)
    match = re.search(r"\{.*\}", str(response.content), re.DOTALL)
    try:
        parsed = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        parsed = {}

    case_type = parsed.get("case_type")
    if case_type not in known_case_types:
        case_type = None
    language = parsed.get("language") or ENGLISH
    return case_type, language


def translate_to_language(text: str, language: str) -> str:
    """Translates outgoing text into the client's language. Cached — the
    same handful of questions and reprompt templates repeat across every
    conversation in a given language. A no-op for English, so the common
    case makes no LLM call at all."""
    if language == ENGLISH:
        return text

    cache = _load_cache()
    cache_key = f"{language}:{text}"
    if cache_key in cache:
        return cache[cache_key]

    prompt = (
        f"Translate the following text into the language with ISO 639-1 code {language!r}. "
        "Respond with ONLY the translated text, no explanation, no quotes.\n\n"
        f"Text: {text}"
    )
    response = _llm().invoke(prompt)
    translated = str(response.content).strip()

    cache[cache_key] = translated
    _save_cache(cache)
    return translated


def translate_to_english(text: str, language: str) -> str:
    """Translates an incoming answer back to English before validating or
    storing it. Not cached — client answers are per-conversation and
    rarely repeat verbatim. A no-op for English."""
    if language == ENGLISH:
        return text

    prompt = (
        f"Translate the following text from the language with ISO 639-1 code {language!r} into English. "
        "Respond with ONLY the translated text, no explanation, no quotes.\n\n"
        f"Text: {text}"
    )
    response = _llm().invoke(prompt)
    return str(response.content).strip()
