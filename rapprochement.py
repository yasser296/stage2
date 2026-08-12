from collections import defaultdict
from decimal import Decimal, InvalidOperation
import html
import os
import re
import shutil
import tempfile
import tarfile
import zipfile
import glob

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data"
OUTPUT_DIR = os.path.join(BASE_DIR, "Output")
RAPPORT_DIR = os.path.join(OUTPUT_DIR, "rapport")

fichiers = glob.glob(os.path.join(BASE_DIR, "EXTRACTION*.zip"))
if not fichiers:
    raise FileNotFoundError(
        f"Aucun fichier EXTRACTION*.zip trouvé dans {BASE_DIR}"
    )
CHEMIN_FICHIER_S = fichiers[-1]

SELECTED_CATEGORIE = "KTP"

chemin_d = os.path.join(BASE_DIR,"D",SELECTED_CATEGORIE)
if os.path.isdir(chemin_d):
    REPERTOIRE_D = chemin_d
elif os.path.isfile(chemin_d + ".zip"):
    REPERTOIRE_D = chemin_d + ".zip"
elif os.path.isfile(chemin_d + ".tar"):
    REPERTOIRE_D = chemin_d + ".tar"
else:
    raise FileNotFoundError(
        f"Aucun dossier ou ZIP trouvé pour {SELECTED_CATEGORIE}"
    )

# CATEGORIES = ["KTP","AGI","delta v9","delta v10","SmartCash","gateway","FTI","openPay RTGS"]


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

def detecter_format_datablock(bloc):
    texte = html.unescape(bloc).strip()
    contient_xml_mx = bool(
        re.search(
            r"<\?xml"
            r"|</?[A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*\b"
            r"|</?(?:Document|AppHdr|GrpHdr)\b",
            texte,
            re.I
        )
    )

    if contient_xml_mx:
        return "MX"
    
    champs_mt = re.findall(
        r"(?:^|\s):\d{2}[A-Z]?:",
        texte,
        re.M
    )
    # On exige au moins deux champs pour éviter les faux positifs
    if len(champs_mt) >= 2:
        return "MT"

    return "INCONNU"

def extraire_datablocks(message):

    message = html.unescape(message)
    datablocks = re.findall(
        r"<DataBlock\b[^>]*>(.*?)</DataBlock>",
        message,
        re.S | re.I
    )
    block = []

    if not datablocks:
            return block 
    
    if len(datablocks) > 1 :
        for bloc in datablocks:
            if detecter_format_datablock(bloc) == "MT":
                bloc_normalise = normalize_delta_bloc(bloc)
                block.append(bloc_normalise)
    else :
        block.append(normalize_delta_bloc(datablocks[0]))      

    return block

