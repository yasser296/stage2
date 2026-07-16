"""
Rapprochement SAA vs D (GI) — Script de comparaison de messages SWIFT.

Extrait les messages OUTPUT d'une archive SAA (ZIP) et les compare
aux messages D (fichiers GI) pour identifier les écarts.

Génère :
- Rapport de rapprochement SAA vs D
- Rapport d'anomalies (messages sans/avec plusieurs DataBlocks)
- Exemples de messages par routing point
- Rapports détaillés par catégorie/routing point
"""

import html
import os
import re
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\msi\Desktop\stage2\Nouveau dossier"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "Output")
RAPPORT_DIR = os.path.join(OUTPUT_DIR, "rapport")

CHEMIN_FICHIER_S = os.path.join(DATA_DIR, "EXTRACTION0306.zip")
REPERTOIRE_D = os.path.join(DATA_DIR, "SGMB-GI")

ROUTING_POINT_TO_CATEGORY = {
    "SGMB_KONDOR_EP":        "KTP",
    "KTP_MX_EP":             "KTP",
    "SGMB_CARTHAGO_EP":      "AGI",
    "SGMB_OPENPAY_CONV_MX":  "delta v10", # convertisseur
    "SGTG_OPENPAY_CONV_MX":  "delta v9", # convertisseur
    "SGMB_OPENPAY_EP":       "openPay RTGS",
    "SGMB_SMARTCASH_EP":     "SmartCash",
    # "MATGTOPRINT_EP":        "Delta",
    # "MATGTOPRINT_MX_EP":     "Delta",
    "PRINTMT101EXPDEV_EP":   "gateway",
    "PRINTMT101EXPMAD_EP":   "delta v10",
    "SGTG101RECUEP":         "delta v9",
    # "PRINTINC_EP":           "PRINTINC",
    # "PRTACK_EP":             "PRTRACK",
    "FTI_EP":                "FTI",
    "NOSTRO_MX_EP":          "SmartCash",
}


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def normalize_bloc(text):
    """Nettoie et normalise un bloc pour comparaison."""
    text = text.replace("&#xD;", "\n")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text.strip())
    return text

def Affiche_bloc(text):
    """Nettoie et normalise un bloc Swift ou XML pour comparaison champ par champ."""
    # Remplace les retours chariot encodés
    text = text.replace("&#xD;", "\n")
    # Ajoute un retour à la ligne après chaque balise complète <...>...</...>
    text = re.sub(r"(</[^>]+>)", r"\1\n", text)
    # Découpage des champs SWIFT
    parts = re.split(r"(?=:\d{2}[A-Z]?:)", text)
    return "\n".join(p.strip() for p in parts if p.strip())


def is_output_message(message):
    """Vérifie si un message est de type OUTPUT."""
    return bool(re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I))


def extract_message_identifier(message):
    """Extrait le contenu de <MessageIdentifier> d'un message XML."""
    match = re.search(
        r"<MessageIdentifier\b[^>]*>(.*?)</MessageIdentifier>",
        html.unescape(message),
        re.I | re.S,
    )
    return match.group(1).strip() if match else None


def extract_sumid(message):
    """Extrait le contenu de <SUmid> d'un message XML."""
    match = re.search(
        r"<SUmid\b[^>]*>(.*?)</SUmid>",
        html.unescape(message),
        re.I | re.S,
    )
    return match.group(1).strip() if match else None


def detect_categories(message):
    """
    Détecte les catégories d'un message via <CreatingRoutingPoint>.
    Retourne un dict {routing_point: catégorie}.
    """
    message_unesc = html.unescape(message)
    all_rp = re.findall(
        r"<CreatingRoutingPoint>\s*(\S+?)\s*</CreatingRoutingPoint>",
        message_unesc,
        re.I,
    )

    if not all_rp:
        return {"AUCUN": "SANS_ROUTING_POINT"}

    return {
        rp: ROUTING_POINT_TO_CATEGORY.get(rp, "Non prise en charge")
        for rp in all_rp
    }


# ============================================================
# EXTRACTION DE DATABLOCKS
# ============================================================

def extraire_datablocks(message, message_identifier):
    """
    Extrait et formate les blocs de données d'un message.
    Retourne (blocs_formatés, anomalies).
    """
    matches = re.findall(r"<DataBlock>(.*?)</DataBlock>", message, re.S)
    text_matches = re.findall(
        r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>",
        message, re.S,
    )
    external_files = re.findall(
        r"<PayloadPhysicalFileName>(.*?)</PayloadPhysicalFileName>",
        message, re.S,
    )

    blocs_inline = matches + text_matches
    blocs_tous = blocs_inline + external_files
    blocs_normalise = [normalize_bloc(bloc) for bloc in blocs_tous] 
    blocs_formates = [Affiche_bloc(bloc) for bloc in blocs_normalise]

    # Détection des anomalies
    anomalies = []
    categories = detect_categories(message)

    if not blocs_inline and not blocs_tous:
        anomalies.append({
            "type": "OUTPUT_SANS_DATABLOCK",
            "categories_S": categories,
            "message": message,
            "message_identifier": message_identifier,
        })

    if len(blocs_inline) > 1:
        anomalies.append({
            "type": "OUTPUT_PLUSIEURS_DATABLOCK",
            "categories_S": categories,
            "nombre_blocs": len(blocs_inline),
            "message": message,
            "message_identifier": message_identifier,
        })

    return blocs_formates, anomalies


