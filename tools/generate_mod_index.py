#!/usr/bin/env python3
"""Régénère l'inventaire du wiki à partir d'un dossier Minecraft mods."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GUIDES = {
    "apotheosis": ("Guide vérifié", "../apotheosis/gemmes.md"),
    "toms_storage": ("Guide disponible", "../guide/rangement.md"),
    "storagedrawers": ("Guide disponible", "../guide/rangement.md"),
    "sophisticatedbackpacks": ("Guide disponible", "../guide/rangement.md"),
    "ironchest": ("Guide disponible", "../guide/rangement.md"),
    "naturescompass": ("Guide disponible", "../guide/exploration.md"),
    "explorerscompass": ("Guide disponible", "../guide/exploration.md"),
    "waystones": ("Guide disponible", "../guide/exploration.md"),
    "xaerominimap": ("Guide disponible", "../guide/exploration.md"),
    "xaeroworldmap": ("Guide disponible", "../guide/exploration.md"),
    "ftbquests": ("Guide disponible", "../guide/progression.md"),
    "skilltree": ("Guide disponible", "../guide/progression.md"),
    "jei": ("Guide disponible", "../guide/recherche.md"),
    "jade": ("Guide disponible", "../guide/debuter.md"),
    "controlling": ("Guide disponible", "../guide/debuter.md"),
}


def clean(value: Any) -> str:
    text = str(value or "")
    return " ".join(text.replace("\x00", "").split()).strip()


def filename_guess(filename: str) -> str:
    stem = filename[:-4] if filename.lower().endswith(".jar") else filename
    stem = re.sub(r"(?i)(?:[-_ ]?(?:forge|mc)?1\.\d+(?:\.\d+)?).*$", "", stem)
    stem = re.sub(r"[-_]+", " ", stem).strip()
    return stem or filename


def regex_metadata(raw: str) -> list[dict[str, str]]:
    blocks = re.split(r"(?m)^\s*\[\[mods\]\]\s*$", raw)[1:]
    result: list[dict[str, str]] = []
    for block in blocks:
        block = re.split(r"(?m)^\s*\[\[dependencies\.", block, maxsplit=1)[0]
        values: dict[str, str] = {}
        for key in ("modId", "displayName", "version", "description", "displayURL"):
            quoted = re.search(rf"(?ms)^\s*{key}\s*=\s*(['\"]{{1,3}})(.*?)\1", block)
            if quoted:
                values[key] = clean(quoted.group(2))
        if values:
            result.append(values)
    return result


def read_metadata(jar: Path) -> tuple[list[dict[str, str]], str]:
    try:
        with zipfile.ZipFile(jar) as archive:
            names = set(archive.namelist())
            if "META-INF/mods.toml" in names:
                raw = archive.read("META-INF/mods.toml").decode("utf-8", "replace")
                try:
                    parsed = tomllib.loads(raw)
                    mods = parsed.get("mods", [])
                    if isinstance(mods, list) and mods:
                        return [dict(item) for item in mods if isinstance(item, dict)], "mods.toml"
                except tomllib.TOMLDecodeError:
                    pass
                fallback = regex_metadata(raw)
                if fallback:
                    return fallback, "mods.toml (lecture simplifiée)"
            if "fabric.mod.json" in names:
                parsed = json.loads(archive.read("fabric.mod.json").decode("utf-8", "replace"))
                return [{
                    "modId": parsed.get("id", ""),
                    "displayName": parsed.get("name", ""),
                    "version": parsed.get("version", ""),
                    "description": parsed.get("description", ""),
                    "displayURL": "",
                }], "fabric.mod.json"
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError):
        return [], "illisible"
    return [], "nom du fichier"


def guide_for(ids: list[str], filename: str) -> tuple[str, str | None]:
    lowered = filename.lower()
    for mod_id in ids:
        if mod_id in GUIDES:
            return GUIDES[mod_id]
    for key, guide in GUIDES.items():
        if key in lowered:
            return guide
    return "À compléter", None


def inspect_jar(jar: Path) -> dict[str, Any]:
    metadata, source = read_metadata(jar)
    names = [clean(item.get("displayName")) for item in metadata]
    ids = [clean(item.get("modId")) for item in metadata]
    versions = [clean(item.get("version")) for item in metadata]
    names = [value for value in names if value and "${" not in value]
    ids = [value for value in ids if value]
    versions = [value for value in versions if value and "${" not in value]
    status, guide = guide_for(ids, jar.name)
    return {
        "file": jar.name,
        "name": " + ".join(dict.fromkeys(names)) or filename_guess(jar.name),
        "mod_ids": list(dict.fromkeys(ids)),
        "version_metadata": ", ".join(dict.fromkeys(versions)) or None,
        "metadata_source": source,
        "status": status,
        "guide": guide,
    }


def anchor_group(name: str) -> str:
    first = name[:1].upper()
    return first if "A" <= first <= "Z" else "#"


def generate(mods_dir: Path) -> int:
    if not mods_dir.is_dir():
        raise SystemExit(f"Dossier introuvable : {mods_dir}")

    jars = sorted(mods_dir.glob("*.jar"), key=lambda path: path.name.casefold())
    if not jars:
        raise SystemExit(f"Aucun fichier .jar trouvé dans : {mods_dir}")

    entries = [inspect_jar(jar) for jar in jars]
    entries.sort(key=lambda item: (item["name"].casefold(), item["file"].casefold()))

    data_dir = PROJECT_ROOT / "data"
    docs_dir = PROJECT_ROOT / "docs" / "mods"
    data_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "mod-jars.txt").write_text(
        "\n".join(jar.name for jar in jars) + "\n", encoding="utf-8"
    )
    (data_dir / "mods.json").write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    index: list[str] = [
        "# Index des mods",
        "",
        '!!! info "Inventaire vérifié"',
        f"    **{len(jars)} fichiers `.jar`** ont été lus. L'export d'origine contient 293 entrées, car il inclut aussi `arborescence.txt`.",
        "",
        "Les noms affichés viennent des métadonnées embarquées quand elles sont lisibles. « À compléter » signifie que le fichier est bien présent, mais que sa mécanique n'est pas encore décrite dans ce wiki.",
        "",
    ]

    current_group = ""
    for entry in entries:
        group = anchor_group(entry["name"])
        if group != current_group:
            current_group = group
            index.extend([f"## {group}", ""])
        ids = ", ".join(f"`{mod_id}`" for mod_id in entry["mod_ids"])
        detail = f" — identifiant {ids}" if ids else ""
        if entry["guide"]:
            status = f'[:material-book-open-variant: {entry["status"]}]({entry["guide"]}){{ .status-ok }}'
        else:
            status = '<span class="status-todo">À compléter</span>'
        index.extend([
            '<div class="mod-entry" markdown>',
            f'**{entry["name"]}** — {status}  ',
            f'`{entry["file"]}`{detail}',
            "</div>",
            "",
        ])

    (docs_dir / "index.md").write_text("\n".join(index), encoding="utf-8")

    raw_page = [
        "# Liste brute des fichiers",
        "",
        '!!! info "Comptage"',
        f"    Cette liste contient **{len(jars)} `.jar`**. Le fichier `arborescence.txt`, présent dans l'export de 293 entrées, n'est pas un mod et n'apparaît donc pas ci-dessous.",
        "",
        "```text",
        *(jar.name for jar in jars),
        "```",
        "",
    ]
    (docs_dir / "fichiers.md").write_text("\n".join(raw_page), encoding="utf-8")
    return len(jars)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mods_dir", type=Path, help="Chemin vers le dossier minecraft/mods")
    args = parser.parse_args()
    count = generate(args.mods_dir.resolve())
    print(f"Index régénéré : {count} fichiers .jar")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

