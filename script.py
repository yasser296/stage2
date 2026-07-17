import os
import re
import html



chemin = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\EXTRACTION0306.xml"
output_dir = r"C:\Users\msi\Desktop\stage2\script.txt"


def extract_request_subtype(message):
    match = re.search(
        r"<RequestSubtype\b[^>]*>\s*(.*?)\s*</RequestSubtype>",
        message,
        re.S | re.I
    )

    if match:
        return match.group(1).strip()

    return None

def is_output_message(message):
    """Vérifie si un message est de type OUTPUT."""
    return bool(re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.I))


def extract_SubFormat(message):
    """Extrait le contenu de <SubFormat> d'un message XML."""
    match = re.search(
        r"<SubFormat\b[^>]*>(.*?)</SubFormat>",
        html.unescape(message),
        re.I | re.S,
    )
    return match.group(1).strip() if match else None

def extract_Service(message):
    """Extrait le contenu de <Service> d'un message XML."""
    match = re.search(
        r"<Service\b[^>]*>(.*?)</Service>",
        html.unescape(message),
        re.I | re.S,
    )
    return match.group(1).strip() if match else None

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


with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

messages = re.findall(r"<Message\b.*?</Message>", content, re.S | re.I)

resultats = set()

for message in messages:
    message = html.unescape(message)
    msg_type = extract_message_identifier(message)
    request_subtype = extract_request_subtype(message)
    sumid = extract_sumid(message)
    service = extract_Service(message)
    subFormat = extract_SubFormat(message)
    
    if not re.search(r"to rp \[FLTS_RP_TO\]", message, re.I) and not re.search(r"to rp \[DDASSEND\]", message, re.I) :
        

        if msg_type:
            resultats.add((msg_type, request_subtype ,sumid, service, subFormat))

print("Messages n'ayant pas to rp [FLTS_RP_TO] ni to rp [DDASSEND] :")




with open(output_dir, "w", encoding="utf-8") as f:
    
    for msg_type, request_subtype ,sumid, service, subFormat in sorted(resultats):
        f.write(f"{msg_type},| sumId :, {sumid} ,| {service} :, { service },| subFormat : {subFormat} \n" )

print("Nombre de messages trouvés :", len(resultats))