# ============================================================
# PARSERS
# ============================================================

def parse_messages_d(directory):
    """Extrait les blocs {2}{4} et <Body> des fichiers D (GI)."""
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Répertoire D introuvable : {directory}")

    all_messages = []

    for root, _, files in os.walk(directory):
        for fname in files:
            full_path = os.path.join(root, fname)
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            for bloc2, bloc4 in re.findall(r"\{2:(.*?)\}.*?\{4:(.*?)\-}", content, re.S):
                all_messages.append((normalize_bloc(bloc4), bloc2.strip(), full_path))

            for body in re.findall(r"<Body>(.*?)</Body>", content, re.S):
                all_messages.append((normalize_bloc(body), "BODY", full_path))

    return all_messages


def parse_messages_s(zip_path):
    """
    Décompresse l'archive SAA et extrait les messages OUTPUT.

    Retourne :
        all_messages    – liste de dicts {categories_S, blocs, nombre_blocs, message_identifier}
        exemples_par_rp – dict {routing_point: (catégorie, message_xml)}
        anomalies_info  – dict {compteurs, anomalies} pour le rapport
    """
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Archive S introuvable : {zip_path}")

    temp_dir = tempfile.mkdtemp()

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        all_messages = []
        anomalies = []
        exemples_par_rp = {}
        compteurs = {
            "sans_datablock": 0,
            "plusieurs_datablocks": 0,
            "surplus_datablocks": 0,
        }

        for root, _, files in os.walk(temp_dir):
            for fname in files:
                full_path = os.path.join(root, fname)
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
                if not messages:
                    messages = [content]

                for message in messages:
                    if not is_output_message(message):
                        continue

                    categories = detect_categories(message)
                    msg_id = extract_message_identifier(message)
                    blocs, anomalies_msg = extraire_datablocks(message, msg_id)
                    anomalies.extend(anomalies_msg)

                    # Un exemple par routing point
                    for rp, cat in categories.items():
                        if rp not in exemples_par_rp:
                            exemples_par_rp[rp] = (cat, message)

                    if not blocs:
                        compteurs["sans_datablock"] += 1
                        all_messages.append({
                            "categories_S": categories,
                            "blocs": [],
                            "nombre_blocs": 0,
                            "message_identifier": msg_id,
                        })
                        continue

                    if len(blocs) > 1:
                        compteurs["plusieurs_datablocks"] += 1
                        compteurs["surplus_datablocks"] += len(blocs) - 1

                    all_messages.append({
                        "categories_S": categories,
                        "blocs": blocs,
                        "nombre_blocs": len(blocs),
                        "message_identifier": msg_id,
                    })

        anomalies_info = {"compteurs": compteurs, "anomalies": anomalies}
        return all_messages, exemples_par_rp, anomalies_info

    finally:
        shutil.rmtree(temp_dir)


# ============================================================
# RAPPORTS
# ============================================================

