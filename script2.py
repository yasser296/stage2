from collections import Counter
import os
import re
import html

from file2 import extract_files, extract_message_identifier, extract_sumid, is_output_message

BASE_DIR = r"C:\Users\msi\Desktop\stage2\Nouveau dossier"
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "Output")

CHEMIN_FICHIER_S = os.path.join(DATA_DIR, "EXTRACTION0306.zip")


def detect_traitement_special_saa(message):
    """
    Détecte les messages SAA qui correspondent aux traitements spéciaux :
    - pacs avec MsgId + date + montant
    - fin.700 ou bloc contenant les champs du MT700
    """

    message_unesc = html.unescape(message)
    msg_id = extract_message_identifier(message_unesc)

    # Cas équivalent I103 / I202 / I200 côté SAA
    # Le traitement spécial cherche pacs:MsgId + IntrBkSttlmDt + IntrBkSttlmAmt
    has_pacs_msgid = re.search(r"<pacs:MsgId>\s*.*?\s*</pacs:MsgId>", message_unesc, re.S | re.I)
    has_pacs_date = re.search(r"<pacs:IntrBkSttlmDt>\s*.*?\s*</pacs:IntrBkSttlmDt>", message_unesc, re.S | re.I)
    has_pacs_amount = re.search(r"<pacs:IntrBkSttlmAmt\b[^>]*>\s*.*?\s*</pacs:IntrBkSttlmAmt>", message_unesc, re.S | re.I)

    if has_pacs_msgid and has_pacs_date and has_pacs_amount:
        return "PACS_EQUIVALENT_I103_I202_I200"

    # Cas équivalent I700 côté SAA
    if msg_id == "fin.700":
        return "FIN700"

    champs_700 = [":27:", ":40A:", ":20:", ":31C:", ":40E:", ":31D:", ":50:"]
    if all(champ in message_unesc for champ in champs_700):
        return "FIN700_CHAMPS"

    return None


def rassembler_messages_traitement_special_saa(zip_saa, output_file):
    messages_speciaux = []
    compteur_types = Counter()

    for content, fname, full_path in extract_files(zip_saa):
        messages = re.findall(r"<Message\b.*?</Message>", content, re.S | re.I)

        if not messages:
            messages = [content]

        for message in messages:
            message_unesc = html.unescape(message)

            traitement = detect_traitement_special_saa(message_unesc)

            if traitement:
                msg_id = extract_message_identifier(message_unesc)
                sumid = extract_sumid(message_unesc)
                subformat = "OUTPUT" if is_output_message(message_unesc) else "NON_OUTPUT"

                messages_speciaux.append({
                    "traitement": traitement,
                    "message_identifier": msg_id,
                    "sumid": sumid,
                    "subformat": subformat,
                    "fichier": full_path,
                    "message_xml": message_unesc
                })

                compteur_types[(traitement, msg_id, subformat)] += 1

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== Messages SAA avec traitement spécial ===\n\n")
        f.write(f"Nombre total : {len(messages_speciaux)}\n\n")

        f.write("Répartition :\n")
        for (traitement, msg_id, subformat), nb in compteur_types.items():
            f.write(f"{traitement} | {msg_id} | {subformat} : {nb}\n")

        f.write("\n" + "=" * 100 + "\n\n")

        for i, msg in enumerate(messages_speciaux, start=1):
            f.write(f"Message {i}\n")
            f.write(f"Traitement : {msg['traitement']}\n")
            f.write(f"MessageIdentifier : {msg['message_identifier']}\n")
            f.write(f"SUmid : {msg['sumid']}\n")
            f.write(f"SubFormat : {msg['subformat']}\n")
            f.write(f"Fichier : {msg['fichier']}\n")
            f.write("Message XML :\n")
            f.write(msg["message_xml"])
            f.write("\n\n" + "-" * 100 + "\n\n")

    return len(messages_speciaux), compteur_types


output_special = os.path.join(OUTPUT_DIR, "messages_SAA_traitement_special.txt")

nb_speciaux, compteur_speciaux = rassembler_messages_traitement_special_saa(
    CHEMIN_FICHIER_S,
    output_special
)

print("Nombre de messages SAA avec traitement spécial :", nb_speciaux)
print("Répartition :")
for cle, valeur in compteur_speciaux.items():
    print(cle, ":", valeur)

print("Fichier généré :", output_special)