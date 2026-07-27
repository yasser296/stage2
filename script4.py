from collections import defaultdict
import os
import re

from file import extract_files
from file2 import Affiche_bloc, detect_categories, extract_message_identifier, extract_sumid, extraire_datablocks, is_output_message

BASE_DIR = r"C:\Users\msi\Desktop\stage2\Nouveau dossier"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "Output")
RAPPORT_DIR = os.path.join(OUTPUT_DIR, "rapport")

CHEMIN_FICHIER_S = os.path.join(DATA_DIR, "EXTRACTION0306.zip")
REPERTOIRE_D = os.path.join(DATA_DIR, "D")

CATEGORIES = ["KTP","AGI","delta v9","delta v10","SmartCash","gateway","FTI","openPay RTGS"]

def parse_messages_s(zip_path):
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Archive S introuvable : {zip_path}")

    all_messages = []
    anomalies = []
    exemples_par_rp = {}
    compteurs = {
        "sans_datablock": 0,
        "plusieurs_datablocks": 0,
        "surplus_datablocks": 0,
    }

    for content, fname, full_path in extract_files(zip_path):
            messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
            if not messages:
                messages = [content]

            for message in messages:
                if not is_output_message(message):
                    continue

                categories = detect_categories(message)
                msg_id = extract_message_identifier(message)
                sumid = extract_sumid(message)
                block, anomalie_msg = extraire_datablocks(message, msg_id)
                if anomalie_msg:
                    anomalies.append(anomalie_msg)

                # Un exemple par routing point
                for rp, cat in categories.items():
                    if rp not in exemples_par_rp:
                        exemples_par_rp[rp] = (cat, message)

                if not block:
                    compteurs["sans_datablock"] += 1
                    all_messages.append({
                        "categories_S": categories,
                        "blocs": [],
                        "nombre_blocs": 0,
                        "message_identifier": msg_id,
                        "sumid": sumid,
                    })
                    continue

                if anomalie_msg and (anomalie_msg["type"] == "OUTPUT_PLUSIEURS_DATABLOCK"):
                    compteurs["plusieurs_datablocks"] += 1
                    compteurs["surplus_datablocks"] += 1

                all_messages.append({
                    "categories_S": categories,
                    "blocs": block,
                    "nombre_blocs": len(block),
                    "message_identifier": msg_id,
                    "sumid": sumid,
                })

    anomalies_info = {"compteurs": compteurs, "anomalies": anomalies}
    return all_messages, exemples_par_rp, anomalies_info


def write_repeated_blocks_report(s_messages, output_dir):
    index_blocs = defaultdict(list)

    # Associer chaque bloc aux messages qui le contiennent
    for numero_message, msg in enumerate(s_messages, start=1):

        for bloc in msg["blocs"]:

            index_blocs[bloc].append({
                "numero_message": numero_message,
                "sumid": msg.get("sumid"),
                "message_identifier": msg.get("message_identifier"),
                "categories_S": msg.get("categories_S", {}),
            })
    # Garder uniquement les blocs répétés
    blocs_repetes = {
        bloc: messages
        for bloc, messages in index_blocs.items()
        if len(messages) > 1
    }

    rapport_path = os.path.join(output_dir,"DataBlocks_repetes_SAA.txt")
    os.makedirs(output_dir, exist_ok=True)
    with open(rapport_path, "w", encoding="utf-8") as f:
        f.write("=== DATABLOCKS RÉPÉTÉS DANS SAA ===\n\n")
        f.write(
            f"Nombre de contenus de DataBlock répétés : "
            f"{len(blocs_repetes)}\n\n"
        )
        if not blocs_repetes:
            f.write("Aucun DataBlock répété.\n")

        for numero_bloc, (bloc, messages) in enumerate(
            blocs_repetes.items(),
            start=1
        ):

            f.write("=" * 100 + "\n")
            f.write(f"DATABLOCK RÉPÉTÉ N° {numero_bloc}\n")
            f.write(f"Nombre d'occurrences : {len(messages)}\n")
            f.write("=" * 100 + "\n\n")

            for numero_occurrence, info in enumerate(
                messages,
                start=1
            ):

                f.write(
                    f"Occurrence {numero_occurrence}\n"
                )

                f.write(
                    f"Numéro du message dans S_messages : "
                    f"{info['numero_message']}\n"
                )

                f.write(
                    f"SUmid : "
                    f"{info['sumid'] or 'AUCUN'}\n"
                )

                f.write(
                    f"MessageIdentifier : "
                    f"{info['message_identifier'] or 'AUCUN'}\n"
                )

                f.write("Catégories :\n")

                for rp, categorie in info["categories_S"].items():
                    f.write(f"  {rp} -> {categorie}\n")

                f.write("\n")

            f.write("Contenu du DataBlock :\n")
            f.write(Affiche_bloc(bloc))
            f.write("\n\n")

    print(
        "Nombre de DataBlocks différents répétés :",
        len(blocs_repetes)
    )

    print(
        "Rapport des répétitions :",
        rapport_path
    )

if __name__ == "__main__":
    messages_S, exemples_par_rp, anomalies_info = parse_messages_s(
        CHEMIN_FICHIER_S
    )

    write_repeated_blocks_report(
        messages_S,
        OUTPUT_DIR
    )