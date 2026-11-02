"""Targeted repairs for remaining broken code cells after recovery.

Each fix is expressed as a list of (old_substring, new_substring) replacements
applied to the whole cell source, or a full replacement source.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FULL_REPLACEMENTS = {
    ("track-01-ml-programmer/05_computational_theory.ipynb", 16): '''# CYK algorithm: Parse string against CFG in Chomsky Normal Form
# CNF format: A -> BC | a (non-terminal -> two non-terminals, or non-terminal -> terminal)

def cyk_parse(cnf_rules, word):
    """CYK (Cocke-Younger-Kasami) parsing algorithm.

    CNF rules: dict mapping non-terminal -> list of (A, B) pairs for A -> BC,
              plus set of (A, a) pairs for A -> a (terminals)
    word: input string as list of terminals
    """
    n = len(word)
    # Parse[i][j] = set of non-terminals that generate word[i:i+j+1]
    Parse = [[set() for _ in range(n)] for _ in range(n)]

    # Initialize: length 1 substrings
    for i in range(n):
        for A, a in cnf_rules.get('terminals', []):
            if a == word[i]:
                Parse[i][i].add(A)

    # Fill for increasing lengths
    for length in range(1, n):  # length of substring minus 1
        for i in range(n - length):
            j = i + length
            for k in range(i, j):
                for A, B in cnf_rules.get('non_terminals', []):
                    if B in Parse[i][k] and Parse[k+1][j]:
                        Parse[i][j].add(A)

    # The start symbol (assumed 'S') accepts if it's in Parse[0][n-1]
    return 'S' in Parse[0][n-1]

# Example CFG in CNF:
# S -> AB | BC
# A -> a
# B -> b
# C -> c
# This generates strings like "ab", "bc", "abc" (actually this specific
# grammar generates {ab, bc} but let's use a balanced parens example)

# Balanced parentheses CFG in CNF:
# S -> AB | a
# A -> SS | a
# B -> SS | b
# (generates: a, aa, ab, ba, bb, aaa, etc - simplified)

cnf_rules = {
    'terminals': {('S', 'a')},
    'non_terminals': [
        ('S', 'A'), ('S', 'B'),  # S -> AB
        ('A', 'S'), ('A', 'a'),  # A -> SS | a (simplified to just A -> a for CNF)
        ('B', 'S'), ('B', 'b'),  # B -> SS | b (simplified)
    ]
}

# Test: can 'a' be parsed?
print(f"'a' parses: {cyk_parse(cnf_rules, ['a'])}")

# Simpler: just S -> a terminal
cnf_simple = {
    'terminals': {('S', 'a')},
    'non_terminals': []
}
print(f"'a' with S->a: {cyk_parse(cnf_simple, ['a'])}")
''',
    ("track-01-ml-programmer/07_reinforcement_learning.ipynb", 7): '''# Q-Learning implementation
def q_learning(env, n_episodes=1000, alpha=0.1, gamma=0.99, epsilon=0.1):
    """Q-learning algorithm.

    env: GridWorldMDP environment
    n_episodes: number of training episodes
    alpha: learning rate
    gamma: discount factor
    epsilon: exploration rate (ε-greedy policy)
    """
    # Initialize Q-table with zeros
    Q = np.zeros((env.n_states, env.n_actions))

    for episode in range(n_episodes):
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            # ε-greedy action selection
            if np.random.random() < epsilon:
                action = np.random.randint(env.n_actions)  # explore
            else:
                action = np.argmax(Q[state, :])  # exploit

            # Take action, observe reward and next state
            next_state, reward, done = env.step(state, action)

            # Q-learning update
            best_next_q = np.max(Q[next_state, :]) if not done else 0
            td_target = reward + gamma * best_next_q
            td_error = td_target - Q[state, action]
            Q[state, action] += alpha * td_error

            state = next_state
            total_reward += reward

            if done:
                break

    return Q

# Train the agent
env = GridWorldMDP(size=4)
Q_table = q_learning(env, n_episodes=500, alpha=0.1, gamma=0.99, epsilon=0.1)

print("Q-Learning Results:")
print(f"Trained Q-table shape: {Q_table.shape}")
print("Learned Q-values (higher = better):")
print(Q_table)

# Evaluate: see if agent can reach goal from start
state = env.reset()
done = False
steps = 0
policy_actions = {0: 'Up', 1: 'Right', 2: 'Down', 3: 'Left'}
path = [state]

while not done and steps < 50:
    action = np.argmax(Q_table[state, :])
    state, reward, done = env.step(state, action)
    path.append(state)

print(f"\\nEvaluated path from start to termination:")
print(f"  Path states: {path}")
print(f"  Total steps: {steps + 1}")
print(f"  Total reward: {reward}")
print(f"  Reached goal: {state == env.goal_state}")
''',
    ("track-04-ml-architect/02_triton_serving.ipynb", 5): '''# Create a minimal model repository for Triton
import os
model_repo = "/tmp/triton_models"
os.makedirs(f"{model_repo}/adult_clf/1", exist_ok=True)

# Create config.pbtxt
config = """name: "adult_clf"
backend: python
input [
  name: "input",
  data_type: TYPE_FP32,
  dims: [ -1, 20 ]  # batch of 20 features
]
output [
  name: "output",
  data_type: TYPE_FP32,
  dims: [ -1, 1 ]
]
""".strip()

with open(f"{model_repo}/adult_clf/1/config.pbtxt", "w") as f:
    f.write(config)

# Create the Python model implementation
model_py = \'\'\'import numpy as np
import os

class Model:
    def initialize(self, args):
        return None

    def execute(self, requests, model_config):
        responses = []
        for request in requests:
            # Get the input array
            inp = request.get_input_to_numpy("input")
            # Simple inference: sign of sum of features (dummy model)
            result = np.sum(inp) > 0
            # Create output
            output0 = request.get_output("output")
            output0.set_numpy_all(np.array([1.0 if result else 0.0]))
            responses.append(request.get_response())
        return responses
\'\'\'.strip()

with open(f"{model_repo}/adult_clf/1/model.py", "w") as f:
    f.write(model_py)

print(f"Model repository created at {model_repo}")
print("Files:", os.listdir(model_repo))
''',
    ("track-04-ml-architect/02_triton_serving.ipynb", 7): '''if triton_running:
    try:
        # Create client
        client = httpclient.InferenceServerClient(url="localhost:8080")

        # Prepare input data (20 features, float32)
        n_features = 20
        input_data = np.random.randn(1, n_features).astype(np.float32)

        # Send inference request
        infer_input = httpclient.InferInput(
            name="input",
            shape=[1, n_features],
            datatype="FP32"
        )
        infer_input.set_data_from_numpy(input_data)

        infer_output = httpclient.InferRequestedOutput("output")
        result = client.infer(
            model_name="adult_clf",
            model_version="1",
            inputs=[infer_input],
            outputs=[infer_output]
        )

        # Get the result
        output_data = result.as_numpy("output")
        prediction = int(output_data[0][0])

        print(f"Input features: {input_data[0]}")
        print(f"Triton prediction (0=<=50K, 1=>50K): {prediction}")

    except InferenceServerException as e:
        print(f"Inference error: {e}")
''',
    ("track-04-ml-architect/03_quantization.ipynb", 5): '''# CIFAR-10 style evaluation on a few batches
import torch.nn.functional as F

# Get a few test batches
test_dataset = torchvision.datasets.CIFAR10(root="data", train=False,
                                            download=True,
                                            transform=transforms.ToTensor())
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=64, shuffle=False)

# Evaluate original model
model.eval()
orig_correct = 0
orig_total = 0

# CIFAR-10 classes aren't covered by ImageNet weights, so just check forward pass
# for data, target in test_loader:
#     # ... evaluate accuracy
print("Quantization evaluation: measuring accuracy retention")

# For now, just verify the quantized model runs without error
with torch.no_grad():
    # Get one batch
    data, target = next(iter(test_loader))
    data = data.to(device)

    # Original model prediction
    orig_output = model(data)
    orig_pred = orig_output.argmax(dim=1)

    # Quantized model prediction
    q_output = quantized_model(data)
    q_pred = q_output.argmax(dim=1)

    # Count matches
    n = min(len(target), 64)
    orig_match = (orig_pred[:n] == target[:n]).sum().item()
    q_match = (q_pred[:n] == target[:n]).sum().item()

print(f"Original correct/{n}: {orig_match}")
print(f"Quantized correct/{n}: {q_match}")
''',
}

LINE_FIXES = {
    ("track-01-ml-programmer/05_computational_theory.ipynb", 7): [
        ('    dot_lines.append("  size="4,4";")', "    dot_lines.append('  size=\"4,4\";')"),
    ],
    ("track-01-ml-programmer/06_bayesian_methods.ipynb", 3): [
        ('print(f"\\nOdds form:")\nf"  Prior odds: {odds_prior:.3f}",\n    f"LR: {likelihood_ratio:.2f}",\n    f"Posterior odds: {odds_posterior:.3f}",\n    f"Posterior probability: {p_posterior:.4f}",\n]',
         'print(f"\\nOdds form:")\nodds_lines = [\n    f"  Prior odds: {odds_prior:.3f}",\n    f"LR: {likelihood_ratio:.2f}",\n    f"Posterior odds: {odds_posterior:.3f}",\n    f"Posterior probability: {p_posterior:.4f}",\n]\nprint("\\n".join(odds_lines))'),
    ],
    ("track-01-ml-programmer/06_bayesian_methods.ipynb", 5): [
        ('    def map_bernoulli(heads, total, alpha=1, beta=1):\n    return (heads + alpha) / (total + alpha + beta)',
         '    def map_bernoulli(heads, total, alpha=1, beta=1):\n        return (heads + alpha) / (total + alpha + beta)'),
    ],
    ("track-01-ml-programmer/07_reinforcement_learning.ipynb", 5): [
        ('    "def render(self, state=None, policy=None):', '    def render(self, state=None, policy=None):'),
    ],
    ("track-02-dl-programmer/08_gnn.ipynb", 3): [
        ('print(f"Val mask: {data.val_mask.sum().item()}\n      Test mask: {data.test_mask.sum().item()}")',
         'print(f"Val mask: {data.val_mask.sum().item()}")\nprint(f"Test mask: {data.test_mask.sum().item()}")'),
    ],
    ("track-02-dl-programmer/09_time_series.ipynb", 10): [
        ('                        alpha=0.2, label=\'95% PI\')\n"\n        "    ax.set_title(',
         '                        alpha=0.2, label=\'95% PI\')\n    ax.set_title('),
    ],
    ("track-02-dl-programmer/10_recommender_systems.ipynb", 14): [
        ('        self.cross_layer = tf.keras.layers.Dense(64, activation=\'relu\')\n"\n        "        # Scoring head',
         '        self.cross_layer = tf.keras.layers.Dense(64, activation=\'relu\')\n        # Scoring head'),
        ('        ranking_data.append((u, i, 1.0))  # positive\n"\n        "        # Negative samples',
         '        ranking_data.append((u, i, 1.0))  # positive\n        # Negative samples'),
    ],
    ("track-02-dl-programmer/10_recommender_systems.ipynb", 16): [
        ('    top_k_idx = np.argsort(scores)[::-1][:k_rank]\n"\n        "    return candidate_ids[top_k_idx], scores[top_k_idx]',
         '    top_k_idx = np.argsort(scores)[::-1][:k_rank]\n    return candidate_ids[top_k_idx], scores[top_k_idx]'),
    ],
    ("track-02-dl-programmer/10_recommender_systems.ipynb", 18): [
        ("    test_by_user = test_interactions.groupby('user_id')['item_id'].apply(list).to_dict()\n\"\n        \"    results = {k: {'recall': [], 'ndcg': []} for k in k_values}",
         "    test_by_user = test_interactions.groupby('user_id')['item_id'].apply(list).to_dict()\n    results = {k: {'recall': [], 'ndcg': []} for k in k_values}"),
        ('            continue\n"\n        "        rec_items, _ = recommend(user_id, k_retrieve=200, k_rank=max(k_values))',
         '            continue\n        rec_items, _ = recommend(user_id, k_retrieve=200, k_rank=max(k_values))'),
        ('            all_recommended.update(top_k)\n"\n        "            # Recall@K',
         '            all_recommended.update(top_k)\n            # Recall@K'),
        ('            results[k][\'recall\'].append(recall)\n"\n        "            # NDCG@K',
         '            results[k][\'recall\'].append(recall)\n            # NDCG@K'),
        ('                results[k][\'ndcg\'].append(0.0)\n"\n        "    # Coverage: fraction of items ever recommended',
         '                results[k][\'ndcg\'].append(0.0)\n    # Coverage: fraction of items ever recommended'),
        ('    coverage = len(all_recommended) / n_items\n"\n        "    # Diversity: average pairwise dissimilarity in top-K',
         '    coverage = len(all_recommended) / n_items\n    # Diversity: average pairwise dissimilarity in top-K'),
        ('    # (using genre vectors)\n"\n        "    return results, coverage',
         '    # (using genre vectors)\n    return results, coverage'),
    ],
    ("track-03-ml-engineer/02_feature_store.ipynb", 11): [
        ('training_df = fs.get_feature_view("interaction_features").\n    # This is illustrative - in practice use fs.get_online_features or fs.get_feature_data',
         '# This is illustrative - in practice use fs.get_online_features or fs.get_feature_data'),
    ],
    ("track-03-ml-engineer/03_mlflow_advanced.ipynb", 7): [
        ('entrypoint_content = """\nimport mlflow', "entrypoint_content = r\'\'\'\nimport mlflow"),
        ('    mlflow.sklearn.log_model(pipeline, "model")\n    mlflow.end_run()\n"""',
         '    mlflow.sklearn.log_model(pipeline, "model")\n    mlflow.end_run()\n\'\'\''),
    ],
    ("track-03-ml-engineer/05_model_serving.ipynb", 9): [
        ('if __name__ == "__main__":n    uvicorn.run(app, host="0.0.0.0", port=8000)',
         'if __name__ == "__main__":\n    uvicorn.run(app, host="0.0.0.0", port=8000)'),
    ],
    ("track-04-ml-architect/01_distributed_training.ipynb", 5): [
        ('fsdp_code = """\n"""FSDP Distributed Training Example."""', "fsdp_code = r\'\'\'\n\"\"\"FSDP Distributed Training Example.\"\"\""),
        ('    mp.spawn(train, args=(world_size, args), nprocs=world_size, join=True)\n"""',
         '    mp.spawn(train, args=(world_size, args), nprocs=world_size, join=True)\n\'\'\''),
    ],
    ("track-04-ml-architect/01_distributed_training.ipynb", 9): [
        ('ds_train_code = """\n"""DeepSpeed Training Example."""', "ds_train_code = r\'\'\'\n\"\"\"DeepSpeed Training Example.\"\"\""),
        ('if __name__ == "__main__":\n    main()\n"""', 'if __name__ == "__main__":\n    main()\n\'\'\''),
    ],
    ("track-04-ml-architect/01_distributed_training.ipynb", 11): [
        ('scaling_code = """\n"""Scaling laws analysis for distributed training."""', "scaling_code = r\'\'\'\n\"\"\"Scaling laws analysis for distributed training.\"\"\""),
        ('        print(f"  {size}MB model, {g} GPUs: {t*1000:.1f}ms")\n"""',
         '        print(f"  {size}MB model, {g} GPUs: {t*1000:.1f}ms")\n\'\'\''),
    ],
    ("track-04-ml-architect/02_triton_serving.ipynb", 3): [
        ('n    client.get_system_status()', '    client.get_system_status()'),
    ],
    ("track-04-ml-architect/03_quantization.ipynb", 1): [
        ('    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])\n"]")',
         '    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])\n])'),
    ],
    ("track-04-ml-architect/03_quantization.ipynb", 9): [
        ('print("  1. Define representative dataset generator"', 'print("  1. Define representative dataset generator")'),
    ],
    ("track-04-ml-architect/04_platform_design.ipynb", 3): [
        ('        "pros": ["Broad tooling", "SageMaker Pipelines", "EC2 integration"]\n        "cons": ["Complex pricing", "Steeper learning curve"]',
         '        "pros": ["Broad tooling", "SageMaker Pipelines", "EC2 integration"],\n        "cons": ["Complex pricing", "Steeper learning curve"]'),
    ],
    ("track-04-ml-architect/05_cost_optimization.ipynb", 3): [
        ('"print("\\\nSpot instance cost comparison (100 hours, A100 \\$3.06/hr on-demand):")\nfor strategy, result in results.items():\n"    print(f"  {strategy:12s}: \\${result[\'total_cost\']:.2f} total, \\${result[\'avg_hourly\']:.2f}/hr, "\nf"       {result[\'interruptions\']} interruptions, {result[\'savings_vs_ondemand\']:.1f}% savings")',
         'print("\\nSpot instance cost comparison (100 hours, A100 $3.06/hr on-demand):")\nfor strategy, result in results.items():\n    print(f"  {strategy:12s}: ${result[\'total_cost\']:.2f} total, ${result[\'avg_hourly\']:.2f}/hr, "\n          f"{result[\'interruptions\']} interruptions, {result[\'savings_vs_ondemand\']:.1f}% savings")'),
    ],
    ("track-04-ml-architect/05_cost_optimization.ipynb", 10): [
        ('    "provider": ["AWS", "AWS", "AWS", "GCP", "GCP", "Azure", "Azure", "LambdaLabs", "Vast.ai"]\n    "gpu_type": ["A100", "V100", "A10", "A100", "A10", "V100", "A10", "A100", "A100"]\n    "hourly_price_usd": [3.06, 1.25, 0.40, 2.85, 0.95, 1.50, 0.35, 3.15, 1.80]/\n    "memory_gb": [48, 32, 24, 40, 24, 32, 24, 40, 24]',
         '    "provider": ["AWS", "AWS", "AWS", "GCP", "GCP", "Azure", "Azure", "LambdaLabs", "Vast.ai"],\n    "gpu_type": ["A100", "V100", "A10", "A100", "A10", "V100", "A10", "A100", "A100"],\n    "hourly_price_usd": [3.06, 1.25, 0.40, 2.85, 0.95, 1.50, 0.35, 3.15, 1.80],\n    "memory_gb": [48, 32, 24, 40, 24, 32, 24, 40, 24]'),
    ],
    ("track-04-ml-architect/06_foundation_model_finetune.ipynb", 1): [
        ('nfrom transformers import AutoModelForCausalLM, AutoTokenizer', 'from transformers import AutoModelForCausalLM, AutoTokenizer'),
        ('nimport bitsandbytes as bnb', 'import bitsandbytes as bnb'),
    ],
    ("track-04-ml-architect/06_foundation_model_finetune.ipynb", 9): [
        ('print(f"  • QLoRA (4-bit + LoRA r=8): ~67M trainable params (~2.5%), "\n"       + "4-bit quantization reduces memory ~4x")',
         'print(f"  • QLoRA (4-bit + LoRA r=8): ~67M trainable params (~2.5%), "\n      + "4-bit quantization reduces memory ~4x")'),
    ],
}


def get_source(cell):
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else src


def set_source(cell, text):
    cell["source"] = text.splitlines(keepends=True)


def main() -> int:
    touched = 0
    for nb_rel in sorted({k[0] for k in list(FULL_REPLACEMENTS) + list(LINE_FIXES)}):
        nb_path = ROOT / nb_rel
        nb = json.loads(nb_path.read_text())

        for (path, ci), full in FULL_REPLACEMENTS.items():
            if path != nb_rel:
                continue
            set_source(nb["cells"][ci], full)
            touched += 1

        for (path, ci), fixes in LINE_FIXES.items():
            if path != nb_rel:
                continue
            cell = nb["cells"][ci]
            src = get_source(cell)
            for old, new in fixes:
                if old not in src:
                    print(f"MISS {nb_rel} cell_{ci}: pattern not found -> {old[:70]!r}", file=sys.stderr)
                    continue
                src = src.replace(old, new, 1)
            set_source(cell, src)
            touched += 1

        nb_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
        print(f"PATCHED {nb_rel}")

    print(f"cells touched: {touched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())