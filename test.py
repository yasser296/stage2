import html
import os
import re
from collections import defaultdict
from code2_clean import detect_category_S, ROUTING_POINT_TO_CATEGORY

 # Dictionnaire étendu avec les non-considérés
RP_TO_CAT = {
    "SGMB_KONDOR_EP":        "KTP",
    "KTP_MX_EP":             "KTP",
    "SGMB_CARTHAGO_EP":      "AGI",
    "MATGTOPRINT_EP":        "DELTA",
    "MATGTOPRINT_MX_EP":     "DELTA",
    "SGMB_OPENPAY_CONV_MX":  "openPay",
    "SGTG_OPENPAY_CONV_MX":  "openPay",
    "SGMB_OPENPAY_EP":       "openPay",
    "SGMB_SMARTCASH_EP":     "SmartCash",
    "PRINTMT101EXPDEV_EP":   "PRINTMT",
    "PRINTMT101EXPMAD_EP":   "PRINTMT",
    "PRINTMT101EXPMAD_EPqf": "PRINTMT",
    "SGTG101RECUEP":         "SGTG",
    "PRINTINC_EP":           "PRINTINC",
    "PRTACK_EP":             "PRTRACK",
    "FTI_EP":                "FTI",
    "NOSTRO_MX_EP":          "NOSTRO",
        
        # Nouvelles catégories
    "IMP_08_PRINT_MT":       "IMP",
    "IMP_08_PRINT_MX":       "IMP",
    "IMP_09_PRINT_MX":       "IMP",
    "OCPfaDeltaEP":          "OCPfaDeltaEP",
    "_AI_from_APPLI":        "_AI_from_APPLI",
    "_SI_from_SWIFT":        "_SI_from_SWIFT",
    "_SI_from_SWIFTNet":     "_SI_from_SWIFTNet",
    "_SI_to_SWIFT":          "_SI_to_SWIFT",
    "_SI_to_SWIFTNet":       "_SI_to_SWIFTNet"
}

def lookingCategories():
        T = set()
        PotentialCategories = []
        with open(r"data\EXTRACTION0306.xml", encoding="utf-8") as f:
            content = f.read()
        messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
        for message in messages:
            # Garder seulement les messages OUTPUT
            if re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
                PotentialCategories.extend(re.findall(r"<MessageIdentifier>(.*?)</MessageIdentifier>", message, re.S))
        
        for category in PotentialCategories:
            T.add(category.strip())
        print(T)

def lookingCategories2():
        TypesInCategories = defaultdict(set)

        with open(r"data\EXTRACTION0306.xml", encoding="utf-8") as f:
            content = f.read()
        messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
        if not messages:
            messages = [content]

        for message in messages:
            # Garder seulement les messages OUTPUT
            if not re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
                continue
            
            rps = re.findall(r"<CreatingRoutingPoint>(.*?)</CreatingRoutingPoint>", message, re.S)
            type_match = re.search(r"<MessageIdentifier>(.*?)</MessageIdentifier>", message, re.S)
            if not type_match:
                continue

            msg_type = type_match.group(1).strip()
            for rp in rps:
                rp = rp.strip()
                cat = RP_TO_CAT.get(rp, f"INCONNU ({rp})")
                TypesInCategories[(rp, cat)].add(msg_type)
        # for (rp, cat), types in TypesInCategories.items():
        #     print(f"rp : {rp} | category : {cat} | types : {sorted(set(types))}")
        return TypesInCategories








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
            cat = RP_TO_CAT.get(rp, f"INCONNU ({rp})")
            TypesInCategories[(rp, cat)].add(msg_type)
        # for (rp, cat), types in TypesInCategories.items():
        #     print(f"rp : {rp} | category : {cat} | types : {sorted(set(types))}")
        return TypesInCategories
        

