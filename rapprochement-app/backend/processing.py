from functools import lru_cache
from pathlib import Path

import Rapprochement as rapprochement_categorie
import file2
from config import SAA_ZIP, D_SOURCE


CATEGORIES = file2.CATEGORIES


@lru_cache(maxsize=1)
def load_global_sources():
    """Lit une seule fois les sources utilisées par le rapport global."""
    messages_d = file2.parse_messages_D(str(D_SOURCE))
    messages_s, _, _ = file2.parse_messages_s(str(SAA_ZIP))
    return messages_d, messages_s


def find_category_source(category: str) -> Path:
    """Retourne le dossier ou l'archive D qui correspond à la catégorie."""
    directory = D_SOURCE / category
    if directory.is_dir():
        return directory

    for suffix in [".zip", ".tar"]:
        archive = D_SOURCE / f"{category}{suffix}"
        if archive.is_file():
            return archive

    raise FileNotFoundError(
        f"Aucun dossier ou ZIP trouvé pour la catégorie {category}"
    )


@lru_cache(maxsize=None)
def load_category_sources(category: str):
    """Lit une seule fois les sources d'une catégorie."""
    source_d = find_category_source(category)
    messages_d = rapprochement_categorie.parse_messages_D(str(source_d))
    messages_s = rapprochement_categorie.parse_messages_s(
        rapprochement_categorie.CHEMIN_FICHIER_S,
        category,
    )
    return messages_d, messages_s


def clear_sources_cache():
    """Force une nouvelle lecture des sources au prochain rapprochement."""
    load_global_sources.cache_clear()
    load_category_sources.cache_clear()


def run_global_comparison(output_directory: Path):
    messages_d, messages_s = load_global_sources()
    result = file2.compare_and_save(
        messages_d,
        messages_s,
        str(output_directory),
    )

    (
        total_d,
        total_s,
        total_blocks_saa,
        matched,
        missing,
        matched_by_category,
        messages_by_category,
        duplicates,
    ) = result

    categories = [
        {
            "name": category,
            "messages": messages_by_category.get(category, 0),
            "matched": matched_by_category.get(category, 0),
        }
        for category in CATEGORIES
    ]

    return {
        "summary": {
            "totalD": total_d,
            "totalMessagesSaa": total_s,
            "totalDataBlocksSaa": total_blocks_saa,
            "matched": matched,
            "missing": missing,
            "duplicates": duplicates,
        },
        "categories": categories,
        "reportFilename": "Rapprochement_SAA_vs_D.txt",
    }


def run_category_comparison(output_directory: Path, category: str):
    messages_d, messages_s = load_category_sources(category)
    result = rapprochement_categorie.compare_and_save(
        messages_d,
        messages_s,
        str(output_directory),
        category,
    )

    total_d, total_s, total_blocks_saa, matched, missing = result
    all_blocks = [
        block
        for message in messages_s
        for block in message["blocs"]
    ]
    duplicates = len(all_blocks) - len(set(all_blocks))

    return {
        "summary": {
            "totalD": total_d,
            "totalMessagesSaa": total_s,
            "totalDataBlocksSaa": total_blocks_saa,
            "matched": matched,
            "missing": missing,
            "duplicates": duplicates,
        },
        "categories": [
            {
                "name": category,
                "messages": total_s,
                "matched": matched,
            }
        ],
        "reportFilename": f"Rapprochement_SAA_vs_{category}.txt",
    }


def run_comparison(output_directory: Path, selected_category=None):
    output_directory.mkdir(parents=True, exist_ok=True)

    if selected_category:
        return run_category_comparison(output_directory, selected_category)

    return run_global_comparison(output_directory)
