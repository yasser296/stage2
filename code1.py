import os
import re
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

    Décompresse l'archive .zip

    """

    if not os.path.exists(ZIP_file):

        raise FileNotFoundError(f"Archive S introuvable : {ZIP_file}")

   

    # Crée un dossier temporaire pour extraire l'archive

    temp_dir = tempfile.mkdtemp()

    try:

        # Extraction de l'archive .zip

        with zipfile.ZipFile(ZIP_file, "r") as zip:

            zip.extractall(temp_dir)

       

        all_messages = []

        # Parcours récursif du contenu extrait

        for root, _, files in os.walk(temp_dir):

            for fname in files:

                    # Nouveau nom avec extension .txt

                    new_name = os.path.splitext(fname)[0] + ".txt"

                    old_path = os.path.join(root, fname)

                    new_path = os.path.join(root, new_name)

                   

                    # Renommer le fichier

                    os.rename(old_path, new_path)

                    # Lire le contenu comme texte

                    with open(new_path, encoding="utf-8") as f:

                        content = f.read()

                        matches = re.findall(r"<DataBlock>(.*?)</DataBlock>", content, re.S)

                        text_matches = re.findall(r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>", content, re.S)

                        for bloc in  matches + text_matches:

                            bloc_norm = normalize_bloc(bloc)

                            all_messages.append(bloc_norm)

        return all_messages

    finally:

        # Nettoyage du dossier temporaire

        shutil.rmtree(temp_dir)

 

def compare_and_save(D_messages, S_messages, output_dir):

    """Compare blocs D et S pour doublons et absents."""

    os.makedirs(output_dir, exist_ok=True)

    # Indexation des sources

    source_map = defaultdict(list)

    for bloc4, bloc2, path in D_messages:

        source_map[bloc4].append((bloc2, path))

 

    # Détection doublons

    duplicates = [bloc for bloc, paths in source_map.items() if len(paths) > 1]

 

    # Détection absents

    set_D = set(bloc4 for bloc4, bloc2, path in D_messages)

    set_S = set(S_messages)

    missing_in_S = set_D - set_S

 

    # Rapport complet

    with open(os.path.join(output_dir, "Rapprochement_GI.txt"), "w", encoding="utf-8") as f:

        f.write("=== Rapport de rapprochement GI vs SAA ===\n\n")

        f.write(f"Nombre de messages émis par GI = {len(D_messages)}\n")

        f.write(f"Nombre de messages Absents dans SAA = {len(missing_in_S)}\n\n")

        f.write(f"---- Ces messages ont été envoyés par le système opérant mais ne figurent pas dans SAA : ----\n\n\n")

 

        for bloc4, bloc2, path in D_messages:

            if bloc4 in duplicates:

                status = "DOUBLON"

            elif bloc4 in missing_in_S:

                status = "ABSENT"

                f.write(f"Statut: {status}\nHeader: {bloc2}\nText:\n{Affiche_bloc(bloc4)}\n\n")

                #f.write(f"Statut: {status}\nHeader: {bloc2}\nText:\n{bloc4}\nSource: {path}\n\n")

            else:

                status = "OK"

            #f.write(f"Statut: {status}\nBloc2: {bloc2}\nSource: {path}\nBloc:\n{bloc4}\n\n")

 

    return (len(D_messages), len(S_messages), len(duplicates), len(missing_in_S))

 

# Exemple d'utilisation avec tes chemins

if __name__ == "__main__":

    chemin_fichier_S = r"C:/Users/Documents/Documentation/Rapprochement/Extraction_SAA/EXTRACTION0306.zip"

    repertoire_D = r"C:/Users/Documents/Documentation/Rapprochement/SO/SGMB-GI"

    output_dir = r"C:/Users/Documents/Documentation/Rapprochement"

 

    D_msgs = parse_messages_D(repertoire_D)

    S_msgs = parse_messages_S(chemin_fichier_S)

    stats = compare_and_save(D_msgs, S_msgs, output_dir)

 

    #print("Rapport généré dans:", output_dir)

    #print("Stats:", stats)

 