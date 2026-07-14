import html
import os
import re
from collections import Counter
import zipfile
import tempfile
import shutil
from collections import defaultdict

 

def normalize_bloc(text):

    """Nettoie et normalise un bloc pour comparaison."""

    text = text.replace("&#xD;", "\n")

    text = text.replace("&lt;", "<")

    text = text.replace("&gt;", ">")

    text = re.sub(r"\s+", " ", text.strip())

    return text

def Affiche_bloc(text):

    """Nettoie et normalise un bloc Swift pour comparaison champ par champ."""

    text = text.replace("&#xD;", "\n")

    text = re.sub(r"\s+", " ", text.strip())

    parts = re.split(r"(?=:\d{2}[A-Z]?:)", text)

    return "\n".join(p.strip() for p in parts if p.strip())



def detect_category_S(message):
    """
    Détecte seulement les catégories utiles :
    - KTP
    - AGI
    - AUTRE
    """

    message = html.unescape(message)

    if "KONDOR" in message:
        return "KTP"

    if re.search(r"<SessionHolder>\s*SAHAMCartMPout\s*</SessionHolder>", message, re.I):
        return "AGI"

    return "AUTRE"



def parse_messages_D(directory):

    """Extrait blocs {2}{4} et <Body> des fichiers D."""

    all_messages = []

    if not os.path.exists(directory):

        raise FileNotFoundError(f"Répertoire D introuvable : {directory}")

    for root, _, files in os.walk(directory):

        for fname in files:

            full_path = os.path.join(root, fname)

            with open(full_path, encoding="utf-8") as f:

                content = f.read()

            # Recherche {2}{4}

            matches = re.findall(r"\{2:(.*?)\}.*?\{4:(.*?)\-}", content, re.S)

            for bloc2, bloc4 in matches:

                bloc4_norm = normalize_bloc(bloc4)

                all_messages.append((bloc4_norm, bloc2.strip(), full_path))

            # Recherche <Body>

            body_matches = re.findall(r"<Body>(.*?)</Body>", content, re.S)

            for bloc_body in body_matches:

                bloc_body_norm = normalize_bloc(bloc_body)

                all_messages.append((bloc_body_norm, "BODY", full_path))

    return all_messages

 

def parse_messages_S(ZIP_file):
    """
    Décompresse l'archive SAA et extrait les messages OUTPUT.
    Chaque message S contient :
    - bloc : le texte SWIFT normalisé
    - category_S : KTP / DELTA / GI / AUTRE
    - is_converter : True / False
    """

    if not os.path.exists(ZIP_file):
        raise FileNotFoundError(f"Archive S introuvable : {ZIP_file}")

    temp_dir = tempfile.mkdtemp()

    try:

        # Extraction de l'archive .zip

        with zipfile.ZipFile(ZIP_file, "r") as zip_file:
            zip_file.extractall(temp_dir)

        all_messages = []

        anomalies = []

        # debug

        debug_categories_output = Counter()
        debug_categories_extraites = Counter()

        total_output = 0
        total_datablock = 0
        total_text_modified = 0
        total_blocs_extraits = 0

        messages_avec_plusieurs_datablock = 0
        messages_sans_datablock = 0
        surplus_datablock = 0

        # Parcours récursif du contenu extrait

        for root, _, files in os.walk(temp_dir):

            for fname in files:

                full_path = os.path.join(root, fname)

                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                    content_debug = html.unescape(content)

                    # Découper le fichier en messages complets <Message>...</Message>
                    messages = re.findall(r"<Message\b.*?</Message>", content, re.S)

                    # Si le fichier ne contient pas de balise <Message>, on garde l'ancien comportement
                    if not messages:
                        messages = [content]

                    for message in messages:

                        # Garder seulement les messages OUTPUT
                        if not re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
                            continue

                        total_output += 1

                        category_S = detect_category_S(message)

                        debug_categories_output[category_S] += 1

                        # Extraire <DataBlock>
                        matches = re.findall(r"<DataBlock>(.*?)</DataBlock>", message, re.S)
                        
                        # Extraire aussi l'ancien format <Text> Modified data Message text : ...
                        text_matches = re.findall(
                            r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>",
                            message,
                            re.S
                        )

                        blocs_trouves = matches + text_matches

                        if len(blocs_trouves) == 0:
                            messages_sans_datablock += 1

                            anomalies.append({
                                "type": "OUTPUT_SANS_DATABLOCK",
                                "category_S": category_S,
                                "source": full_path,
                                "message": message[:1000]
                            })

                            debug_categories_extraites[category_S] += 1

                            all_messages.append({
                                "category_S": category_S,
                                "blocs": [],
                                "source": full_path,
                                "nombre_blocs": 0,
                                "message_xml": message[:1000]
                            })

                            continue

                        if len(blocs_trouves) > 1:
                            messages_avec_plusieurs_datablock += 1
                            surplus_datablock += len(blocs_trouves) - 1

                            anomalies.append({
                                "type": "OUTPUT_PLUSIEURS_DATABLOCK",
                                "category_S": category_S,
                                "source": full_path,
                                "nombre_blocs": len(blocs_trouves),
                                "message": message[:1000]
                            })

                        total_datablock += len(matches)
                        total_text_modified += len(text_matches)
                        total_blocs_extraits += len(matches) + len(text_matches)

                        blocs_norm = []

                        for bloc in blocs_trouves:
                            bloc_norm = normalize_bloc(bloc)
                            blocs_norm.append(bloc_norm)

                        debug_categories_extraites[category_S] += 1

                        all_messages.append({
                            "category_S": category_S,
                            "blocs": blocs_norm,
                            "source": full_path,
                            "nombre_blocs": len(blocs_norm),
                            "message_xml": message[:1000]
                        })

        print("Total messages OUTPUT :", total_output)
        print("Total DataBlock extraits :", total_datablock)
        print("Total Text Modified extraits :", total_text_modified)
        print("Total blocs extraits :", total_blocs_extraits)


        print("Messages avec plusieurs DataBlock :", messages_avec_plusieurs_datablock)

        # debug ecart resultat

        output_anomalies = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output\Anomalies_SAA.txt"

        os.makedirs(os.path.dirname(output_anomalies), exist_ok=True)

        with open(output_anomalies, "w", encoding="utf-8") as f:
            f.write("=== Anomalies SAA ===\n\n")

            f.write(f"Messages OUTPUT sans DataBlock : {messages_sans_datablock}\n")
            f.write(f"Messages OUTPUT avec plusieurs DataBlock : {messages_avec_plusieurs_datablock}\n")
            f.write(f"Surplus de DataBlock : {surplus_datablock}\n\n")

            for a in anomalies:
                f.write(f"Type : {a['type']}\n")
                f.write(f"Catégorie : {a['category_S']}\n")
                f.write(f"Source : {a['source']}\n")

                if "nombre_blocs" in a:
                    f.write(f"Nombre de blocs : {a['nombre_blocs']}\n")

                f.write("Extrait du message XML :\n")
                f.write(a["message"])
                f.write("\n\n" + "-" * 80 + "\n\n")



        return all_messages

    finally:

        # Nettoyage du dossier temporaire

        shutil.rmtree(temp_dir)

 

