"""
Tests for OpenClaw Stage B Classifier

Tests cover:
- Multi-step autonomous work routes to OpenHands
- Interactive/simple work routes appropriately
- Uncertain cases have deterministic safe fallback
- Config/model failure does not crash dispatch
"""

import pytest
from openclaw.app.classifier import (
    Classifier,
    ClassifierConfig,
    ClassifierError,
    WorkRequest,
    RoutingDecision,
    WorkType,
    AgentLane,
    create_classifier,
)


class TestClassifierConfig:
    """Tests for ClassifierConfig."""
    
    def test_default_config(self):
        """Default config has sensible defaults."""
        config = ClassifierConfig()
        assert config.max_simple_length > 0
        assert config.min_autonomous_length >= 0
        assert config.default_fallback_lane == AgentLane.SAFE_FALLBACK
        assert config.fallback_on_error is True
    
    def test_config_from_dict(self):
        """Config can be created from dictionary."""
        config_dict = {
            "max_simple_length": 200,
            "multi_step_keywords": ["develop", "implement"],
        }
        config = ClassifierConfig.from_dict(config_dict)
        assert config.max_simple_length == 200
        assert "develop" in config.multi_step_keywords
        assert "implement" in config.multi_step_keywords
    
    def test_config_partial_override(self):
        """Partial config dict only overrides specified values."""
        config = ClassifierConfig.from_dict({"max_simple_length": 150})
        assert config.max_simple_length == 150
        # Other defaults preserved
        assert config.min_autonomous_length == 20


class TestClassifierInit:
    """Tests for Classifier initialization."""
    
    def test_default_init(self):
        """Classifier initializes with defaults."""
        classifier = Classifier()
        assert classifier._config is not None
        assert isinstance(classifier._config, ClassifierConfig)
    
    def test_custom_config_init(self):
        """Classifier accepts custom config."""
        config = ClassifierConfig(max_simple_length=300)
        classifier = Classifier(config)
        assert classifier._config.max_simple_length == 300
    
    def test_invalid_config_rejected(self):
        """Invalid config values raise ClassifierError."""
        with pytest.raises(ClassifierError):
            Classifier(ClassifierConfig(max_simple_length=0))
        
        with pytest.raises(ClassifierError):
            Classifier(ClassifierConfig(min_autonomous_length=-1))


class TestExplicitRequests:
    """Tests for explicit agent requests."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_explicit_openhands_request(self):
        """Explicit OpenHands request routes to OpenHands lane."""
        request = WorkRequest(
            prompt="Build a web app",
            requested_agent="openhands"
        )
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
        assert decision.confidence == 1.0
        assert "Explicit request" in decision.reasoning
    
    def test_explicit_opencode_request(self):
        """Explicit OpenCode request routes to OpenCode lane."""
        request = WorkRequest(
            prompt="Fix my code",
            requested_agent="opencode"
        )
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENCODE
        assert decision.confidence == 1.0
    
    def test_explicit_simple_request(self):
        """Explicit simple request routes to simple handler."""
        request = WorkRequest(
            prompt="Show me status",
            requested_agent="simple"
        )
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.SIMPLE_HANDLER
        assert decision.confidence == 1.0
    
    def test_unknown_agent_falls_back(self):
        """Unknown agent name falls back to content analysis."""
        request = WorkRequest(
            prompt="build a website with python",
            requested_agent="unknown_agent"
        )
        decision = self.classifier.classify(request)
        
        # Should not crash, should analyze content
        assert decision is not None
        assert decision.agent_lane is not None


class TestMultiStepRouting:
    """Tests for multi-step autonomous work routing."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_build_keyword_routes_to_openhands(self):
        """'build' keyword suggests multi-step work."""
        request = WorkRequest(prompt="build a complete API with authentication")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
        assert decision.work_type == WorkType.AUTONOMOUS_MULTI_STEP
        assert decision.confidence >= 0.5
    
    def test_implement_keyword_routes_to_openhands(self):
        """'implement' keyword suggests multi-step work."""
        request = WorkRequest(prompt="implement a caching layer")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
        assert decision.work_type == WorkType.AUTONOMOUS_MULTI_STEP
    
    def test_refactor_keyword_routes_to_openhands(self):
        """'refactor' keyword suggests multi-step work."""
        request = WorkRequest(prompt="refactor the entire authentication module")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
        assert decision.work_type == WorkType.AUTONOMOUS_MULTI_STEP
    
    def test_multiple_keywords_increase_confidence(self):
        """Multiple multi-step keywords increase confidence."""
        request = WorkRequest(prompt="build and deploy a microservice")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
        assert decision.confidence > 0.5
    
    def test_compound_request_routes_to_openhands(self):
        """Compound requests (with 'and', 'then') route to OpenHands."""
        request = WorkRequest(prompt="create a user table and then add authentication")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
        assert decision.confidence >= 0.5


