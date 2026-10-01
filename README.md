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
dataset beside it when the model does not already carry a copy. A separate
machine-readable dataset must also be included when its license requires source
availability, even if the model embeds the data. The application extracts the
asset into `<ExamplesRoot>/<id>/`, and resolves the dataset path recorded inside
the model against that folder, so the dataset only has to keep the file name the
model refers to.

Third-party dataset licensing material must travel in the same ZIP as the
example, including when the dataset is embedded in the `.nd` file. Assets that
use third-party data must therefore also contain:

```
LICENSES/DATASET-LICENSE.txt
```

The notice identifies the dataset and source, states the applicable license(s),
records material changes, and provides the attribution required for
redistribution. See [`licenses/README.md`](licenses/README.md) for the packaging
rules and template.

## Current tag

Latest release: `v3.0.0`.
