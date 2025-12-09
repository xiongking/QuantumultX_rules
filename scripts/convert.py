import requests
import yaml
import os
import re

RULE_FILE = "rules.txt"

def safe_filename(url: str):
    """Extract filename from URL like xxx.yaml → xxx.list"""
    name = url.strip().split("/")[-1]
    name = re.sub(r"\.ya?ml$", "", name)
    return f"{name}.list"

def clash_to_qx(rules):
    qx = []
    for rule in rules:
        if ":" not in rule:
            continue
        typ, val = rule.split(":", 1)
        typ = typ.strip()
        val = val.strip()

        if typ in [
            "DOMAIN",
            "DOMAIN-SUFFIX",
            "DOMAIN-KEYWORD",
            "IP-CIDR",
            "IP-CIDR6",
            "URL-REGEX",
        ]:
            qx.append(val)
    return qx


def process_one(url):
    print(f"Downloading {url}")
    content = requests.get(url).text

    data = yaml.safe_load(content)
    rules = data.get("payload") or data.get("rules") or []

    qx_list = clash_to_qx(rules)

    filename = safe_filename(url)
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(qx_list))

    print(f"Written → {filename}")


def main():
    if not os.path.exists(RULE_FILE):
        print(f"rules.txt not found.")
        return

    with open(RULE_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            process_one(url)
        except Exception as e:
            print(f"Error processing {url}: {e}")

if __name__ == "__main__":
    main()
