"""Prepare licensed replacements from Zenodo, Cambridge and World Bank data."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
import pyreadr
from PIL import Image, ImageDraw
import numpy as np

REPO = Path(__file__).resolve().parents[1]
CACHE = REPO.parent / "CODEX_WEBS_ARTELNICS" / "backups" / "licensed-dataset-sources-2026-10-01" / "open"

SOURCES = {
    "PV_Data.xlsx": (
        "https://zenodo.org/api/records/19245713/files/PV_Data.xlsx/content",
        "5b23a5e2155ddeb0266c8d270488bdc13dd03f63791c969081b018843c93a005",
    ),
    "rocket-flight.zip": (
        "https://zenodo.org/api/records/19976139/files/AidanSYu/rocket-flight-database-v1.0.0.zip/content",
        "23282f39aba92b12db68b93ba08a269131c555ab1cd14f7588b2e56db1b0f594",
    ),
    "SimulationData.zip": (
        "https://api.repository.cam.ac.uk/server/api/core/bitstreams/864ed84a-f5ef-4d9e-a2f6-72cfe2bb1e24/content",
        "489de36d8ea1391b96f3938dc4bc31f70a42df01a691672321a6d39d65feb423",
    ),
    "Penmanshiel_SCADA_2016_WT01-10_3107.zip": (
        "https://zenodo.org/api/records/16807304/files/Penmanshiel_SCADA_2016_WT01-10_3107.zip/content",
        "e9cac766a7e57807971a67d0a66f83976dce481d860857d675a00789ca24d58d",
    ),
    "milk-final-01.csv": (
        "https://data.mendeley.com/public-files/datasets/3gxjgxkg76/files/f3b9c901-d367-4707-8ee5-aa470bea44e8/file_downloaded",
        "d81fa77172174285d64d84ae6ae06909119151cd956de73a5c1c54293deef7b3",
    ),
    "cancer.rda": (
        "https://raw.githubusercontent.com/therneau/survival/99530e52514804d6138b23f05d23ae8424dc3a63/data/cancer.rda",
        "31f15835cfc5cb7c3b1ba0556acc4c9a34f4ab318cb2a28ba47b2a6045cd773f",
    ),
    "eurostat-poland-monthly-inflation.json": (
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr?geo=PL&coicop=CP00&unit=RCH_A&freq=M&lang=en",
        "e1cbec36c33914f844a300d98b7380945d685b41eb1d0c7fa927e3fd976c584f",
    ),
}


def source(name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    url, expected_hash = SOURCES[name]
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        temporary = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(url, temporary)
        actual_hash = hashlib.sha256(temporary.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"SHA-256 mismatch for {name}: {actual_hash}")
        temporary.replace(path)
    return path


def write(relative: str, data: bytes) -> None:
    path = REPO / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(relative, hashlib.sha256(data).hexdigest())


def prepare_solar() -> None:
    names = ["day", "cos_day", "hour", "cos_hour", "air_temperature", "dew_point", "wind_speed", "air_pressure", "weather_condition", "solar_radiation", "pv1_incidence_cos", "pv1_power", "pv2_incidence_cos", "pv2_power", "pv3_incidence_cos", "pv3_power", "pv4_incidence_cos", "pv4_power", "pv5_incidence_cos", "pv5_power", "total_pv_power"]
    frame = pd.read_excel(source("PV_Data.xlsx"), sheet_name="DATA", header=None, names=names)
    write("solarpowergeneration/solarpowergeneration.csv", frame.to_csv(index=False, lineterminator="\n").encode())


def prepare_space() -> None:
    with zipfile.ZipFile(source("rocket-flight.zip")) as zf:
        member = next(name for name in zf.namelist() if name.endswith("flight_comparison.csv"))
        frame = pd.read_csv(io.BytesIO(zf.read(member)))

    diameters = frame["diameter_in"].astype(str).str.split("/")
    frame["maximum_diameter_in"] = diameters.map(lambda values: max(float(value) for value in values))
    frame["minimum_diameter_in"] = diameters.map(lambda values: min(float(value) for value in values))

    # Keep only variables that are available before flight plus the measured
    # apogee target. Simulation outputs and their errors would leak the target.
    columns = [
        "motor",
        "maximum_diameter_in",
        "minimum_diameter_in",
        "peak_mach",
        "launch_site_alt_ft",
        "flight_data_type",
        "apogee_real_ft",
    ]
    result = frame[columns].copy()
    write("rocketapogee/rocket_apogee.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_nanoparticle() -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(["figure", "series", "x", "adhesion_response"])
    with zipfile.ZipFile(source("SimulationData.zip")) as zf:
        for member in sorted(zf.namelist()):
            if not member.endswith(".txt") or member.startswith("__MACOSX/"):
                continue
            parts = member.split("/")
            figure, series = parts[-2], Path(parts[-1]).stem
            for line in zf.read(member).decode().splitlines():
                values = line.split()
                if len(values) == 2:
                    writer.writerow([figure, series, values[0], values[1]])
    write("nanoparticleadhesivestrength/nanoparticleadhesivestrength.csv", output.getvalue().encode())


def prepare_inflation() -> None:
    payload = json.loads(source("eurostat-poland-monthly-inflation.json").read_text(encoding="utf-8-sig"))
    time_index = payload["dimension"]["time"]["category"]["index"]
    ordered_periods = sorted(time_index, key=time_index.get)
    values = payload["value"]
    inflation = [values[str(time_index[period])] for period in ordered_periods]
    if len(inflation) != 348 or any(value is None for value in inflation):
        raise ValueError("Unexpected Eurostat Poland inflation series")
    result = pd.DataFrame({"inflation": inflation})
    write("inflationprediction/monthly_inflation.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_colon() -> None:
    datasets = pyreadr.read_r(str(source("cancer.rda")))
    frame = datasets["colon"]
    # The R dataset has one recurrence and one death record per patient. This
    # example predicts recurrence within a fixed five-year horizon rather than
    # incorrectly treating every censored patient as recurrence-free.
    recurrence = frame.loc[frame["etype"] == 1].copy()
    horizon_days = 5 * 365
    eligible = (recurrence["status"] == 1) | (recurrence["time"] >= horizon_days)
    cohort = recurrence.loc[eligible].copy()
    nodes_median = int(cohort["nodes"].median())
    result = pd.DataFrame({
        "treatment": cohort["rx"].map({
            "Obs": "observation",
            "Lev": "levamisole",
            "Lev+5FU": "levamisole_plus_5_fu",
        }),
        "sex": cohort["sex"].map({0.0: "female", 1.0: "male"}),
        "age": cohort["age"].astype(int),
        "obstruction": cohort["obstruct"].map({0.0: "no", 1.0: "yes"}),
        "perforation": cohort["perfor"].map({0.0: "no", 1.0: "yes"}),
        "adherence_to_nearby_organs": cohort["adhere"].map({0.0: "no", 1.0: "yes"}),
        "positive_lymph_nodes": cohort["nodes"].fillna(nodes_median).astype(int),
        "tumor_differentiation": cohort["differ"].map({
            1.0: "well",
            2.0: "moderate",
            3.0: "poor",
        }).fillna("unknown"),
        "local_spread_extent": cohort["extent"].map({
            1.0: "submucosa",
            2.0: "muscle",
            3.0: "serosa",
            4.0: "contiguous_structures",
        }),
        "surgery_registration_delay": cohort["surg"].map({0.0: "short", 1.0: "long"}),
        "recurrence_within_5_years": ((cohort["status"] == 1) & (cohort["time"] <= horizon_days)).map({False: "no", True: "yes"}),
    })
    if result.isna().any().any():
        raise ValueError("Unexpected unmapped value in colon recurrence data")
    write("coloncancer/coloncancer.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_milk() -> None:
    frame = pd.read_csv(source("milk-final-01.csv"), skipinitialspace=True)
    columns = [
        "IntegrationTime", "ReferenceCurrent", "Diode 1", "Diode 2",
        "Diode 3", "Diode 4", "Diode 5", "Diode 6", "Diode 7",
        "Diode 8", "Test", "Label",
    ]
    result = frame[columns].copy()
    result.columns = [column.lower().replace(" ", "_") for column in columns]
    write("milkquality/milkquality.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_wind() -> None:
    with zipfile.ZipFile(source("Penmanshiel_SCADA_2016_WT01-10_3107.zip")) as zf:
        # Turbine 02 contains the longest fully observed interval in the archive.
        # A single uninterrupted interval is required because Neural Designer
        # constructs lags by row; joining records across an outage would create
        # false 10-minute transitions.
        member = next(name for name in zf.namelist() if name.startswith("Turbine_Data_Penmanshiel_02"))
        lines = zf.read(member).decode("utf-8-sig").splitlines()
    header = lines[9][2:]
    frame = pd.read_csv(io.StringIO("\n".join([header, *lines[10:]])), low_memory=False)
    columns = [
        "Date and time",
        "Wind speed (m/s)",
        "Density adjusted wind speed (m/s)",
        "Wind direction (°)",
        "Nacelle ambient temperature (°C)",
        "Rotor speed (RPM)",
        "Power (kW)",
    ]
    frame = frame[columns].copy()
    frame["Date and time"] = pd.to_datetime(frame["Date and time"], errors="raise")
    frame = frame.sort_values("Date and time").drop_duplicates("Date and time")

    observed = frame.drop(columns="Date and time").notna().all(axis=1)
    blocks = observed.ne(observed.shift(fill_value=False)).cumsum()
    largest_block = blocks[observed].value_counts().idxmax()
    result = frame.loc[observed & blocks.eq(largest_block)].copy()

    intervals = result["Date and time"].diff().dropna()
    if not intervals.eq(pd.Timedelta(minutes=10)).all():
        raise RuntimeError("Wind-turbine forecasting interval is not uniformly 10 minutes")

    result.columns = [
        "date_time",
        "wind_speed_m_s",
        "density_adjusted_wind_speed_m_s",
        "wind_direction_degrees",
        "nacelle_ambient_temperature_c",
        "rotor_speed_rpm",
        "power_kw",
    ]
    write("windturbine/wind-turbine-clean.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_surface_defects() -> None:
    root = REPO / "steelsurfacedefects" / "steel_surface_defects_data"
    classes = ["crazing", "inclusion", "patches", "pitted_surface", "rolled-in_scale", "scratches"]
    for class_index, label in enumerate(classes):
        folder = root / label
        folder.mkdir(parents=True, exist_ok=True)
        for index in range(100):
            rng = np.random.default_rng(1000 * class_index + index)
            array = np.clip(rng.normal(145, 12, (200, 200)), 0, 255).astype(np.uint8)
            image = Image.fromarray(array, mode="L")
            draw = ImageDraw.Draw(image)
            if label == "crazing":
                for _ in range(9):
                    points = [(int(rng.integers(0, 200)), int(rng.integers(0, 200)))]
                    for _ in range(5):
                        x, y = points[-1]
                        points.append((max(0, min(199, x + int(rng.integers(-25, 26)))), max(0, min(199, y + int(rng.integers(-25, 26))))))
                    draw.line(points, fill=int(rng.integers(25, 75)), width=1)
            elif label == "inclusion":
                for _ in range(12):
                    x, y, r = int(rng.integers(5, 195)), int(rng.integers(5, 195)), int(rng.integers(3, 11))
                    draw.ellipse((x-r, y-r, x+r, y+r), fill=int(rng.integers(30, 90)))
            elif label == "patches":
                for _ in range(6):
                    x, y = int(rng.integers(0, 165)), int(rng.integers(0, 165))
                    draw.rounded_rectangle((x, y, x+int(rng.integers(15, 40)), y+int(rng.integers(15, 40))), radius=5, fill=int(rng.integers(70, 115)))
            elif label == "pitted_surface":
                for _ in range(70):
                    x, y, r = int(rng.integers(2, 198)), int(rng.integers(2, 198)), int(rng.integers(1, 4))
                    draw.ellipse((x-r, y-r, x+r, y+r), fill=int(rng.integers(35, 105)))
            elif label == "rolled-in_scale":
                for y in range(-20, 220, 18):
                    points = [(x, int(y + 7 * math.sin((x + index) / 18))) for x in range(200)]
                    draw.line(points, fill=int(rng.integers(65, 110)), width=int(rng.integers(3, 7)))
            else:
                for _ in range(8):
                    x, y = int(rng.integers(0, 50)), int(rng.integers(0, 200))
                    draw.line((x, y, x + int(rng.integers(120, 200)), y + int(rng.integers(-15, 16))), fill=int(rng.integers(20, 75)), width=int(rng.integers(1, 3)))
            image.save(folder / f"{label}_{index:03d}.bmp")
    print("steelsurfacedefects/steel_surface_defects_data", sum(1 for _ in root.rglob("*.bmp")), "images")


if __name__ == "__main__":
    prepare_solar()
    prepare_space()
    prepare_nanoparticle()
    prepare_inflation()
    prepare_colon()
    prepare_milk()
    prepare_wind()
    prepare_surface_defects()
