# Automated drift monitoring script with MLflow integration.

import json
import os
from datetime import datetime

import mlflow
import pandas as pd
from evidently.legacy.metric_preset import DataDriftPreset
from evidently.legacy.report import Report
from mlflow.tracking import MlflowClient

DRIFT_THRESHOLD = 0.3  # Alert if drift share > 30%
ACCURACY_DRIFT_THRESHOLD = 0.05  # Alert if accuracy drops > 5%
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
MLFLOW_URI = os.environ.get("MLFLOW_URI", "sqlite:///mlflow.db")

mlflow.set_tracking_uri(MLFLOW_URI)
client = MlflowClient()


def check_drift(
    reference_path: str, current_path: str, model_path: str = None, output_dir: str = "./reports"
) -> dict:
    """Run drift check and return results with MLflow logging."""
    ref_df = pd.read_csv(reference_path)
    curr_df = pd.read_csv(current_path)

    # Exclude non-feature columns
    exclude_cols = ["target", "timestamp", "prediction", "prediction_proba"]
    feature_cols = [c for c in ref_df.columns if c not in exclude_cols]

    # MLflow run
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("production_drift_monitoring")

    with mlflow.start_run(run_name=f"drift_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
        mlflow.log_param("reference_path", reference_path)
        mlflow.log_param("current_path", current_path)

        # Data drift report
        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=ref_df[feature_cols], current_data=curr_df[feature_cols])

        # Save HTML report
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"{output_dir}/drift_report_{timestamp}.html"
        report.save_html(report_path)
        mlflow.log_artifact(report_path)

        # Extract results
        results = report.as_dict()
        drift_info = {"timestamp": timestamp}
        for metric in results["metrics"]:
            if metric["metric"] == "DatasetDriftMetric":
                drift_info["dataset_drift"] = metric["result"]["dataset_drift"]
                drift_info["drift_share"] = metric["result"]["drift_share"]
                drift_info["n_drifted"] = metric["result"]["number_of_drifted_columns"]
                drift_info["n_total"] = metric["result"]["number_of_columns"]

                # Log to MLflow
                mlflow.log_metric("dataset_drift_detected", int(metric["result"]["dataset_drift"]))
                mlflow.log_metric("drift_share", metric["result"]["drift_share"])
                mlflow.log_metric(
                    "n_drifted_columns", metric["result"]["number_of_drifted_columns"]
                )
                mlflow.log_metric("total_columns", metric["result"]["number_of_columns"])

        # Model performance drift (if model provided)
        if model_path and os.path.exists(model_path):
            import joblib

            model = joblib.load(model_path)

            exclude_cols = ["target", "timestamp", "prediction", "prediction_proba"]
            feature_cols = [c for c in ref_df.columns if c not in exclude_cols]

            X_ref = ref_df[feature_cols]
            y_ref = ref_df["target"]
            X_curr = curr_df[feature_cols]
            y_curr = curr_df["target"]

            ref_pred = model.predict(X_ref)
            curr_pred = model.predict(X_curr)

            from sklearn.metrics import accuracy_score

            ref_acc = accuracy_score(y_ref, ref_pred)
            curr_acc = accuracy_score(y_curr, curr_pred)

            acc_drift = ref_acc - curr_acc

            mlflow.log_metric("ref_accuracy", ref_acc)
            mlflow.log_metric("curr_accuracy", curr_acc)
            mlflow.log_metric("accuracy_drift", acc_drift)
            drift_info["accuracy_drift"] = acc_drift

            # Check accuracy drift threshold
            if abs(acc_drift) > ACCURACY_DRIFT_THRESHOLD:
                drift_info["performance_alert"] = True
                print(f"⚠️ PERFORMANCE DRIFT: accuracy dropped by {acc_drift:.4f}")

        # Alert if drift detected
        alert_triggered = False
        if drift_info.get("drift_share", 0) > DRIFT_THRESHOLD:
            drift_info["alert"] = True
            drift_info["alert_reason"] = (
                f"Drift share {drift_info['drift_share']:.1%} exceeds threshold {DRIFT_THRESHOLD}"
            )
            alert_triggered = True
        if drift_info.get("performance_alert", False):
            drift_info["alert"] = True
            drift_info["alert_reason"] = (
                drift_info.get("alert_reason", "")
                + "; "
                + f"Accuracy drift {abs(acc_drift):.4f} exceeds {ACCURACY_DRIFT_THRESHOLD}"
            )
            alert_triggered = True

        if alert_triggered:
            send_alert(drift_info, report_path)
            mlflow.log_param("alert_triggered", "true")
        else:
            mlflow.log_param("alert_triggered", "false")

        # Save JSON summary
        summary_path = f"{output_dir}/drift_summary_{timestamp}.json"
        with open(summary_path, "w") as f:
            json.dump(drift_info, f, indent=2)
        mlflow.log_artifact(summary_path)

        return drift_info


def send_alert(drift_info: dict, report_path: str):
    """Send email alert (configure SMTP)."""
    if not ALERT_EMAIL:
        print("ALERT_EMAIL not configured, skipping email")
        return

    subject = f"⚠️ Data Drift Alert: {drift_info['drift_share']:.1%} features drifted"
    body = f"""Data drift detected in production data.

    Drift share: {drift_info["drift_share"]:.1%}
    Drifted columns: {drift_info["n_drifted"]} / {drift_info["n_total"]}

    Full report: {report_path}
    """

    # Implement SMTP sending here
    print(f"ALERT: {subject}\n{body}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--output-dir", default="./reports")
    args = parser.parse_args()

    result = check_drift(args.reference, args.current, args.model, args.output_dir)
    print(json.dumps(result, indent=2))
