# Bearing dataset derivation

The distributed CSV is an adaptation of experiment `E2` from *Run-to-failure
vibration dataset of self-aligning double-row ball bearings - Part 1*, by
Alberto Gabrielli, Luca Arpa, Mattia Battarra and Emiliano Mucchi.

- Canonical record: https://data.mendeley.com/datasets/htk59pp5wx/1
- DOI: `10.17632/htk59pp5wx.1`
- License: Creative Commons Attribution 4.0 International
- Source file: `E2.7z`, 1,968,022,214 bytes
- Source SHA-256: `209A6D7692C893B3FC326765D9052CBDB70CBCCA8244CD40EACEAA32215F4086`

`E2` contains 1,985 acquisitions from one complete accelerated run-to-failure
test. Each acquisition is a five-second radial-acceleration signal sampled at
25.6 kHz. The transformation divides each acquisition into five
non-overlapping one-second windows and produces one CSV row per window.

The 18 input features comprise mean, standard deviation, RMS, absolute peak,
peak-to-peak amplitude, mean absolute amplitude, skewness, kurtosis, crest,
impulse and shape factors, zero-crossing rate, spectral centroid, and relative
power in five frequency bands spanning 0–12.8 kHz.

The original dataset does not contain a binary anomaly annotation. For this
teaching example, Artelnics defines windows from the final 10% of acquisitions
as `anomaly=1`; earlier windows are `anomaly=0`. Consequently this target is a
derived proximity-to-failure label and must not be represented as an annotation
made or validated by the original authors.

The complete transformation, including download URL and hash verification, is
implemented in `tools/prepare-bearing-replacement.py` at repository level.
