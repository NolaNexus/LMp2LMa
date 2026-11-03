from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "ml-engineer",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "drift_monitoring",
    default_args=default_args,
    schedule_interval="0 2 * * *",  # Daily at 2 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    check_drift = BashOperator(
        task_id="check_drift",
        bash_command=(
            "cd /opt/ml/monitoring && "
            "python monitoring.py "
            "--reference /data/reference.csv "
            "--current /data/current_{{ ds }}.csv "
            "--model /models/production_model.joblib "
            "--output-dir /reports"
        ),
    )

    # Optional: retrain trigger
    retrain = BashOperator(
        task_id="retrain_if_needed",
        bash_command=(
            "cd /opt/ml && python retrain.py --trigger-file /reports/drift_trigger_{{ ds }}.flag"
        ),
    )

    check_drift >> retrain
