from functools import lru_cache
from pathlib import Path

from config import SAA_ZIP, D_SOURCE
from file2 import (
    CATEGORIES,
    parse_messages_D,
    parse_messages_s,
    compare_and_save,
)


@lru_cache(maxsize=1)
def load_sources():
    """
    Lit SAA et D une seule fois.

    Les appels suivants réutilisent les données en mémoire tant que le serveur FastAPI reste lancé.
    """
    messages_d = parse_messages_D(str(D_SOURCE))

    messages_s, exemples, anomalies = parse_messages_s(
        str(SAA_ZIP)
    )

    return messages_d, messages_s


def clear_sources_cache():
    """Force une nouvelle lecture des fichiers stockés."""
    load_sources.cache_clear()


def run_comparison(output_directory: Path, selected_category=None):
    output_directory.mkdir(parents=True, exist_ok=True)

    messages_d, messages_s = load_sources()

    if selected_category:
        messages_s = [
            message for message in messages_s
            if selected_category in message["categories_S"].values()
        ]

    result = compare_and_save(
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

    categories = []
    categories_to_show = [selected_category] if selected_category else CATEGORIES

    for category in categories_to_show:
        categories.append({
            "name": category,
            "messages": messages_by_category.get(category, 0),
            "matched": matched_by_category.get(category, 0),
        })

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
    }
