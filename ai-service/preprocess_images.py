#!/usr/bin/env python3
"""Create deterministic PlantVillage splits and reusable PyTorch transforms.

The script writes only metadata and representative previews. Source images stay
in ``data/plantvillage/raw`` so validation and test samples cannot accidentally
receive training augmentation.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFile
from torchvision import transforms


ImageFile.LOAD_TRUNCATED_IMAGES = False
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
IMAGE_SIZE = 224
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
DEFAULT_ROOT = Path(__file__).resolve().parent / "data" / "plantvillage"


@dataclass(frozen=True)
class ImageRecord:
    relative_path: str
    class_name: str
    label: int
    split: str


class ImagePreprocessor:
    """Transforms for an ImageNet-pretrained CNN, ready for Stage 2 loading."""

    def __init__(self, image_size: int = IMAGE_SIZE) -> None:
        self.validation_transform = transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )
        # Applied only after a sample has been assigned to the train split.
        self.training_transform = transforms.Compose(
            [
                transforms.RandomResizedCrop(image_size, scale=(0.8, 1.0)),
                transforms.RandomRotation(20),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            ]
        )

    @staticmethod
    def load_rgb(image_path: Path) -> Image.Image:
        """Load an image in a consistent RGB colour format."""
        with Image.open(image_path) as image:
            converted = image.convert("RGB")
            converted.load()
            return converted


def allocate_splits(items: list[Path], rng: random.Random) -> dict[str, list[Path]]:
    shuffled = list(items)
    rng.shuffle(shuffled)
    count = len(shuffled)
    train_end = int(count * 0.70)
    validation_end = train_end + int(count * 0.15)
    return {
        "train": shuffled[:train_end],
        "val": shuffled[train_end:validation_end],
        "test": shuffled[validation_end:],
    }


def resolve_image_dir(data_root: Path) -> Path:
    """Use the downloader's ``raw`` layout or standard PlantVillage ``color``."""
    for directory_name in ("raw", "color"):
        candidate = data_root / directory_name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        f"PlantVillage images were not found under {data_root}. "
        "Expected either a raw/ directory from download_plantvillage.py or a standard color/ directory."
    )


def discover_images(image_dir: Path) -> dict[str, list[Path]]:
    if not image_dir.is_dir():
        raise FileNotFoundError(
            f"PlantVillage image data was not found at {image_dir}. "
            "Run download_plantvillage.py first."
        )
    classes: dict[str, list[Path]] = {}
    for class_dir in sorted(path for path in image_dir.iterdir() if path.is_dir()):
        images = sorted(
            path for path in class_dir.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if images:
            classes[class_dir.name] = images
    if not classes:
        raise RuntimeError(f"No supported images found under {image_dir}")
    return classes


def validate_rgb(images_by_class: dict[str, list[Path]]) -> None:
    failures: list[str] = []
    for image_paths in images_by_class.values():
        for image_path in image_paths:
            try:
                ImagePreprocessor.load_rgb(image_path)
            except Exception as error:  # Pillow has several possible decode errors.
                failures.append(f"{image_path}: {error}")
    if failures:
        preview = "\n".join(failures[:10])
        raise RuntimeError(f"Found {len(failures)} unreadable images:\n{preview}")


def make_records(images_by_class: dict[str, list[Path]], image_dir: Path, seed: int) -> tuple[list[ImageRecord], dict[str, int]]:
    class_to_index = {class_name: index for index, class_name in enumerate(sorted(images_by_class))}
    rng = random.Random(seed)
    records: list[ImageRecord] = []
    for class_name in sorted(images_by_class):
        for split, image_paths in allocate_splits(images_by_class[class_name], rng).items():
            records.extend(
                ImageRecord(
                    relative_path=str(image_path.relative_to(image_dir)),
                    class_name=class_name,
                    label=class_to_index[class_name],
                    split=split,
                )
                for image_path in image_paths
            )
    return records, class_to_index


def write_metadata(root: Path, records: list[ImageRecord], class_to_index: dict[str, int], seed: int, image_dir: Path) -> dict:
    metadata_dir = root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    with (metadata_dir / "splits.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["relative_path", "class_name", "label", "split"])
        writer.writeheader()
        writer.writerows(record.__dict__ for record in records)
    (metadata_dir / "class_to_index.json").write_text(
        json.dumps(class_to_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    by_split = Counter(record.split for record in records)
    distribution: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for record in records:
        distribution[record.class_name][record.split] += 1
    summary = {
        "image_directory": image_dir.name,
        "image_size": [IMAGE_SIZE, IMAGE_SIZE],
        "normalization": {"mean": IMAGENET_MEAN, "std": IMAGENET_STD},
        "split_ratio": {"train": 0.70, "val": 0.15, "test": 0.15},
        "seed": seed,
        "total_images": len(records),
        "split_sizes": dict(sorted(by_split.items())),
        "class_count": len(class_to_index),
        "class_distribution": {name: dict(sorted(counts.items())) for name, counts in sorted(distribution.items())},
        "augmentation": "Training records only: random resized crop, rotation, horizontal/vertical flip, translation, brightness/contrast jitter.",
    }
    (metadata_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def write_preview_images(root: Path, image_dir: Path, records: list[ImageRecord], count: int, seed: int) -> list[str]:
    """Save resized RGB and train-only augmentation previews for visual inspection."""
    preview_dir = root / "samples"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for prior_preview in preview_dir.glob("*.png"):
        prior_preview.unlink()

    training_records = [record for record in records if record.split == "train"]
    chosen = random.Random(seed).sample(training_records, min(count, len(training_records)))
    preprocessor = ImagePreprocessor()
    created: list[str] = []
    for index, record in enumerate(chosen, start=1):
        image = preprocessor.load_rgb(image_dir / record.relative_path)
        resized = image.resize((IMAGE_SIZE, IMAGE_SIZE))
        resized_name = f"{index:02d}_{record.label}_resized_rgb.png"
        resized.save(preview_dir / resized_name)
        created.append(str(Path("samples") / resized_name))

        # Render the geometric/colour training augmentation without normalization
        # so the preview remains human-readable. The actual tensor transform above
        # additionally applies ImageNet normalization.
        visual_augmentation = transforms.Compose(preprocessor.training_transform.transforms[:-2])
        augmented = visual_augmentation(image)
        augmented_name = f"{index:02d}_{record.label}_augmented_train.png"
        augmented.save(preview_dir / augmented_name)
        created.append(str(Path("samples") / augmented_name))
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--preview-count", type=int, default=5)
    args = parser.parse_args()

    image_dir = resolve_image_dir(args.data_root)
    images_by_class = discover_images(image_dir)
    print("Validating image readability and RGB conversion ...")
    validate_rgb(images_by_class)
    records, class_to_index = make_records(images_by_class, image_dir, args.seed)
    summary = write_metadata(args.data_root, records, class_to_index, args.seed, image_dir)
    previews = write_preview_images(args.data_root, image_dir, records, args.preview_count, args.seed)
    print(json.dumps({**summary, "sample_images": previews}, indent=2))


if __name__ == "__main__":
    main()
