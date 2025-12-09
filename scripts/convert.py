import os
import yaml
import re
import requests
import ipaddress
from datetime import datetime

RULES_FILE = "rules.txt"

# QuantumultX 支持的规则类型
VALID_TYPES = ["DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "URL-REGEX"]

def safe_filename(name):
    """生成安全文件名"""
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    return f"{name}.list"

def fetch_yaml(url):
    """下载 YAML 文件"""
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return yaml.safe_load(r.text)
    except requests.exceptions.HTTPError as e:
        print(f"[Error] Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        print(f"[Error] Unknown error fetching {url}: {e}")
        return None

def extract_rules(data):
    """提取 QX 支持的规则，包括标准规则和纯 IP/CIDR"""
    rules = []
    raw_rules = data.get("payload") or data.get("rules") or []

    for item in raw_rules:
        if not isinstance(item, str):
            continue

        parts = [p.strip() for p in item.split(",")]

        # 标准格式 TYPE,TARGET
        if len(parts) >= 2:
            typ, target = parts[0], parts[1]
            if typ in VALID_TYPES:
                rules.append(f"{typ},{target}")
        elif len(parts) == 1:
            # 如果只有一个字段，尝试解析为 IP/CIDR
            try:
                ipaddress.ip_network(parts[0])
                rules.append(f"IP-CIDR,{parts[0]}")
            except ValueError:
                # 不是 IP/CIDR 就忽略
                continue

    return sorted(set(rules))

def process_url(url, depth=0):
    """下载 YAML 并生成 .list 文件，支持嵌套 rule-provider"""
    if depth > 3:
        print(f"[Error] Too many nested providers: {url}")
        return None

    print(f"[Download] {url}")
    data = fetch_yaml(url)
    if not data:
        print(f"[Skip] Could not fetch {url}")
        return None

    # 如果是 rule-provider 类型，且有 url 指向真实规则
    if data.get("type") == "http" and "url" in data:
        nested_url = data["url"]
        print(f"[Info] Nested rule-provider found, downloading {nested_url}")
        return process_url(nested_url, depth+1)

    # 文件名
    name = data.get("name") or url.strip().split("/")[-1].replace(".yaml","").replace(".yml","")
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
    """清理旧的 .list 文件"""
    for f in os.listdir("."):
        if f.endswith(".list"):
            os.remove(f)
            print(f"[Clean] Removed old list: {f}")

def generate_readme(list_files):
    """生成 README.md"""
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
