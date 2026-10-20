---
name: ml-model-optimization
description: Procedures for hardware checks, model verification, and safe quantization in EcoCompress AI.
---

# ML Model Optimization Skill

## Principles
1. Verify device, VRAM, and runtime compatibility before executing optimization pipelines.
2. The original model is strictly read-only; save optimized artifacts separately with unique IDs.
3. Record model architecture, parameter count, input modalities, and optimization hyperparameters for full provenance.
4. Support standard quantization formats (e.g., PyTorch dynamic quantization, ONNX Runtime INT8) that run predictably on Windows.
5. Fail gracefully if a model or operator is unsupported; never silently fall back or switch methods without user notification.
