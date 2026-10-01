"""Build licensed replacement datasets from pinned UCI archives.

Run from any directory. Downloads are cached outside the repository and all
derived CSV files are written under neuraldesigner-models using legacy names
expected by the existing projects. The projects must be rebuilt afterwards.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


REPO = Path(__file__).resolve().parents[1]
CACHE = REPO.parent / "CODEX_WEBS_ARTELNICS" / "backups" / "licensed-dataset-sources-2026-10-01" / "uci"

ARCHIVES = {
    "ai4i.zip": ("https://archive.ics.uci.edu/static/public/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bdataset.zip", "f601f14294bcf190f9d720676b7f0aea46a26cde9ab8ebc7b4f8174d9d26b252"),
    "diabetes.zip": ("https://archive.ics.uci.edu/static/public/529/early%2Bstage%2Bdiabetes%2Brisk%2Bprediction%2Bdataset.zip", "67594c0f11257688b57493798e70737b7156ba37a2e6ac75507ae3a35221a388"),
    "retinopathy.zip": ("https://archive.ics.uci.edu/static/public/329/diabetic%2Bretinopathy%2Bdebrecen.zip", "64ee2dbaffc69dab77cc0fb7458fa93cb21a20f15938cafacdc195a5e2226b2c"),
    "rna-seq.zip": ("https://archive.ics.uci.edu/static/public/401/gene%2Bexpression%2Bcancer%2Brna%2Bseq.zip", "06bbb28393ed85b4365f461f20ad75996f2579af4a047945c038ec27386e3bfb"),
    "primary-tumor.zip": ("https://archive.ics.uci.edu/static/public/83/primary%2Btumor.zip", "d866e8d1f358cdd51233982d4ab0680a19a6fd46be0517b5686196e5fa3c33f3"),
    "sales-weekly.zip": ("https://archive.ics.uci.edu/static/public/396/sales%2Btransactions%2Bdataset%2Bweekly.zip", "dededa20f199af8f2bb96184bb1696befda902849a700bde283fe763afc90ba9"),
    "htru2.zip": ("https://archive.ics.uci.edu/static/public/372/htru2.zip", "ba442c076dd22a8952700f26e38499fc1806037dcf7bea0e125e6bfba393f379"),
    "iranian-churn.zip": ("https://archive.ics.uci.edu/static/public/563/iranian%2Bchurn%2Bdataset.zip", "696c3a1812267980751f30d19193a1b430ac4ad76172bb089e664c96813ead66"),
    "beijing-air.zip": ("https://archive.ics.uci.edu/static/public/501/beijing%2Bmulti%2Bsite%2Bair%2Bquality%2Bdata.zip", "b04da438b2f331ac0ffd45aebdfec0d20d2367feb5f6948c4b1f7ce1191e33c4"),
    "default-credit.zip": ("https://archive.ics.uci.edu/static/public/350/default%2Bof%2Bcredit%2Bcard%2Bclients.zip", "56c885f84457f6680f8438f02bfcdac9579323d8a94465ee5f26e32baa727602"),
}


def archive(name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    url, expected = ARCHIVES[name]
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Hash mismatch for {name}: {actual}")
    return path


def zip_bytes(name: str, member: str) -> bytes:
    with zipfile.ZipFile(archive(name)) as zf:
        return zf.read(member)


def write_bytes(relative: str, data: bytes) -> None:
    path = REPO / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(relative, hashlib.sha256(data).hexdigest())


def normalize_csv_bytes(data: bytes) -> bytes:
    text = data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def prepare_ai4i() -> None:
    data = normalize_csv_bytes(zip_bytes("ai4i.zip", "ai4i2020.csv"))
    write_bytes("machinefailureprediction/machine_failure.csv", data)


def prepare_diabetes() -> None:
    data = normalize_csv_bytes(zip_bytes("diabetes.zip", "diabetes_data_upload.csv"))
    write_bytes("diabetesprognosis/diabetesprognosis.csv", data)


def prepare_retinopathy() -> None:
    text = zip_bytes("retinopathy.zip", "messidor_features.arff").decode("utf-8")
    rows = [line for line in text.splitlines() if line and not line.startswith("@")]
    names = ["quality", "pre_screening"] + [f"ma{i}" for i in range(1, 7)] + [f"exudate{i}" for i in range(1, 9)] + ["macula_optic_disc_distance", "optic_disc_diameter", "am_fm_classification", "class"]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(names)
    writer.writerows(csv.reader(rows))
    write_bytes("diabeticretinopathy/diabeticretinopathy.csv", output.getvalue().encode())


def prepare_rna_seq() -> None:
    with zipfile.ZipFile(archive("rna-seq.zip")) as outer:
        payload = outer.read("TCGA-PANCAN-HiSeq-801x20531.tar.gz")
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tf:
        data_member = tf.extractfile("TCGA-PANCAN-HiSeq-801x20531/data.csv")
        labels_member = tf.extractfile("TCGA-PANCAN-HiSeq-801x20531/labels.csv")
        if data_member is None or labels_member is None:
            raise ValueError("RNA-Seq archive members missing")
        data = pd.read_csv(data_member, index_col=0)
        labels = pd.read_csv(labels_member, index_col=0)
    if not data.index.equals(labels.index):
        raise ValueError("RNA-Seq sample identifiers do not align")
    # Keep the 1,000 most variable genes, ordered by original gene number.
    selected = list(data.var(axis=0).nlargest(1000).index)
    selected.sort(key=lambda value: int(value.split("_")[1]))
    result = data[selected].copy()
    result["class"] = labels["Class"]
    output = result.to_csv(index_label="sample", lineterminator="\n").encode()
    write_bytes("cancertypeclassification/cancer_type_gene_expression.csv", output)


def prepare_primary_tumor() -> None:
    rows = list(csv.reader(io.StringIO(zip_bytes("primary-tumor.zip", "primary-tumor.data").decode())))
    names = ["class", "age", "sex", "histologic_type", "degree_of_differentiation", "bone", "bone_marrow", "lung", "pleura", "peritoneum", "liver", "brain", "skin", "neck", "supraclavicular", "axillar", "mediastinum", "abdominal"]
    domains = {
        "class": ["lung", "head_and_neck", "esophagus", "thyroid", "stomach", "duodenum_and_small_intestine", "colon", "rectum", "anus", "salivary_glands", "pancreas", "gallbladder", "liver", "kidney", "bladder", "testis", "prostate", "ovary", "corpus_uteri", "cervix_uteri", "vagina", "breast"],
        "age": ["under_30", "30_to_59", "60_or_over"],
        "sex": ["male", "female"],
        "histologic_type": ["epidermoid", "adeno", "anaplastic"],
        "degree_of_differentiation": ["well", "fairly", "poorly"],
    }
    yes_no_columns = names[5:]

    decoded_rows = []
    for row in rows:
        decoded = []
        for column, value in zip(names, row):
            if value == "?":
                decoded.append(value)
            elif column in domains:
                decoded.append(domains[column][int(value) - 1])
            elif column in yes_no_columns:
                decoded.append(["yes", "no"][int(value) - 1])
            else:
                raise ValueError(f"No domain mapping for {column}")
        decoded_rows.append(decoded)

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(names)
    writer.writerows(decoded_rows)
    write_bytes("primarytumor/primary_tumor.csv", output.getvalue().encode())


def prepare_sales() -> None:
    source = pd.read_csv(io.BytesIO(zip_bytes("sales-weekly.zip", "Sales_Transactions_Dataset_Weekly.csv")))
    weekly_columns = [f"W{index}" for index in range(52)]
    # Neural Designer creates lags and forecasting targets internally. Preserve
    # chronological order and expose only the aggregate weekly sales series.
    result = pd.DataFrame({"sales": source[weekly_columns].sum(axis=0).to_numpy(dtype=int)})
    write_bytes("pharmasales/pharmasales.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_htru2() -> None:
    raw = zip_bytes("htru2.zip", "HTRU_2.csv").decode().replace("\r", "\n")
    rows = [row for row in csv.reader(io.StringIO(raw)) if row]
    names = ["profile_mean", "profile_stdev", "profile_skewness", "profile_kurtosis", "dm_mean", "dm_stdev", "dm_skewness", "dm_kurtosis", "class"]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(names)
    writer.writerows(rows)
    write_bytes("pulsardetection/pulsar_candidates.csv", output.getvalue().encode())


def prepare_churn() -> None:
    data = normalize_csv_bytes(zip_bytes("iranian-churn.zip", "Customer Churn.csv"))
    write_bytes("telecommunicationschurn/telecommunicationschurn.csv", data)


def prepare_credit_default() -> None:
    with zipfile.ZipFile(archive("default-credit.zip")) as zf:
        frame = pd.read_excel(io.BytesIO(zf.read("default of credit card clients.xls")), header=1)
    frame = frame.rename(columns={frame.columns[-1]: "default_payment_next_month"})
    write_bytes("creditdefault/credit_default.csv", frame.to_csv(index=False, lineterminator="\n").encode())


def prepare_no2() -> None:
    with zipfile.ZipFile(archive("beijing-air.zip")) as outer:
        inner_data = outer.read("PRSA2017_Data_20130301-20170228.zip")
    with zipfile.ZipFile(io.BytesIO(inner_data)) as inner:
        member = "PRSA_Data_20130301-20170228/PRSA_Data_Aotizhongxin_20130301-20170228.csv"
        frame = pd.read_csv(inner.open(member))
    timestamps = pd.to_datetime(frame[["year", "month", "day", "hour"]])
    if timestamps.duplicated().any() or not timestamps.diff().dropna().eq(pd.Timedelta(hours=1)).all():
        raise ValueError("Aotizhongxin source is not a continuous hourly series")
    # Neural Designer creates lags and forecasting targets internally. Keep all
    # hours and interpolate only the missing NO2 measurements so the series is
    # continuous and is detected as numeric rather than categorical.
    result = frame[["NO2"]].copy()
    result["NO2"] = result["NO2"].interpolate(method="linear", limit_direction="both")
    if result["NO2"].isna().any():
        raise ValueError("NO2 interpolation left missing values")
    write_bytes("NO2forecasting/beijingNO2forecasting.csv", result.to_csv(index=False, lineterminator="\n").encode())


def prepare_coupled_pendulums() -> None:
    g, length, mass, coupling, damping, dt = 9.81, 1.0, 1.0, 0.8, 0.03, 0.01
    state = np.array([0.35, -0.20, 0.0, 0.0], dtype=float)

    def derivative(value: np.ndarray) -> np.ndarray:
        t1, t2, w1, w2 = value
        scale = coupling / (mass * length * length)
        return np.array([w1, w2, -g / length * math.sin(t1) - scale * (t1 - t2) - damping * w1, -g / length * math.sin(t2) - scale * (t2 - t1) - damping * w2])

    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(["time", "theta_1", "theta_2", "omega_1", "omega_2"])
    for index in range(10000):
        writer.writerow([f"{index * dt:.2f}", *(f"{value:.10f}" for value in state)])
        k1 = derivative(state)
        k2 = derivative(state + dt * k1 / 2)
        k3 = derivative(state + dt * k2 / 2)
        k4 = derivative(state + dt * k3)
        state = state + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    write_bytes("coupledpendulums/coupledpendulums.csv", output.getvalue().encode())


def main() -> None:
    for function in [prepare_ai4i, prepare_diabetes, prepare_retinopathy, prepare_rna_seq, prepare_primary_tumor, prepare_sales, prepare_htru2, prepare_churn, prepare_credit_default, prepare_no2, prepare_coupled_pendulums]:
        function()


if __name__ == "__main__":
    main()
