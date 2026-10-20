"""
Safe Model Inspection Service for EcoCompress AI (Phase 3).
Inspects model architectures, parameter counts, file sizes, format safety, and licenses.
Strictly read-only: NEVER downloads weight tensors, executes code, or uses pickle.load.
"""

import json
import struct
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from config import settings

# Approved local directory roots for safe local model inspection
APPROVED_LOCAL_ROOTS: List[Path] = [
    settings.artifacts_dir.resolve(),
    (settings.base_dir / "models").resolve(),
    Path("D:/Projects/Compression AI/data").resolve(),
]


class ModelInspectionError(Exception):
    def __init__(self, message: str, code: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


def sanitize_and_validate_local_path(raw_path: str) -> Path:
    """
    Validates that a local path is strictly contained within approved roots.
    Rejects directory traversal (..) and access to arbitrary drives/system folders.
    """
    clean_str = raw_path.strip()
    if not clean_str:
        raise ModelInspectionError("Local model path cannot be empty.", code="EMPTY_PATH")

    try:
        resolved = Path(clean_str).resolve()
    except Exception as e:
        raise ModelInspectionError(f"Malformed path: {str(e)}", code="INVALID_PATH")

    # Enforce confinement to approved roots
    is_contained = any(
        resolved == root or root in resolved.parents for root in APPROVED_LOCAL_ROOTS
    )

    if not is_contained:
        raise ModelInspectionError(
            f"Access denied: Path '{raw_path}' is outside approved model directories. "
            f"Approved roots: {[str(r) for r in APPROVED_LOCAL_ROOTS]}",
            code="UNAPPROVED_DIRECTORY",
        )

    if not resolved.exists():
        raise ModelInspectionError(f"Local model directory does not exist: '{resolved}'", code="LOCAL_NOT_FOUND")

    if not resolved.is_dir():
        raise ModelInspectionError(f"Specified path is not a directory: '{resolved}'", code="NOT_A_DIRECTORY")

    return resolved


def parse_safetensors_header(file_path: Path) -> Dict[str, Any]:
    """
    Reads only the 8-byte length prefix and the UTF-8 JSON header of a .safetensors file.
    Does NOT load any tensor bytes into memory.
    """
    if not file_path.exists() or file_path.stat().st_size < 8:
        return {"error": "Invalid or truncated safetensors file"}

    with open(file_path, "rb") as f:
        header_len_bytes = f.read(8)
        if len(header_len_bytes) < 8:
            return {"error": "Missing 8-byte header size prefix"}

        header_len = struct.unpack("<Q", header_len_bytes)[0]
        # Safety guard: Header should not be absurdly large (> 100 MB)
        if header_len > 100 * 1024 * 1024:
            return {"error": "Header length exceeds safety threshold (100 MB)"}

        header_json_bytes = f.read(header_len)
        try:
            header = json.loads(header_json_bytes.decode("utf-8"))
        except Exception as e:
            return {"error": f"Failed to parse safetensors JSON header: {str(e)}"}

    total_params = 0
    tensors_summary = []
    for tensor_name, info in header.items():
        if tensor_name == "__metadata__":
            continue
        shape = info.get("shape", [])
        dtype = info.get("dtype", "unknown")
        # Compute element count
        elems = 1
        for dim in shape:
            elems *= dim
        total_params += elems
        tensors_summary.append({"name": tensor_name, "shape": shape, "dtype": dtype, "params": elems})

    return {
        "total_parameters": total_params,
        "tensor_count": len(tensors_summary),
        "metadata": header.get("__metadata__", {}),
    }


def inspect_local_model(local_path_str: str) -> Dict[str, Any]:
    """
    Inspects an approved local model directory.
    Reads config.json and safetensors header without downloading or running code.
    """
    resolved_dir = sanitize_and_validate_local_path(local_path_str)

    config_path = resolved_dir / "config.json"
    config_data: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            config_data = {"error": f"Failed to parse config.json: {str(e)}"}

    # File inventory
    files_list = []
    total_size_bytes = 0
    has_safetensors = False
    has_pickle = False
    safetensors_params = 0

    for item in resolved_dir.iterdir():
        if item.is_file():
            size = item.stat().st_size
            total_size_bytes += size
            lower_name = item.name.lower()
            files_list.append({"filename": item.name, "size_bytes": size, "size_mb": round(size / (1024**2), 2)})

            if lower_name.endswith(".safetensors"):
                has_safetensors = True
                parsed = parse_safetensors_header(item)
                if "total_parameters" in parsed:
                    safetensors_params += parsed["total_parameters"]
            elif lower_name.endswith((".bin", ".pt", ".pkl", ".pth")):
                has_pickle = True

    # Parameter determination
    parameter_count = safetensors_params if safetensors_params > 0 else None
    if parameter_count is None and "num_parameters" in config_data:
        parameter_count = config_data.get("num_parameters")

    architecture = config_data.get("architectures", [config_data.get("model_type", "Unknown")])
    if isinstance(architecture, list) and architecture:
        architecture = architecture[0]

    security_warnings = []
    if has_pickle and not has_safetensors:
        security_warnings.append(
            "Legacy pickled PyTorch weights (.bin/.pt) detected. "
            "Pickle files can execute arbitrary code upon loading. Conversion to .safetensors is required."
        )

    return {
        "source": "local",
        "model_id": str(resolved_dir),
        "name": resolved_dir.name,
        "architecture": str(architecture),
        "task": config_data.get("task", config_data.get("pipeline_tag", "unspecified")),
        "parameter_count": parameter_count,
        "format": "safetensors" if has_safetensors else "bin/pickle" if has_pickle else "unknown",
        "has_safetensors": has_safetensors,
        "has_pickle": has_pickle,
        "total_weight_size_mb": round(total_size_bytes / (1024**2), 2),
        "files_count": len(files_list),
        "files_summary": files_list[:20],  # cap list for clean output
        "license": config_data.get("license", "Local / Unspecified"),
        "security_warnings": security_warnings,
        "raw_config": {k: v for k, v in config_data.items() if k in ["hidden_size", "num_hidden_layers", "num_attention_heads", "vocab_size"]},
    }


def inspect_huggingface_model(model_id: str, revision: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely retrieves metadata for a model from the official Hugging Face Hub API.
    Does NOT download weights or run repository code.
    """
    clean_id = model_id.strip()
    if not clean_id or ".." in clean_id or any(c in clean_id for c in [";", "&", "|", "`", "$"]):
        raise ModelInspectionError("Invalid Hugging Face model identifier.", code="INVALID_MODEL_ID")

    api_url = f"https://huggingface.co/api/models/{clean_id}"
    params = {}
    if revision:
        params["revision"] = revision

    headers = {"User-Agent": "EcoCompressAI-Phase3/0.3.0"}

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(api_url, params=params, headers=headers)
    except httpx.TimeoutException:
        raise ModelInspectionError(
            f"Connection timed out while contacting Hugging Face API for '{clean_id}'. Check network connectivity.",
            code="NETWORK_TIMEOUT",
        )
    except Exception as e:
        raise ModelInspectionError(f"Network error querying Hugging Face API: {str(e)}", code="NETWORK_ERROR")

    if resp.status_code == 404:
        raise ModelInspectionError(
            f"Model '{clean_id}' was not found on Hugging Face Hub (HTTP 404). Check spelling or repository name.",
            code="MODEL_NOT_FOUND",
        )
    elif resp.status_code == 401 or resp.status_code == 403:
        raise ModelInspectionError(
            f"Model '{clean_id}' is private, gated, or requires an authenticated Hugging Face token (HTTP {resp.status_code}).",
            code="GATED_OR_PRIVATE",
        )
    elif resp.status_code != 200:
        raise ModelInspectionError(
            f"Hugging Face API returned HTTP {resp.status_code}: {resp.text[:200]}",
            code="API_ERROR",
        )

    data = resp.json()

    # Extract metadata fields safely
    pipeline_tag = data.get("pipeline_tag") or "unspecified"
    config_dict = data.get("config", {}) or {}
    architectures = config_dict.get("architectures", [])
    architecture_name = architectures[0] if architectures else config_dict.get("model_type", "Unknown")

    # Safetensors and parameter analysis
    safetensors_info = data.get("safetensors", {}) or {}
    param_count = safetensors_info.get("total")

    # Inspect siblings (file inventory without downloading content)
    siblings = data.get("siblings", []) or []
    files_summary = []
    total_weight_bytes = 0
    has_safetensors = False
    has_pickle = False

    for s in siblings:
        rfilename = s.get("rfilename", "")
        # Get weight file sizes from lfs pointer if present
        lfs_info = s.get("lfs", {}) or {}
        size_bytes = lfs_info.get("size", 0)
        total_weight_bytes += size_bytes

        lower = rfilename.lower()
        if lower.endswith(".safetensors"):
            has_safetensors = True
        elif lower.endswith((".bin", ".pt", ".pkl")):
            has_pickle = True

        files_summary.append({
            "filename": rfilename,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024**2), 2) if size_bytes else None,
        })

    # License metadata extraction
    tags = data.get("tags", []) or []
    card_data = data.get("cardData", {}) or {}
    license_tag = card_data.get("license") or next(
        (t.replace("license:", "") for t in tags if t.startswith("license:")),
        "Unspecified / Not Declared",
    )

    security_warnings = []
    if has_pickle and not has_safetensors:
        security_warnings.append(
            "Repository contains only pickled weights (.bin). "
            "EcoCompress AI enforces .safetensors checkpoints to prevent deserialization vulnerabilities."
        )

    return {
        "source": "huggingface",
        "model_id": data.get("id", clean_id),
        "name": data.get("id", clean_id).split("/")[-1],
        "architecture": architecture_name,
        "task": pipeline_tag,
        "parameter_count": param_count,
        "format": "safetensors" if has_safetensors else "bin/pickle" if has_pickle else "unknown",
        "has_safetensors": has_safetensors,
        "has_pickle": has_pickle,
        "total_weight_size_mb": round(total_weight_bytes / (1024**2), 2) if total_weight_bytes else None,
        "files_count": len(files_summary),
        "files_summary": files_summary[:25],
        "license": license_tag,
        "private": data.get("private", False),
        "gated": data.get("gated", False),
        "sha": data.get("sha"),
        "security_warnings": security_warnings,
        "raw_config": {k: v for k, v in config_dict.items() if k in ["hidden_size", "num_hidden_layers", "num_attention_heads", "vocab_size"]},
    }
