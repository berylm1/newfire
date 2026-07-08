"""
OpenClaw Stage B Classifier

Routes incoming work requests to the appropriate agent lane based on
work complexity, autonomy requirements, and infrastructure constraints.

Classification Strategy
----------------------
This implementation uses rules+config routing. The routing can evolve toward
LLM-based classification in future by replacing the heuristic classifier
with a model call while maintaining the same interface and safety guarantees.

Work Types:
- AUTONOMOUS_MULTI_STEP: Multi-step work requiring OpenHands agent
- INTERACTIVE_SIMPLE: Simple, interactive work routed appropriately
- AUTOMATED_BATCH: Batch/automated work
- UNCERTAIN: Cases where classification is ambiguous (safe fallback)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class WorkType(Enum):
    """Classification categories for work routing."""
    AUTONOMOUS_MULTI_STEP = "autonomous_multi_step"
    INTERACTIVE_SIMPLE = "interactive_simple"
    AUTOMATED_BATCH = "automated_batch"
    UNCERTAIN = "uncertain"


class AgentLane(Enum):
    """Target agent lanes for routed work."""
    OPENHANDS = "openhands"
    OPENCODE = "opencode"
    SIMPLE_HANDLER = "simple_handler"
    SAFE_FALLBACK = "safe_fallback"


@dataclass
class ClassifierConfig:
    """Configuration for classifier behavior.
    
    All parameters are configurable to allow runtime tuning without code changes.
    """
    # Autonomy thresholds
    multi_step_keywords: list[str] = field(default_factory=lambda: [
        "build", "implement", "create", "refactor", "fix", "debug",
        "analyze", "research", "review", "test", "deploy", "migrate"
    ])
    
    simple_keywords: list[str] = field(default_factory=lambda: [
        "show", "list", "get", "check", "status", "info", "help", "query"
    ])
    
    # Complexity indicators (higher = more complex)
    max_simple_length: int = 100  # Max prompt length for simple routing
    min_autonomous_length: int = 20  # Min prompt length to consider autonomous (lowered for short multi-step keywords)
    
    # Agent capabilities
    openhands_capabilities: list[str] = field(default_factory=lambda: [
        "browser", "file_edit", "terminal", "multi_step", "code_review"
    ])
    
    opencode_capabilities: list[str] = field(default_factory=lambda: [
        "code_edit", "terminal", "single_file", "quick_fix"
    ])
    
    # Safe fallback configuration
    default_fallback_lane: AgentLane = AgentLane.SAFE_FALLBACK
    fallback_on_error: bool = True
    
    @classmethod
    def from_dict(cls, config: dict) -> "ClassifierConfig":
        """Create config from dictionary, supporting partial overrides."""
        defaults = cls()
        for key, value in config.items():
            if hasattr(defaults, key):
                setattr(defaults, key, value)
        return defaults


@dataclass
class WorkRequest:
    """Incoming work request to classify and route."""
    prompt: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    requested_agent: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RoutingDecision:
    """Result of classification and routing decision."""
    work_type: WorkType
    agent_lane: AgentLane
    confidence: float  # 0.0 to 1.0
    reasoning: str
    config_used: bool = True
    error: Optional[str] = None


class ClassifierError(Exception):
    """Raised when classifier encounters a non-recoverable error."""
    pass


class Classifier:
    """Stage B classifier with rules+config based routing.
    
    Routes work requests to appropriate agent lanes based on:
    - Prompt content analysis (keywords, length)
    - Explicit agent requests (when valid)
    - Config-driven thresholds
    - Safe fallback on uncertainty
    
    This is a tested, deterministic implementation suitable for production.
    """
    
    def __init__(self, config: Optional[ClassifierConfig] = None):
        """Initialize classifier with optional config.
        
        Args:
            config: Classifier configuration. Uses defaults if not provided.
        """
        self._config = config or ClassifierConfig()
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if self._config.max_simple_length <= 0:
            raise ClassifierError("max_simple_length must be positive")
        if self._config.min_autonomous_length < 0:
            raise ClassifierError("min_autonomous_length cannot be negative")
        if not self._config.default_fallback_lane:
            raise ClassifierError("default_fallback_lane must be set")
    
    def classify(self, request: WorkRequest) -> RoutingDecision:
        """Classify a work request and return routing decision.
        
        Args:
            request: The work request to classify.
            
        Returns:
            RoutingDecision with work type, agent lane, and confidence.
        """
        try:
            # Check for explicit agent request first
            if request.requested_agent:
                decision = self._handle_explicit_request(request)
                if decision:
                    return decision
            
            # Analyze prompt content
            return self._classify_by_content(request)
            
        except Exception as e:
            logger.error(f"Classifier error: {e}")
            if self._config.fallback_on_error:
                return self._safe_fallback(str(e))
            raise ClassifierError(f"Classification failed: {e}") from e
    
    def _handle_explicit_request(self, request: WorkRequest) -> Optional[RoutingDecision]:
        """Handle explicitly requested agent.
        
        Args:
            request: Work request with requested_agent set.
            
        Returns:
            RoutingDecision if valid request, None otherwise.
        """
        agent = request.requested_agent.lower().strip()
        
        # Map requested agents to lanes
        agent_map = {
            "openhands": AgentLane.OPENHANDS,
            "opencode": AgentLane.OPENCODE,
            "simple": AgentLane.SIMPLE_HANDLER,
        }
        
        if agent in agent_map:
            lane = agent_map[agent]
            return RoutingDecision(
                work_type=self._infer_work_type(lane),
                agent_lane=lane,
                confidence=1.0,
                reasoning=f"Explicit request for {agent}",
                config_used=True
            )
        
        # Unknown agent - log warning and continue to content analysis
        logger.warning(f"Unknown requested agent: {agent}")
        return None
    
    def _infer_work_type(self, lane: AgentLane) -> WorkType:
        """Infer work type from target agent lane."""
        type_map = {
            AgentLane.OPENHANDS: WorkType.AUTONOMOUS_MULTI_STEP,
            AgentLane.OPENCODE: WorkType.INTERACTIVE_SIMPLE,
            AgentLane.SIMPLE_HANDLER: WorkType.INTERACTIVE_SIMPLE,
            AgentLane.SAFE_FALLBACK: WorkType.UNCERTAIN,
        }
        return type_map.get(lane, WorkType.UNCERTAIN)
    
    def _classify_by_content(self, request: WorkRequest) -> RoutingDecision:
        """Classify work based on prompt content analysis.
        
        Uses keyword matching and length heuristics to determine work type
        and appropriate routing.
        """
        prompt_lower = request.prompt.lower()
        prompt_length = len(request.prompt)
        
        # Check for multi-step/autonomous indicators
        multi_step_score = self._score_multi_step(prompt_lower, prompt_length)
        
        # Check for simple work indicators
        simple_score = self._score_simple(prompt_lower, prompt_length)
        
        # Determine classification - check multi-step first when keyword detected
        if multi_step_score >= 0.5:
            # Multi-step routing requires sufficient length OR keyword match
            if prompt_length >= self._config.min_autonomous_length:
                return self._route_autonomous(request, multi_step_score)
            # Short prompts with multi-step keywords still route to autonomous
            # if the confidence indicates keyword match
            if multi_step_score >= 0.6:
                return self._route_autonomous(request, multi_step_score)
        
        if simple_score >= 0.4 and prompt_length <= self._config.max_simple_length:
            return self._route_simple(request, simple_score)
        
        # Ambiguous case - use safe fallback
        return self._safe_fallback("Ambiguous content classification")
    
    def _score_multi_step(self, prompt: str, length: int) -> float:
        """Score how likely this is multi-step autonomous work.
        
        Returns:
            Score from 0.0 to 1.0 indicating multi-step likelihood.
        """
        score = 0.0
        
        # Count multi-step keywords (each keyword contributes 0.25)
        multi_step_hits = sum(1 for kw in self._config.multi_step_keywords if kw in prompt)
        keyword_score = min(multi_step_hits * 0.25, 0.75)  # Each keyword adds 0.25, cap at 0.75
        score += keyword_score
        
        # Length suggests complexity
        if length >= self._config.min_autonomous_length:
            length_factor = min(length / 300, 1.0)  # Normalize to 300 chars for faster scoring
            score += length_factor * 0.25
        
        # Check for compound request patterns
        compound_indicators = [" and ", " then ", " after ", " followed by ", " and then "]
        if any(ind in prompt for ind in compound_indicators):
            score += 0.25
        
        # Single keyword presence gives base score, boost for short prompts
        if multi_step_hits >= 1:
            if length < self._config.min_autonomous_length:
                # Boost score for short prompts with keywords
                score = max(score, 0.6)
            else:
                score = max(score, 0.5)  # Minimum score if keyword found
        
        return min(score, 1.0)
    
    def _score_simple(self, prompt: str, length: int) -> float:
        """Score how likely this is simple/interactive work.
        
        Returns:
            Score from 0.0 to 1.0 indicating simple work likelihood.
        """
        score = 0.0
        
        # Check for multi-step keywords first - if present, reduce simple score
        multi_step_hits = sum(1 for kw in self._config.multi_step_keywords if kw in prompt)
        if multi_step_hits > 0:
            # Multi-step keywords present - reduce simple score significantly
            return 0.1
        
        # Count simple keywords (each contributes 0.2)
        simple_hits = sum(1 for kw in self._config.simple_keywords if kw in prompt)
        keyword_score = min(simple_hits * 0.2, 0.5)
        score += keyword_score
        
        # Short length suggests simplicity
        if length <= self._config.max_simple_length:
            length_factor = 1.0 - (length / self._config.max_simple_length)
            score += length_factor * 0.25
        
        # Single question or request pattern
        question_markers = ["?", "what", "how", "show me", "list"]
        if any(marker in prompt for marker in question_markers):
            score += 0.25
        
        # Single keyword presence gives base score
        if simple_hits >= 1:
            score = max(score, 0.4)
        
        return min(score, 1.0)
    
    def _route_autonomous(self, request: WorkRequest, confidence: float) -> RoutingDecision:
        """Route to autonomous multi-step agent."""
        return RoutingDecision(
            work_type=WorkType.AUTONOMOUS_MULTI_STEP,
            agent_lane=AgentLane.OPENHANDS,
            confidence=confidence,
            reasoning=f"Multi-step work detected (confidence: {confidence:.2f})",
            config_used=True
        )
    
    def _route_simple(self, request: WorkRequest, confidence: float) -> RoutingDecision:
        """Route to simple/interactive handler."""
        # Determine specific lane based on content
        if "code" in request.prompt.lower() or "file" in request.prompt.lower():
            lane = AgentLane.OPENCODE
        else:
            lane = AgentLane.SIMPLE_HANDLER
        
        return RoutingDecision(
            work_type=WorkType.INTERACTIVE_SIMPLE,
            agent_lane=lane,
            confidence=confidence,
            reasoning=f"Simple interactive work detected (confidence: {confidence:.2f})",
            config_used=True
        )
    
    def _safe_fallback(self, reason: str) -> RoutingDecision:
        """Safe fallback for uncertain cases or errors."""
        return RoutingDecision(
            work_type=WorkType.UNCERTAIN,
            agent_lane=self._config.default_fallback_lane,
            confidence=0.0,
            reasoning=f"Safe fallback activated: {reason}",
            config_used=True,
            error=reason if "error" in reason.lower() else None
        )
    
    def classify_batch(self, requests: list[WorkRequest]) -> list[RoutingDecision]:
        """Classify multiple work requests.
        
        Args:
            requests: List of work requests to classify.
            
        Returns:
            List of routing decisions in same order as requests.
        """
        return [self.classify(req) for req in requests]


def create_classifier(config: Optional[dict] = None) -> Classifier:
    """Factory function to create a configured classifier.
    
    Args:
        config: Optional configuration dictionary.
        
    Returns:
        Configured Classifier instance.
    """
    if config:
        classifier_config = ClassifierConfig.from_dict(config)
        return Classifier(classifier_config)
    return Classifier()
