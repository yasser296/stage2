import html
import os
import re
import shutil
import tempfile
import zipfile
import random
import string

from file2 import detect_categories, extract_message_identifier, is_output_message, normalize_delta_bloc

BASE_DIR = r"C:\Users\msi\Desktop\stage2\Nouveau dossier"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "Output")
RAPPORT_DIR = os.path.join(OUTPUT_DIR, "rapport")

CHEMIN_FICHIER_S = os.path.join(DATA_DIR, "EXTRACTION0306.zip")
REPERTOIRE_D = os.path.join(DATA_DIR, "D")


def extraire_datablocks(message):
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
    return blocs


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


def parse_messages_s(zip_path):
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Archive S introuvable : {zip_path}")

    all_messages = []
    exemples_par_rp = {}

    for content, fname, full_path in extract_files(zip_path):
            messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
            if not messages:
                messages = [content]

            for message in messages:
                if not is_output_message(message):
                    continue

                categories = detect_categories(message)
                msg_id = extract_message_identifier(message)
                blocs = extraire_datablocks(message)

                # Un exemple par routing point
                for rp, cat in categories.items():
                    if rp not in exemples_par_rp:
                        exemples_par_rp[rp] = (cat, message)

                if not blocs:
                    all_messages.append({
                        "categories_S": categories,
                        "blocs": [],
                        "nombre_blocs": 0,
                        "message_identifier": msg_id,
                    })
                    continue

                all_messages.append({
                    "categories_S": categories,
                    "blocs": blocs,
                    "nombre_blocs": len(blocs),
                    "message_identifier": msg_id,
                })
    return all_messages, exemples_par_rp

def write_D_files(s_messages, repertoire_D):
    """Écrit un fichier de rapport par catégorie/routing point."""
    shutil.rmtree(repertoire_D, ignore_errors=True)
    os.makedirs(repertoire_D, exist_ok=True)
    n = 0
    nb_messages_fin = 0
    for msg in s_messages:
        message_identifier = msg["message_identifier"]
        type = re.fullmatch(
            r"fin\.(\d{3})",
            message_identifier.strip(),
            re.I
        )
        if not type:
            continue

        type = type.group(1)
        
        if not msg["blocs"]:
            continue

        
        nb_messages_fin += 1
        for rp, cat in msg["categories_S"].items():
            if cat.upper().startswith("NON PRISE EN CHARGE") or cat == "SANS_ROUTING_POINT":
                continue
            n += 1
            cat_dir = os.path.join(repertoire_D, cat)
            os.makedirs(cat_dir, exist_ok=True)
            file_path = os.path.join(cat_dir, f"{rp}{n}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(rf"{{1:F01{generer_String()}}}")
                f.write(rf"{{2:O{type}{generer_String()}}}")
                f.write("{4:\n")
                for block in msg["blocs"]:
                    f.write(block)
                f.write("\n-}")
    print(nb_messages_fin)
    # nb messages fin : 3418
    # nb messages fin (categories prises en charges) : 1539

# def generer_identifiant():
#     # 1. Génère un nombre à 3 chiffres (entre 100 et 999)
#     nombre = random.randint(100, 999)
#     # 2. Définit la longueur de la chaîne (ici 14 maximum)
#     longueur_string = 14
#     # 3. Génère la chaîne en majuscules et chiffres
#     caracteres = string.ascii_uppercase + string.digits
#     chaine = "".join(random.choices(caracteres, k=longueur_string))
#     # 4. Combine les deux parties
#     return f"{nombre}{chaine}"

def generer_String():
    # 2. Définit la longueur de la chaîne (ici 14 maximum)
    longueur_string = 14
    # 3. Génère la chaîne en majuscules et chiffres
    caracteres = string.ascii_uppercase + string.digits
    chaine = "".join(random.choices(caracteres, k=longueur_string))
    # 4. Combine les deux parties
    return f"{chaine}"


if __name__ == "__main__":



    messages_S, exemples_par_rp = parse_messages_s(CHEMIN_FICHIER_S)
    
    
    write_D_files(messages_S, REPERTOIRE_D)
