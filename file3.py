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

def normalize_delta_block(text):
    """Normalisation compatible avec la comparaison Delta de file.py."""
    text = text.replace("&#xD;", "\n")
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?=:\d{2}[A-Z]?:)", text)
    return "\n".join(p.strip() for p in parts if p.strip())


def extract_files(path):
    """Retourne le contenu des fichiers d'un dossier ou d'une archive ZIP."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chemin introuvable : {path}")

    if zipfile.is_zipfile(path):
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(path, "r") as archive:
                archive.extractall(temp_dir)

            for root, _, files in os.walk(temp_dir):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    with open(full_path, encoding="utf-8") as f:
                        yield f.read(), fname, full_path
        finally:
            shutil.rmtree(temp_dir)
    else:
        for root, _, files in os.walk(path):
            for fname in files:
                full_path = os.path.join(root, fname)
                with open(full_path, encoding="utf-8") as f:
                    yield f.read(), fname, full_path


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

    for content, fname, full_path in extract_files(directory):
        if fname.endswith(".Z"):
            continue
        for bloc2, bloc4 in re.findall(r"\{2:(.*?)\}.*?\{4:(.*?)\-}", content, re.S):
            bloc2 = bloc2.strip()
            if not bloc2.startswith("O"):
                continue
            all_messages.append((normalize_bloc(bloc4), bloc2, full_path))

        for body in re.findall(r"<Body>(.*?)</Body>", content, re.S):
            all_messages.append((normalize_bloc(body), "BODY", full_path))

    return all_messages


def parse_messages_s(zip_path):
    """
    Décompresse l'archive SAA et extrait les messages OUTPUT.

    Retourne :
        all_messages    - liste de dicts {categories_S, blocs, nombre_blocs, message_identifier}
        exemples_par_rp - dict {routing_point: (catégorie, message_xml)}
        anomalies_info  - dict {compteurs, anomalies} pour le rapport
    """
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


def extract_pacs_msgid_from_file(zip_file):
    all_msgids = []
    for content, _, _ in extract_files(zip_file):
        msgids = re.findall(
            r"&lt;pacs:MsgId&gt;(.*?)&lt;/pacs:MsgId&gt;",
            content
        )
        for mid in msgids:
            all_msgids.append(mid.strip())
    return all_msgids

def extract_pacs_triplets(zip_file):
    """Extrait les triplets (date, currency, amount) bloc par bloc."""
    triplets = set()
    for content, _, _ in extract_files(zip_file):
        blocks = re.findall(r"<DataBlock>(.*?)</DataBlock>", content, re.S)
        for bloc in blocks:
            dates = re.findall(r"&lt;pacs:IntrBkSttlmDt&gt;(.*?)&lt;/pacs:IntrBkSttlmDt&gt;", bloc)
            montants = re.findall(r"&lt;pacs:IntrBkSttlmAmt Ccy=\"([A-Z]{3})\"&gt;(.*?)&lt;/pacs:IntrBkSttlmAmt&gt;", bloc)
            for d in dates:
                for ccy, amt in montants:
                    triplets.add((d.strip(), ccy.strip(), amt.strip()))
    return triplets

def normalize_amount(amount_raw):
    """Normalise le montant Swift (virgule -> point, suppression virgule finale)."""
    amount = amount_raw.strip()
    if amount.endswith(","):
        amount = amount[:-1]
    amount = amount.replace(",", ".")
    return amount

def convert_date_32A(date_raw):
    """Convertit YYMMDD en YYYY-MM-DD (ex: 260505 -> 2026-05-05)."""
    return f"20{date_raw[:2]}-{date_raw[2:4]}-{date_raw[4:]}"
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
    os.makedirs(rapport_dir, exist_ok=True)

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
                    f.write(f" DataBlock: {i + 1} \n")
                    f.write(block)
                    if i < len(msg["blocs"]) - 1:
                        f.write("\n" + "-" * 100 + "\n")
                f.write("\n\n\n" + "=" * 80 + "\n\n\n")



MT700_COMPARE_FIELDS = ("27", "40A", "20", "31C", "40E", "31D", "50")


def flatten_s_blocks(s_messages):
    """Retourne tous les blocs SAA dans une seule liste."""
    return [bloc for msg in s_messages for bloc in msg["blocs"]]


def build_s_block_index(s_messages):
    """Indexe les blocs SAA pour retrouver leurs metadonnees."""
    s_index = defaultdict(list)
    for msg in s_messages:
        for bloc in msg["blocs"]:
            s_index[bloc].append(msg)
    return s_index


def build_d_block_index(d_messages):
    """Indexe les blocs D pour retrouver leurs headers et fichiers source."""
    d_index = defaultdict(list)
    for bloc4, bloc2, path in d_messages:
        d_index[bloc4].append((bloc2, path))
    return d_index


def extract_saa_blocks_for_delta(zip_path):
    """Extrait tous les blocs SAA utiles au controle SAA -> D."""
    blocks = []
    for content, _, _ in extract_files(zip_path):
        datablocks = re.findall(r"<DataBlock>(.*?)</DataBlock>", content, re.S)
        text_blocks = re.findall(
            r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>",
            content,
            re.S,
        )
        for bloc in datablocks + text_blocks:
            blocks.append(normalize_delta_block(bloc))
    return blocks


def build_d_delta_block_index(d_messages):
    """Indexe les blocs D avec la normalisation du controle D -> SAA."""
    d_index = defaultdict(list)
    for bloc4, bloc2, path in d_messages:
        d_index[normalize_delta_block(bloc4)].append((bloc2, path, bloc4))
    return d_index


def extract_swift_fields(block, field_name):
    return re.findall(rf":{field_name}:(.+)", block)


def compare_mt700_fields(d_block, s_blocks):
    d_fields = {
        field: extract_swift_fields(d_block, field)
        for field in MT700_COMPARE_FIELDS
    }

    for s_block in s_blocks:
        if all(d_fields[field] == extract_swift_fields(s_block, field)
               for field in MT700_COMPARE_FIELDS):
            return True, d_fields

    return False, d_fields


def compare_delta_to_saa(d_messages, zip_path):
    """
    Compare SAA vers d.

    Les blocs D exactement presents dans SAA sont OK.
    Les O103/O202/O200 peuvent matcher via champ 20 + champ 32A.
    Les O700 peuvent matcher via les champs principaux compares.
    """
    s_blocks = extract_saa_blocks_for_delta(zip_path)
    d_compare_messages = [
        (normalize_delta_block(bloc4), bloc2, filepath)
        for bloc4, bloc2, filepath in d_messages
    ]

    set_d = {bloc4 for bloc4, _, _ in d_compare_messages}
    set_s = set(s_blocks)
    missing_delta_blocks = set_d - set_s

    msgids = set(extract_pacs_msgid_from_file(zip_path))
    triplets_s = extract_pacs_triplets(zip_path)

    rapprochements = []
    matched_blocks = set()

    for bloc4, bloc2, filepath in d_compare_messages:
        if bloc2.startswith(("O103", "O202", "O200")):
            champs20 = re.findall(r":20:(.+)", bloc4)
            champs32a = re.findall(r":32A:(\d{6})([A-Z]{3})([\d,]+)", bloc4)

            if not champs20 or not champs32a:
                rapprochements.append({
                    "type": "MT103/202/200",
                    "status": "NON_TESTE",
                    "source": filepath,
                    "header": bloc2,
                    "details": "Champ 20 ou 32A manquant",
                })
                continue

            block_matched = False
            for c20 in champs20:
                val20 = c20.strip()
                for date_raw, currency, amount_raw in champs32a:
                    date_iso = convert_date_32A(date_raw)
                    amount = normalize_amount(amount_raw)
                    matched = (
                        val20 in msgids
                        and (date_iso, currency, amount) in triplets_s
                    )
                    block_matched = block_matched or matched
                    rapprochements.append({
                        "type": "MT103/202/200",
                        "status": "MATCH" if matched else "NON_MATCH",
                        "source": filepath,
                        "header": bloc2,
                        "details": (
                            f"Champ20={val20}; "
                            f"Champ32A={date_iso} {currency} {amount}"
                        ),
                    })

            if block_matched:
                matched_blocks.add(bloc4)

        elif bloc2.startswith("O700"):
            matched, compared_fields = compare_mt700_fields(bloc4, s_blocks)
            rapprochements.append({
                "type": "MT700",
                "status": "MATCH" if matched else "NON_MATCH",
                "source": filepath,
                "header": bloc2,
                "details": ", ".join(
                    f"{field}={compared_fields[field]}"
                    for field in MT700_COMPARE_FIELDS
                ),
            })
            if matched:
                matched_blocks.add(bloc4)

    return {
        "missing_delta_blocks": missing_delta_blocks - matched_blocks,
        "matched_blocks": matched_blocks,
        "rapprochements": rapprochements,
        "msgids_count": len(msgids),
        "triplets_count": len(triplets_s),
        "s_delta_blocks_count": len(s_blocks),
    }


def write_summary(f, stats):
    f.write("=== Rapport de rapprochement SAA vs D ===\n\n")
    f.write("RESUME\n")
    f.write("-" * 80 + "\n")
    f.write(f"Messages SAA OUTPUT            : {stats['s_messages_count']}\n")
    f.write(f"Blocs SAA extraits             : {stats['s_blocks_count']}\n")
    f.write(f"Messages D                     : {stats['d_messages_count']}\n")
    f.write(f"Blocs D uniques                : {stats['d_unique_blocks_count']}\n")
    f.write(f"Doublons D                     : {stats['global_duplicates_count']}\n")
    f.write(f"MsgId pacs uniques dans SAA    : {stats['msgids_count']}\n")
    f.write(f"SAA present mais absent dans D : {stats['missing_saa_in_d_count']}\n\n")


def write_missing_saa_section(f, missing_blocks, s_index):
    f.write("SECTION 1 - BLOCS SAA PRESENTS MAIS ABSENTS DANS D\n")
    f.write("=" * 80 + "\n\n")

    if not missing_blocks:
        f.write("Aucun bloc SAA absent dans D.\n\n")
        return

    for index, bloc in enumerate(sorted(missing_blocks), start=1):
        for info in s_index[bloc]:
            f.write(f"[{index}] Statut : ABSENT_DANS_D\n")
            f.write(f"Type SAA : {info['message_identifier']}\n")
            f.write("Categories SAA :\n")
            for rp, cat in info["categories_S"].items():
                f.write(f"  - {rp} -> {cat}\n")
            f.write("Bloc :\n")
            f.write(f"{bloc}\n")
            f.write("\n" + "-" * 80 + "\n\n")


def write_missing_delta_section(f, missing_delta_blocks, d_index):
    f.write("SECTION 2 - BLOCS DELTA PRESENTS MAIS ABSENTS DANS SAA\n")
    f.write("=" * 80 + "\n\n")

    if not missing_delta_blocks:
        f.write("Aucun bloc Delta absent dans SAA.\n\n")
        return

    for index, bloc in enumerate(sorted(missing_delta_blocks), start=1):
        f.write(f"[{index}] Statut : ABSENT_DANS_SAA\n")
        original_bloc = bloc
        for bloc2, path, source_bloc in d_index[bloc]:
            original_bloc = source_bloc
            f.write(f"Header : {bloc2}\n")
            f.write(f"Source : {path}\n")
        f.write("Bloc :\n")
        f.write(f"{original_bloc}\n")
        f.write("\n" + "-" * 80 + "\n\n")


def write_delta_reconciliation_section(f, rapprochements):
    f.write("SECTION 3 - RAPPROCHEMENT DES MESSAGES DELTA\n")
    f.write("=" * 80 + "\n\n")

    if not rapprochements:
        f.write("Aucun message Delta de type O103, O202, O200 ou O700.\n\n")
        return

    for index, item in enumerate(rapprochements, start=1):
        f.write(f"[{index}] {item['type']} - {item['status']}\n")
        f.write(f"Header : {item['header']}\n")
        f.write(f"Source : {item['source']}\n")
        f.write(f"Details : {item['details']}\n")
        f.write("\n" + "-" * 80 + "\n\n")


def write_reconciliation_report(d_messages, s_messages, output_dir):
    """Compare les messages SAA et D puis ecrit un rapport structure."""
    os.makedirs(output_dir, exist_ok=True)

    s_blocks = flatten_s_blocks(s_messages)
    set_d = {bloc4 for bloc4, _, _ in d_messages}
    set_s = set(s_blocks)

    missing_blocks = set_s - set_d
    compare = compare_delta_to_saa(d_messages, CHEMIN_FICHIER_S)
    missing_delta_blocks = compare["missing_delta_blocks"]

    global_source_map = defaultdict(list)
    filtered_source_map = defaultdict(list)
    for bloc4, bloc2, path in d_messages:
        global_source_map[(bloc2, bloc4)].append(path)
        if bloc2.startswith(("O103", "O202", "O200", "O700")):
            filtered_source_map[(bloc2, bloc4)].append(path)

    global_duplicates = [
        bloc for bloc, paths in global_source_map.items()
        if len(paths) > 1
    ]
    filtered_duplicates = [
        bloc for bloc, paths in filtered_source_map.items()
        if len(paths) > 1
    ]

    stats = {
        "s_messages_count": len(s_messages),
        "s_blocks_count": len(s_blocks),
        "d_messages_count": len(d_messages),
        "d_unique_blocks_count": len(set_d),
        "global_duplicates_count": len(global_duplicates),
        "filtered_duplicates_count": len(filtered_duplicates),
        "msgids_count": compare["msgids_count"],
        "triplets_count": compare["triplets_count"],
        "s_delta_blocks_count": compare["s_delta_blocks_count"],
        "compare_checks_count": len(compare["rapprochements"]),
        "compare_matches_count": sum(
            1 for item in compare["rapprochements"]
            if item["status"] == "MATCH"
        ),
        "missing_saa_in_d_count": len(missing_blocks),
        "missing_delta_in_saa_count": len(missing_delta_blocks),
    }

    report_path = os.path.join(output_dir, "Rapprochement_SAA_vs_D.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        write_summary(f, stats)
        write_missing_saa_section(f, missing_blocks, build_s_block_index(s_messages))
        if missing_delta_blocks:
            write_missing_delta_section(f, missing_delta_blocks, build_d_delta_block_index(d_messages))
        if compare["rapprochements"]:
            write_delta_reconciliation_section(f, compare["rapprochements"])

    stats["report_path"] = report_path
    return stats


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
    print("Blocs SAA absents dans D :", stats["missing_saa_in_d_count"])
    print("MsgId pacs uniques dans SAA :", stats["msgids_count"])
    print("Rapport de rapprochement :", stats["report_path"])
    print("Rapport généré dans :", OUTPUT_DIR)
