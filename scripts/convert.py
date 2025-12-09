import yaml
import requests
import os
import re

def extract_name(url):
    return re.sub(r'\.ya?ml$', '', url.split('/')[-1])

def extract_rules(data):
    result = []

    if isinstance(data, dict):
        if "payload" in data:
            result += data["payload"]
        if "rules" in data:
            result += data["rules"]

        for v in data.values():
            if isinstance(v, dict):
                result += extract_rules(v)
            elif isinstance(v, list):
                for i in v:
                    if isinstance(i, dict):
                        result += extract_rules(i)
    return result

def convert_line(line):
    line = line.strip()
    if not line:
        return None
    if "," in line:
        return line
    return None

def process_url(url):
    print(f"Processing: {url}")
    name = extract_name(url)
    output = f"dist/{name}.list"

    try:
        raw = requests.get(url, timeout=20).text
        data = yaml.safe_load(raw)
        rules = extract_rules(data)

        cleaned = []
        for r in rules:
            qx = convert_line(r)
            if qx:
                cleaned.append(qx)

        os.makedirs("dist", exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(cleaned))

        print(f"Saved {output} ({len(cleaned)} rules)")
    except Exception as e:
        print("Error:", e)

def main():
    with open("rules.txt", "r") as f:
        urls = [l.strip() for l in f if l.strip()]

    for url in urls:
        process_url(url)

if __name__ == "__main__":
    main()
