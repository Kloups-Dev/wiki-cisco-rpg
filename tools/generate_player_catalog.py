#!/usr/bin/env python3
"""Génère le catalogue joueur depuis les fichiers exacts du pack Cisco."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GROUPS = json.loads((ROOT / "data" / "content-groups.json").read_text(encoding="utf-8"))
GROUP_BY_NS = {ns: group for group in GROUPS for ns in group["namespaces"]}
CATEGORIES = {
    "magie": ("Magie et sorts", "Sorts, grimoires, rituels et ateliers magiques."),
    "equipement": ("Armes, armures et améliorations", "Équipement, gemmes, curios et pouvoirs."),
    "boss": ("Boss, dimensions et butin", "Boss, invocations, donjons et récompenses."),
    "progression": ("Progression du personnage", "Compétences, origines et enchantements."),
}
RECIPE_LABELS = {
    "minecraft:crafting_shaped": "Établi — recette ordonnée",
    "minecraft:crafting_shapeless": "Établi — recette libre",
    "minecraft:smelting": "Four",
    "minecraft:blasting": "Haut fourneau",
    "minecraft:smoking": "Fumoir",
    "minecraft:campfire_cooking": "Feu de camp",
    "minecraft:stonecutting": "Tailleur de pierre",
    "minecraft:smithing": "Table de forge",
    "crafttweaker:shapeless": "Établi — recette Cisco",
    "crafttweaker:smithing": "Table de forge — recette Cisco",
}


@dataclass
class Archive:
    path: Path
    source: str
    handle: zipfile.ZipFile
    names: set[str]


def read_json(archive: Archive, name: str) -> Any | None:
    try:
        return json.loads(archive.handle.read(name).decode("utf-8", "replace"))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def humanize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title()


def pick_jars(mods_dir: Path) -> tuple[list[Path], dict[str, list[str]]]:
    selected, grouped = [], defaultdict(list)
    for jar in sorted(mods_dir.glob("*.jar"), key=lambda item: item.name.casefold()):
        for group in GROUPS:
            if any(pattern.casefold() in jar.name.casefold() for pattern in group["patterns"]):
                selected.append(jar)
                grouped[group["slug"]].append(jar.name)
                break
    return selected, dict(grouped)


def resource_index(archives: list[Archive]) -> dict[str, Archive]:
    result = {}
    for archive in archives:
        for name in archive.names:
            if name.startswith(("assets/", "data/")):
                result.setdefault(name, archive)
    return result


def translations(archives: list[Archive], locale: str) -> dict[str, str]:
    result = {}
    suffix = f"/lang/{locale}.json"
    for archive in archives:
        for name in archive.names:
            if not name.endswith(suffix):
                continue
            data = read_json(archive, name)
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str):
                        result[key] = re.sub(r"§.", "", value)
    return result


def split_resource(value: str, default_ns: str) -> tuple[str, str]:
    return tuple(value.split(":", 1)) if ":" in value else (default_ns, value)


def model_textures(index: dict[str, Archive], ns: str, model: str, seen=None) -> dict[str, str]:
    seen = seen or set()
    marker = (ns, model)
    if marker in seen:
        return {}
    seen.add(marker)
    name = f"assets/{ns}/models/{model}.json"
    archive = index.get(name)
    if not archive:
        return {}
    data = read_json(archive, name)
    if not isinstance(data, dict):
        return {}
    result = {}
    parent = data.get("parent")
    if isinstance(parent, str) and parent not in {
        "minecraft:item/generated", "minecraft:item/handheld",
        "minecraft:item/handheld_rod", "builtin/entity",
    }:
        parent_ns, parent_model = split_resource(parent, ns)
        result.update(model_textures(index, parent_ns, parent_model, seen))
    if isinstance(data.get("textures"), dict):
        result.update({str(k): str(v) for k, v in data["textures"].items() if isinstance(v, str)})
    return result


def icon_resource(index: dict[str, Archive], item_id: str) -> str | None:
    ns, path = item_id.split(":", 1)
    textures = model_textures(index, ns, f"item/{path}")
    for key in ("layer0", "all", "texture", "particle", "layer1"):
        value = textures.get(key)
        seen = set()
        while isinstance(value, str) and value.startswith("#") and value[1:] not in seen:
            seen.add(value[1:])
            value = textures.get(value[1:])
        if isinstance(value, str) and not value.startswith("#"):
            tex_ns, tex_path = split_resource(value, ns)
            name = f"assets/{tex_ns}/textures/{tex_path}.png"
            if name in index:
                return name
    for name in (
        f"assets/{ns}/textures/item/{path}.png",
        f"assets/{ns}/textures/items/{path}.png",
        f"assets/{ns}/textures/block/{path}.png",
        f"assets/{ns}/textures/blocks/{path}.png",
    ):
        if name in index:
            return name
    return None


def ingredient(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"item": value}
    if isinstance(value, list):
        return {"alternatives": [ingredient(entry) for entry in value]}
    if not isinstance(value, dict):
        return {}
    if isinstance(value.get("item"), str):
        return {"item": value["item"]}
    if isinstance(value.get("tag"), str):
        return {"tag": value["tag"]}
    return ingredient(value["ingredient"]) if "ingredient" in value else {}


def ingredient_items(value: dict[str, Any]) -> list[str]:
    if isinstance(value.get("item"), str):
        return [value["item"]]
    result = []
    for entry in value.get("alternatives", []):
        if isinstance(entry, dict):
            result.extend(ingredient_items(entry))
    return result


def result_item(value: Any) -> tuple[str | None, int]:
    if isinstance(value, str):
        return value, 1
    if not isinstance(value, dict):
        return None, 1
    item_id = value.get("item") or value.get("id")
    try:
        count = int(value.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    return (item_id if isinstance(item_id, str) else None), count


def parse_recipe(data: dict[str, Any], recipe_id: str, source: str) -> dict[str, Any] | None:
    output, count = result_item(data.get("result", data.get("output")))
    if not output or ":" not in output:
        return None
    kind, slots, layout = str(data.get("type", "inconnu")), [], "custom"
    if kind == "minecraft:crafting_shaped" and isinstance(data.get("pattern"), list):
        slots, layout = [{} for _ in range(9)], "grid"
        keys = data.get("key", {})
        for row, line in enumerate(data["pattern"][:3]):
            for column, symbol in enumerate(str(line)[:3]):
                if symbol != " ":
                    slots[row * 3 + column] = ingredient(keys.get(symbol))
    elif kind == "minecraft:crafting_shapeless":
        slots = [ingredient(entry) for entry in data.get("ingredients", [])[:9]]
        slots += [{} for _ in range(9 - len(slots))]
        layout = "grid"
    elif kind in {
        "minecraft:smelting", "minecraft:blasting", "minecraft:smoking",
        "minecraft:campfire_cooking", "minecraft:stonecutting",
    }:
        slots, layout = [ingredient(data.get("ingredient"))], "single"
    elif "smithing" in kind:
        slots = [ingredient(data[key]) for key in ("template", "base", "addition") if key in data]
        layout = "smithing"
    else:
        for key in ("ingredients", "input", "base", "addition", "catalyst"):
            value = data.get(key)
            if isinstance(value, list):
                slots.extend(ingredient(entry) for entry in value)
            elif value is not None:
                slots.append(ingredient(value))
    return {
        "id": recipe_id, "type": kind, "layout": layout, "slots": slots,
        "result": output, "count": count, "source": source,
    }


def jar_recipes(archives: list[Archive]) -> list[dict[str, Any]]:
    result = []
    for archive in archives:
        for name in archive.names:
            match = re.fullmatch(r"data/([^/]+)/recipes/(.+)\.json", name)
            if not match:
                continue
            data = read_json(archive, name)
            if isinstance(data, dict):
                parsed = parse_recipe(data, f"{match.group(1)}:{match.group(2)}", archive.source)
                if parsed:
                    result.append(parsed)
    return result


def crafttweaker(path: Path) -> tuple[list[dict[str, Any]], set[str]]:
    raw = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    removed = set(re.findall(r'removeByModid\("([^"]+)"\)', raw))
    item = r"<item:([^>]+)>"
    result = []
    for name, output, raw_inputs in re.findall(
        rf'craftingTable\.addShapeless\("([^"]+)",\s*{item},\s*\[(.*?)\]\s*\);', raw, re.DOTALL
    ):
        inputs = re.findall(item, raw_inputs)[:9]
        result.append({
            "id": f"crafttweaker:{name}", "type": "crafttweaker:shapeless",
            "layout": "grid", "slots": [{"item": value} for value in inputs] + [{}] * (9 - len(inputs)),
            "result": output, "count": 1, "source": path.name,
        })
    for name, output, base, addition in re.findall(
        rf'smithing\.addRecipe\("([^"]+)",\s*{item},\s*{item},\s*{item}\s*\);', raw
    ):
        result.append({
            "id": f"crafttweaker:{name}", "type": "crafttweaker:smithing",
            "layout": "smithing", "slots": [{"item": base}, {"item": addition}],
            "result": output, "count": 1, "source": path.name,
        })
    return result, removed


def localized_name(item_id: str, fr: dict[str, str], en: dict[str, str]) -> tuple[str, str]:
    ns, path = item_id.split(":", 1)
    keys = (f"item.{ns}.{path}", f"block.{ns}.{path}")
    french = next((fr[key] for key in keys if key in fr), None)
    english = next((en[key] for key in keys if key in en), None)
    fallback = humanize(path)
    return french or english or fallback, english or french or fallback


def extract_icons(item_ids: list[str], index: dict[str, Archive]) -> dict[str, str]:
    icons = {}
    for item_id in item_ids:
        resource = icon_resource(index, item_id)
        if not resource:
            continue
        ns, path = item_id.split(":", 1)
        target = ROOT / "docs" / "assets" / "generated" / "items" / ns / f"{path}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(index[resource].handle.read(resource))
        icons[item_id] = f"assets/generated/items/{ns}/{path}.png"
    return icons


def item_link(item_id: str, known: set[str], prefix="../") -> str | None:
    if item_id not in known:
        return None
    ns, path = item_id.split(":", 1)
    return f"{prefix}{ns}/{path}.md"


def slot_html(
    slot: dict[str, Any], names: dict[str, str], icons: dict[str, str], known: set[str],
    item_prefix: str = "../", icon_prefix: str = "../../../",
) -> str:
    if not slot:
        return '<span class="jei-slot jei-slot--empty"></span>'
    choices = ingredient_items(slot)
    item_id = choices[0] if choices else None
    if item_id:
        label = names.get(item_id, humanize(item_id.split(":")[-1]))
        icon = icons.get(item_id)
        content = f'<img src="{icon_prefix}{html.escape(icon)}" alt="" loading="lazy">' if icon else "?"
        title = html.escape(f"{label} ({item_id})", quote=True)
        href = item_link(item_id, known, item_prefix)
        tag = "a" if href else "span"
        link = f' href="{href}"' if href else ""
        return f'<{tag} class="jei-slot"{link} title="{title}">{content}</{tag}>'
    if slot.get("tag"):
        return f'<span class="jei-slot jei-slot--tag" title="#{html.escape(slot["tag"])}">#</span>'
    return '<span class="jei-slot">?</span>'


def recipe_html(
    recipe: dict[str, Any], names: dict[str, str], icons: dict[str, str], known: set[str],
    item_prefix: str = "../", icon_prefix: str = "../../../",
) -> str:
    slots = list(recipe["slots"])
    if recipe["layout"] == "grid":
        slots = (slots + [{}] * 9)[:9]
        inputs = '<div class="jei-grid">' + "".join(
            slot_html(slot, names, icons, known, item_prefix, icon_prefix) for slot in slots
        ) + "</div>"
    else:
        inputs = '<div class="jei-inputs">' + "".join(
            slot_html(slot, names, icons, known, item_prefix, icon_prefix) for slot in slots
        ) + "</div>"
    output = recipe["result"]
    result_icon = f'<img src="{icon_prefix}{icons[output]}" alt="">' if output in icons else "?"
    count = f'<span class="jei-count">{recipe["count"]}</span>' if recipe["count"] > 1 else ""
    label = RECIPE_LABELS.get(recipe["type"], humanize(recipe["type"].split(":")[-1]))
    return (
        '<div class="jei-recipe">'
        f'<div class="jei-recipe__head"><strong>{html.escape(label)}</strong><span>{html.escape(recipe["id"])}</span></div>'
        f'<div class="jei-recipe__body">{inputs}<span class="jei-arrow">→</span>'
        f'<span class="jei-slot jei-slot--result">{result_icon}{count}</span></div>'
        f'<div class="jei-recipe__source">Source exacte : {html.escape(recipe["source"])}</div></div>'
    )


def write_pages(
    items: list[str], names: dict[str, str], english_names: dict[str, str], icons: dict[str, str],
    recipes_by_result: dict[str, list[dict[str, Any]]], uses: dict[str, list[dict[str, Any]]],
    grouped_jars: dict[str, list[str]], recipe_counts: dict[str, int],
) -> None:
    known = set(items)
    item_root = ROOT / "docs" / "catalogue" / "objets"
    for item_id in items:
        ns, path = item_id.split(":", 1)
        group = GROUP_BY_NS[ns]
        target = item_root / ns / f"{path}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        depth = len(target.relative_to(ROOT / "docs").parent.parts)
        root_prefix = "../" * depth
        item_prefix = f"{root_prefix}catalogue/objets/"
        name, english = names[item_id], english_names[item_id]
        icon = (
            f'<img class="mc-item-icon" src="{root_prefix}{icons[item_id]}" alt="{html.escape(name, quote=True)}">'
            if item_id in icons else '<div class="mc-item-icon mc-item-icon--missing">?</div>'
        )
        lines = [
            f"# {name}", "", '<div class="mc-item-showcase">', icon, '<div class="mc-tooltip-card">',
            f'<div class="mc-tooltip-card__name">{html.escape(name)}</div>',
        ]
        if english.casefold() != name.casefold():
            lines.append(f'<div class="mc-tooltip-card__alias">{html.escape(english)}</div>')
        lines += [
            f'<div class="mc-tooltip-card__mod">{html.escape(group["name"])}</div>',
            f'<div class="mc-tooltip-card__id">{html.escape(item_id)}</div>', "</div>", "</div>", "",
            '!!! success "Présence vérifiée"', f"    Objet fourni par les fichiers exacts de **{group['name']}**.", "",
            "## Obtention et fabrication", "",
        ]
        found = recipes_by_result.get(item_id, [])
        lines += [
            recipe_html(recipe, names, icons, known, item_prefix, root_prefix) for recipe in found
        ] if found else [
            '!!! warning "Pas de recette directe trouvée"',
            "    L'objet peut provenir d'un boss, d'un coffre, d'un échange ou d'une mécanique spéciale visible dans JEI.",
        ]
        lines += ["", "## Utilisé dans", ""]
        seen = set()
        for recipe in uses.get(item_id, []):
            output = recipe["result"]
            if output in seen:
                continue
            seen.add(output)
            label = names.get(output, humanize(output.split(":")[-1]))
            href = item_link(output, known, item_prefix)
            lines.append(f"- [{label}]({href}) — <code>{output}</code>" if href else f"- **{label}** — <code>{output}</code>")
        if not seen:
            lines.append("Aucun usage direct trouvé dans les recettes statiques analysées.")
        lines += [
            "", "## Effets et caractéristiques", "",
            '!!! info "À confirmer dans la partie"',
            "    Les dégâts, attributs, sorts, affixes, sockets et valeurs NBT dynamiques seront ajoutés après vérification de l'infobulle réelle en jeu.",
            "", f"[Tous les objets de {group['name']}]({root_prefix}contenu/{group['slug']}.md)", "",
        ]
        target.write_text("\n".join(lines), encoding="utf-8")

    group_root = ROOT / "docs" / "contenu"
    group_root.mkdir(parents=True, exist_ok=True)
    by_ns = defaultdict(list)
    for item_id in items:
        by_ns[item_id.split(":")[0]].append(item_id)
    for group in GROUPS:
        group_items = [item for ns in group["namespaces"] for item in by_ns.get(ns, [])]
        count = sum(recipe_counts.get(ns, 0) for ns in group["namespaces"])
        lines = [
            f"# {group['name']}", "", group["summary"], "",
            '<div class="content-summary">',
            f'<span><strong>{len(group_items)}</strong> objets indexés</span>',
            f'<span><strong>{count}</strong> recettes détectées</span>',
            f'<a href="{group["source"]}">Source documentaire ↗</a>', "</div>", "",
            "## Fichiers exacts du pack", "",
        ]
        lines += [f"- <code>{html.escape(jar)}</code>" for jar in grouped_jars.get(group["slug"], [])]
        lines += [
            "", '!!! warning "La version installée fait foi"',
            "    Les sources externes servent à comprendre le mod. Les recettes affichées ici viennent des fichiers 1.19.2 et des personnalisations Cisco.",
            "", "## Objets recherchables", "", '<div class="item-catalog-grid">',
        ]
        for item_id in group_items:
            ns, path = item_id.split(":")
            picture = f'<img src="../{icons[item_id]}" alt="" loading="lazy">' if item_id in icons else '<span class="catalog-missing">?</span>'
            lines.append(
                f'<a class="catalog-item" href="../catalogue/objets/{ns}/{path}.md" title="{item_id}">'
                f'{picture}<span>{html.escape(names[item_id])}</span></a>'
            )
        lines += ["</div>", ""]
        (group_root / f"{group['slug']}.md").write_text("\n".join(lines), encoding="utf-8")

    category_root = ROOT / "docs" / "categories"
    category_root.mkdir(parents=True, exist_ok=True)
    for slug, (title, description) in CATEGORIES.items():
        lines = [f"# {title}", "", description, "", '<div class="grid cards" markdown>', ""]
        for group in [value for value in GROUPS if value["category"] == slug]:
            count = sum(len(by_ns.get(ns, [])) for ns in group["namespaces"])
            lines += [
                f"-   **{group['name']}**", "", f"    {group['summary']}", "",
                f"    **{count} objets indexés**", "",
                f"    [:octicons-arrow-right-24: Ouvrir](../contenu/{group['slug']}.md)", "",
            ]
        lines += ["</div>", ""]
        (category_root / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "# Catalogue des objets", "", f"**{len(items)} objets et blocs utiles** indexés depuis le pack exact.",
        "", "Recherche possible par nom français, anglais, mod ou identifiant technique.", "",
    ]
    by_letter = defaultdict(list)
    for item_id in items:
        first = names[item_id][:1].upper()
        by_letter[first if first.isalpha() else "#"].append(item_id)
    for letter in sorted(by_letter):
        lines += [f"## {letter}", "", '<div class="catalog-list">']
        for item_id in sorted(by_letter[letter], key=lambda value: names[value].casefold()):
            ns, path = item_id.split(":")
            picture = f'<img src="../{icons[item_id]}" alt="" loading="lazy">' if item_id in icons else '<span class="catalog-missing">?</span>'
            lines.append(
                f'<a href="objets/{ns}/{path}.md">{picture}<span><strong>{html.escape(names[item_id])}</strong>'
                f'<small>{html.escape(GROUP_BY_NS[ns]["name"])}</small></span></a>'
            )
        lines += ["</div>", ""]
    catalog = ROOT / "docs" / "catalogue"
    catalog.mkdir(parents=True, exist_ok=True)
    (catalog / "index.md").write_text("\n".join(lines), encoding="utf-8")


def generate(mods_dir: Path, minecraft_jar: Path, ct_script: Path) -> dict[str, int]:
    selected, grouped = pick_jars(mods_dir)
    if not selected:
        raise SystemExit("Aucun mod de contenu sélectionné.")
    for path in (
        ROOT / "docs" / "catalogue" / "objets", ROOT / "docs" / "assets" / "generated",
        ROOT / "docs" / "contenu", ROOT / "docs" / "categories",
    ):
        if path.exists():
            shutil.rmtree(path)
    opened = []
    try:
        for path in [minecraft_jar, *selected]:
            handle = zipfile.ZipFile(path)
            opened.append(Archive(path, path.name, handle, set(handle.namelist())))
        vanilla, mod_archives = opened[0], opened[1:]
        index = resource_index(opened)
        fr, en = translations(opened, "fr_fr"), translations(opened, "en_us")
        recipes = jar_recipes(mod_archives)
        custom, removed = crafttweaker(ct_script)
        recipes = [entry for entry in recipes if entry["id"].split(":")[0] not in removed] + custom

        model_ids = set()
        for resource in index:
            match = re.fullmatch(r"assets/([^/]+)/models/item/(.+)\.json", resource)
            if match and match.group(1) in GROUP_BY_NS:
                model_ids.add(f"{match.group(1)}:{match.group(2)}")

        # A mod often contains internal item models (bow pulling frames, GUI-only
        # variants, etc.) which are not real registry objects.  A player-facing
        # object must have both an item model and a translated item/block name.
        translated_ids = set()
        for key in set(fr) | set(en):
            match = re.fullmatch(r"(?:item|block)\.([^.]+)\.(.+)", key)
            if match and match.group(1) in GROUP_BY_NS:
                translated_ids.add(f"{match.group(1)}:{match.group(2)}")
        item_ids = model_ids & translated_ids
        item_ids.update(entry["result"] for entry in recipes if entry["result"].split(":")[0] in GROUP_BY_NS)
        items = sorted(item_ids)
        names, english_names = {}, {}
        for item_id in items:
            names[item_id], english_names[item_id] = localized_name(item_id, fr, en)
        icons = extract_icons(items, index)

        by_result, uses, recipe_counts = defaultdict(list), defaultdict(list), defaultdict(int)
        for recipe in recipes:
            by_result[recipe["result"]].append(recipe)
            recipe_counts[recipe["result"].split(":")[0]] += 1
            for slot in recipe["slots"]:
                for item_id in ingredient_items(slot):
                    uses[item_id].append(recipe)
        write_pages(items, names, english_names, icons, by_result, uses, grouped, recipe_counts)

        counts = {
            "groups": len(GROUPS), "jars": len(selected), "items": len(items),
            "icons": len(icons), "recipes": len(recipes), "crafttweaker_recipes": len(custom),
        }
        summary = {
            "pack": "Cisco's Fantasy Medieval RPG [Ultimate]", "minecraft": "1.19.2",
            "selected_jars": [path.name for path in selected],
            "removed_recipe_namespaces": sorted(removed), "counts": counts,
            "groups": [{**group, "jars": grouped.get(group["slug"], [])} for group in GROUPS],
        }
        (ROOT / "data" / "player-content.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (ROOT / "data" / "recipes-player.json").write_text(
            json.dumps(recipes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return counts
    finally:
        for archive in opened:
            archive.handle.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mods_dir", type=Path)
    parser.add_argument("--minecraft-jar", required=True, type=Path)
    parser.add_argument("--crafttweaker-script", required=True, type=Path)
    args = parser.parse_args()
    counts = generate(args.mods_dir.resolve(), args.minecraft_jar.resolve(), args.crafttweaker_script.resolve())
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
