#!/usr/bin/env python3
"""Download and organize the PlantVillage RGB dataset.

The default source is the public PlantVillage-Dataset repository.  It is
downloaded as an archive and its ``raw/color`` class folders are placed in
``data/plantvillage/raw``.  Dataset files are intentionally not committed.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_URL = (
    "https://github.com/spMohanty/PlantVillage-Dataset/archive/refs/heads/master.zip"
)
DATA_ROOT = Path(__file__).resolve().parent / "data" / "plantvillage"


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    """Extract an archive while preventing paths from escaping destination."""
    destination = destination.resolve()
    for member in archive.infolist():
        member_path = (destination / member.filename).resolve()
        if destination not in member_path.parents and member_path != destination:
            raise ValueError(f"Unsafe archive member: {member.filename}")
    archive.extractall(destination)


def find_color_directory(extracted_root: Path) -> Path:
    matches = [path for path in extracted_root.rglob("color") if path.is_dir()]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one PlantVillage 'color' directory; "
            f"found {len(matches)}. Check the archive source."
        )
    return matches[0]


def download_and_organize(url: str, destination: Path, force: bool) -> None:
    raw_dir = destination / "raw"
    if raw_dir.exists() and any(raw_dir.iterdir()) and not force:
        print(f"Dataset already exists at {raw_dir}; use --force to replace it.")
        return

    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="plantvillage_") as temporary:
        temp_root = Path(temporary)
        archive_path = temp_root / "plantvillage.zip"
        print(f"Downloading PlantVillage archive from {url} ...")
        urllib.request.urlretrieve(url, archive_path)

        extraction_dir = temp_root / "extracted"
        extraction_dir.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            safe_extract(archive, extraction_dir)

        color_dir = find_color_directory(extraction_dir)
        staged_raw = temp_root / "raw"
        shutil.copytree(color_dir, staged_raw)

        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        shutil.move(str(staged_raw), str(raw_dir))

    class_count = sum(1 for item in raw_dir.iterdir() if item.is_dir())
    image_count = sum(1 for item in raw_dir.rglob("*") if item.suffix.lower() in {".jpg", ".jpeg", ".png"})
    print(f"Organized {image_count} images across {class_count} classes in {raw_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="PlantVillage ZIP archive URL")
    parser.add_argument("--destination", type=Path, default=DATA_ROOT)
    parser.add_argument("--force", action="store_true", help="Replace an existing raw dataset")
    args = parser.parse_args()
    download_and_organize(args.url, args.destination, args.force)


if __name__ == "__main__":
    main()
