"""
LLM-powered Customer Support System
Core domain models and interfaces
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    POLICY_VIOLATION = "policy_violation"
    CUSTOMER_REQUEST = "customer_request"
    SLA_BREACH_RISK = "sla_breach_risk"
    COMPLEX_TECHNICAL = "complex_technical"


@dataclass
class Customer:
    id: str
    email: str
    name: str
    tier: str = "standard"  # standard, premium, enterprise
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Ticket:
    id: str = field(default_factory=lambda: str(uuid4()))
    customer_id: str = ""
    title: str = ""
    description: str = ""
    category: TicketCategory = TicketCategory.GENERAL
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    assigned_agent: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid4()))
    ticket_id: str = ""
    author_id: str = ""  # customer_id or "system" or agent_id
    content: str = ""
    is_llm_generated: bool = False
    llm_metadata: Dict[str, Any] = field(default_factory=dict)  # provider, model, tokens, latency
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ClassificationResult:
    category: TicketCategory
    confidence: float
    suggested_priority: TicketPriority
    reasoning: str
    model_used: str
    processing_time_ms: float


@dataclass
class GenerationResult:
    response: str
    confidence: float
    model_used: str
    tokens_used: int
    processing_time_ms: float
    citations: List[str] = field(default_factory=list)


@dataclass
class EscalationDecision:
    should_escalate: bool
    reason: Optional[EscalationReason] = None
    confidence: float = 0.0
    suggested_agent: Optional[str] = None
    reasoning: str = ""


# Domain Events
@dataclass
class DomainEvent:
    event_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid4()))


# Events
TICKET_CREATED = "ticket.created"
TICKET_CLASSIFIED = "ticket.classified"
RESPONSE_GENERATED = "response.generated"
TICKET_ESCALATED = "ticket.escalated"
TICKET_RESOLVED = "ticket.resolved"
CUSTOMER_REPLIED = "customer.replied"
