#!/usr/bin/env python3
"""Make embedded Neural Designer data-source paths local to each project."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import h5py
import numpy as np


ABSOLUTE_PATH = re.compile(r"^(?:[A-Za-z]:[/\\]|[/\\]{2})")
EMBEDDED_DRIVE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[/\\]")


def ndm_dataset(project: h5py.File) -> h5py.Dataset:
    names = [name for name in project["files"] if name.lower().endswith(".ndm")]
    if len(names) != 1:
        raise ValueError(f"expected one embedded .ndm, found {names}")
    return project["files"][names[0]]


def source_path(raw: bytes) -> str:
    metadata = json.loads(raw.decode("utf-8"))
    return metadata["Dataset"]["DataSource"]["Path"]


def local_name(path: str) -> str:
    return re.split(r"[/\\]", path.rstrip("/\\"))[-1]


def absolute_strings(value: object, trail: tuple[str, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from absolute_strings(child, trail + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from absolute_strings(child, trail + (str(index),))
    elif isinstance(value, str) and (
        EMBEDDED_DRIVE_PATH.search(value) or value.startswith(("//", "\\\\"))
    ):
        yield "/".join(trail), value


def replacement_bytes(raw: bytes, old_path: str, new_path: str) -> bytes:
    text = raw.decode("utf-8")
    old_token = json.dumps(old_path)
    new_token = json.dumps(new_path)
    if text.count(old_token) != 1:
        raise ValueError(f"source path token occurs {text.count(old_token)} times")
    updated = text.replace(old_token, new_token, 1).encode("utf-8")
    if source_path(updated) != new_path:
        raise ValueError("updated source path did not survive JSON parsing")
    return updated


def recreate_dataset(dataset: h5py.Dataset, raw: bytes) -> None:
    parent = dataset.parent
    name = dataset.name.rsplit("/", 1)[-1]
    attrs = dict(dataset.attrs)
    chunks = dataset.chunks
    compression = dataset.compression
    compression_opts = dataset.compression_opts
    shuffle = dataset.shuffle
    fletcher32 = dataset.fletcher32
    scaleoffset = dataset.scaleoffset

    del parent[name]
    kwargs: dict[str, object] = {}
    if chunks is not None:
        kwargs["chunks"] = (min(chunks[0], len(raw)),)
    if compression is not None:
        kwargs["compression"] = compression
        kwargs["compression_opts"] = compression_opts
    if shuffle:
        kwargs["shuffle"] = True
    if fletcher32:
        kwargs["fletcher32"] = True
    if scaleoffset is not None:
        kwargs["scaleoffset"] = scaleoffset

    recreated = parent.create_dataset(name, data=np.frombuffer(raw, dtype=np.uint8), **kwargs)
    for key, value in attrs.items():
        recreated.attrs[key] = value
    recreated.attrs["src_size"] = len(raw)
    recreated.attrs["src_mtime"] = int(time.time() * 1000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    projects = sorted(root.rglob("*.nd"))
    changes: list[tuple[Path, str, str, bytes]] = []
    broken: list[tuple[Path, str]] = []
    embedded_absolute: list[tuple[Path, str, str, str]] = []

    for project_path in projects:
        with h5py.File(project_path, "r") as project:
            dataset = ndm_dataset(project)
            raw = dataset[:].tobytes()
            old_path = source_path(raw)
            for name, embedded in project["files"].items():
                if not name.lower().endswith((".ndm", ".ndo")):
                    continue
                document = json.loads(embedded[:].tobytes().decode("utf-8"))
                for trail, value in absolute_strings(document):
                    embedded_absolute.append((project_path, name, trail, value))
        new_path = local_name(old_path) if ABSOLUTE_PATH.match(old_path) else old_path
        if ABSOLUTE_PATH.match(old_path):
            if not (project_path.parent / new_path).exists():
                raise FileNotFoundError(f"{project_path}: local source does not exist: {new_path}")
            changes.append((project_path, old_path, new_path, replacement_bytes(raw, old_path, new_path)))
        if not ABSOLUTE_PATH.match(new_path) and not (project_path.parent / new_path).exists():
            broken.append((project_path, new_path))

    if args.check:
        print(
            f"projects={len(projects)} absolute_paths={len(changes)} "
            f"embedded_absolute_values={len(embedded_absolute)} "
            f"broken_relative_paths={len(broken)}"
        )
        for project_path, name, trail, value in embedded_absolute:
            print(f"ABSOLUTE {project_path.relative_to(root)}::{name}::{trail} -> {value!r}")
        for project_path, path in broken:
            print(f"BROKEN {project_path.relative_to(root)} -> {path}")
        return 1 if changes or embedded_absolute else 0

    originals: list[tuple[Path, bytes]] = []
    try:
        for project_path, old_path, new_path, updated in changes:
            with h5py.File(project_path, "r+") as project:
                dataset = ndm_dataset(project)
                originals.append((project_path, dataset[:].tobytes()))
                recreate_dataset(dataset, updated)
            print(f"UPDATED {project_path.relative_to(root)}: {old_path} -> {new_path}")
    except Exception:
        for project_path, raw in reversed(originals):
            with h5py.File(project_path, "r+") as project:
                recreate_dataset(ndm_dataset(project), raw)
        raise

    print(
        f"projects={len(projects)} updated={len(changes)} "
        f"embedded_absolute_values={len(embedded_absolute)} "
        f"broken_relative_paths={len(broken)}"
    )
    for project_path, name, trail, value in embedded_absolute:
        print(f"ABSOLUTE {project_path.relative_to(root)}::{name}::{trail} -> {value!r}")
    for project_path, path in broken:
        print(f"BROKEN {project_path.relative_to(root)} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
