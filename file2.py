from collections import Counter, defaultdict
import html
import os
import re
import shutil
import tempfile
import zipfile

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

def normalize_delta_bloc(text):
    """Nettoie et normalise un bloc Swift pour comparaison champ par champ."""
    text = text.replace("&#xD;", "\n")
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?=:\d{2}[A-Z]?:)", text)
    return "\n".join(p.strip() for p in parts if p.strip())

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
    # blocs_normalise = [normalize_bloc(bloc) for bloc in blocs_tous] 
    blocs_formates = [Affiche_bloc(bloc) for bloc in blocs_tous]

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




def extract_files(path):
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


    
def parse_messages_D(directory):
    """Extrait tous les couples bloc2/bloc4 de tous les fichiers D."""
    all_messages = []
    for content, fname, full_path in extract_files(directory):
        if fname.endswith(".Z"):
            continue
        bloc2_match = re.search(r"\{2:(.*?)\}", content)
        if bloc2_match:
            bloc2 = bloc2_match.group(1)
            if bloc2.startswith("I"):
                continue
        matches = re.findall(r"\{2:(.*?)\}.*?\{4:(.*?)\-}", content, re.S)
        for bloc2, bloc4 in matches:
            bloc4_norm = normalize_delta_bloc(bloc4)
            all_messages.append((bloc4_norm, bloc2.strip(), full_path))

        for body in re.findall(r"<Body>(.*?)</Body>", content, re.S):
                all_messages.append((normalize_bloc(body), "BODY", full_path))
    return all_messages

