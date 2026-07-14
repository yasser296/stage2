import html
import os
import re
from collections import Counter, defaultdict
import zipfile
import tempfile
import shutil




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

def extraire_datablock(message, message_identifier):
    """Extrait le bloc de données d'un message."""
    anomalies = []
    matches = re.findall(r"<DataBlock>(.*?)</DataBlock>", message, re.S)
    text_matches = re.findall(
        r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>",
        message,
        re.S
    )
    external_files_matches = re.findall(r"<PayloadPhysicalFileName>(.*?)</PayloadPhysicalFileName>", message, re.S)
    blocs = matches + text_matches + external_files_matches
    blocs_trouves = matches + text_matches 
    blocs_norm = [normalize_bloc(bloc) for bloc in blocs]
    category_S, rp_S = detect_category_S(message)
    if len(blocs_trouves) == 0:
        if (blocs) == 0:
            anomalies.append({
            "type": "OUTPUT_SANS_DATABLOCK",
            "category_S": category_S,
            "message": message,
            "message_identifier": message_identifier
                        })

    if len(blocs_trouves) > 1:
        anomalies.append({
            "type": "OUTPUT_PLUSIEURS_DATABLOCK",
            "category_S": category_S,
            "nombre_blocs": len(blocs_trouves),
            "message": message,
            "message_identifier": message_identifier
        })
    return blocs_norm, anomalies

def lookingCategories3(message):
        TypesInCategories = defaultdict(set)

        # Garder seulement les messages OUTPUT
        if not re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
            return "Message non OUTPUT"
            
        rps = re.findall(r"<CreatingRoutingPoint>(.*?)</CreatingRoutingPoint>", message, re.S)
        type_match = re.search(r"<MessageIdentifier>(.*?)</MessageIdentifier>", message, re.S)
        if not type_match:
            return "Aucun MessageIdentifier trouvé"

        msg_type = type_match.group(1).strip()
        for rp in rps:
            rp = rp.strip()
            cat = ROUTING_POINT_TO_CATEGORY.get(rp, f"NON PRIS EN CHARGE ({rp})")
            TypesInCategories[(rp, cat)].add(msg_type)
        # for (rp, cat), types in TypesInCategories.items():
        #     print(f"rp : {rp} | category : {cat} | types : {sorted(set(types))}")
        return TypesInCategories

CATEGORIES = ["KTP","AGI","Delta v9","openPay","SmartCash","FTI","PRINTMT","SGTG","PRTRACK"]

# Mapping CreatingRoutingPoint -> Catégorie
ROUTING_POINT_TO_CATEGORY = {
    "SGMB_KONDOR_EP":        "KTP",
    "KTP_MX_EP":             "KTP",
    "SGMB_CARTHAGO_EP":      "AGI",
    "SGMB_OPENPAY_CONV_MX":  "Delta v9", # convertisseur
    "SGTG_OPENPAY_CONV_MX":  "Delta v9", # convertisseur
    "SGMB_OPENPAY_EP":       "openPay",
    "SGMB_SMARTCASH_EP":     "SmartCash",
    "MATGTOPRINT_EP":        "Delta v9",
    "MATGTOPRINT_MX_EP":     "Delta v9",
    "PRINTMT101EXPDEV_EP":   "PRINTMT",
    "PRINTMT101EXPMAD_EP":   "PRINTMT",
    "SGTG101RECUEP":         "SGTG",
    "PRINTINC_EP":           "PRINTINC",
    "PRTACK_EP":             "PRTRACK",
    "FTI_EP":                "FTI",
    "NOSTRO_MX_EP":          "SmartCash",
}


