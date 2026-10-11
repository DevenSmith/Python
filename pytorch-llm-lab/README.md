# PyTorch LLM Lab

A hands-on language-modeling project that progresses from manual gradient descent to a
GPT-style transformer built from scratch, then applies full fine-tuning, LoRA, instruction
formatting, and controlled evaluation to pretrained models.

The project contains 31 incremental lessons written in Python and PyTorch. It was built to
understand the mechanics behind LLM training rather than treating a high-level training API
as a black box.

## Highlights

- Implemented tokenization, embeddings, positional information, causal self-attention,
  multi-head attention, residual connections, layer normalization, feed-forward networks,
  and autoregressive generation.
- Built a reusable 824,897-parameter character-level GPT and trained it on Tiny Shakespeare
  with CUDA.
- Added dropout, gradient clipping, cosine learning-rate scheduling, mixed precision,
  validation, checkpointing, and resumed training.
- Fine-tuned all 124,439,808 parameters of GPT-2 on Tiny Shakespeare.
- Fine-tuned GPT-2 with LoRA using only 294,912 trainable parameters (0.2364%).
- Prepared response-only instruction-tuning labels with a production chat template.
- Compared the original, fully fine-tuned, and LoRA-adapted models on the same 10,240 held-out
  token positions.

## Results

| Model | Trainable parameters | Validation loss | Perplexity | Learned weights |
|---|---:|---:|---:|---:|
| Original GPT-2 | 0 | 4.5310 | 92.85 | Existing base model |
| Full fine-tune | 124,439,808 | **3.5972** | **36.50** | 497.77 MB |
| LoRA | 294,912 (0.2364%) | 3.7880 | 44.17 | **1.18 MB adapter** |

Both adapted models were evaluated against identical validation batches selected with a
fixed random seed. Full fine-tuning achieved the strongest domain performance; LoRA captured
most of the improvement with roughly 422 times fewer trainable parameters and a much smaller
task-specific artifact.

Example generation after full fine-tuning:

~~~text
ROMEO:
And you, that have been the cause of strife and destruction,
Have been the cause of war?
What a duke hath been the cause of war!
~~~

The output demonstrates domain adaptation, but it also shows repetition and invented content.
The repository treats those limitations as evaluation findings rather than evidence of factual
understanding.

## Learning path

| Lessons | Topics |
|---|---|
| 01–03 | Gradient descent, modules, optimizers, datasets, and batching |
| 04–05 | Character tokenization, shifted targets, token and position embeddings |
| 06–09 | Causal attention, queries/keys/values, batching, and multi-head attention |
| 10–11 | Transformer blocks and a complete miniature GPT |
| 12–15 | Training, validation, checkpoint loading, generation, temperature, and top-k |
| 16–20 | Tiny Shakespeare, CUDA training, resume/save workflows, and training improvements |
| 21–24 | Hugging Face tokenizers, pretrained generation, padding masks, and logits |
| 25–28 | GPT-2 baseline measurement, full fine-tuning, and controlled comparison |
| 29 | LoRA/PEFT training, adapter saving, and adapter reloading |
| 30 | Chat templates and response-only instruction labels |
| 31 | Final original-vs-full-vs-LoRA evaluation |

The reusable transformer implementation lives in
**src/pytorch_llm_lab/model.py**. The lessons remain separate so each concept can be run and
inspected independently.

## Project structure

~~~text
pytorch-llm-lab/
├── scripts/
│   └── download_tiny_shakespeare.py
├── src/pytorch_llm_lab/
│   ├── device.py
│   ├── model.py
│   └── lessons/
├── tests/
├── pyproject.toml
└── README.md
~~~

Downloaded data, virtual environments, generated package metadata, and model checkpoints are
excluded from Git. Full and adapter checkpoints are reproducible outputs, not source files.

## Setup

Python 3.10 or newer is required. These commands use PowerShell on Windows.

~~~powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
~~~

For the CUDA environment used to produce the reported results:

~~~powershell
python -m pip install torch==2.14.0+cu130 --index-url https://download.pytorch.org/whl/cu130
python -m pip install -e ".[dev]"
~~~

PyTorch packages are specific to the installed GPU driver and platform. Use the
[official PyTorch selector](https://pytorch.org/get-started/locally/) when the command above
does not match the target machine. A CPU installation can run the early lessons and tests,
but training lessons will be significantly slower.

Verify the environment:

~~~powershell
python -m pytorch_llm_lab.device
~~~

## Dataset

Download the Tiny Shakespeare corpus:

~~~powershell
python scripts/download_tiny_shakespeare.py
~~~

The script retrieves the corpus published with
[karpathy/char-rnn](https://github.com/karpathy/char-rnn/tree/master/data/tinyshakespeare)
and writes it to **data/tiny_shakespeare.txt**.

## Running lessons

Lessons are ordinary Python modules:

~~~powershell
python -m pytorch_llm_lab.lessons.lesson_01_gradient_descent
python -m pytorch_llm_lab.lessons.lesson_11_tiny_gpt
python -m pytorch_llm_lab.lessons.lesson_24_next_token_probabilities
~~~

The later training scripts build on locally generated checkpoints:

~~~powershell
python -m pytorch_llm_lab.lessons.lesson_27_fine_tune_gpt2
python -m pytorch_llm_lab.lessons.lesson_29_lora
python -m pytorch_llm_lab.lessons.lesson_31_final_evaluation
~~~

Hugging Face model files are downloaded on first use and cached locally. Public model downloads
do not require an access token, although authenticated requests receive higher rate limits.

## Quality checks

~~~powershell
python -m ruff check src tests scripts
python -m pytest
~~~

Tests cover the original gradient-descent exercise, transformer output shapes, maximum context
validation, and the causal-attention guarantee that future tokens cannot affect earlier
positions.

## Evaluation notes

- Dataset splits occur before training; the final 10% is reserved for validation.
- Lesson 31 creates one fixed set of 20 validation batches and sends those exact tensors to all
  three models.
- Loss and perplexity measure next-token prediction on this domain. They do not measure factual
  accuracy, safety, bias, or general instruction-following quality.
- Generated text is sampled output and may contain repetition, fabricated names, or other
  unreliable content.
- Tiny Shakespeare is useful for controlled learning experiments, not for production model
  development.

## Technologies

Python, PyTorch, CUDA, Hugging Face Transformers, PEFT/LoRA, mixed-precision training,
pytest, and Ruff.
