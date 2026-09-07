# Neural Designer — Example Models

Collection of example datasets and pre-trained models distributed by [Neural Designer](https://www.neuraldesigner.com) as built-in examples.

Each folder is a self-contained example with:

- `<id>.nd` — model file
- the source dataset, under its own name

## Release contract

The Neural Designer desktop application downloads each example on demand from
this repository's GitHub Releases. The URL pattern is:

```
https://github.com/Artelnics/neuraldesigner-models/releases/download/<tag>/<id>.zip
```

Every release asset is a ZIP holding `<id>.nd` at its root, plus the source
dataset beside it when the model does not already carry a copy. The application
extracts it into `<ExamplesRoot>/<id>/`, and resolves the dataset path recorded
inside the model against that folder, so the CSV only has to keep the file name
the model refers to.

## Current tag

Latest release: `v3.0.0`.
