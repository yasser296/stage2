from collections import defaultdict
from decimal import Decimal, InvalidOperation
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
REPERTOIRE_D = os.path.join(DATA_DIR, "D")

CATEGORIES = ["KTP","AGI","delta v9","delta v10","SmartCash","gateway","FTI"]

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
        r"<MessageIdentifier\b[^>]*>(.*?)</MessageIdentifier>", html.unescape(message), re.I | re.S,
    )
    return match.group(1).strip() if match else None


def extract_sumid(message):
    """Extrait le contenu de <SUmid> d'un message XML."""
    match = re.search(r"<SUmid\b[^>]*>(.*?)</SUmid>", html.unescape(message), re.I | re.S,)
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
    Extrait seulement les DataBlock des messages SAA OUTPUT.
    Retourne :
    - blocs normalisés pour comparaison
    - anomalies
    """

    message = html.unescape(message)

    datablocks = re.findall(
        r"<DataBlock\b[^>]*>(.*?)</DataBlock>",
        message,
        re.S | re.I
    )

    blocs = []

    for bloc in datablocks:
        bloc_normalise = normalize_delta_bloc(bloc)
        blocs.append(bloc_normalise)

    anomalies = []
    categories = detect_categories(message)

    if not datablocks:
        anomalies.append({
            "type": "OUTPUT_SANS_DATABLOCK",
            "categories_S": categories,
            "message": message,
            "message_identifier": message_identifier,
        })

    if len(datablocks) > 1:
        anomalies.append({
            "type": "OUTPUT_PLUSIEURS_DATABLOCK",
            "categories_S": categories,
            "nombre_blocs": len(datablocks),
            "message": message,
            "message_identifier": message_identifier,
        })

    return blocs, anomalies

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
                all_messages.append((normalize_delta_bloc(body), "BODY", full_path))
    return all_messages

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


def normalize_amount(amount_raw):
    """ Normalise les montants D et SAA. """
    amount = amount_raw.strip()
    amount = amount.replace(" ", "")
    # Dans D, une virgule peut être présente sans décimales
    if amount.endswith(","):
        amount = amount[:-1]
    # Même séparateur décimal pour D et SAA
    amount = amount.replace(",", ".")
    try:
        amount_decimal = Decimal(amount)
        # Supprime les zéros inutiles après la virgule
        return format(amount_decimal.normalize(), "f")
    except InvalidOperation:
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
                    f.write(Affiche_bloc(block))
                    if i < len(msg["blocs"]) - 1:
                        f.write("\n" + "-" * 100 + "\n")
                f.write("\n\n\n" + "=" * 80 + "\n\n\n")


def write_examples_report(exemples_par_rp, OUTPUT_DIR):
    """Écrit un fichier avec un exemple de message XML par routing point."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chemin = os.path.join(OUTPUT_DIR, "exemples-messages.txt")

    with open(chemin, "w", encoding="utf-8") as f:
        f.write("=== Exemple de message par identificateur ===\n\n")

        for rp in sorted(exemples_par_rp):
            categorie, message = exemples_par_rp[rp]

            msg_id = extract_message_identifier(message)
            type_str = f" | MESSAGE IDENTIFIER : {msg_id}" if msg_id else ""

            sumid = extract_sumid(message)

            blocs, _ = extraire_datablocks(message, msg_id)

            f.write("=" * 80 + "\n")
            f.write(f"CATÉGORIE : {categorie}{type_str} | IDENTIFICATEUR : {rp}\n")
            f.write(f"SUmid : {sumid or 'AUCUN'}\n")
            f.write("=" * 80 + "\n\n")
            for bloc in blocs:
                f.write(html.unescape(Affiche_bloc(bloc)))
                f.write("\n")
            f.write("\n\n")

    print(f"Fichier d'exemples généré : {chemin}")

