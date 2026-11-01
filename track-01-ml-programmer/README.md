# Module 1: Foundations — ML Programmer to ML Architect

## Overview
Core ML engineering fundamentals: data preprocessing, model training, evaluation, and experiment tracking.

## Notebooks

| Notebook | Description | Key Skills |
|----------|-------------|------------|
| `01_data_preprocessing.ipynb` | End-to-end data pipeline: loading, exploration, preprocessing, validation, training, evaluation | ColumnTransformer, Pipeline, Great Expectations, feature engineering |
| `02_experiment_tracking.ipynb` | MLflow experiment tracking: model comparison, hyperparameter tuning, model registry | MLflow, cross-validation, GridSearchCV, model versioning |
| `03_model_evaluation.ipynb` | Deep evaluation: learning curves, validation curves, calibration, fairness analysis | CV strategies, ROC/PR curves, calibration, permutation importance, subgroup analysis |

## Quick Start

```bash
# Activate conda environment
conda activate ml-arch

# Launch Jupyter
jupyter lab module-01-foundations/

# Or launch MLflow UI (after running notebook 02)
mlflow ui --backend-store-uri file:./mlruns --port 5000
```

## Learning Path

1. **Start with 01_data_preprocessing.ipynb** — Build a complete preprocessing pipeline with validation
2. **Then 02_experiment_tracking.ipynb** — Track experiments, compare models, register best model
3. **Finally 03_model_evaluation.ipynb** — Master evaluation techniques and error analysis

## Artifacts

Trained pipelines and metadata are saved to `../artifacts/`:
- `adult_income_pipeline.joblib` — Serialized sklearn pipeline
- `pipeline_metadata.json` — Feature names, params, data splits

## Dependencies

All required packages installed in `ml-arch` conda environment:
- scikit-learn, pandas, numpy, matplotlib, seaborn
- mlflow, great-expectations
- jupyter, ipykernel

## Exercises to Extend

- [ ] Swap RandomForest for XGBoost/LightGBM
- [ ] Add Optuna for hyperparameter optimization
- [ ] Implement data versioning with DVC
- [ ] Create model cards for each trained model
- [ ] Build a simple FastAPI serving endpoint
- [ ] Add drift detection with Evidently AI