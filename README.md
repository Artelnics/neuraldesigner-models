# Neural Designer — Example Models

Collection of example datasets and pre-trained models distributed by [Neural Designer](https://www.neuraldesigner.com) as built-in examples.

Each folder is a self-contained example with:

- `<id>.nd` — model file
- `<id>.csv` — dataset

## Release contract

The Neural Designer desktop application downloads each example on demand from
this repository's GitHub Releases. The URL pattern is:

```
https://github.com/Artelnics/neuraldesigner-models/releases/download/<tag>/<id>.zip
```

Every release asset must be a ZIP containing a single top-level folder named
`<id>/`, so that extracting with `tar -xf` produces `<id>/<id>.ndm` etc.

## Current tag

Latest release: `v1.0.0` — 56 examples.
