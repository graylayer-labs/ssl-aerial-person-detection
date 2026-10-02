"""Frozen vision backbones: loading, weight checksums and patch features.

Shared by `tools/forward_pass_cost.py` (#64) and the feature cache (#65). The
weights come from the Hugging Face hub through `transformers` and are never
modified. `NaflexExtractor` turns one image into a grid of patch features and
is the only thing the cache needs from a model, so tests replace it with a
fake.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import AutoModel, Siglip2VisionModel, SiglipVisionModel


@dataclass(frozen=True)
class Spec:
    repo: str
    kind: str  # "siglip", "naflex" or "dinov2"
    patch: int
    tile_px: int  # side of one forward pass for the fixed-resolution models
    # (label, patch budget) for naflex, one forward pass per image
    budgets: tuple[tuple[str, int], ...] = ()


SPECS = {
    "siglip2-base-512": Spec("google/siglip2-base-patch16-512", "siglip", 16, 512),
    "siglip2-large-512": Spec("google/siglip2-large-patch16-512", "siglip", 16, 512),
    "siglip2-base-naflex": Spec(
        "google/siglip2-base-patch16-naflex",
        "naflex",
        16,
        0,
        (("~512", 1024), ("~1024", 4096)),
    ),
    "dinov2-base": Spec("facebook/dinov2-base", "dinov2", 14, 518),
}


def load(spec: Spec, device: str) -> torch.nn.Module:
    """The vision tower in half precision on `device`, in eval mode."""
    if spec.kind == "siglip":
        model = SiglipVisionModel.from_pretrained(spec.repo, dtype=torch.float16)
    elif spec.kind == "naflex":
        model = Siglip2VisionModel.from_pretrained(spec.repo, dtype=torch.float16)
    else:
        model = AutoModel.from_pretrained(spec.repo, dtype=torch.float16)
    module: torch.nn.Module = model
    return module.to(device).eval()


def weight_checksums(repo: str) -> dict[str, str]:
    """SHA-256 of each `.safetensors` file of `repo`, by file name."""
    from huggingface_hub import snapshot_download

    try:  # the cache first: a stalled hub connection must not hang a run
        root = Path(
            snapshot_download(
                repo, allow_patterns=["*.safetensors"], local_files_only=True
            )
        )
    except Exception:
        root = Path(snapshot_download(repo, allow_patterns=["*.safetensors"]))
    out = {}
    for path in sorted(root.glob("*.safetensors")):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while block := handle.read(1 << 24):
                digest.update(block)
        out[path.name] = digest.hexdigest()
    return out


def pool2(grid_features: torch.Tensor, k: int = 2) -> torch.Tensor:
    """Average-pool an h x w x d grid by k x k. An odd side loses its last row
    or column. `k` of 1 returns the grid unchanged."""
    if k == 1:
        return grid_features
    x = grid_features.permute(2, 0, 1).unsqueeze(0)
    return F.avg_pool2d(x, k).squeeze(0).permute(1, 2, 0)


class NaflexExtractor:
    """One image to a pooled grid of patch features, as a NumPy fp16 array.

    The image keeps its aspect ratio; the processor picks the grid that fits
    `token_budget` patches. Any image mode is converted to RGB first, so a
    one-channel thermal frame is replicated to three identical channels. The
    features are the last hidden state of the vision tower, not the pooled
    embedding.
    """

    def __init__(self, model, processor, token_budget: int, pooling: int) -> None:
        self.model = model
        self.processor = processor
        self.token_budget = token_budget
        self.pooling = pooling

    def prepare(self, image: Image.Image) -> dict[str, torch.Tensor]:
        """Resize and patchify on the CPU; safe to call from worker threads."""
        return self.processor(
            images=[image.convert("RGB")],
            return_tensors="pt",
            max_num_patches=self.token_budget,
        )

    def __call__(self, image: Image.Image) -> np.ndarray:
        return self.extract(self.prepare(image))

    def extract(self, inputs: dict[str, torch.Tensor]) -> np.ndarray:
        """Run the vision tower on prepared inputs and pool the patch grid."""
        device = next(self.model.parameters()).device
        feed = {
            k: v.to(device, self.model.dtype if v.is_floating_point() else v.dtype)
            for k, v in inputs.items()
        }
        with torch.no_grad():
            tokens = self.model(**feed).last_hidden_state[0]
            h, w = (int(v) for v in inputs["spatial_shapes"][0])
            grid = pool2(tokens[: h * w].reshape(h, w, -1), self.pooling)
            host = grid.to(torch.float16).cpu()
        if device.type == "mps":
            torch.mps.synchronize()
        return host.numpy()
