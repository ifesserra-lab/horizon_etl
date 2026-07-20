"""
Convert the JSON canonical exports into a Parquet layout for storage/consumption.

Layout produced in the destination directory:

* array-of-objects file  ->  ``<name>.parquet`` (nested object/list fields are
  stored as JSON strings; readers revive them with ``JSON.parse``).
* node-link graph file    ->  ``<name>.nodes.parquet`` + ``<name>.edges.parquet``
  + ``<name>.meta.json`` (the small ``metadata`` / ``graph_stats`` /
  ``directed`` / ``multigraph`` wrapper).
* other small object (marts, summaries, ``_meta``)  ->  copied as ``<name>.json``
  (already tiny and deeply nested; Parquet adds no value).

Round-trips losslessly for the homogeneous canonical/graph tables. Usage::

    python -m src.scripts.export_parquet --src data/exports --dst data/exports_parquet
"""

import argparse
import glob
import json
import os
import shutil

import pandas as pd

COMPRESSION = "zstd"


def _stringify_nested(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda v: (
                    v
                    if isinstance(v, (str, type(None)))
                    else json.dumps(v, ensure_ascii=False)
                )
            )
    return df


def _write_table(rows: list, path: str) -> None:
    df = pd.json_normalize(rows, max_level=0)
    _stringify_nested(df).to_parquet(path, compression=COMPRESSION, index=False)


def _is_graph(data) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("graph"), dict)
        and "nodes" in data["graph"]
        and "edges" in data["graph"]
    )


def convert_file(path: str, dst_dir: str) -> str:
    name = os.path.basename(path)
    stem = name[:-5] if name.endswith(".json") else name
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, list) and data and isinstance(data[0], dict):
        _write_table(data, os.path.join(dst_dir, f"{stem}.parquet"))
        return "table"

    if _is_graph(data):
        graph = data["graph"]
        _write_table(graph["nodes"], os.path.join(dst_dir, f"{stem}.nodes.parquet"))
        _write_table(graph["edges"], os.path.join(dst_dir, f"{stem}.edges.parquet"))
        meta = {
            "metadata": data.get("metadata"),
            "graph_stats": data.get("graph_stats"),
            "graph": {
                "directed": graph.get("directed"),
                "multigraph": graph.get("multigraph"),
                "graph": graph.get("graph"),
            },
        }
        with open(
            os.path.join(dst_dir, f"{stem}.meta.json"), "w", encoding="utf-8"
        ) as fh:
            json.dump(meta, fh, ensure_ascii=False)
        return "graph"

    # small nested object (mart/summary/_meta): keep as JSON
    shutil.copy2(path, os.path.join(dst_dir, name))
    return "json"


def convert_dir(src: str, dst: str) -> dict:
    os.makedirs(dst, exist_ok=True)
    stats = {"table": 0, "graph": 0, "json": 0, "error": 0}
    for path in sorted(glob.glob(os.path.join(src, "*.json"))):
        try:
            stats[convert_file(path, dst)] += 1
        except Exception as exc:  # keep going; report at the end
            print(f"ERROR converting {os.path.basename(path)}: {exc}")
            stats["error"] += 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert JSON exports to Parquet layout."
    )
    parser.add_argument("--src", default="data/exports")
    parser.add_argument("--dst", default="data/exports_parquet")
    args = parser.parse_args()
    stats = convert_dir(args.src, args.dst)
    print(f"Parquet conversion complete: {stats} -> {args.dst}")


if __name__ == "__main__":
    main()
