# OpenClaw Classifier Module

Stage B classifier that routes incoming work requests to appropriate agent lanes.

## Overview

The classifier implements **rules+config based routing** to determine the appropriate agent lane for incoming work requests. This is a tested, deterministic implementation suitable for production use.

## Classification Strategy

The classifier analyzes incoming requests using:

1. **Explicit Agent Requests**: When a specific agent is requested, it's honored if valid
2. **Content Analysis**: Keyword matching and length heuristics determine work complexity
3. **Safe Fallback**: Ambiguous cases route to a safe fallback lane

### Work Types

| Work Type | Description |
|-----------|-------------|
| `AUTONOMOUS_MULTI_STEP` | Multi-step work requiring OpenHands agent |
| `INTERACTIVE_SIMPLE` | Simple, interactive work |
| `AUTOMATED_BATCH` | Batch/automated work |
| `UNCERTAIN` | Ambiguous cases (uses safe fallback) |

### Agent Lanes

| Agent Lane | Target | Use Case |
|------------|--------|----------|
| `OPENHANDS` | OpenHands agent | Multi-step autonomous tasks |
| `OPENCODE` | OpenCode agent | Code-focused work |
| `SIMPLE_HANDLER` | Simple handler | Basic queries/commands |
| `SAFE_FALLBACK` | Safe fallback | Uncertain/error cases |

## Usage

```python
from openclaw.app.classifier import Classifier, WorkRequest, create_classifier

# Using default config
classifier = Classifier()

# Or with custom config
from openclaw.app.classifier import ClassifierConfig
config = ClassifierConfig(max_simple_length=200)
classifier = Classifier(config)

# Or using factory
classifier = create_classifier({"max_simple_length": 200})

# Classify a request
request = WorkRequest(
    prompt="build a web application with authentication",
    user_id="user123",
    tenant_id="tenant456"
)
decision = classifier.classify(request)

print(f"Route to: {decision.agent_lane.value}")
print(f"Work type: {decision.work_type.value}")
print(f"Confidence: {decision.confidence:.2f}")
```

## Configuration

The `ClassifierConfig` class provides tunable parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `multi_step_keywords` | build, implement, create, refactor, fix, debug, analyze, research, review, test, deploy, migrate | Keywords indicating multi-step work |
| `simple_keywords` | show, list, get, check, status, info, help, query | Keywords indicating simple work |
| `max_simple_length` | 100 | Max prompt length for simple routing |
| `min_autonomous_length` | 50 | Min prompt length for autonomous routing |
| `default_fallback_lane` | SAFE_FALLBACK | Lane for uncertain cases |
| `fallback_on_error` | true | Enable fallback on classification errors |

### Customizing Keywords

```python
config = ClassifierConfig(
    multi_step_keywords=["develop", "create", "build"],
    simple_keywords=["show", "list", "get"]
)
classifier = Classifier(config)
```

## Classification Logic

### Explicit Requests

When `requested_agent` is set in `WorkRequest`, the classifier honors the request if the agent is known:
- `openhands` → `OPENHANDS` lane
- `opencode` → `OPENCODE` lane  
- `simple` → `SIMPLE_HANDLER` lane
- Unknown agents → falls back to content analysis

### Content Analysis

**Multi-step indicators** (score each):
- Multi-step keyword present: +0.4 max
- Length >= min_autonomous_length: +0.3 max
- Compound patterns ("and", "then"): +0.3

**Simple work indicators** (score each):
- Simple keyword present: +0.4 max
- Length <= max_simple_length: +0.3 max
- Question patterns: +0.3

**Routing thresholds**:
- Multi-step score > 0.7 AND length >= min_autonomous_length → `OPENHANDS`
- Simple score > 0.6 AND length <= max_simple_length → `OPENCODE` or `SIMPLE_HANDLER`
- Otherwise → `SAFE_FALLBACK`

## Safe Fallback

The classifier always produces a valid routing decision, even for:
- Empty prompts
- Ambiguous content
- Classification errors
- Unknown agents

This ensures the dispatch system never crashes due to classification failures.

## Testing

Run tests with pytest:

```bash
python -m pytest tests/test_classifier.py -v
```

### Test Coverage

Tests verify:
- ✅ Multi-step autonomous work routes to OpenHands
- ✅ Simple/interactive work routes appropriately  
- ✅ Uncertain cases have deterministic safe fallback
- ✅ Config failures don't crash dispatch
- ✅ Batch processing works correctly
- ✅ Edge cases (unicode, long prompts, special chars) handled

## Evolution Toward LLM-Based Classification

This rules+config implementation can evolve to LLM-based classification:

1. **Same Interface**: The `Classifier` class maintains the same interface
2. **Extensible Design**: Add `LLMClassifier` subclass with same methods
3. **Gradual Migration**: Route high-confidence cases to rules, low-confidence to LLM
4. **Fallback Chain**: LLM failure → rules fallback → safe fallback

Example evolution path:
```python
class LLMClassifier(Classifier):
    """Classifier using LLM for ambiguous cases."""
    
    def _classify_by_content(self, request):
        # High confidence? Use rules
        score = self._quick_score(request.prompt)
        if score > 0.8:
            return super()._classify_by_content(request)
        
        # Low confidence? Ask LLM
        return self._llm_classify(request)
```

## Safety Guarantees

1. **No Crash**: Classification always returns valid `RoutingDecision`
2. **Deterministic**: Same input → same output (for rules-based)
3. **Configurable**: All thresholds tunable without code changes
4. **Observable**: Confidence scores and reasoning in decisions
5. **Fail-Safe**: Errors route to safe fallback, not undefined state