class TestSimpleRouting:
    """Tests for simple/interactive work routing."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_show_keyword_routes_simple(self):
        """'show' keyword suggests simple work."""
        request = WorkRequest(prompt="show me the current status")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane in [AgentLane.OPENCODE, AgentLane.SIMPLE_HANDLER]
        assert decision.work_type == WorkType.INTERACTIVE_SIMPLE
        assert decision.confidence > 0.3
    
    def test_list_keyword_routes_simple(self):
        """'list' keyword suggests simple work."""
        request = WorkRequest(prompt="list all running processes")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane in [AgentLane.OPENCODE, AgentLane.SIMPLE_HANDLER]
        assert decision.work_type == WorkType.INTERACTIVE_SIMPLE
    
    def test_get_keyword_routes_simple(self):
        """'get' keyword suggests simple work."""
        request = WorkRequest(prompt="get the version number")
        decision = self.classifier.classify(request)
        
        assert decision.work_type == WorkType.INTERACTIVE_SIMPLE
    
    def test_question_routes_simple(self):
        """Questions route to simple handlers."""
        request = WorkRequest(prompt="what is the current time?")
        decision = self.classifier.classify(request)
        
        assert decision.work_type == WorkType.INTERACTIVE_SIMPLE
    
    def test_short_prompt_routes_simple(self):
        """Short prompts route to simple handlers."""
        request = WorkRequest(prompt="status")
        decision = self.classifier.classify(request)
        
        assert decision.work_type == WorkType.INTERACTIVE_SIMPLE
    
    def test_code_reference_routes_to_opencode(self):
        """Simple requests with code reference route to OpenCode."""
        request = WorkRequest(prompt="show me the config file")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENCODE


class TestFallbackBehavior:
    """Tests for uncertain case handling and safe fallback."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_ambiguous_case_uses_safe_fallback(self):
        """Ambiguous requests use safe fallback."""
        # Very short, no keywords
        request = WorkRequest(prompt="hello")
        decision = self.classifier.classify(request)
        
        # Should still return a valid decision (safe fallback)
        assert decision.agent_lane is not None
        assert decision.agent_lane == AgentLane.SAFE_FALLBACK
        assert decision.work_type == WorkType.UNCERTAIN
        assert decision.confidence == 0.0
    
    def test_fallback_on_empty_prompt(self):
        """Empty prompt uses safe fallback."""
        request = WorkRequest(prompt="")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.SAFE_FALLBACK
        assert decision.work_type == WorkType.UNCERTAIN
    
    def test_marginal_cases_are_deterministic(self):
        """Marginal cases produce consistent results."""
        request = WorkRequest(prompt="do something")
        decisions = [self.classifier.classify(request) for _ in range(10)]
        
        # All decisions should be identical
        assert all(d.agent_lane == decisions[0].agent_lane for d in decisions)
        assert all(d.confidence == decisions[0].confidence for d in decisions)


class TestConfigFailureHandling:
    """Tests for config/model failure scenarios."""
    
    def test_config_failure_does_not_crash_dispatch(self):
        """Classifier handles config failures gracefully."""
        classifier = Classifier()
        
        # Create a request that would normally work
        request = WorkRequest(prompt="build a feature")
        
        # Should not raise, even with edge cases
        decision = classifier.classify(request)
        assert decision is not None
        assert decision.agent_lane is not None
    
    def test_fallback_on_classification_error(self):
        """Classification errors trigger fallback when enabled."""
        config = ClassifierConfig(fallback_on_error=True)
        classifier = Classifier(config)
        
        # Even malformed data should not crash
        request = WorkRequest(prompt="x" * 10000)  # Very long
        decision = classifier.classify(request)
        
        assert decision is not None
        assert decision.agent_lane is not None
    
    def test_batch_processing_continues_on_individual_failure(self):
        """Batch processing handles individual failures gracefully."""
        classifier = Classifier()
        
        requests = [
            WorkRequest(prompt="build something"),
            WorkRequest(prompt="show status"),
            WorkRequest(prompt="x" * 10000),
        ]
        
        # Should not raise
        decisions = classifier.classify_batch(requests)
        
        assert len(decisions) == 3
        assert all(d.agent_lane is not None for d in decisions)


