"""Build a compact bearing anomaly dataset from Ferrara experiment E2.

The source contains one five-second, 25.6 kHz vibration recording every five
minutes during a run-to-failure test. Each recording is divided into five
one-second windows. The final 10% of acquisitions are labelled as anomalous;
this is an Artelnics-derived label, not an annotation supplied by the authors.
"""

from __future__ import annotations

import csv
import hashlib
import math
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import py7zr
from scipy.io import loadmat


REPO = Path(__file__).resolve().parents[1]
CACHE = REPO.parent / "CODEX_WEBS_ARTELNICS" / "backups" / "licensed-dataset-sources-2026-10-01" / "bearing-ferrara"
ARCHIVE = CACHE / "E2.7z"
SOURCE_URL = "https://data.mendeley.com/public-files/datasets/htk59pp5wx/files/28dc48f9-a72e-43be-a8f9-fabce38f6172/file_downloaded"
SOURCE_SHA256 = "209a6d7692c893b3fc326765d9052cbdb70cbcca8244cd40eaceaa32215f4086"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_archive() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.exists() and file_sha256(ARCHIVE) == SOURCE_SHA256:
        return
    temporary = ARCHIVE.with_suffix(".7z.part")
    urllib.request.urlretrieve(SOURCE_URL, temporary)
    digest = file_sha256(temporary)
    if digest != SOURCE_SHA256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Unexpected E2.7z SHA-256: {digest}")
    temporary.replace(ARCHIVE)


def features(signal: np.ndarray, sampling_frequency: float) -> list[float]:
    signal = np.asarray(signal, dtype=np.float64)
    mean = float(signal.mean())
    centered = signal - mean
    std = float(centered.std())
    rms = float(np.sqrt(np.mean(signal * signal)))
    peak = float(np.max(np.abs(signal)))
    mean_abs = float(np.mean(np.abs(signal)))
    normalized = centered / std if std else np.zeros_like(centered)

    tapered = centered * np.hanning(len(centered))
    spectrum = np.abs(np.fft.rfft(tapered)) ** 2
    frequencies = np.fft.rfftfreq(len(tapered), 1.0 / sampling_frequency)
    total_power = float(spectrum.sum()) or 1.0

    def relative_power(low: float, high: float) -> float:
        mask = (frequencies >= low) & (frequencies < high)
        return float(spectrum[mask].sum() / total_power)

    return [
        mean,
        std,
        rms,
        peak,
        float(np.ptp(signal)),
        mean_abs,
        float(np.mean(normalized**3)),
        float(np.mean(normalized**4)),
        peak / rms if rms else 0.0,
        peak / mean_abs if mean_abs else 0.0,
        rms / mean_abs if mean_abs else 0.0,
        float(np.mean(np.signbit(centered[1:]) != np.signbit(centered[:-1]))),
        float(np.sum(frequencies * spectrum) / total_power),
        relative_power(0, 500),
        relative_power(500, 2_000),
        relative_power(2_000, 5_000),
        relative_power(5_000, 10_000),
        relative_power(10_000, sampling_frequency / 2 + 1),
    ]


def main() -> None:
    ensure_archive()
    output = REPO / "bearinganomalydetection" / "bearing_anomaly_detection.csv"
    header = [
        "mean", "standard_deviation", "rms", "absolute_peak", "peak_to_peak",
        "mean_absolute", "skewness", "kurtosis", "crest_factor",
        "impulse_factor", "shape_factor", "zero_crossing_rate",
        "spectral_centroid_hz", "relative_power_0_500_hz",
        "relative_power_500_2000_hz", "relative_power_2000_5000_hz",
        "relative_power_5000_10000_hz", "relative_power_10000_12800_hz",
        "anomaly",
    ]

    with tempfile.TemporaryDirectory(prefix="extract-e2-", dir=CACHE) as temporary:
        extraction_root = Path(temporary).resolve()
        if CACHE.resolve() not in extraction_root.parents:
            raise RuntimeError("Unsafe extraction directory")
        with py7zr.SevenZipFile(ARCHIVE, mode="r") as archive:
            archive.extractall(path=extraction_root)
        recordings = sorted(
            (extraction_root / "E2").glob("E2_*.mat"),
            key=lambda path: int(path.stem.split("_")[-1]),
        )
        anomaly_start = math.ceil(len(recordings) * 0.9)
        with output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(header)
            for acquisition, path in enumerate(recordings, start=1):
                payload = loadmat(path)
                signal = np.asarray(payload["y"]).ravel()
                sampling_frequency = float(np.asarray(payload["Fs"]).item())
                samples_per_window = round(sampling_frequency)
                anomaly = int(acquisition >= anomaly_start)
                for start in range(0, len(signal) - samples_per_window + 1, samples_per_window):
                    row = features(signal[start:start + samples_per_window], sampling_frequency)
                    writer.writerow([*(f"{value:.10g}" for value in row), anomaly])

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"{output.relative_to(REPO)}: {output.stat().st_size} bytes; SHA-256 {digest}")


if __name__ == "__main__":
    main()
