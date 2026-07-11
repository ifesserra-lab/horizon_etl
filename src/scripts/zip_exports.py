#!/usr/bin/env python3
"""Compacta os arquivos pesados de dados/exports em um .zip versionável e (opcional) commita.

Motivo: o hook de pre-commit bloqueia JSON crus grandes ("use storage externo ou mantenha
local"). Um .zip único passa pelo hook e versiona o snapshot dos dados de forma compacta.

Por padrão compacta os JSON sob data/exports/ + as fontes pesadas (FAPES, bolsistas, mestrado).

Uso:
  python -m src.scripts.zip_exports                 # gera o zip (não commita)
  python -m src.scripts.zip_exports --commit        # gera o zip E commita
  python -m src.scripts.zip_exports --out data/exports/exports.zip --glob 'data/raw/**/*.json'
"""
from __future__ import annotations

import argparse
import glob
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "data" / "exports" / "data_snapshot.zip"
# padrões padrão: exports + fontes pesadas que o hook costuma bloquear
DEFAULT_PATTERNS = [
    "data/exports/**/*.json",
    "data/exports/**/*.csv",
    "data/mestrado/*.json",
]


def collect(patterns: list[str], out: Path) -> list[Path]:
    files: set[Path] = set()
    for pat in patterns:
        for f in glob.glob(str(ROOT / pat), recursive=True):
            p = Path(f)
            if p.is_file() and p.suffix.lower() in (".json", ".csv") and p != out:
                files.add(p)
    return sorted(files)


def make_zip(files: list[Path], out: Path) -> tuple[int, int]:
    out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            z.write(f, arcname=str(f.relative_to(ROOT)))
            total += f.stat().st_size
    return total, out.stat().st_size


def main() -> None:
    ap = argparse.ArgumentParser(description="Compacta exports/dados em .zip e (opcional) commita.")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="caminho do .zip de saída")
    ap.add_argument("--glob", action="append", help="padrão(s) de arquivo (repetível); substitui os padrões")
    ap.add_argument("--commit", action="store_true", help="git add do zip + commit")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    patterns = args.glob or DEFAULT_PATTERNS
    files = collect(patterns, out)
    if not files:
        print("Nenhum arquivo .json/.csv encontrado para os padrões:", patterns)
        return

    orig, zsz = make_zip(files, out)
    ratio = (zsz / orig * 100) if orig else 0
    print(f"Zip: {out.relative_to(ROOT)}")
    print(f"  {len(files)} arquivos · {orig/1e6:.1f} MB -> {zsz/1e6:.1f} MB ({ratio:.0f}% do original)")
    for f in files:
        print("  +", f.relative_to(ROOT))

    if args.commit:
        rel = str(out.relative_to(ROOT))
        subprocess.run(["git", "-C", str(ROOT), "add", rel], check=True)
        msg = (f"chore: snapshot zip de dados/exports "
               f"({len(files)} arquivos, {zsz/1e6:.1f} MB, {datetime.now():%Y-%m-%d})")
        r = subprocess.run(["git", "-C", str(ROOT), "commit", "-m", msg])
        print("commit:", "OK" if r.returncode == 0 else "nada a commitar ou erro")


if __name__ == "__main__":
    main()
