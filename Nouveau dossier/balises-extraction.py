import re
import html
import xml.etree.ElementTree as ET


def enlever_namespace(tag):
    """
    Exemple :
    {urn:swift:saa:xsd:messaging}Message -> Message
    """
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def nettoyer_texte(text):
    if text is None:
        return ""

    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def formatter_attributs(element):
    """
    Affiche les attributs d'une balise si elle en a.
    Exemple :
    <Amt Ccy="MAD"> -> Amt [Ccy=MAD]
    """
    if not element.attrib:
        return ""

    attributs = []
    for cle, valeur in element.attrib.items():
        cle = enlever_namespace(cle)
        attributs.append(f'{cle}="{valeur}"')

    return " [" + ", ".join(attributs) + "]"


def couper_texte(texte, limite=120):
    """
    Coupe les textes très longs pour garder l'affichage lisible.
    """
    if len(texte) > limite:
        return texte[:limite] + "..."
    return texte


def afficher_hierarchie(
    element,
    prefix="",
    is_last=True,
    is_root=True,
    lignes=None,
    ignorer_datablock_long=True
):
    """
    Affiche toutes les balises en gardant une hiérarchie bien visible.
    Exemple :
    Message
    ├── Identifier
    │   └── SUmid : ...
    └── Text
        └── DataBlock : ...
    """

    if lignes is None:
        lignes = []

    nom_balise = enlever_namespace(element.tag)
    attributs = formatter_attributs(element)
    texte = nettoyer_texte(element.text)

    if is_root:
        connecteur = ""
    else:
        connecteur = "└── " if is_last else "├── "

    # Cas spécial DataBlock
    if nom_balise == "DataBlock" and ignorer_datablock_long:
        ligne = f"{prefix}{connecteur}{nom_balise}{attributs} : [CONTENU DATABLOCK XML]"
    else:
        if texte:
            # texte = couper_texte(texte)
            ligne = f"{prefix}{connecteur}{nom_balise}{attributs} : {texte}"
        else:
            ligne = f"{prefix}{connecteur}{nom_balise}{attributs}"

    lignes.append(ligne)

    enfants = list(element)

    if is_root:
        nouveau_prefix = ""
    else:
        nouveau_prefix = prefix + ("    " if is_last else "│   ")

    for index, enfant in enumerate(enfants):
        dernier = index == len(enfants) - 1

        afficher_hierarchie(
            enfant,
            prefix=nouveau_prefix,
            is_last=dernier,
            is_root=False,
            lignes=lignes,
            ignorer_datablock_long=ignorer_datablock_long
        )

    return lignes


def chercher_premier_element(root, nom_recherche):
    """
    Cherche une balise par son nom sans tenir compte du namespace.
    Exemple : chercher DataBlock même si namespace présent.
    """
    for elem in root.iter():
        if enlever_namespace(elem.tag) == nom_recherche:
            return elem
    return None

# chercher un message avec son id
def extraire_message_depuis_fichier(chemin_fichier, sumid_recherche=None):
    """
    Extrait un seul message depuis le fichier XML.
    Si sumid_recherche est donné, il prend ce message précis.
    Sinon, il prend le premier message OUTPUT.
    """
    with open(chemin_fichier, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    messages = re.findall(r"<Message\b.*?</Message>", content, re.S | re.I)

    print("Nombre de messages trouvés :", len(messages))

    for message in messages:
        if sumid_recherche:
            if f"<SUmid>{sumid_recherche}</SUmid>" in message:
                return message
        else:
            if re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.S | re.I):
                return message

    return None

def afficher_datablock(datablock_xml, lignes):
    datablock_xml = html.unescape(datablock_xml).strip()

    lignes.append("")
    lignes.append("=" * 100)
    lignes.append("HIERARCHIE INTERNE DU DATABLOCK")
    lignes.append("=" * 100)

    # Cas 1 : DataBlock XML, par exemple MX / CAMT / PACS
    if datablock_xml.startswith("<"):
        try:
            datablock_root = ET.fromstring("<Root>" + datablock_xml + "</Root>")
            lignes.extend(afficher_hierarchie(datablock_root, ignorer_datablock_long=True))
        except ET.ParseError as e:
            lignes.append("Impossible de parser le DataBlock XML.")
            lignes.append(f"Erreur : {e}")
            lignes.append(datablock_xml)

    # Cas 2 : DataBlock SWIFT FIN texte, par exemple :20:, :21:, :79:
    else:
        lignes.append("DataBlock FIN")
        champs = re.split(r"(?=:\d{2}[A-Z]?:)", datablock_xml)

        for champ in champs:
            champ = champ.strip()
            if champ:
                lignes.append(f"  {champ}")

def analyser_message(message_xml):
    """
    Analyse un message SAA et retourne les lignes hiérarchiques.
    """
    root = ET.fromstring(message_xml)

    lignes = []

    lignes.append("=" * 100)
    lignes.append("HIERARCHIE DU MESSAGE SAA")
    lignes.append("=" * 100)
    lignes.extend(afficher_hierarchie(root, ignorer_datablock_long=True))

    # Analyse séparée du DataBlock
    datablock_elem = chercher_premier_element(root, "DataBlock")

    if datablock_elem is not None and datablock_elem.text:
        datablock_xml = html.unescape(datablock_elem.text).strip()

        lignes.append("")
        lignes.append("=" * 100)
        lignes.append("HIERARCHIE INTERNE DU DATABLOCK")
        lignes.append("=" * 100)

        try:
            # DataBlock peut contenir plusieurs racines : AppHdr + Document
            # donc on ajoute une racine artificielle.
            afficher_datablock(datablock_elem.text, lignes)

        except ET.ParseError as e:
            lignes.append("Impossible de parser le DataBlock comme XML.")
            lignes.append(f"Erreur : {e}")
            lignes.append("")
            lignes.append("Contenu brut du DataBlock :")
            lignes.append(datablock_xml)
    else:
        lignes.append("")
        lignes.append("=" * 100)
        lignes.append("DATABLOCK")
        lignes.append("=" * 100)
        lignes.append("Ce message ne contient pas de DataBlock.")

    return lignes


def main():
    chemin_fichier = r"data\EXTRACTION0306.xml"

    # Mets ici un SUmid si tu veux analyser un message précis.
    # Exemple :
    # sumid_recherche = "15DFB505FFF2D690"
    sumid_recherche = "15DF9B55FFF2D393"

    message_xml = extraire_message_depuis_fichier(chemin_fichier, sumid_recherche)

    if message_xml is None:
        print("Aucun message trouvé.")
        return

    lignes = analyser_message(message_xml)

    # Affichage dans le terminal
    for ligne in lignes:
        print(ligne)

    # Sauvegarde dans un fichier texte
    chemin_sortie = "hierarchie_message.txt"

    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes))

    print()
    print("Fichier généré :", chemin_sortie)


main()