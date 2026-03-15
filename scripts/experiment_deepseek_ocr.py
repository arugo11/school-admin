#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--model-path', default='data/models/deepseek-ocr')
    parser.add_argument('--mode', choices=['full', '8bit', 'offload'], default='offload')
    parser.add_argument('--output-dir', default='data/local-ocr-probes/deepseek-ocr-cli')
    args = parser.parse_args()

    os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0')
    start = time.time()
    result: dict[str, object] = {'mode': args.mode, 'image': args.image, 'model_path': args.model_path}
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
        result['torch'] = torch.__version__
        tokenizer = AutoTokenizer.from_pretrained(args.model_path, trust_remote_code=True)
        kwargs = dict(
            trust_remote_code=True,
            use_safetensors=True,
            attn_implementation='eager',
            low_cpu_mem_usage=True,
        )
        if args.mode == '8bit':
            from transformers import BitsAndBytesConfig
            kwargs['quantization_config'] = BitsAndBytesConfig(load_in_8bit=True)
            kwargs['device_map'] = 'auto'
        elif args.mode == 'offload':
            kwargs['device_map'] = 'auto'
            kwargs['max_memory'] = {0: '10GiB', 'cpu': '64GiB'}
            offload_dir = Path(args.output_dir) / 'offload'
            offload_dir.mkdir(parents=True, exist_ok=True)
            kwargs['offload_folder'] = str(offload_dir)
        model = AutoModel.from_pretrained(args.model_path, **kwargs)
        if args.mode == 'full':
            model = model.eval().cuda().to(torch.bfloat16)
        else:
            model = model.eval()
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        res = model.infer(tokenizer, prompt='<image>\nFree OCR.', image_file=args.image, output_path=str(out_dir), base_size=512, image_size=512, crop_mode=False, save_results=True, test_compress=False)
        result['elapsed_s'] = round(time.time() - start, 3)
        result['success'] = True
        result['output_preview'] = str(res)[:4000]
    except Exception as exc:
        result['elapsed_s'] = round(time.time() - start, 3)
        result['success'] = False
        result['error'] = repr(exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
