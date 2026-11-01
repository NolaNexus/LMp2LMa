# Zero-Setup Execution Badges

Add to notebooks and README for Colab/Kaggle/CodeSpaces.

## Colab Badge
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USER/LMp2LMa/blob/main/{notebook_path})

## Kaggle Badge
[![Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/kernels/welcome?src=https://github.com/YOUR_USER/LMp2LMa/blob/main/{notebook_path})

## GitHub Codespaces Badge
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/YOUR_USER/LMp2LMa?devcontainer_path=.devcontainer/devcontainer.json)

---

## DevContainer for Codespaces
Create `.devcontainer/devcontainer.json`:

```json
{
  "name": "ML Architect Journey",
  "build": { "dockerfile": "Dockerfile", "target": "gpu-dev" },
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-toolsai.jupyter",
        "github.copilot"
      ]
    }
  },
  "runArgs": ["--gpus", "all"],
  "postCreateCommand": "pip install -r requirements-gpu.txt"
}
```

---

## Usage in Notebooks
Add as first cell in each notebook:

```markdown
# Notebook Title

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USER/LMp2LMa/blob/main/track-01-ml-programmer/01_data_preprocessing.ipynb)
[![Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/kernels/welcome?src=https://github.com/YOUR_USER/LMp2LMa/blob/main/track-01-ml-programmer/01_data_preprocessing.ipynb)
[![Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/YOUR_USER/LMp2LMa)
```
