# DeepSeek-OCR Feasibility Experiment

Date: 2026-03-15

## Goal
Evaluate whether a local DeepSeek-OCR backend would be a more stable replacement for the current AOAI-based OCR path.

## Environment
- GPU: NVIDIA GeForce RTX 5070 Ti 16GB
- PyTorch: `2.12.0.dev20260315+cu128`
- Model: `deepseek-ai/DeepSeek-OCR`
- Script: `scripts/experiment_deepseek_ocr.py`
- Test image: `data/test/confirmation_test-3.jpg`

## Tested Modes

### 1. Full precision / bf16 on GPU
Command shape:
- `python3 scripts/experiment_deepseek_ocr.py --image data/test/confirmation_test-3.jpg --mode full`

Result:
- `elapsed_s: 5.662`
- `success: false`
- Failure: CUDA OOM during model placement

Artifact:
- `data/local-ocr-probes/deepseek-full.json`

### 2. 8bit quantized
Command shape:
- `python3 scripts/experiment_deepseek_ocr.py --image data/test/confirmation_test-3.jpg --mode 8bit`

Result:
- `elapsed_s: 6.105`
- `success: false`
- Failure: bitsandbytes runtime incompatibility in the vision branch
- Error: `RuntimeError('Only two or three dimensional matrices are supported for argument A')`

Artifact:
- `data/local-ocr-probes/deepseek-8bit.json`

### 3. CPU offload / mixed placement
Command shape:
- `python3 scripts/experiment_deepseek_ocr.py --image data/test/confirmation_test-3.jpg --mode offload`

Result:
- `elapsed_s: 4.521`
- `success: false`
- Failure: still hits CUDA OOM during generation even with offload enabled

Artifact:
- `data/local-ocr-probes/deepseek-offload.json`

## Conclusion
DeepSeek-OCR is not a drop-in stable replacement in the current environment today.

Why:
- full precision does not fit comfortably in 16GB VRAM with this model/runtime stack
- 8bit quantization currently breaks in the vision path
- CPU offload still does not prevent generation-time GPU OOM

## Judgment
- Stability today: fail
- Speed comparison today: inconclusive because inference never completed
- Recommendation: do not switch the demo OCR backend to DeepSeek-OCR right now

## Practical Next Steps If We Revisit This
1. Try `deepseek-ai/DeepSeek-OCR-2` or a smaller OCR-focused model
2. Try the official vLLM recipe rather than raw Transformers custom code
3. Consider a lighter local OCR backend just for bbox/text extraction instead of full DeepSeek-OCR
4. Keep the local path as a side quest until it completes a full image successfully