def lookingTypes():
        result = defaultdict(set)
        with open(r"data\EXTRACTION0306.xml", encoding="utf-8") as f:
            content = f.read()
        messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
        for message in messages:
            # Garder seulement les messages OUTPUT
            if re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
                category, rp = detect_category_S(message)
                message_identifier = ""
                message_identifier_match = re.findall(
                    r"<MessageIdentifier\b[^>]*>(.*?)</MessageIdentifier>",
                    html.unescape(message),
                    re.I | re.S
                )
                if message_identifier_match:
                    message_identifier = message_identifier_match.group(1).strip()
                result[rp].update([message_identifier])
                    
        for rp, types in result.items():
            print(f"{rp}, Category: {ROUTING_POINT_TO_CATEGORY.get(rp, 'Unknown')}, Types: {list(types)}")

def verify_message_identifiers():
        with open(r"data\EXTRACTION0306.xml", encoding="utf-8") as f:
            content = f.read()
            
        messages = re.findall(r"<Message\b.*?</Message>", content, re.S)
        
        total_output = 0
        anomalies_0 = 0
        anomalies_multiple = 0
        
        for message in messages:
            if re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
                total_output += 1
                # On compte le nombre de balises MessageIdentifier ouvrantes
                identifiers = re.findall(r"<MessageIdentifier\b[^>]*>", message, re.I)
                count = len(identifiers)
                
                if count == 0:
                    anomalies_0 += 1
                elif count > 1:
                    anomalies_multiple += 1
                    
        print("\n=== Vérification des MessageIdentifier ===")
        print(f"Total des messages OUTPUT analysés : {total_output}")
        print(f"Messages avec 0 MessageIdentifier : {anomalies_0}")
        print(f"Messages avec plusieurs MessageIdentifier : {anomalies_multiple}")
        
        if anomalies_0 == 0 and anomalies_multiple == 0:
            print("-> SUCCÈS : Tous les messages OUTPUT ont exactement une seule balise MessageIdentifier.\n")
        else:
            print("-> ANOMALIE : Certains messages ne respectent pas la règle d'unicité.\n")

import re

def extract_all_types():
    print("Recherche de tous les types (MessageIdentifier) disponibles...")
    types_found = set()
    
    # Lecture du fichier d'extraction
    with open(r"data\EXTRACTION0306.xml", encoding="utf-8") as f:
        content = f.read()

    # Découpage du fichier en messages (tolérant aux éventuels namespaces comme <saa:Message>)
    messages = re.findall(r"<[a-zA-Z0-9:]*Message\b.*?</[a-zA-Z0-9:]*Message>", content, re.I | re.S)
    
    # Sécurité : Si les balises <Message> sont absentes, on traite tout le fichier d'un coup
    if not messages:
        messages = [content]

    # Traitement de chaque message isolé
    for message in messages:
        # On vérifie que c'est bien un message OUTPUT
        if re.search(r"<[a-zA-Z0-9:]*SubFormat>\s*OUTPUT\s*</[a-zA-Z0-9:]*SubFormat>", message, re.I):
            
            # Extraction du type via MessageIdentifier
            match = re.search(r"<[a-zA-Z0-9:]*MessageIdentifier\b[^>]*>(.*?)</[a-zA-Z0-9:]*MessageIdentifier>", message, re.I | re.S)
            
            # Si on a trouvé la balise, on l'ajoute à la liste (le set() empêche les doublons)
            if match:
                types_found.add(match.group(1).strip())
                
    # Affichage des résultats
    print(f"\nTotal de types uniques trouvés : {len(types_found)}")
    print("Liste détaillée :")
    for t in sorted(types_found):
        print(f" - {t}")






def normalize_bloc(text):
    """Nettoie et normalise un bloc pour comparaison."""
    text = text.replace("&#xD;", "\n")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = re.sub(r"\s+", " ", text.strip())
    return text

def extract_messages_OUTPUT_from_file(source):
    result = []
    with open(source, "r", encoding="utf-8") as f:
        content = f.read()
    messages = re.findall(r"<message>(.*?)</message>", content, re.S)
    if not messages:
        messages = [content]
    for message in messages:
        # Garder seulement les messages OUTPUT
        if not re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I):
            continue
        normalize_bloc(message)
        result.append((message, source))
    return result