def detect_category_S(message):
    """
    Détecte la catégorie d'un message OUTPUT
    via les balises <CreatingRoutingPoint>.
    Un message peut contenir plusieurs routing points :
    on priorise celui qui correspond à une catégorie connue.
    """
    message_unesc = html.unescape(message)
    all_rp = re.findall(
        r"<CreatingRoutingPoint>\s*(\S+?)\s*</CreatingRoutingPoint>",
        message_unesc,
        re.I
    )

    if not all_rp:
        return "SANS_ROUTING_POINT", "AUCUN"

    # Chercher le premier routing point qui correspond à une catégorie connue
    for rp in all_rp:
        if rp in ROUTING_POINT_TO_CATEGORY:
            return ROUTING_POINT_TO_CATEGORY[rp], rp

    # Aucun routing point connu trouvé
    return "INCONNU:" + all_rp[0], all_rp[0]


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
    - blocs : les textes SWIFT normalisés
    - category_S : KTP / AGI / AUTRE
    """
    if not os.path.exists(ZIP_file):
        raise FileNotFoundError(f"Archive S introuvable : {ZIP_file}")

    temp_dir = tempfile.mkdtemp()

    shutil.rmtree(r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output\rapport")
    os.makedirs(r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output\rapport")

    try:
        with zipfile.ZipFile(ZIP_file, "r") as zip_file:
            zip_file.extractall(temp_dir)

        all_messages = []
        anomalies = []
        exemples_par_identificateur = {}  # Un exemple de message XML par identificateur (Routing Point)

        messages_avec_plusieurs_datablock = 0
        messages_sans_datablock = 0
        surplus_datablock = 0

        for root, _, files in os.walk(temp_dir):
            for fname in files:
                full_path = os.path.join(root, fname)
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()
                # Découper le fichier en messages complets <Message>...</Message>
                messages = re.findall(r"<Message\b.*?</Message>", content, re.S)

                if not messages:
                    messages = [content]

                for message in messages:

                    # Garder seulement les messages OUTPUT
                    if not re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
                        continue

                    category_S, rp_S = detect_category_S(message)

                    # Collecter un exemple par identificateur
                    if rp_S not in exemples_par_identificateur:
                        exemples_par_identificateur[rp_S] = (category_S, message)

                    message_identifier = extract_Type(message)
                    blocs_trouves, anomalies_list = extraire_datablock(message , message_identifier)
                    anomalies.extend(anomalies_list)

                    

                    if len(blocs_trouves) == 0:
                        messages_sans_datablock += 1

                        all_messages.append({
                            "category_S": category_S,
                            "blocs": [],
                            "nombre_blocs": 0,
                            "message_identifier": message_identifier,
                        })
                        continue

                    if len(blocs_trouves) > 1:
                        messages_avec_plusieurs_datablock += 1
                        surplus_datablock += len(blocs_trouves) - 1

                    all_messages.append({
                        "category_S": category_S,
                        "blocs": blocs_trouves,
                        "nombre_blocs": len(blocs_trouves),
                        "message_identifier": message_identifier,
                    })

                    
                    CreateRapport(blocs_trouves, message)

        # Écriture du fichier d'anomalies
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
                f.write(f"message_identifier : {a['message_identifier']}\n")

                if "nombre_blocs" in a:
                    f.write(f"Nombre de blocs : {a['nombre_blocs']}\n")

                f.write("Extrait du message XML :\n")
                f.write(a["message"])
                f.write("\n\n" + "-" * 100 + "\n\n")

        return all_messages, exemples_par_identificateur
        
    finally:
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
        f.write(f"Nombre de messages SAA OUTPUT = {len(S_messages)}\n")
        f.write(f"Nombre de blocs SAA extraits = {nombre_blocs_saa}\n")
        f.write(f"Nombre de messages dans D = {len(D_messages)}\n\n")
        f.write(f"Nombre de blocs SAA absents dans D = {len(missing_in_D)}\n")
        f.write("---- Messages présents dans SAA mais absents dans D ----\n\n")

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


def ecrire_exemples(exemples_par_identificateur, output_dir):
    """Écrit un fichier avec un exemple de message XML par identificateur (Routing Point)."""
    os.makedirs(output_dir, exist_ok=True)
    chemin = os.path.join(output_dir, "exemples-messages.txt")

    with open(chemin, "w", encoding="utf-8") as f:
        f.write("=== Exemple de message par identificateur ===\n\n")

        for identificateur in sorted(exemples_par_identificateur):
            categorie, message = exemples_par_identificateur[identificateur]
            
            # Recherche du contenu de la balise <MessageIdentifier>
            message_identifier_match = re.search(
                r"<MessageIdentifier\b[^>]*>(.*?)</MessageIdentifier>",
                html.unescape(message),
                re.I | re.S
            )
            if message_identifier_match:
                message_identifier = message_identifier_match.group(1).strip()
                type_str = f" | MESSAGE IDENTIFIER : {message_identifier}"
            else:
                type_str = ""


            SUmid_match = re.search(
                r"<SUmid\b[^>]*>(.*?)</SUmid>",
                html.unescape(message),
                re.I | re.S
            )
            # <SUmid>{sumid_recherche}</SUmid>
            if SUmid_match:
                SUmid = SUmid_match.group(1).strip()
                MessageId = f" | SUmid : {SUmid}"
            else:
                MessageId = ""

            blocs_trouves, _ = extraire_datablock(message , message_identifier)
            
            f.write("=" * 80 + "\n")
            f.write(f"CATÉGORIE : {categorie}{type_str} | IDENTIFICATEUR : {identificateur}\n")
            f.write(f"MessageId : {MessageId}\n")
            f.write("=" * 80 + "\n\n")
            for bloc in blocs_trouves :
                f.write(html.unescape(f"{bloc} + \n"))           
            f.write("\n\n")

    print(f"Fichier d'exemples généré : {chemin}")

def extract_Type(message):
    message_identifier_match = re.search(
        r"<MessageIdentifier\b[^>]*>(.*?)</MessageIdentifier>",
        html.unescape(message),
        re.I | re.S
    )
    if message_identifier_match:
        return message_identifier_match.group(1).strip()
    else:
        return None

def CreateRapport(dataBlockList, message):
    # print("Création du rapport de rapprochement GI vs SAA...")
    typesInCategorie = lookingCategories3(message)
    cles = list(typesInCategorie.keys())
    type = extract_Type(message)
    for (rp, cat) in cles:
        path = rf"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output\rapport\{cat}-{rp}.txt"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Si le rapport existe déjà, on ajoute ; sinon on crée et écrit l'en-tête
        file_exists = os.path.exists(path)
        mode = "a" if file_exists else "w"
        with open(path, mode, encoding="utf-8") as f:
            if not file_exists:
                f.write(f"=== Rapport {cat} , Routing Point: {rp} === \n\n\n")
            # f.write("\n" + "=" * 80 + "\n\n\n")
            f.write(f"Type: {type} \n")
            nbr = 1
            for i, block in enumerate(dataBlockList):
                f.write(f" DataBlock: {nbr} \n")
                nbr += 1
                f.write(block)
                if i < len(dataBlockList) - 1:  # N'écrit pas la ligne pour le dernier élément
                    f.write("\n" + "-" * 100 + "\n")
            f.write("\n\n\n" + "=" * 80 + "\n\n\n")
            
    # print("Rapport créé avec succès.")


if __name__ == "__main__":

    chemin_fichier_S = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\EXTRACTION0306.zip"
    repertoire_D = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\SGMB-GI"
    output_dir = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output"

    D_msgs = parse_messages_D(repertoire_D)
    S_msgs, exemples = parse_messages_S(chemin_fichier_S)

    # Résumé console
    print("Catégories SAA :", Counter(msg["category_S"] for msg in S_msgs))
    print("Messages D trouvés :", len(D_msgs))
    print("Messages SAA extraits :", len(S_msgs))

    ecrire_exemples(exemples, output_dir)

    stats = compare_and_save(D_msgs, S_msgs, output_dir)
    print("Rapport généré dans :", output_dir)
