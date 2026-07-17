from collections import defaultdict
import os
import re
import shutil
import tempfile
import zipfile

def normalize_bloc(text):
    """Nettoie et normalise un bloc Swift pour comparaison champ par champ."""
    text = text.replace("&#xD;", "\n")
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?=:\d{2}[A-Z]?:)", text)
    return "\n".join(p.strip() for p in parts if p.strip())

def extract_Files(path):
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


def extract_pacs_msgid_from_file(zip_file):
    all_msgids = []
    for content, _ , _ in extract_Files(zip_file):
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
    for content, _ , _ in extract_Files(zip_file) :
        blocks = re.findall(r"<DataBlock>(.*?)</DataBlock>", content, re.S)
        for bloc in blocks:
            dates = re.findall(r"&lt;pacs:IntrBkSttlmDt&gt;(.*?)&lt;/pacs:IntrBkSttlmDt&gt;", bloc)
            montants = re.findall(r"&lt;pacs:IntrBkSttlmAmt Ccy=\"([A-Z]{3})\"&gt;(.*?)&lt;/pacs:IntrBkSttlmAmt&gt;", bloc)
            for d in dates:
                for ccy, amt in montants:
                    triplets.add((d.strip(), ccy.strip(), amt.strip()))
    return triplets
    
def parse_messages_D(directory):
    """Extrait tous les couples bloc2/bloc4 de tous les fichiers D."""
    all_messages = []
    for content, fname, full_path in extract_Files(directory):
        if fname.endswith(".Z"):
            continue
        bloc2_match = re.search(r"\{2:(.*?)\}", content)
        if bloc2_match:
            bloc2 = bloc2_match.group(1)
            if bloc2.startswith("O"):
                continue
        matches = re.findall(r"\{2:(.*?)\}.*?\{4:(.*?)\-}", content, re.S)
        for bloc2, bloc4 in matches:
            bloc4_norm = normalize_bloc(bloc4)
            all_messages.append((bloc4_norm, bloc2.strip(), full_path))
    return all_messages

def parse_messages_S(zip_file):
    """Extrait tous les couples bloc2/bloc4 de tous les fichiers D."""
    all_messages = []
    for content, fname, full_path in extract_Files(zip_file):
        matches = re.findall(r"<DataBlock>(.*?)</DataBlock>", content, re.S)
        text_matches = re.findall(r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>", content, re.S)
        for bloc in  matches + text_matches:
            bloc_norm = normalize_bloc(bloc)
            all_messages.append(bloc_norm)
    return all_messages

    
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

def compare_and_save(D_messages, S_messages, msgids, output_dir, chemin_fichier_S):
    """Compare blocs D/S :
       - rapproche MsgId + champ32A pour bloc2 = I103/I202/I200
       - rapproche champ par champ pour bloc2 = I700
    """
    os.makedirs(output_dir, exist_ok=True)

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
    set_S = set(S_messages)
    missing_in_S = set_D - set_S

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
    missing_in_S = missing_in_S - matched_blocs

    with open(os.path.join(output_dir, "Rapprochement_DELTA.txt"), "w", encoding="utf-8") as f:
        f.write("=== Rapport de rapprochement DELTA vs SAA ===\n\n")
        f.write(f"Nombre de messages émis par Delta  = {len(D_messages)}\n")
        f.write(f"Nombre de messages Absents dans SAA = {len(missing_in_S)}\n\n")
        f.write(f"----------- Ces messages ont été envoyés par le système opérant mais ne figurent pas dans SAA : -----------\n\n\n")
        for bloc in missing_in_S:
            for (bloc2, bloc4), paths in global_source_map.items():
                if bloc4 == bloc:
                    f.write(f"Header: {bloc2}\nText:\n{bloc4}\n\n")
    return (len(blocs_i_only), len(D_messages), len(S_messages),
            len(duplicates), len(global_duplicates),
            len(missing_in_S), len(rapprochements))

# === Exemple d’utilisation ===
chemin_fichier_S = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\EXTRACTION0306.zip"
repertoire_D = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\SGMB-GI"
output_dir = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output"

if __name__ == "__main__":

    # Parsing des messages
    messages_D = parse_messages_D(repertoire_D)
    messages_S = parse_messages_S(chemin_fichier_S)
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
