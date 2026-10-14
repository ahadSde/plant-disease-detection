"""Inference wrapper for the Stage 2 ResNet-50 checkpoint."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import resnet50


AI_SERVICE = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = AI_SERVICE / "outputs" / "resnet50_best.pt"
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


@dataclass(frozen=True)
class Prediction:
    disease_class: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return {"disease_class": self.disease_class, "confidence": self.confidence}


class CNNClassifier:
    """Load the saved 38-class model and produce ImageNet-normalized predictions."""

    def __init__(self, checkpoint_path: Path = DEFAULT_CHECKPOINT) -> None:
        self.checkpoint_path = checkpoint_path
        self.device = torch.device("cpu")
        self.model: nn.Module | None = None
        self.index_to_class: list[str] = []
        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )

    def load(self) -> None:
        if self.model is not None:
            return
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"CNN checkpoint is absent: {self.checkpoint_path}")
        try:
            checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
        except TypeError:  # Compatibility with older PyTorch releases.
            checkpoint = torch.load(self.checkpoint_path, map_location=self.device)
        class_to_index = checkpoint["class_to_index"]
        self.index_to_class = [name for name, _ in sorted(class_to_index.items(), key=lambda item: item[1])]
        model = resnet50(weights=None)
        model.fc = nn.Linear(model.fc.in_features, len(self.index_to_class))
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(self.device).eval()
        self.model = model

    def predict_image(self, image: Image.Image) -> Prediction:
        self.load()
        assert self.model is not None
        tensor = self.transform(image.convert("RGB")).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            probabilities = torch.softmax(self.model(tensor), dim=1)[0]
        index = int(torch.argmax(probabilities).item())
        return Prediction(self.index_to_class[index], float(probabilities[index].item()))

    def predict_bytes(self, image_bytes: bytes) -> Prediction:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            return self.predict_image(image)