def write_anomalies_report(anomalies_info, output_path):
    """Écrit le rapport d'anomalies SAA."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    c = anomalies_info["compteurs"]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=== Anomalies SAA ===\n\n")
        f.write(f"Messages OUTPUT sans DataBlock : {c['sans_datablock']}\n")
        f.write(f"Messages OUTPUT avec plusieurs DataBlock : {c['plusieurs_datablocks']}\n")
        f.write(f"Surplus de DataBlock : {c['surplus_datablocks']}\n\n")

        for a in anomalies_info["anomalies"]:
            f.write(f"Type : {a['type']}\n")
            for rp, cat in a["categories_S"].items():
                f.write(f"{rp} -> {cat}\n")
            f.write(f"message_identifier : {a['message_identifier']}\n")
            if "nombre_blocs" in a:
                f.write(f"Nombre de blocs : {a['nombre_blocs']}\n")
            f.write("Extrait du message XML :\n")
            f.write(a["message"])
            f.write("\n\n" + "-" * 100 + "\n\n")


def write_category_reports(s_messages, rapport_dir):
    """Écrit un fichier de rapport par catégorie/routing point."""
    shutil.rmtree(rapport_dir, ignore_errors=True)
    os.makedirs(rapport_dir)

    for msg in s_messages:
        # if not msg["blocs"]:
        #     continue

        for rp, cat in msg["categories_S"].items():
            if cat.upper().startswith("NON PRIS EN CHARGE") or cat == "SANS_ROUTING_POINT":
                continue

            cat_dir = os.path.join(rapport_dir, cat)
            os.makedirs(cat_dir, exist_ok=True)
            file_path = os.path.join(cat_dir, f"{rp}.txt")

            file_exists = os.path.exists(file_path)
            mode = "a" if file_exists else "w"

            with open(file_path, mode, encoding="utf-8") as f:
                if not file_exists:
                    f.write(f"=== Rapport {cat} , Routing Point: {rp} === \n\n\n")
                f.write(f"Type: {msg['message_identifier']} \n")
                for i, block in enumerate(msg["blocs"]):
                    block = Affiche_bloc(block)
                    f.write(f" DataBlock: {i + 1} \n")
                    f.write(block)
                    if i < len(msg["blocs"]) - 1:
                        f.write("\n" + "-" * 100 + "\n")
                f.write("\n\n\n" + "=" * 80 + "\n\n\n")


def write_reconciliation_report(d_messages, s_messages, output_dir):
    """Compare les messages SAA vs D et écrit le rapport de rapprochement."""
    os.makedirs(output_dir, exist_ok=True)

    set_d = {bloc4 for bloc4, _, _ in d_messages}
    set_s = {bloc for msg in s_messages for bloc in msg["blocs"]}

    missing_in_d = set_s - set_d

    # Index pour retrouver les infos d'un bloc SAA absent
    s_index = defaultdict(list)
    for msg in s_messages:
        for bloc in msg["blocs"]:
            s_index[bloc].append(msg)

    nombre_blocs_saa = sum(len(msg["blocs"]) for msg in s_messages)

    with open(os.path.join(output_dir, "Rapprochement_SAA_vs_D.txt"), "w", encoding="utf-8") as f:
        f.write("=== Rapport de rapprochement SAA vs D ===\n\n")
        f.write(f"Nombre de messages SAA OUTPUT = {len(s_messages)}\n")
        f.write(f"Nombre de blocs SAA extraits = {nombre_blocs_saa}\n")
        f.write(f"Nombre de messages dans D = {len(d_messages)}\n\n")
        f.write(f"Nombre de blocs SAA absents dans D = {len(missing_in_d)}\n")
        f.write("---- Messages présents dans SAA mais absents dans D ----\n\n")

        for bloc in missing_in_d:
            for info in s_index[bloc]:
                f.write("Statut: ABSENT_DANS_D\n")
                f.write(f"Type: {info['message_identifier']}\n")
                f.write("Catégories SAA:\n")
                for rp, cat in info["categories_S"].items():
                    f.write(f"{rp} -> {cat}\n")
                f.write("Text:\n")
                f.write(f"{Affiche_bloc(bloc)}\n\n")

    return len(s_messages), len(d_messages), len(missing_in_d)


def write_examples_report(exemples_par_rp, output_dir):
    """Écrit un fichier avec un exemple de message XML par routing point."""
    os.makedirs(output_dir, exist_ok=True)
    chemin = os.path.join(output_dir, "exemples-messages.txt")

    with open(chemin, "w", encoding="utf-8") as f:
        f.write("=== Exemple de message par identificateur ===\n\n")

        for rp in sorted(exemples_par_rp):
            categorie, message = exemples_par_rp[rp]

            msg_id = extract_message_identifier(message)
            type_str = f" | MESSAGE IDENTIFIER : {msg_id}" if msg_id else ""

            sumid = extract_sumid(message)
            sumid_str = f" | SUmid : {sumid}" if sumid else ""

            blocs, _ = extraire_datablocks(message, msg_id)

            f.write("=" * 80 + "\n")
            f.write(f"CATÉGORIE : {categorie}{type_str} | IDENTIFICATEUR : {rp}\n")
            f.write(f"MessageId : {sumid_str}\n")
            f.write("=" * 80 + "\n\n")
            for bloc in blocs:
                f.write(html.unescape(f"{bloc} + \n"))
            f.write("\n\n")

    print(f"Fichier d'exemples généré : {chemin}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    d_msgs = parse_messages_d(REPERTOIRE_D)
    s_msgs, exemples, anomalies_info = parse_messages_s(CHEMIN_FICHIER_S)

    # Rapports par catégorie et anomalies
    write_category_reports(s_msgs, RAPPORT_DIR)
    write_anomalies_report(anomalies_info, os.path.join(OUTPUT_DIR, "Anomalies_SAA.txt"))

    # Résumé console
    cat_counts = Counter(
        tuple(sorted(set(msg["categories_S"].values())))
        for msg in s_msgs
    )
    print("Catégories SAA :", cat_counts)
    print("Messages D trouvés :", len(d_msgs))
    print("Messages SAA extraits :", len(s_msgs))

    # Exemples et rapprochement
    write_examples_report(exemples, OUTPUT_DIR)
    stats = write_reconciliation_report(d_msgs, s_msgs, OUTPUT_DIR)
    print("Rapport généré dans :", OUTPUT_DIR)