def compare_and_save(D_messages, S_messages, OUTPUT_DIR):
    """Compare les blocs SAA avec D :
    - rapproche MsgId + champ 32A pour O103/O202/O200
    - rapproche champ par champ pour O700
    """

    global_source_map = defaultdict(list)
    for bloc4, bloc2, path in D_messages:
        global_source_map[(bloc2, bloc4)].append(path)
    global_duplicates = [bloc for bloc, paths in global_source_map.items() if len(paths) > 1]

    set_D = set(bloc4 for bloc4, bloc2, path in D_messages)
    set_S = {bloc for msg in S_messages for bloc in msg["blocs"]}
    missing_in_D = set_S - set_D

    # Index pour retrouver les infos d'un bloc SAA absent
    s_index = defaultdict(list)
    for msg in S_messages:
        for bloc in msg["blocs"]:
            s_index[bloc].append(msg)

    nombre_blocs_saa = sum(len(msg["blocs"]) for msg in S_messages)

    # ============================================================
    # COMPARAISONS ADAPTÉES SELON LE FORMAT DU MESSAGE
    # ============================================================

    # blocs_trouves_par_champs doit contenir des blocs SAA, car missing_in_D contient des blocs SAA.
    blocs_trouves_par_champs = set()

    # ------------------------------------------------------------
    # 1. Préparer les données D pour O103 / O202 / O200
    # ------------------------------------------------------------

    # Clé :
    # (champ20, date, devise, montant)
    #
    # Valeur :
    # liste des messages D qui possèdent cette clé
    index_D_pacs = defaultdict(list)

    for bloc4, bloc2, filepath in D_messages:
        if not bloc2.startswith(("O103", "O202", "O200")):
            continue
        champs20 = re.findall(r":20:(.+)", bloc4)
        champs32A = re.findall(r":32A:(\d{6})([A-Z]{3})([\d,]+)", bloc4)
        for champ20 in champs20:
            valeur20 = champ20.strip()
            for date_raw, currency, amount_raw in champs32A:
                date_iso = convert_date_32A(date_raw)
                amount = normalize_amount(amount_raw)
                cle_D = (valeur20, date_iso, currency.strip(), amount)
                index_D_pacs[cle_D].append({"bloc4": bloc4, "bloc2": bloc2, "fichier": filepath})

    # ------------------------------------------------------------
    # 2. Préparer les données D pour O700
    # ------------------------------------------------------------

    index_D_700 = defaultdict(list)

    for bloc4, bloc2, filepath in D_messages:
        if not bloc2.startswith("O700"):
            continue

        cle_D_700 = (
            tuple(re.findall(r":27:(.+)", bloc4)),
            tuple(re.findall(r":40A:(.+)", bloc4)),
            tuple(re.findall(r":20:(.+)", bloc4)),
            tuple(re.findall(r":31C:(.+)", bloc4)),
            tuple(re.findall(r":40E:(.+)", bloc4)),
            tuple(re.findall(r":31D:(.+)", bloc4)),
            tuple(re.findall(r":50:(.+)", bloc4)),
        )

        index_D_700[cle_D_700].append({
            "bloc4": bloc4,
            "bloc2": bloc2,
            "fichier": filepath
        })

    # ------------------------------------------------------------
    # 3. Parcourir les blocs SAA
    # ------------------------------------------------------------

    for message_S in S_messages:
        for bloc_S in message_S["blocs"]:
            # Le bloc correspond déjà directement à un bloc D
            if bloc_S not in missing_in_D:
                continue
            # ====================================================
            # Cas PACS correspondant à O103 / O202 / O200
            # ====================================================

            msgids_S = re.findall(
                r"<pacs:MsgId>\s*(.*?)\s*</pacs:MsgId>", bloc_S, re.S | re.I)
            dates_S = re.findall(
                r"<pacs:IntrBkSttlmDt>\s*(.*?)\s*</pacs:IntrBkSttlmDt>", bloc_S, re.S | re.I)
            montants_S = re.findall(
                r"<pacs:IntrBkSttlmAmt\b[^>]*Ccy=[\"']([A-Z]{3})[\"'][^>]*>\s*(.*?)\s*</pacs:IntrBkSttlmAmt>",bloc_S, re.S | re.I)
            correspondance_pacs = None

            for msgid_S in msgids_S:
                msgid_S = msgid_S.strip()
                for date_S in dates_S:
                    date_S = date_S.strip()
                    for currency_S, amount_S in montants_S:
                        cle_S = (msgid_S, date_S, currency_S.strip().upper(), normalize_amount(amount_S))
                        if cle_S in index_D_pacs and index_D_pacs[cle_S]:
                            correspondance_pacs = index_D_pacs[cle_S].pop(0)
                            break
                    if correspondance_pacs is not None:
                        break
                if correspondance_pacs is not None:
                    break
            if correspondance_pacs is not None:
                # Important : on ajoute le bloc SAA,
                # pas le bloc D.
                blocs_trouves_par_champs.add(bloc_S)
                # Le bloc SAA a déjà été rapproché.
                # Il n'est pas nécessaire de tester ensuite le cas MT700.
                continue

            # ====================================================
            # Cas FIN 700
            # ====================================================

            cle_S_700 = (
                tuple(re.findall(r":27:(.+)", bloc_S)),
                tuple(re.findall(r":40A:(.+)", bloc_S)),
                tuple(re.findall(r":20:(.+)", bloc_S)),
                tuple(re.findall(r":31C:(.+)", bloc_S)),
                tuple(re.findall(r":40E:(.+)", bloc_S)),
                tuple(re.findall(r":31D:(.+)", bloc_S)),
                tuple(re.findall(r":50:(.+)", bloc_S)),
            )

            # Évite de considérer deux blocs sans aucun champ 700
            # comme identiques.
            contient_champ_700 = any(cle_S_700)

            if (contient_champ_700 and cle_S_700 in index_D_700 and index_D_700[cle_S_700]):
                index_D_700[cle_S_700].pop(0)
                blocs_trouves_par_champs.add(bloc_S)

    # ============================================================
    # STATISTIQUES FINALES
    # ============================================================

    # Tous les blocs trouvés ont le même statut final.
    blocs_trouves_directement = set_S & set_D

    blocs_trouves = (blocs_trouves_directement | blocs_trouves_par_champs)
    missing_in_D = set_S - blocs_trouves

    rapport_path = os.path.join(OUTPUT_DIR, "Rapprochement_SAA_vs_D.txt")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(rapport_path, "w", encoding="utf-8") as f:

        # ========================================================
        # RÉSUMÉ
        # ========================================================

        f.write("=== RAPPORT DE RAPPROCHEMENT SAA OUTPUT VS D ===\n\n")
        f.write("=== Résumé ===\n\n")
        f.write(f"Nombre de messages SAA OUTPUT : {len(S_messages)}\n")
        f.write(f"Nombre total de DataBlocks SAA : {nombre_blocs_saa}\n")
        f.write(f"Nombre de blocs SAA uniques : {len(set_S)}\n")
        f.write(f"Nombre de messages D : {len(D_messages)}\n")
        f.write(f"Nombre de blocs SAA trouvés dans D : {len(blocs_trouves)}\n")
        f.write(f"Nombre de blocs SAA uniques absents dans D : {len(missing_in_D)}\n")
        f.write(f"Nombre de doublons globaux dans D : {len(global_duplicates)}\n")

        # ========================================================
        # BLOCS ABSENTS
        # ========================================================

        f.write("\n\n")
        f.write("=" * 100 + "\n")
        f.write("BLOCS SAA ABSENTS DANS D\n")
        f.write("=" * 100 + "\n\n")

        if not missing_in_D:
            f.write("Aucun bloc SAA absent dans D.\n")

        for bloc in missing_in_D:
            for info in s_index[bloc]:
                f.write("Statut : ABSENT_DANS_D\n")
                f.write(f"Type SAA : " f"{info['message_identifier']}\n")
                f.write("Catégories SAA :\n")
                for rp, categorie in info["categories_S"].items():
                    f.write(f"  {rp} -> {categorie}\n")
                f.write("DataBlock SAA :\n")
                f.write(Affiche_bloc(bloc))
                f.write("\n\n")
                f.write("-" * 100)
                f.write("\n\n")

    return (
        len(D_messages),
        len(S_messages),
        nombre_blocs_saa,
        len(blocs_trouves),
        len(missing_in_D),
        len(global_duplicates)
    )

