from collections import defaultdict
import os
import re
from unittest import result

def normalize_bloc(text):
    text = re.sub(r"\s+", " ", text)  
    text = text.strip()  
    return text

def extract_messages_from_file(source):
    result = []
    with open(source, "r", encoding="utf-8") as f:
        content = f.read()
    messages = re.findall(r"<message>(.*?)</message>", content, re.S)
    for message in messages:
        normalize_bloc(message)
        result.append((message, source))
    return result

def extract_messages_from_2files(sourceA , sourceB):
    Absant_ds_A = []
    resultA = []
    resultB = []
    with open(sourceA, "r", encoding="utf-8") as f:
        content = f.read()
    messages = re.findall(r"<message>(.*?)</message>", content, re.S)
    for message in messages:
        normalize_bloc(message)
        resultA.append((message, sourceA))
    
    with open(sourceB, "r", encoding="utf-8") as f:
        content = f.read()
    messages = re.findall(r"<message>(.*?)</message>", content, re.S)
    for message in messages:
        normalize_bloc(message)
        resultB.append((message, sourceB))

    Absant_ds_A = set(resultA) - set(resultB)
    return Absant_ds_A

def detect_repetition(file):
    D = {}
    repetition = set()
    for f in file :
        n = 0
        for r in file :
            if r == f :
                n += 1
                D[f] = n 
        if D[f] > 1 :
            repetition.add(f)
    return D , repetition

def ecrire_rapport(sourceA, sourceB ,output_dir):
    Absant_ds_A = extract_messages_from_2files(sourceA , sourceB)
    totalA = len(sourceA)
    totalB = len(sourceB)
    with open(output_dir, "w", encoding="utf-8") as f:
        pass


        


def lire_fichier(source):
    if os.path.isfile(source):
        return extract_messages_from_file(source)

    elif os.path.isdir(source):
        result = []
        for root, _, fichiers in os.walk(source):
            for fichier in fichiers:               
                path = os.path.join(root, fichier)
                result.extend(extract_messages_from_file(path))
        return result
            
    return None

    

def comparer(source1, source2):
    pass

def main():
    comparer("source1.txt", "source2.txt")
    print("demarage")

main()