def compare_and_save(D_messages, S_messages, output_dir):
    """Compare les messages SAA avec les messages D."""

    os.makedirs(output_dir, exist_ok=True)

    # D_messages est une liste de tuples : (bloc, header, path)
    set_D = set(bloc4 for bloc4, bloc2, path in D_messages)

    # S_messages est une liste de dictionnaires
    set_S = set()

    for msg in S_messages:
        for bloc in msg["blocs"]:
            set_S.add(bloc)

    # Messages présents dans SAA mais absents dans D
    missing_in_D = set_S - set_D

    # Index pour retrouver les infos du message SAA absent
    S_index = defaultdict(list)

    for msg in S_messages:
        for bloc in msg["blocs"]:
            S_index[bloc].append(msg)
    
    nombre_blocs_saa = sum(len(msg["blocs"]) for msg in S_messages)

    with open(os.path.join(output_dir, "Rapprochement_SAA_vs_D.txt"), "w", encoding="utf-8") as f:

        f.write("=== Rapport de rapprochement SAA vs D ===\n\n")

        f.write(f"Nombre de blocs SAA extraits = {len(S_messages)}\n")
        f.write(f"Nombre de messages dans D = {len(D_messages)}\n\n")

        f.write(f"Nombre de messages SAA absents dans D = {len(missing_in_D)}\n")

        f.write("---- Messages présents dans SAA mais absents dans D ----\n\n\n")

        f.write(f"Nombre de messages SAA OUTPUT = {len(S_messages)}\n")
        f.write(f"Nombre de blocs SAA extraits = {nombre_blocs_saa}\n")
        f.write(f"Nombre de messages dans D = {len(D_messages)}\n\n")

        for bloc in missing_in_D:

            infos = S_index[bloc]

            for info in infos:
                f.write("Statut: ABSENT_DANS_D\n")
                f.write(f"Catégorie SAA: {info['category_S']}\n")
                f.write("Text:\n")
                f.write(f"{Affiche_bloc(bloc)}\n\n")

    return (
        len(S_messages),
        len(D_messages),
        len(missing_in_D),
    )

 

# Exemple d'utilisation avec tes chemins

if __name__ == "__main__":

    chemin_fichier_S = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\EXTRACTION0306.zip"

    repertoire_D = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\SGMB-GI"

    output_dir = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output"

    D_msgs = parse_messages_D(repertoire_D)
    S_msgs = parse_messages_S(chemin_fichier_S)



print("Répartition catégories SAA :")
print(Counter(msg["category_S"] for msg in S_msgs))



stats = compare_and_save(D_msgs, S_msgs, output_dir)

print("Messages D trouvés :", len(D_msgs))
print("Blocs SAA extraits :", len(S_msgs))

print("Rapport généré dans :", output_dir)
print("Stats :", stats)

 