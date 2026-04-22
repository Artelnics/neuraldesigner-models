# Neural Designer — Example Models

Collection of example datasets and pre-trained models distributed by [Neural Designer](https://www.neuraldesigner.com) as built-in examples.

Each folder is a self-contained example with:

- `<id>.ndm` — model definition (Neural Designer XML)
- `<id>.csv` — source dataset
- `<id>_Data.bin` — cached dataset
- `<id>_Params.bin` — trained parameters

## Release contract

The Neural Designer desktop application downloads each example on demand from
this repository's GitHub Releases. The URL pattern is:

```
https://github.com/Artelnics/neuraldesigner-models/releases/download/<tag>/<id>.zip
```

Every release asset must be a ZIP containing a single top-level folder named
`<id>/`, so that extracting with `tar -xf` produces `<id>/<id>.ndm` etc.

## Adding a new example

See `neuraleditor/ADDING_EXAMPLES.md` in the Neural Designer source repository
for the full step-by-step workflow (UI button, catalog entry, zip packaging,
release upload).

## Current tag

Latest release: `v1.0.0` — 56 examples.
