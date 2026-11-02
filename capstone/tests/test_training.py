import json
from pathlib import Path

from capstone.training.train import train


def test_train_offline(tmp_path):
    cfg = json.loads(Path("capstone/training/config.json").read_text())
    cfg["mlflow"]["tracking_uri"] = f"sqlite:///{tmp_path / 'mlflow.db'}"
    cfg["output"]["last_run_path"] = str(tmp_path / "last_run.json")

    result = train(Path(_write_cfg(cfg, tmp_path)))

    assert result.accuracy > 0.0
    assert result.train_samples + result.test_samples > 0
    last_run = json.loads((tmp_path / "last_run.json").read_text())
    assert last_run["run_id"] == result.run_id
    assert last_run["model_uri"].startswith("runs:/")


def _write_cfg(cfg, tmp_path) -> str:
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg))
    return str(cfg_path)
