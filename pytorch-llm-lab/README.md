# PyTorch LLM Lab

This is a learn-by-building course. We will start with tensors and gradient descent,
then work toward a small GPT-style language model that can be trained on this computer.

## Course path

1. Tensors, gradients, and a training loop
2. `nn.Module`, optimizers, and batching
3. Text data, tokens, and embeddings
4. Self-attention and causal masks
5. A complete miniature GPT
6. Training, evaluation, checkpoints, and text generation
7. Fine-tuning a pretrained model with LoRA

Each lesson will live in `src/pytorch_llm_lab/lessons`. Tests are small experiments that
confirm the important behavior rather than merely checking syntax.

## Setup (PowerShell)

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.14.0+cu130 --index-url https://download.pytorch.org/whl/cu130
python -m pip install -e ".[dev]"
```

The CUDA command above matches the NVIDIA GPU and driver detected when this project was
created. On a different computer, use the selector at
<https://pytorch.org/get-started/locally/> and then repeat the editable install.

## Check the environment

```powershell
python -m pytorch_llm_lab.device
```

## Run lesson 1

```powershell
python -m pytorch_llm_lab.lessons.lesson_01_gradient_descent
```

The model should learn a weight near `2`, a bias near `1`, and predict approximately `21`
when `x = 10`.

## Run the tests

```powershell
pytest
```
