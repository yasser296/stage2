import html
import os
import re

from code1 import Affiche_bloc

chemin = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output\rapport\openPay\SGMB_OPENPAY_EP.txt"


with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
    contenu = f.read()

# Extraire chaque DataBlock du rapport
datablocks = re.findall(
    r"DataBlock:\s*\d+\s*\n(.*?)(?=\n\s*DataBlock:\s*\d+\s*\n|\n-{20,}|\n={20,}|\Z)",
    contenu,
    re.S | re.I
)

nombre_datablocks = len(datablocks)
nombre_datablocks_avec_swift_iap = 0
nombre_datablocks_avec_plusieurs_swift_iap = 0
path = r"C:\Users\msi\Desktop\stage2\Nouveau dossier\data\Output\rapport\openPay"
datoblockVide = []

for datablock in datablocks:
    datablock = html.unescape(datablock)
    datablock = Affiche_bloc(datablock)
    bizsvc_trouves = re.findall(
        r"<(?:\w+:)?BizSvc\b[^>]*>\s*(swift\.iap[^<]*)\s*</(?:\w+:)?BizSvc>",
        datablock,
        re.S | re.I
    )

    if len(bizsvc_trouves) >= 1:
        nombre_datablocks_avec_swift_iap += 1

    if len(bizsvc_trouves) == 0:
        datoblockVide.append(datablock)

    if len(bizsvc_trouves) > 1:
        nombre_datablocks_avec_plusieurs_swift_iap += 1

filePath = os.path.join(path, f"DataBlocks-sansswift-iap.txt")

os.makedirs(os.path.dirname(filePath), exist_ok=True)

with open(filePath, "w", encoding="utf-8") as f:   
    for i, block in enumerate(datoblockVide):
        f.write(f" DataBlock:  \n")
        f.write(block)
        if i < len(datoblockVide) - 1:  # N'écrit pas la ligne pour le dernier élément
            f.write("\n" + "-" * 100 + "\n")
    f.write("\n\n\n" + "=" * 80 + "\n\n\n")


print("Nombre de DataBlocks :", nombre_datablocks)
print("Nombre de DataBlocks avec swift.iap dans BizSvc :", nombre_datablocks_avec_swift_iap)
print("Nombre de DataBlocks avec plusieurs swift.iap dans BizSvc :", nombre_datablocks_avec_plusieurs_swift_iap)