def parse_messages_s(zip_path):
    """
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
    for content, _ , _ in extract_files(zip_file):
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
    for content, _ , _ in extract_files(zip_file) :
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
                    f.write(f" DataBlock: {i + 1} \n")
                    f.write(block)
                    if i < len(msg["blocs"]) - 1:
                        f.write("\n" + "-" * 100 + "\n")
                f.write("\n\n\n" + "=" * 80 + "\n\n\n")


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
                f.write(f"{bloc}\n\n")

    return len(s_messages), len(d_messages), len(missing_in_d)





def compare_and_save(D_messages, S_messages, msgids, output_dir, chemin_fichier_S):
    """Compare blocs D/S :
       - rapproche MsgId + champ32A pour bloc2 = I103/I202/I200
       - rapproche champ par champ pour bloc2 = I700
    """

    global_source_map = defaultdict(list)
    for bloc4, bloc2, path in D_messages:
        global_source_map[(bloc2, bloc4)].append(path)
    global_duplicates = [bloc for bloc, paths in global_source_map.items() if len(paths) > 1]

    blocs_i_only = []
    source_map = defaultdict(list)
    for bloc4, bloc2, path in D_messages:
        if bloc2.startswith(("I103", "I202", "I200", "I700")):
            blocs_i_only.append(bloc4)
            source_map[(bloc2, bloc4)].append(path)

    duplicates = [bloc for bloc, paths in source_map.items() if len(paths) > 1]

    set_D = set(bloc4 for bloc4, bloc2, path in D_messages)
    set_S = {bloc for msg in S_messages for bloc in msg["blocs"]}
    missing_in_D = set_S - set_D

    # Index pour retrouver les infos d'un bloc SAA absent
    s_index = defaultdict(list)
    for msg in S_messages:
        for bloc in msg["blocs"]:
            s_index[bloc].append(msg)

    nombre_blocs_saa = sum(len(msg["blocs"]) for msg in S_messages)

    triplets_S = extract_pacs_triplets(chemin_fichier_S)

    rapprochements = []
    matched_blocs = set()
    for bloc4, bloc2, filepath in D_messages:
        # --- Cas MT103 / MT202 / MT200 ---
        if bloc2.startswith(("I103", "I202", "I200")):
            champs20 = re.findall(r":20:(.+)", bloc4)
            champs32A = re.findall(r":32A:(\d{6})([A-Z]{3})([\d,]+)", bloc4)
            for c20 in champs20:
                val20 = c20.strip()
                for date_raw, currency, amount_raw in champs32A:
                    date_iso = convert_date_32A(date_raw)
                    amount = normalize_amount(amount_raw)
                    if (val20 in msgids and (date_iso, currency, amount) in triplets_S):
                        rapprochements.append(f"{filepath} -> MT103/202/200 MATCH Champ20: {val20}, Champ32A: {date_iso} {currency} {amount}")
                        matched_blocs.add(bloc4)
                    else:
                        rapprochements.append(f"{filepath} -> MT103/202/200 NE CORRESPOND PAS Champ20: {val20}, Champ32A: {date_iso} {currency} {amount}")

        # --- Cas MT700 ---
        elif bloc2.startswith("I700"):
            champs27  = re.findall(r":27:(.+)", bloc4)
            champs40A = re.findall(r":40A:(.+)", bloc4)
            champs20  = re.findall(r":20:(.+)", bloc4)
            champs31C = re.findall(r":31C:(.+)", bloc4)
            champs40E = re.findall(r":40E:(.+)", bloc4)
            champs31D = re.findall(r":31D:(.+)", bloc4)
            champs50  = re.findall(r":50:(.+)", bloc4)

            match_found = False
            for blocS in S_messages:
                s27  = re.findall(r":27:(.+)", blocS)
                s40A = re.findall(r":40A:(.+)", blocS)
                s20  = re.findall(r":20:(.+)", blocS)
                s31C = re.findall(r":31C:(.+)", blocS)
                s40E = re.findall(r":40E:(.+)", blocS)
                s31D = re.findall(r":31D:(.+)", blocS)
                s50  = re.findall(r":50:(.+)", blocS)

                if (champs27 == s27 and champs40A == s40A and champs20 == s20 and
                    champs31C == s31C and champs40E == s40E and champs31D == s31D and champs50 == s50):
                    match_found = True
                    break

            if match_found:
                rapprochements.append(
                    f"{filepath} -> MT700 MATCH Champs 27:{champs27}, 40A:{champs40A}, 20:{champs20}, 31C:{champs31C}, 40E:{champs40E}, 31D:{champs31D}, 50:{champs50}"
                )
                matched_blocs.add(bloc4)
            else:
                rapprochements.append(
                    f"{filepath} -> MT700 NE CORRESPOND PAS Champs 27:{champs27}, 40A:{champs40A}, 20:{champs20}, 31C:{champs31C}, 40E:{champs40E}, 31D:{champs31D}, 50:{champs50}"
                )

    # Exclure les blocs matchés des absents
    missing_in_D = missing_in_D - matched_blocs

    with open(os.path.join(output_dir, "Rapprochement_SAA_vs_D.txt"), "a", encoding="utf-8") as f:
        f.write("===Section : rapprochement des messages DELTA vs SAA ===\n\n")
        f.write(f"Nombre de messages émis  = {len(D_messages)}\n")
        f.write(f"Nombre de messages Absents dans le systeme operant = {len(missing_in_D)}\n\n")
        f.write(f"----------- Ces messages ont été envoyés par SAA mais ne figurent pas dans le système opérant : -----------\n\n\n")
        for bloc in missing_in_D:
            for (bloc2, bloc4), paths in global_source_map.items():
                if bloc4 == bloc:
                    f.write(f"Header: {bloc2}\nText:\n{bloc4}\n\n")
        # f.write(f"Details de rapprochements : \n\n")
        # for r in rapprochements :
        #     f.write(f"{r}\n")
    return (len(blocs_i_only), len(D_messages), len(S_messages),
            len(duplicates), len(global_duplicates),
            len(missing_in_D), len(rapprochements))

# === Exemple d’utilisation ===
chemin_fichier_S = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\EXTRACTION0306.zip"
repertoire_D = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\SGMB-GI"
output_dir = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output"

if __name__ == "__main__":

    # Parsing des messages
    messages_D = parse_messages_D(repertoire_D)
    messages_S = parse_messages_s(chemin_fichier_S)
    msgids = extract_pacs_msgid_from_file(chemin_fichier_S)

    # Comparaison et génération des rapports
    total_D_filtre, total_D_brut, total_S, nb_duplicates_filtres, nb_duplicates_globaux, nb_missing, nb_rapprochements = compare_and_save(
        messages_D, messages_S, msgids, output_dir, chemin_fichier_S
    )

    # Affichage des résultats
    print("Nombre total de messages émis par Delta :", total_D_brut)
    print("Nombre total de messages sur SAA :", total_S)
    print("Nombre de rapprochements (champ20 + champ32A) :", nb_rapprochements)
    print("Nombre de doublons globaux (tous D) :", nb_duplicates_globaux)
    print("Nombre de messages absents :", nb_missing)
    print("Chemin du rapport complet :", os.path.join(output_dir, "rapport_complet.txt"))
    print("Chemin du rapprochement MT103-202-200 (champ20+32A) :", os.path.join(output_dir, "rapprochement_msgid_field20_32A.txt"))
    print("Chemin du fichier doublons :", os.path.join(output_dir, "doublons.txt"))
    print("Chemin du fichier absents :", os.path.join(output_dir, "absents.txt"))
