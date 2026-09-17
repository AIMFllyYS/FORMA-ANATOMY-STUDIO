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

## balanced / HD tiers (self-hosted, Z-Anatomy re-export)

The app ships the **standard** tier only. To enable `balanced` / `HD`:

1. Install Blender (≥ 3.x, headless supported) and download the Z-Anatomy
   `Startup.blend` (or `Z-Anatomy.zip`) — **not** redistributed here.
2. Export all seven systems at a tier (the script evaluates source geometry,
   filters `.j/.g/'` special objects, writes `anatomyId/side/tier` extras and a
   per-run manifest; it does not auto-decimate, so choose source collections /
   apply your own documented reduction before invoking when targeting a budget):

   ```bash
   blender -b Startup.blend --python tools/export_blender.py -- \
     --output models/hd --tier hd
   blender -b Startup.blend --python tools/export_blender.py -- \
     --output models/balanced --tier balanced
   ```

3. Compress each GLB and place manifests where the build expects them:

   ```bash
   gzip -n models/hd/*.glb && mv models/hd/*.glb.gz models/
   cp models/hd/manifest.json models/manifests/hd.json
   ```

4. Host `models/*.glb.gz` over HTTPS with permissive CORS (GitHub Releases /
   Pages / S3). Point the app at them by setting custom tier bases (localStorage
   key `forma-model-bases-v1`) or editing `web/model-sources.json` `bases` and
   flipping `available:true`, then rebuild.

5. Verify AC-6 against the manifest: HD muscles / vessels / nerves triangle
   counts must be ≥ 2× the standard tier. If a tier fails the budget, keep its
   registry `available:false`; the UI labels it as needing self-hosting rather
   than pretending it exists.

All tiers are CC BY-SA 4.0 derivatives carrying the BodyParts3D attribution
chain; see `licenses/SOURCE_NOTICES.md`. Real-machine frame rates (AC-12) must
be measured on representative hardware before advertising a tier as ≥30 fps.
