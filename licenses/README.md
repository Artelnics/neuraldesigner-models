# Dataset license notices

The example archives are downloaded independently from GitHub Releases rather
than installed with Neural Designer. Dataset notices therefore belong in each
example archive, not only in the Neural Designer installer license directory.

For every redistributable third-party dataset:

1. Add `LICENSES/DATASET-LICENSE.txt` to the example source directory.
2. Include that `LICENSES` directory unchanged in the corresponding release
   ZIP, whether the dataset is a separate file or embedded in `<id>.nd`.
3. Identify the dataset, publisher/licensor, canonical source URL, license name
   and license URL.
4. Describe filtering, relabelling, format conversion, or other material
   changes made by Artelnics.
5. Preserve any upstream notices and comply with attribution, share-alike,
   source-availability, or other license-specific requirements.

For an ODbL derivative database, include the derivative dataset as a separate
machine-readable file in the archive even if the `.nd` model also embeds it.
This makes the source-availability obligation explicit and lets recipients use
the database independently of Neural Designer.

The Neural Designer end-user license applies to the software and Artelnics-owned
parts of an example. It does not replace or restrict the license granted by an
upstream dataset licensor.

Use [`DATASET-LICENSE.template.txt`](DATASET-LICENSE.template.txt) when adding a
new notice. A URL to the full legal text may be used when the dataset license
expressly permits a URI instead of bundling a complete copy. Bundle the full
text whenever the applicable license requires it.

ODbL/DbCL examples include offline copies of both license texts, the
GPL-licensed example includes the complete GPL 2.0 text, and the LGPL-licensed
example includes the complete LGPL 2.0 text, in their own `LICENSES`
directories.
