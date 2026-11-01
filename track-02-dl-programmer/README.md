# Module 4: Deep Learning Specialization

**Maps to Skillsoft Track 2: DL Programmer** — 21 courses | ~21h

## Focus
Neural networks, CNNs, RNNs, transformers, advanced DL techniques

## Key Topics
1. **Neural Network Fundamentals**
   - Biological vs artificial neurons, perceptrons, backprop
   - Activation functions, initialization, normalization
   - Universal approximation, depth vs width

2. **CNNs for Vision**
   - Conv layers, pooling, receptive fields
   - ResNet, EfficientNet, Vision Transformers (ViT)
   - Detection (YOLO, Faster R-CNN), segmentation (U-Net, Mask R-CNN)

3. **RNNs & Sequence Modeling**
   - LSTM, GRU, bidirectional RNNs
   - Attention mechanisms, Seq2Seq
   - Teacher forcing, scheduled sampling

4. **Transformers & Attention**
   - Self-attention, multi-head attention
   - BERT, GPT, T5 architectures
   - Positional encodings, masking strategies

5. **Generative Models**
   - VAEs, GANs, Diffusion models (DDPM, Stable Diffusion)
   - Flow-based models, autoregressive models

6. **Advanced Training Techniques**
   - Mixed precision, gradient accumulation
   - Curriculum learning, contrastive learning
   - Self-supervised learning (SimCLR, MoCo, MAE)

7. **DL for Specialized Domains**
   - NLP: tokenization, embeddings, fine-tuning LLMs
   - Time series: TCN, Transformers for forecasting
   - Graph Neural Networks (GCN, GAT, GraphSAGE)

## Prerequisites
- Module 1 complete (ML fundamentals)
- Linear algebra, calculus, probability (refresher in Track 1)
- Python, PyTorch or TensorFlow/Keras basics

## Notebooks
| # | Notebook | Description |
|---|----------|-------------|
| 01 | `01_nn_fundamentals.ipynb` | From-scratch MLP, backprop, autograd verification |
| 02 | `02_cnn_vision.ipynb` | ResNet/EfficientNet on CIFAR/ImageNet subset; Grad-CAM |
| 03 | `03_rnn_seq.ipynb` | LSTM/GRU for text classification; attention visualization |
| 04 | `04_transformers.ipynb` | BERT fine-tuning; custom transformer from scratch |
| 05 | `05_generative.ipynb` | VAE/GAN on MNIST; Stable Diffusion inference |
| 06 | `06_self_supervised.ipynb` | SimCLR on CIFAR-10; linear probe evaluation |
| 07 | `07_nlp_finetune.ipynb` | LoRA fine-tuning LLM on custom dataset |
| 08 | `08_gnn.ipynb` | GCN/GAT on Cora/Citeseer; node classification |

## Tools to Learn
- PyTorch (primary) / TensorFlow-Keras
- Hugging Face Transformers, PEFT, Accelerate
- TIMM (vision models), TorchVision, TorchText
- Weights & Biases / MLflow for DL experiment tracking
- Lightning / Accelerate for training loops

## Deliverables
- Trained CNN with visualization & interpretability
- Fine-tuned transformer (BERT or LLM) with evaluation
- Generative model samples + FID/IS metrics
- Self-supervised pre-training + downstream transfer results