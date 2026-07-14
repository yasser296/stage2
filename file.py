import re

chemin = r"data\EXTRACTION0306.xml"

with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()

messages = re.findall(r"<Message\b.*?</Message>", content, re.S | re.I)

count_output_payload = 0

for message in messages:
    is_output = re.search(r"<SubFormat>\s*OUTPUT\s*</SubFormat>", message, re.S | re.I)
    has_payload = re.search(r"<PayloadPhysicalFileName>", message, re.S | re.I)

    if is_output and has_payload:
        count_output_payload += 1

print("Messages OUTPUT avec PayloadPhysicalFileName :", count_output_payload)