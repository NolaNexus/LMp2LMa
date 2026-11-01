"""Audit trail logger for ML model lifecycle."""

import json
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from enum import Enum
import hashlib

class EventType(Enum):
    MODEL_CREATED = "MODEL_CREATED"
    MODEL_TRAINED = "MODEL_TRAINED"
    MODEL_VALIDATED = "MODEL_VALIDATED"
    MODEL_REGISTERED = "MODEL_REGISTERED"
    MODEL_DEPLOYED = "MODEL_DEPLOYED"
    MODEL_ROLLED_BACK = "MODEL_ROLLED_BACK"
    MODEL_RETIRED = "MODEL_RETIRED"
    DATA_INGESTED = "DATA_INGESTED"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    CONFIG_CHANGED = "CONFIG_CHANGED"

@dataclass
class AuditEvent:
    event_id: str
    event_type: EventType
    timestamp: str
    actor: str
    model_name: str
    model_version: str
    details: Dict[str, Any]
    previous_event_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def hash(self) -> str:
        """Compute hash for tamper detection."""
        content = f"{self.event_id}{self.event_type.value}{self.timestamp}{self.actor}{self.model_name}{self.model_version}{json.dumps(self.details, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

class AuditLogger:
    """Append-only audit log with integrity verification."""
    
    def __init__(self, log_path: str = "audit_log.jsonl"):
        self.log_path = log_path
        self.last_hash = None
    
    def log(self, event: AuditEvent):
        # Chain hashes for integrity
        if self.last_hash:
            event.details["previous_hash"] = self.last_hash
        event_hash = event.hash()
        event.details["event_hash"] = event_hash
        self.last_hash = event_hash
        
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(asdict(event), default=str) + '\n')
        
        print(f"AUDIT: {event.event_type.value} | {event.model_name} v{event.model_version} | {event.actor}")
    
    def verify_integrity(self) -> bool:
        """Verify log integrity by recomputing hashes."""
        last_hash = None
        with open(self.log_path, 'r') as f:
            for i, line in enumerate(f):
                event_data = json.loads(line)
                # Recompute
                event = AuditEvent(**event_data)
                if event.details.get("previous_hash") != last_hash:
                    print(f"Integrity check failed at line {i+1}: hash chain broken")
                    return False
                if event.details.get("event_hash") != event.hash():
                    print(f"Integrity check failed at line {i+1}: event hash mismatch")
                    return False
                last_hash = event.details["event_hash"]
        print("Integrity check passed")
        return True
    
    def query(self, model_name: str = None, event_type: EventType = None, since: str = None) -> list:
        """Query audit log."""
        events = []
        with open(self.log_path, 'r') as f:
            for line in f:
                event_data = json.loads(line)
                if model_name and event_data["model_name"] != model_name:
                    continue
                if event_type and event_data["event_type"] != event_type.value:
                    continue
                if since and event_data["timestamp"] < since:
                    continue
                events.append(event_data)
        return events

# Example usage
if __name__ == "__main__":
    logger = AuditLogger("audit_log.jsonl")
    
    # Log model creation
    logger.log(AuditEvent(
        event_id="",
        event_type=EventType.MODEL_CREATED,
        timestamp="",
        actor="ml-engineer",
        model_name="churn_classifier",
        model_version="1.0.0",
        details={"algorithm": "RandomForest", "features": 20, "training_data": "synthetic"},
    ))
    
    # Log training
    logger.log(AuditEvent(
        event_id="",
        event_type=EventType.MODEL_TRAINED,
        timestamp="",
        actor="ml-engineer",
        model_name="churn_classifier",
        model_version="1.0.0",
        details={"accuracy": 0.87, "auc": 0.92, "train_duration_sec": 45},
    ))
    
    # Log validation
    logger.log(AuditEvent(
        event_id="",
        event_type=EventType.MODEL_VALIDATED,
        timestamp="",
        actor="ci-pipeline",
        model_name="churn_classifier",
        model_version="1.0.0",
        details={"gates_passed": True, "validation_report": "validation_report.json"},
    ))
    
    # Verify integrity
    logger.verify_integrity()
    
    # Query
    events = logger.query(model_name="churn_classifier")
    print(f"\nFound {len(events)} events for churn_classifier")