if __name__ == "__main__":

    # ============================================================
    # 1. Parsing
    # ============================================================

    messages_D = parse_messages_D(REPERTOIRE_D)

    messages_S, exemples_par_rp, anomalies_info = parse_messages_s(CHEMIN_FICHIER_S)
    
    (total_D, total_S, total_blocs_SAA, nb_blocs_trouves, nb_blocs_absents, nb_duplicates_globaux) = compare_and_save(messages_D, messages_S, OUTPUT_DIR)

    # ============================================================
    # 3. Création des autres rapports
    # ============================================================

    chemin_anomalies = os.path.join(OUTPUT_DIR, "Anomalies_SAA.txt")
    write_anomalies_report(anomalies_info, chemin_anomalies)
    write_category_reports(messages_S, RAPPORT_DIR)
    write_examples_report(exemples_par_rp,OUTPUT_DIR)

    # ============================================================
    # 4. Affichage
    # ============================================================

    print("Nombre total de messages D :", total_D)
    print("Nombre total de messages SAA OUTPUT :", total_S)
    print("Nombre total de DataBlocks SAA :", total_blocs_SAA)
    print("Nombre de blocs SAA trouvés dans D :", nb_blocs_trouves)
    print("Nombre de blocs SAA absents dans D :", nb_blocs_absents)
    print("Nombre de doublons globaux dans D :", nb_duplicates_globaux)
    print("Rapport de rapprochement :", os.path.join(OUTPUT_DIR, "Rapprochement_SAA_vs_D.txt"))
    print("Rapport des anomalies :", chemin_anomalies)
    print("Rapports par catégorie :", RAPPORT_DIR)
    print("Exemples par routing point :", os.path.join(OUTPUT_DIR, "exemples-messages.txt"))
