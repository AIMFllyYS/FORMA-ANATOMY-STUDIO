# Model sources and attribution — not a blanket relicensing statement

This delivered project contains no anatomical mesh binaries. It contains a
viewer, public source locations and a builder. A data-filled derivative HTML
must preserve the notices relevant to the assets actually included.

## Original Z-Anatomy

Z-Anatomy, by Gauthier Kervyn and Marcin Zielinski, incorporating BodyParts3D
and contributions from other creators.

https://github.com/Z-Anatomy/Models-of-human-anatomy

The project identifies a CC BY-SA 4.0 licence for Z-Anatomy. Its original
credits also identify separately licensed component models. Preserve the
original source licence and attribution texts, not just this summary.

Some additional source components are under different licences, including
noncommercial Creative Commons variants. In particular, a “Nervous system
& Sense organs” collection is broader than peripheral motor-system nerves;
its contents must not be automatically assumed to have uniform licences.
The new builder preserves provided source metadata but does not automatically
resolve every component licence. Users intending redistribution must retain
the original source notices and check component-level conditions and permissions;
this document is not legal clearance.

## BodyParts3D

BodyParts3D, © The Database Center for Life Science (DBCLS), CC BY-SA 2.1 Japan.

https://lifesciencedb.jp/bp3d/info_en/index.html

The source notes that concepts are missing and there can be errors relevant
to anatomy education, including artist-created and altered contours. Refer
readers to those notices; do not present the model as a universally exact
patient or a completely audited anatomical specimen.

## Optional browser-reduced derivative assets (standard tier)

Public conversion maintained at:
https://github.com/DrMuratAltun/anatomi-simulatoru

Attribution and derivation:
https://github.com/DrMuratAltun/anatomi-simulatoru/blob/main/ATTRIBUTION.md

This upstream describes systems/*.glb as derived from Z-Anatomy Startup.blend
through collection selection, decimation and glTF export. It identifies the
GLBs as CC BY-SA 4.0 derivatives. The workbench does not claim that a reduced
file preserves all original anatomical detail. It does not adopt the
upstream project's logo, trademark or three.js bundle.

The registry `web/model-sources.json` marks this as the always-available
**standard** tier. The upstream retains roughly 46% / 42% / 18% / 17% / 36% /
11% of the subdivided source for skeletal / joints / muscles / nerves /
organs / vessels respectively (measured in the v4 corpus,
`tools/data/nomenclature_coverage.json` sibling statistics). Muscle detail is
the most reduced and is the primary target of the HD tier.

## balanced / HD self-hosted tiers

`balanced` and `HD` are **not downloaded** by the application. They are
produced locally by `tools/export_blender.py --tier balanced|hd` from the
Z-Anatomy template and must be self-hosted (static release / GitHub Pages /
S3 with CORS). The registry marks them `available:false` until a matching
manifest exists in `models/manifests/`. Files are `.glb.gz` and the client
inflates them with `DecompressionStream` when the server does not send
`Content-Encoding: gzip`.

- Both tiers remain CC BY-SA 4.0 derivatives; the BodyParts3D attribution
  chain still applies.
- Nodes carry `extras.anatomyId`, `extras.side`, `extras.tier`,
  `extras.source_name` and evaluated triangle stats so the nomenclature layer
  and SHA-based cache can bind to them without guessing.
- `.j` empty objects, `.g` text objects and trailing-apostrophe
  not-modelled markers are filtered out and never exported as tissue.
- HD target (AC-6): muscles / cardiovascular / nerves triangle counts ≥ 2×
  the standard tier, verified against `models/manifests/*.json`, not assumed.
- Educational content is not a complete anatomical model and is not
  biomechanically certified; see the runtime boundary notices.

For locally supplied files, the importer records their filename and SHA-256,
but this is not evidence that the user owns redistribution rights. Cached
assets are isolated by SHA-256, so switching tiers never mixes models.

## Geometry transformations and appearance

The original Blender route evaluates source geometry and performs a declared
axis conversion without adding a decimation modifier. Normals and triangles
are exported as source-derived surface data. Teaching colours in the viewer
replace source material appearance. Mesh surface patches and exploded views
are study aids; patches remain unreviewed until actual expert validation.

## Forma 3.0 changes

This release also offers organs, vessels and lymph-system endpoints from the
same public upstream. Actual downloaded bytes and SHA-256 are recorded at
runtime. The online URLs follow the upstream branch and are not an immutable
model revision. A different hash must not inherit old surface annotations.

The local learning cards were adapted from the user's preceding project text
and expanded as study notes. They are not peer-reviewed anatomical nomenclature
or a licensed third-party atlas reproduced in full. Reference links accompany
relevant cards; preserve those links and review their content before reliance.
Some source readings have their own Creative Commons/noncommercial conditions;
the code's MIT licence is not a blanket relicence of model or reference content.

The optional Node server uses Vercel AI SDK dependencies under their upstream
licences. Dependencies are declared, not vendored; preserve npm package notices
when deploying. No fonts or external anatomical mesh binaries are in this ZIP.
