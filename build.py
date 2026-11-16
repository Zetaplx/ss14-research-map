from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

DISCIPLINES = {
    "Industrial": "Industrial",
    "Arsenal": "Arsenal",
    "Experimental": "Experimental",
    "CivilianServices": "Civilian Services",
}
DISCIPLINE_ORDER = {name: index for index, name in enumerate(DISCIPLINES.values())}


def load_localizations(resources: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    locale_root = resources / "Locale" / "en-US"
    for folder in ("research", "_Persistence14/research", "_Moffstation/research"):
        directory = locale_root / folder
        if not directory.exists():
            continue
        for path in directory.rglob("*.ftl"):
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^\s*([\w-]+)\s*=\s*(.*?)\s*$", line)
                if match and not line.lstrip().startswith("#"):
                    result[match.group(1)] = match.group(2)
    return result


def fallback_name(proto_id: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", proto_id).replace("_", " ")


def source_for(path: Path) -> str:
    parts = set(path.parts)
    if "_Persistence14" in parts:
        return "Persistence14"
    if "_Moffstation" in parts:
        return "Moffstation"
    return "Base"


def build(resources: Path, template_path: Path, output_path: Path) -> int:
    prototypes = resources / "Prototypes"
    directories = [
        prototypes / "Research",
        prototypes / "_Persistence14" / "Research",
        prototypes / "_Moffstation" / "Research",
    ]
    localizations = load_localizations(resources)
    raw: dict[str, dict] = {}

    for directory in directories:
        for path in sorted(directory.glob("*.yml")) if directory.exists() else []:
            for document in yaml.safe_load_all(path.read_text(encoding="utf-8")):
                if not isinstance(document, list):
                    continue
                for prototype in document:
                    if not isinstance(prototype, dict) or prototype.get("type") != "technology":
                        continue
                    proto_id = prototype["id"]
                    raw[proto_id] = {**prototype, "_source": source_for(path)}

    by_id = {proto_id: item for proto_id, item in raw.items() if not item.get("hidden", False)}
    data = []
    for proto_id, item in by_id.items():
        discipline_id = item["discipline"]
        if discipline_id not in DISCIPLINES:
            continue
        name_key = item.get("name", "")
        requires = item.get("technologyPrerequisites", []) or []
        unresolved = [dep for dep in requires if dep not in by_id]
        if unresolved:
            raise ValueError(f"{proto_id} has unresolved prerequisites: {unresolved}")
        recipes = item.get("recipeUnlocks", {}) or {}
        if not isinstance(recipes, dict):
            raise ValueError(f"{proto_id} recipeUnlocks must be a mapping")
        data.append({
            "name": localizations.get(name_key, fallback_name(proto_id)),
            "source": item["_source"],
            "discipline": DISCIPLINES[discipline_id],
            "tier": int(item["tier"]),
            "cost": int(item.get("cost", 10000)),
            "requires": [localizations.get(by_id[dep].get("name", ""), fallback_name(dep)) for dep in requires],
            "recipes": [{"name": name, "quantity": int(quantity)} for name, quantity in recipes.items()],
        })
    data.sort(key=lambda item: (DISCIPLINE_ORDER[item["discipline"]], item["tier"], item["name"].casefold()))

    template = template_path.read_text(encoding="utf-8-sig")
    if "const technologies = RESEARCH_DATA;" not in template:
        raise ValueError("Template is missing the RESEARCH_DATA insertion point")
    page = template.replace("const technologies = RESEARCH_DATA;", "const technologies = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";", 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    print(f"Built {len(data)} technologies to {output_path}")
    return len(data)


if __name__ == "__main__":
    resource_root = Path(sys.argv[1] if len(sys.argv) > 1 else "source/Resources")
    build(resource_root, Path("site/index.template.html"), Path("dist/index.html"))