def extract_files(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Chemin introuvable : {path}")

    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for fname in files:
                full_path = os.path.join(root, fname)
                with open(full_path, encoding="utf-8") as f:
                    yield f.read(), fname, full_path
    
    elif zipfile.is_zipfile(path):
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
    elif tarfile.is_tarfile(path):
        temp_dir = tempfile.mkdtemp()
        try:
            with tarfile.open(path, "r") as tar:
                tar.extractall(temp_dir, filter="data")
            for root, _, files in os.walk(temp_dir):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    with open(full_path, encoding="utf-8") as f:
                        yield f.read(), fname, full_path
        finally:
            shutil.rmtree(temp_dir)
    else:
        raise ValueError(
            f"Le chemin n'est ni un dossier, ni un ZIP, ni un TAR : {path}"
        )

def parse_messages_D(directory):
    """Extrait tous les couples bloc2/bloc4 de tous les fichiers D."""
    all_messages = []
    for content, fname, full_path in extract_files(directory):
        if fname.endswith(".Z"):
            continue
        matches = re.findall(r"\{2:(.*?)\}.*?\{4:(.*?)\-}", content, re.S)
        for bloc2, bloc4 in matches:
            if bloc2.startswith("I"):
                continue
            bloc4_norm = normalize_delta_bloc(bloc4)
            all_messages.append((bloc4_norm, bloc2.strip(), full_path))
        for body in re.findall(r"<Body>(.*?)</Body>", content, re.S):
                all_messages.append((normalize_delta_bloc(body), "BODY", full_path))
    return all_messages

def parse_messages_s(zip_path):
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Archive S introuvable : {zip_path}")

    all_messages = []
    for content, fname, full_path in extract_files(zip_path):
            messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
            if not messages:
                messages = [content]

            for message in messages:
                if not is_output_message(message):
                    continue

                categories_detectees = detect_categories(message)
                categories = {}

                for routing_point, categorie in categories_detectees.items():
                    if categorie == SELECTED_CATEGORIE:
                        categories[routing_point] = categorie
                if not categories:
                    continue

                msg_id = extract_message_identifier(message)

                NonPrisEnCharge = True
                for catg in categories.values():
                    if catg != "Non prise en charge":
                        NonPrisEnCharge = False

                if NonPrisEnCharge == True:
                    continue

                block = extraire_datablocks(message)

                if not block:
                    all_messages.append({
                        "categories_S": categories,
                        "blocs": [],
                        "nombre_blocs": 0,
                        "message_identifier": msg_id,
                    })
                    continue

                all_messages.append({
                    "categories_S": categories,
                    "blocs": block,
                    "nombre_blocs": len(block),
                    "message_identifier": msg_id,
                })

    return all_messages

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


def compare_and_save(D_messages, S_messages, OUTPUT_DIR):
    
    set_D = set(bloc4 for bloc4, bloc2, path in D_messages)
    set_S = {bloc for msg in S_messages for bloc in msg["blocs"]}
    missing_in_D = set_S - set_D

    # Index pour retrouver les infos d'un bloc SAA absent
    s_index = defaultdict(list)
    k = 0
    for msg in S_messages:
        for bloc in msg["blocs"]:
            s_index[bloc].append(msg)
            if len(s_index[bloc]) > 1:
                k += 1
                print(f"meme bloc dans plusieurs messages est arrives {k} fois")


    # nombre_blocs_saa = sum(len(msg["blocs"]) for msg in S_messages)
    nombre_blocs_saa = len(set_S)

    doublons_saa = sum(
        len(messages) - 1
        for messages in s_index.values()
        if len(messages) > 1
    )

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


            cle_S_700 = (
                tuple(re.findall(r":27:(.+)", bloc_S)),
                tuple(re.findall(r":40A:(.+)", bloc_S)),
                tuple(re.findall(r":20:(.+)", bloc_S)),
                tuple(re.findall(r":31C:(.+)", bloc_S)),
                tuple(re.findall(r":40E:(.+)", bloc_S)),
                tuple(re.findall(r":31D:(.+)", bloc_S)),
                tuple(re.findall(r":50:(.+)", bloc_S)),
            )

            # Évite de considérer deux blocs sans aucun champ 700 comme identiques.
            contient_champ_700 = any(cle_S_700)

            if (contient_champ_700 and (cle_S_700 in index_D_700) and (len(index_D_700[cle_S_700]) > 0)):
                index_D_700[cle_S_700].pop(0)
                blocs_trouves_par_champs.add(bloc_S)


    # Tous les blocs trouvés ont le même statut final.
    blocs_trouves_directement = set_S & set_D

    blocs_trouves = (blocs_trouves_directement | blocs_trouves_par_champs)
    missing_in_D = set_S - blocs_trouves
    

    rapport_path = os.path.join(OUTPUT_DIR, f"Rapprochement_SAA_vs_{SELECTED_CATEGORIE}.txt")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(rapport_path, "w", encoding="utf-8") as f:

        f.write(f"=== RAPPORT DE RAPPROCHEMENT SAA OUTPUT VS {SELECTED_CATEGORIE} ===\n\n")
        f.write("=== Résumé ===\n\n")
        f.write(f"Nombre de messages SAA OUTPUT : {len(S_messages)}\n")
        f.write(f"Nombre total de DataBlocks output SAA uniques : {nombre_blocs_saa}\n") 
        f.write(f"Nombre de messages dans le systeme operant : {len(D_messages)}\n")
        f.write(f"Nombre de blocs output SAA qui ont un match dans le systeme operant : {len(blocs_trouves)}\n")
        if doublons_saa > 0:
            f.write(f"Nombre de DataBlocks SAA dupliqués ignorés : {doublons_saa}\n")

        f.write("\n\n")
        f.write("=" * 100 + "\n")
        f.write("BLOCS SAA ABSENTS DANS D\n")
        f.write("=" * 100 + "\n\n")
        if not missing_in_D:
            f.write("Aucun bloc SAA absent dans D.\n")
        for bloc in missing_in_D:
            info = s_index[bloc][0]
            f.write("Statut : ABSENT_DANS_D\n")
            f.write(f"Type SAA : " f"{info['message_identifier']}\n")
            f.write("Catégories SAA :\n")
            for rp in info["categories_S"].keys():
                f.write(f"  {rp} :\n")
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
        doublons_saa
    )



if __name__ == "__main__":

    messages_D = parse_messages_D(REPERTOIRE_D)
    messages_S = parse_messages_s(CHEMIN_FICHIER_S)
    (total_D, total_S, total_blocs_SAA, nb_blocs_trouves, nb_blocs_absents, doublons_saa) = compare_and_save(messages_D, messages_S, OUTPUT_DIR)
 
    print(f"Nombre total de messages SAA OUTPUT {SELECTED_CATEGORIE}:", total_S)
    print(f"Nombre total de messages du systeme operant {SELECTED_CATEGORIE} :", total_D)
    print(f"Nombre de blocs output presents dans SAA mais absents dans le systeme operant {SELECTED_CATEGORIE} :", nb_blocs_absents)
    print("Rapport de rapprochement :", os.path.join(OUTPUT_DIR, f"Rapprochement_SAA_vs_{SELECTED_CATEGORIE}.txt"))
    if doublons_saa > 0:
        print(f"Nombre de DataBlocks SAA dupliqués ignorés : {doublons_saa}")
