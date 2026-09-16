# User-supplied source models

No anatomical binaries are included in the initial release. Import your previous
data-filled offline HTML or supply uncompressed static GLBs. Keep each source
asset's licence, author, revision and SHA-256; do not assume a public repository
means unrestricted use. `tools/build.py --input-dir PATH` accepts a manifest.json:

```json
{
  "assets": [
    {
      "filename": "your_source_model.glb",
      "category": "skeletal",
      "sourceURL": "https://your-source.example/model",
      "license": "EXACT SOURCE LICENCE REQUIRED",
      "quality": "Describe actual provenance and any upstream simplification"
    }
  ]
}
```

This is a schema example, not an included or verified anatomical source.
