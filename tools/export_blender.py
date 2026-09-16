"""Executed INSIDE Blender by build.py. Does not modify or save the .blend file.
Exports evaluated, static, uncompressed GLB geometry with source object names.
No decimation modifier is added; existing source modifiers are evaluated as-is.
Primary target: original Z-Anatomy template, source collections below.

This exporter needs end-to-end verification against the downloaded source; that
verification was not possible in the artifact-authoring environment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
import bpy
import numpy as np

SYSTEMS = {
    "skeletal": "1: Skeletal system",
    "joints": "3: Joints",
    "muscles": "4: Muscular system",
    "nerves": "7: Nervous system & Sense organs",
}
COLORS = {"skeletal": [0.79, 0.75, 0.63, 1], "joints": [0.48, 0.69, 0.73, 1],
          "muscles": [0.70, 0.37, 0.33, 1], "nerves": [0.80, 0.64, 0.23, 1]}


class GLBWriter:
    def __init__(self, category: str):
        self.category = category
        self.binary = bytearray()
        self.gltf = {"asset": {"version": "2.0", "generator": "Source Mesh Workbench / evaluated source without additional decimation"},
                     "scene": 0, "scenes": [{"name": SYSTEMS[category], "nodes": []}],
                     "nodes": [], "meshes": [], "accessors": [], "bufferViews": [], "buffers": [],
                     "materials": [{"name": "Pedagogical palette, not specimen texture", "pbrMetallicRoughness": {"baseColorFactor": COLORS[category], "metallicFactor": 0, "roughnessFactor": 0.72}, "doubleSided": True}],
                     "extras": {"geometry": "Evaluated source meshes; no additional decimation; source modifiers preserved.",
                                "units": "Source Blender world coordinates transformed from Z-up to glTF Y-up (x,z,-y), no rescaling. Physical specimen calibration NOT verified.",
                                "anatomical_review": "NOT PERFORMED; not certified complete or 1:1 with human anatomy.",
                                "material_change": "Original materials/textures replaced by a teaching palette; surface topology retained.",
                                "source_blender_version": bpy.app.version_string,
                                "scene_unit_settings": {"system": bpy.context.scene.unit_settings.system, "scale_length": bpy.context.scene.unit_settings.scale_length}}}

    def accessor(self, data: np.ndarray, component: int, typ: str, target: int, bounds: bool = False) -> int:
        while len(self.binary) % 4:
            self.binary.append(0)
        raw = data.tobytes(order="C")
        view = len(self.gltf["bufferViews"])
        self.gltf["bufferViews"].append({"buffer": 0, "byteOffset": len(self.binary), "byteLength": len(raw), "target": target})
        self.binary.extend(raw)
        accessor = {"bufferView": view, "componentType": component, "count": int(len(data)), "type": typ}
        if bounds:
            accessor["min"] = data.min(axis=0).astype(float).tolist()
            accessor["max"] = data.max(axis=0).astype(float).tolist()
        index = len(self.gltf["accessors"])
        self.gltf["accessors"].append(accessor)
        return index

    def mesh(self, name: str, positions: np.ndarray, normals: np.ndarray, indices: np.ndarray, extras: dict):
        p = self.accessor(positions.astype("<f4", copy=False), 5126, "VEC3", 34962, True)
        n = self.accessor(normals.astype("<f4", copy=False), 5126, "VEC3", 34962)
        ix = self.accessor(indices.astype("<u4", copy=False).reshape(-1), 5125, "SCALAR", 34963)
        mesh_index = len(self.gltf["meshes"])
        self.gltf["meshes"].append({"name": name, "primitives": [{"attributes": {"POSITION": p, "NORMAL": n}, "indices": ix, "material": 0, "mode": 4}]})
        node = len(self.gltf["nodes"])
        self.gltf["nodes"].append({"name": name, "mesh": mesh_index, "extras": extras})
        self.gltf["scenes"][0]["nodes"].append(node)

    def annotation(self, name: str, content: str, position: list[float], collection_paths: list[str]):
        node = len(self.gltf["nodes"])
        self.gltf["nodes"].append({"name": name, "translation": position,
                                    "extras": {"source_annotation": {"name": name, "text": content,
                                               "kind": "original_source_text_anchor_not_a_segmented_surface", "collection_paths": collection_paths}}})
        self.gltf["scenes"][0]["nodes"].append(node)

    def save(self, path: Path):
        while len(self.binary) % 4:
            self.binary.append(0)
        self.gltf["buffers"] = [{"byteLength": len(self.binary)}]
        js = json.dumps(self.gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        js += b" " * (-len(js) % 4)
        length = 12 + 8 + len(js) + 8 + len(self.binary)
        if length >= 2**32:
            raise ValueError("GLB exceeds 4 GB limit; export smaller source collections")
        with path.open("wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, length))
            f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
            f.write(struct.pack("<II", len(self.binary), 0x004E4942)); f.write(self.binary)


def collection_paths() -> dict[int, list[str]]:
    paths: dict[int, list[str]] = {}
    def visit(c, prefix, seen):
        if c.as_pointer() in seen:
            return
        path = prefix + [c.name]
        paths.setdefault(c.as_pointer(), []).append(" / ".join(path))
        for child in c.children:
            visit(child, path, seen | {c.as_pointer()})
    visit(bpy.context.scene.collection, [], set())
    return paths


def show_sources():
    def layer(lc):
        lc.exclude = False
        lc.hide_viewport = False
        for child in lc.children:
            layer(child)
    for vl in bpy.context.scene.view_layers:
        layer(vl.layer_collection)
    for c in bpy.data.collections:
        c.hide_viewport = False
    for o in bpy.context.scene.objects:
        o.hide_viewport = False
        try:
            o.hide_set(False)
        except RuntimeError:
            pass
    bpy.context.view_layer.update()


def evaluated_arrays(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=False, depsgraph=depsgraph)
    if mesh is None:
        raise ValueError("Evaluation produced no mesh")
    try:
        mesh.calc_loop_triangles()
        if not mesh.loop_triangles:
            return None
        nverts, nloops, ntris = len(mesh.vertices), len(mesh.loops), len(mesh.loop_triangles)
        positions = np.empty(nverts * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", positions)
        positions = positions.reshape(-1, 3).astype(np.float64)
        matrix = np.array(evaluated.matrix_world, dtype=np.float64)
        positions = positions @ matrix[:3, :3].T + matrix[:3, 3]
        # Source coordinate conversion, no physical rescaling.
        positions = positions[:, [0, 2, 1]]
        positions[:, 2] *= -1
        tri_loops = np.empty(ntris * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("loops", tri_loops)
        loop_vertex = np.empty(nloops, dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_vertex)
        # Preserve evaluated split normals at surface seams. Do not add smoothing.
        normal_data = np.empty(nloops * 3, dtype=np.float32)
        normal_source = "source evaluated corner normals"
        if hasattr(mesh, "corner_normals") and len(mesh.corner_normals) == nloops:
            mesh.corner_normals.foreach_get("vector", normal_data)
        elif hasattr(mesh, "calc_normals_split"):
            mesh.calc_normals_split()
            mesh.loops.foreach_get("normal", normal_data)
        else:
            vertex_normals = np.empty(nverts * 3, dtype=np.float32)
            mesh.vertices.foreach_get("normal", vertex_normals)
            normal_data[:] = vertex_normals.reshape(-1, 3)[loop_vertex].reshape(-1)
            normal_source = "source vertex normals fallback (geometry unchanged; split-normal appearance may differ)"
        normals = normal_data.reshape(-1, 3).astype(np.float64)
        try:
            # Row-vector normal transform is multiplication by inverse(linear).
            normals = normals @ np.linalg.inv(matrix[:3, :3])
        except np.linalg.LinAlgError as e:
            raise ValueError("Source has singular world transform") from e
        normals = normals[:, [0, 2, 1]]
        normals[:, 2] *= -1
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        normals /= np.maximum(norms, 1e-20)
        normals = normals.astype(np.float32)
        # Deduplicate only exact vertex-index + float32 normal tuples, never spatial
        # welding or collapsing an anatomical edge. No position quantisation.
        records = np.empty(nloops, dtype=[("vertex", "<u4"), ("normal", "<f4", (3,))])
        records["vertex"] = loop_vertex
        records["normal"] = normals
        unique, inverse = np.unique(records, return_inverse=True)
        output_positions = positions[unique["vertex"]].astype(np.float32)
        output_normals = unique["normal"].copy()
        indices = inverse[tri_loops].astype(np.uint32).reshape(-1, 3)
        # A negative source transform changes winding; preserve outward normal parity.
        if np.linalg.det(matrix[:3, :3]) < 0:
            indices = indices[:, [0, 2, 1]].copy()
        if not np.isfinite(output_positions).all() or not np.isfinite(output_normals).all():
            raise ValueError("Non-finite evaluated source geometry")
        assert len(indices) == ntris, "Triangle count changed"
        return output_positions, output_normals, indices, {"evaluated_vertices": nverts,
                "evaluated_triangles": ntris, "exported_vertices": len(output_positions),
                "exported_triangles": len(indices), "normal_source": normal_source,
                "source_object_type": obj.type, "existing_modifiers": [{"name": m.name, "type": m.type, "show_viewport": bool(m.show_viewport)} for m in obj.modifiers],
                "added_decimation_modifiers": 0, "position_storage": "float32 GLB, source evaluated world positions (x,z,-y)"}
    finally:
        evaluated.to_mesh_clear()


def main():
    args_list = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--systems", default=",".join(SYSTEMS))
    args = parser.parse_args(args_list)
    chosen = args.systems.split(",")
    if any(s not in SYSTEMS for s in chosen):
        raise ValueError("Unknown system")
    args.output.mkdir(parents=True, exist_ok=True)
    show_sources()
    paths = collection_paths()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    manifest = {"exporter": "source-evaluated-no-added-decimation", "blender": bpy.app.version_string,
                "source_filename": Path(bpy.data.filepath).name, "assets": [], "errors": [], "skipped": [],
                "anatomy_review": "not performed", "additional_decimation": False}
    emitted = {}
    for category in chosen:
        name = SYSTEMS[category]
        coll = bpy.data.collections.get(name)
        if coll is None:
            # Fail rather than substitute an unrelated collection.
            candidates = [c for c in bpy.data.collections if c.name.split(":", 1)[-1].strip().casefold() == name.split(":", 1)[-1].strip().casefold()]
            coll = candidates[0] if len(candidates) == 1 else None
        if coll is None:
            raise ValueError("Source collection missing: " + name + ". Available: " + ", ".join(c.name for c in bpy.data.collections))
        writer = GLBWriter(category)
        source_objects = sorted(set(coll.all_objects), key=lambda o: o.name)
        object_count, tri_count, annotation_count = 0, 0, 0
        for i, obj in enumerate(source_objects):
            memberships = sorted(set(p for c in obj.users_collection for p in paths.get(c.as_pointer(), [c.name])))
            if obj.type == "FONT":
                p = obj.matrix_world.translation
                writer.annotation(obj.name, obj.data.body, [float(p.x), float(p.z), -float(p.y)], memberships)
                annotation_count += 1
                continue
            if obj.name.endswith(".g"):
                # Existing source annotation meshes are not anatomical tissue.
                manifest["skipped"].append({"object": obj.name, "reason": "source .g annotation geometry; not counted as anatomical mesh"})
                continue
            if obj.type not in {"MESH", "CURVE", "SURFACE"}:
                manifest["skipped"].append({"object": obj.name, "reason": "non-surface type " + obj.type})
                continue
            if obj.as_pointer() in emitted:
                manifest["skipped"].append({"object": obj.name, "reason": "same source object already exported", "first_system": emitted[obj.as_pointer()]})
                continue
            print(f"[{category}] {i + 1}/{len(source_objects)} {obj.name}", flush=True)
            try:
                result = evaluated_arrays(obj, depsgraph)
                if result is None:
                    manifest["skipped"].append({"object": obj.name, "reason": "source evaluation contains no triangles"})
                    continue
                positions, normals, indices, stats = result
                extras = {"source_name": obj.name, "collection_paths": memberships, **stats}
                writer.mesh(obj.name, positions, normals, indices, extras)
                object_count += 1
                tri_count += len(indices)
                emitted[obj.as_pointer()] = category
            except Exception as e:
                manifest["errors"].append({"object": obj.name, "system": category, "error": str(e)})
        if not object_count:
            raise ValueError("No source surface meshes exported for " + category)
        output = args.output / f"{category}.glb"
        writer.gltf["extras"]["exported_source_objects"] = object_count
        writer.gltf["extras"]["original_text_annotations"] = annotation_count
        writer.save(output)
        manifest["assets"].append({"id": "source-" + category, "category": category, "filename": output.name,
                                   "origin": "source-evaluated", "quality": "源文件评估网格；不添加减面；未经医学审校",
                                   "objects": object_count, "triangles": tri_count, "source_annotation_count": annotation_count,
                                   "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if manifest["errors"]:
        raise RuntimeError(f"{len(manifest['errors'])} source objects failed. Manifest saved; automatic packaging aborted rather than labelled complete.")
    print("Source evaluation export completed. Anatomy and physical scale are not certified.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Blender may exit 0 for Python script exceptions without --python-exit-code;
        # the caller sets an explicit error exit code as well.
        sys.exit(2)
