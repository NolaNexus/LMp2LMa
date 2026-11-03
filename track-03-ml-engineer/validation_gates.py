"""Automated validation gates for ML pipeline."""

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class GateStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"


@dataclass
class ValidationResult:
    gate_name: str
    status: GateStatus
    message: str
    details: Dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ValidationGate:
    """Base class for validation gates."""

    def __init__(self, name: str, threshold: Dict[str, float]):
        self.name = name
        self.threshold = threshold

    def run(self, **kwargs) -> ValidationResult:
        raise NotImplementedError


class PerformanceGate(ValidationGate):
    """Validate model performance metrics."""

    def run(self, metrics: Dict[str, float], **kwargs) -> ValidationResult:
        failures = []
        warnings = []

        for metric, threshold in self.threshold.items():
            if metric in metrics:
                value = metrics[metric]
                if value < threshold:
                    failures.append(f"{metric}: {value:.4f} < {threshold}")
                elif value < threshold * 1.1:
                    warnings.append(f"{metric}: {value:.4f} near threshold {threshold}")

        if failures:
            return ValidationResult(
                self.name,
                GateStatus.FAILED,
                f"Performance gate failed: {', '.join(failures)}",
                {
                    "metrics": metrics,
                    "thresholds": self.threshold,
                    "failures": failures,
                    "warnings": warnings,
                },
            )
        elif warnings:
            return ValidationResult(
                self.name,
                GateStatus.WARNING,
                f"Performance near threshold: {', '.join(warnings)}",
                {"metrics": metrics, "thresholds": self.threshold, "warnings": warnings},
            )
        else:
            return ValidationResult(
                self.name,
                GateStatus.PASSED,
                "All performance metrics above thresholds",
                {"metrics": metrics, "thresholds": self.threshold},
            )


class DataDriftGate(ValidationGate):
    """Validate data drift is within acceptable limits."""

    def run(self, drift_share: float, **kwargs) -> ValidationResult:
        threshold = self.threshold.get("max_drift_share", 0.3)

        if drift_share > threshold:
            return ValidationResult(
                self.name,
                GateStatus.FAILED,
                f"Data drift share {drift_share:.2%} exceeds threshold {threshold:.2%}",
                {"drift_share": drift_share, "threshold": threshold},
            )
        elif drift_share > threshold * 0.5:
            return ValidationResult(
                self.name,
                GateStatus.WARNING,
                f"Data drift share {drift_share:.2%} approaching threshold",
                {"drift_share": drift_share, "threshold": threshold},
            )
        else:
            return ValidationResult(
                self.name,
                GateStatus.PASSED,
                f"Data drift share {drift_share:.2%} within acceptable range",
                {"drift_share": drift_share, "threshold": threshold},
            )


class ValidationPipeline:
    """Run all validation gates."""

    def __init__(self):
        self.gates = []

    def add_gate(self, gate: ValidationGate):
        self.gates.append(gate)

    def run_all(self, **kwargs) -> List[ValidationResult]:
        results = []
        for gate in self.gates:
            result = gate.run(**kwargs)
            results.append(result)
            print(f"[{result.status.value}] {result.gate_name}: {result.message}")
        return results

    def all_passed(self, results: List[ValidationResult]) -> bool:
        return all(r.status == GateStatus.PASSED for r in results)

    def save_report(self, results: List[ValidationResult], path: str):
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "PASSED" if self.all_passed(results) else "FAILED",
            "gates": [asdict(r) for r in results],
        }
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)


# Example usage
if __name__ == "__main__":
    pipeline = ValidationPipeline()

    pipeline.add_gate(
        PerformanceGate(
            "Performance",
            {
                "accuracy": 0.80,
                "auc": 0.85,
                "f1": 0.75,
            },
        )
    )

    pipeline.add_gate(DataDriftGate("Data Drift", {"max_drift_share": 0.3}))

    results = pipeline.run_all(
        metrics={"accuracy": 0.87, "auc": 0.92, "f1": 0.84},
        drift_share=0.15,
    )

    pipeline.save_report(results, "validation_report.json")

    if pipeline.all_passed(results):
        print("\n✅ All gates passed - ready for deployment")
        sys.exit(0)
    else:
        print("\n❌ Gates failed - deployment blocked")
        sys.exit(1)