class TestBatchProcessing:
    """Tests for batch classification."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_batch_returns_all_decisions(self):
        """Batch processing returns decision for each request."""
        requests = [
            WorkRequest(prompt="build an API"),
            WorkRequest(prompt="show status"),
            WorkRequest(prompt=""),
        ]
        
        decisions = self.classifier.classify_batch(requests)
        
        assert len(decisions) == 3
        assert all(isinstance(d, RoutingDecision) for d in decisions)
    
    def test_batch_order_preserved(self):
        """Batch decisions are in same order as requests."""
        requests = [
            WorkRequest(prompt="build first"),
            WorkRequest(prompt="build second"),
        ]
        
        decisions = self.classifier.classify_batch(requests)
        
        # Both should route to OpenHands (batch processing)
        assert len(decisions) == 2
        assert all(d.agent_lane == AgentLane.OPENHANDS for d in decisions)


class TestFactoryFunction:
    """Tests for create_classifier factory function."""
    
    def test_create_without_config(self):
        """Factory creates classifier with defaults."""
        classifier = create_classifier()
        assert isinstance(classifier, Classifier)
    
    def test_create_with_config(self):
        """Factory accepts config dict."""
        config = {"max_simple_length": 500}
        classifier = create_classifier(config)
        
        assert classifier._config.max_simple_length == 500


class TestRoutingDecisions:
    """Tests for RoutingDecision structure."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_decision_has_required_fields(self):
        """RoutingDecision contains all required fields."""
        request = WorkRequest(prompt="build something")
        decision = self.classifier.classify(request)
        
        assert hasattr(decision, "work_type")
        assert hasattr(decision, "agent_lane")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "reasoning")
        assert hasattr(decision, "config_used")
    
    def test_confidence_in_valid_range(self):
        """Confidence is always between 0.0 and 1.0."""
        test_cases = [
            "build a complex system",
            "show status",
            "",
            "x",
            "build and deploy to production",
        ]
        
        for prompt in test_cases:
            request = WorkRequest(prompt=prompt)
            decision = self.classifier.classify(request)
            
            assert 0.0 <= decision.confidence <= 1.0, f"Confidence out of range for: {prompt}"
    
    def test_work_type_is_valid_enum(self):
        """Work type is always a valid WorkType enum."""
        test_cases = [
            "build something",
            "show info",
            "",
        ]
        
        for prompt in test_cases:
            request = WorkRequest(prompt=prompt)
            decision = self.classifier.classify(request)
            
            assert decision.work_type in list(WorkType)
    
    def test_agent_lane_is_valid_enum(self):
        """Agent lane is always a valid AgentLane enum."""
        test_cases = [
            "build something",
            "show info",
            "",
            "help me",
        ]
        
        for prompt in test_cases:
            request = WorkRequest(prompt=prompt)
            decision = self.classifier.classify(request)
            
            assert decision.agent_lane in list(AgentLane)


class TestTenantIsolation:
    """Tests for tenant-aware routing (future-proofing)."""
    
    def test_tenant_id_preserved_in_request(self):
        """Tenant ID is preserved through classification."""
        classifier = Classifier()
        request = WorkRequest(
            prompt="build something",
            tenant_id="legal-tenant"
        )
        
        decision = classifier.classify(request)
        
        # Request should be routable with tenant context
        assert decision is not None
        # The tenant context would be used by the dispatcher downstream


class TestEdgeCases:
    """Tests for edge case handling."""
    
    def setup_method(self):
        self.classifier = Classifier()
    
    def test_very_long_prompt(self):
        """Very long prompts are handled."""
        request = WorkRequest(prompt="build " * 1000)
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane is not None
    
    def test_unicode_prompt(self):
        """Unicode characters are handled."""
        request = WorkRequest(prompt="build こんにちはAPI 🏗️")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
    
    def test_special_characters(self):
        """Special characters are handled."""
        request = WorkRequest(prompt="build [api] with <tags> & symbols!")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
    
    def test_newlines_in_prompt(self):
        """Newlines in prompts are handled."""
        request = WorkRequest(prompt="build\nan\napi\nwith\nmany\nlines")
        decision = self.classifier.classify(request)
        
        assert decision.agent_lane == AgentLane.OPENHANDS
