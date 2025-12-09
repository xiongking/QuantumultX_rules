import os
import re
import requests
import ipaddress
from datetime import datetime

RULES_FILE = "rules.txt"
VALID_TYPES = ["DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "URL-REGEX"]

def safe_filename(name):
    """生成安全文件名"""
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    return f"{name}.list"

def extract_rules_from_lines(lines):
    """从文本行提取 QX 支持的规则，兼容非严格 YAML"""
    rules = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 去掉前面的 '- ' 符号
        if line.startswith("- "):
            line = line[2:].strip()

        parts = [p.strip() for p in line.split(",")]

        if len(parts) >= 2:
            typ, target = parts[0], parts[1]
            if typ in VALID_TYPES:
                rules.append(f"{typ},{target}")
        elif len(parts) == 1:
            try:
                ipaddress.ip_network(parts[0])
                rules.append(f"IP-CIDR,{parts[0]}")
            except ValueError:
                continue

    return sorted(set(rules))

def fetch_content(url):
    """下载远程内容"""
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except requests.exceptions.HTTPError as e:
        print(f"[Error] Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        print(f"[Error] Unknown error fetching {url}: {e}")
        return None

def process_url(url, depth=0):
    """下载 URL，生成 .list 文件，支持嵌套 rule-provider"""
    if depth > 3:
        print(f"[Error] Too many nested providers: {url}")
        return None

    print(f"[Download] {url}")
    content = fetch_content(url)
    if not content:
        print(f"[Skip] Could not fetch {url}")
        return None

    lines = content.splitlines()

    # 检查是否是 rule-provider，尝试找到 url 字段
    for line in lines:
        if "url:" in line:
            nested_url = line.split("url:")[-1].strip()
            if nested_url.startswith("http"):
                print(f"[Info] Nested rule-provider found, downloading {nested_url}")
                return process_url(nested_url, depth+1)

    rules = extract_rules_from_lines(lines)
    if not rules:
        print(f"[Warning] No rules extracted for {url}")
        return None

    filename = safe_filename(url.split("/")[-1].replace(".yaml","").replace(".yml",""))
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(rules))
    print(f"[Success] Generated: {filename} ({len(rules)} rules)")
    return filename

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
