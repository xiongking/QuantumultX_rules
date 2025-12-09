import os
import yaml
import re
import requests
from datetime import datetime

RULES_FILE = "rules.txt"

# QX 支持的规则类型
VALID_TYPES = ["DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "URL-REGEX"]

def safe_filename(name):
    """生成安全文件名"""
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    return f"{name}.list"

def fetch_yaml(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return yaml.safe_load(r.text)
    except requests.exceptions.HTTPError as e:
        print(f"[Error] Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        print(f"[Error] Unknown error fetching {url}: {e}")
        return None

def extract_rules(data):
    """提取 QX 支持的规则"""
    rules = []

    raw_rules = data.get("payload") or data.get("rules") or []

    for item in raw_rules:
        if not isinstance(item, str):
            continue

        # Clash 格式: TYPE,TARGET,[策略]
        parts = [p.strip() for p in item.split(",")]
        if len(parts) >= 2:
            typ, target = parts[0], parts[1]
            if typ in VALID_TYPES:
                rules.append(f"{typ},{target}")

    # 去重并排序
    return sorted(set(rules))

def process_url(url):
    print(f"[Download] {url}")
    data = fetch_yaml(url)
    if not data:
        print(f"[Skip] Could not fetch {url}")
        return None

    # 文件名优先使用 YAML 中 name 字段
    name = data.get("name")
    if not name:
        name = url.strip().split("/")[-1].replace(".yaml","").replace(".yml","")
    filename = safe_filename(name)

    rules = extract_rules(data)
    if rules:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(rules))
        print(f"[Success] Generated: {filename} ({len(rules)} rules)")
        return filename
    else:
        print(f"[Warning] No rules extracted for {url}")
        return None

def cleanup_old_lists():
    for f in os.listdir("."):
        if f.endswith(".list"):
            os.remove(f)
            print(f"[Clean] Removed old list: {f}")

def generate_readme(list_files):
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("# QuantumultX Rule Lists\n\n")
        f.write("自动生成的 QuantumultX 规则列表：\n\n")
        for l in sorted(list_files):
            f.write(f"- `{l}`\n")
        f.write(f"\n_Last update: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_\n")
    print("[Info] README.md updated")

def main():
    if not os.path.exists(RULES_FILE):
        print(f"[Error] {RULES_FILE} not found!")
        return

    cleanup_old_lists()

    with open(RULES_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    generated_files = []
    for url in urls:
        try:
            filename = process_url(url)
            if filename:
                generated_files.append(filename)
        except Exception as e:
            print(f"[Error] Processing {url} failed: {e}")

    if generated_files:
        generate_readme(generated_files)
    else:
        print("[Warning] No list files generated")

if __name__ == "__main__":
    main()