def extraire_datablock(message):
    """Extrait le bloc de données d'un message."""
    anomalies = []
    matches = re.findall(r"<DataBlock>(.*?)</DataBlock>", message, re.S)
    text_matches = re.findall(
                        r"<Text>\s*Modified data\s*Message text\s*:(.*?)</Text>",
                        message,
                        re.S
                    )
    blocs_trouves = matches + text_matches
    blocs_norm = [normalize_bloc(bloc) for bloc in blocs_trouves]

    category_S, rp_S = detect_category_S(message)

    # Aucun DataBlock trouvé → anomalie
    if len(blocs_trouves) == 0:
        anomalies.append({
            "type": "OUTPUT_SANS_DATABLOCK",
            "category_S": category_S,
            "message": message
        })
        return [], anomalies

    # Plusieurs DataBlock trouvés → anomalie mais on renvoie quand même les blocs normalisés
    if len(blocs_trouves) > 1:
        anomalies.append({
            "type": "OUTPUT_PLUSIEURS_DATABLOCK",
            "category_S": category_S,
            "nombre_blocs": len(blocs_trouves),
            "message": message
        })

    return blocs_norm, anomalies

import collections

def extract_types_per_category():
    print("Recherche des types par catégorie (OUTPUT uniquement)...")
    
   

    category_to_types = collections.defaultdict(set)
    
    with open(r"data\EXTRACTION0306.xml", encoding="utf-8") as f:
        content = f.read()

    # Tolérance aux namespaces
    messages = re.findall(r"<[a-zA-Z0-9:]*Message\b.*?</[a-zA-Z0-9:]*Message>", content, re.I | re.S)
    if not messages:
        messages = [content]

    for message in messages:
        # Seulement les messages OUTPUT
        if not re.search(r"<[a-zA-Z0-9:]*SubFormat>\s*OUTPUT\s*</[a-zA-Z0-9:]*SubFormat>", message, re.I):
            continue
            
        # Extraire le type du message
        type_match = re.search(r"<[a-zA-Z0-9:]*MessageIdentifier\b[^>]*>(.*?)</[a-zA-Z0-9:]*MessageIdentifier>", message, re.I | re.S)
        if not type_match:
            continue
            
        msg_type = type_match.group(1).strip()
        
        # Extraire TOUS les Routing Points présents dans le message
        rps = re.findall(r"<[a-zA-Z0-9:]*CreatingRoutingPoint\b[^>]*>(.*?)</[a-zA-Z0-9:]*CreatingRoutingPoint>", message, re.I | re.S)
        
        if not rps:
            category_to_types["SANS_ROUTING_POINT"].add(msg_type)
        else:
            for rp in rps:
                rp = rp.strip()
                # On détermine la catégorie, ou on garde le RP s'il est inconnu
                cat = RP_TO_CAT.get(rp, f"INCONNU ({rp})")
                category_to_types[cat].add(msg_type)
                
    # Affichage des résultats
    print("\n--- Types de messages possibles par Catégorie ---")
    for cat in sorted(category_to_types.keys()):
        types_list = sorted(list(category_to_types[cat]))
        print(f"\n{cat} :")
        # Affichage propre, 5 types par ligne
        for i in range(0, len(types_list), 5):
            print("  " + ", ".join(types_list[i:i+5]))

def extract_Type(message):
    message_identifier = ""
    message_identifier_match = re.findall(
        r"<MessageIdentifier\b[^>]*>(.*?)</MessageIdentifier>",
        html.unescape(message),
        re.I | re.S
    )
    if message_identifier_match:
        message_identifier = message_identifier_match.group(1).strip()
        return message_identifier
    else :
        return None

def CreateRapport(dataBlockList, message):
    print("Création du rapport de rapprochement GI vs SAA...")
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
                f.write(f"\n\n=== Rapport {cat} , Routing Point: {rp} === Type: {type} \n\n")
             
            nbr = 1
            for block in dataBlockList:
                f.write(f" DataBlock: {nbr} \n")
                nbr += 1
                f.write(block)
    print("Rapport créé avec succès.")

def main():
    # lookingCategories()
    # lookingCategories2()
    # extract_types_per_category()
    CreateRapport()
    # extract_all_types()
    # lookingTypes()
    # verify_message_identifiers()

if __name__ == "__main__":
    main()