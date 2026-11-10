"""Preserve NetWeave's BT/DHT routing across upstream updates.

Domain rules catch bootstrap lookups. PROCESS-NAME rules cover IP-only peers
when the Mihomo client exposes process or Android package metadata.
"""
from pathlib import Path

BT_RULES = (
    "DOMAIN,dht.transmissionbt.com,BT",
    "DOMAIN,router.bittorrent.com,BT",
    "DOMAIN,router.utorrent.com,BT",
    "DOMAIN,dht.libtorrent.org,BT",
    "PROCESS-NAME,Transmission,BT",
    "PROCESS-NAME,transmission-daemon,BT",
    "PROCESS-NAME,transmission-qt,BT",
    "PROCESS-NAME,transmission-qt.exe,BT",
    "PROCESS-NAME,qbittorrent,BT",
    "PROCESS-NAME,qBittorrent,BT",
    "PROCESS-NAME,qbittorrent.exe,BT",
    "PROCESS-NAME,qbittorrent-nox,BT",
    "PROCESS-NAME,BitTorrent.exe,BT",
    "PROCESS-NAME,org.proninyaroslav.libretorrent,BT",
    "PROCESS-NAME,com.delphicoder.flud,BT",
)

STATIC_PATHS = (Path("Config/mihomoConfig.yaml"), Path("Config/mihomoConfigLite.yaml"))
JS_PATHS = (Path("Script/mihomoScript.js"), Path("Script/Script.js"))


def replace_once(text, marker, replacement, path):
    count = text.count(marker)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor {marker!r}, got {count}")
    return text.replace(marker, replacement, 1)


def patch_js_text(text, path):
    toggle = "  BT: true, // BT / DHT 下载流量（默认直连）\n"
    if toggle not in text:
        marker = "  // 以下为分流策略配置\n"
        text = replace_once(text, marker, marker + toggle, path)

    begin_marker = "const serviceConfigs = [\n  ...baseGroups,\n"
    start = text.find(begin_marker)
    end = text.find("\n];", start)
    if start < 0 or end < 0:
        raise RuntimeError(f"{path}: serviceConfigs block missing")
    section = text[start:end]
    existing = section.count("    name: 'BT',")
    if existing > 1:
        raise RuntimeError(f"{path}: duplicate BT service")
    if existing == 0:
        group = (
            "  {\n"
            "    name: 'BT',\n"
            "    baseOption: selectBaseOption,\n"
            "    direct: true,\n"
            "    defaultSelected: '直连',\n"
            "    rules: [\n"
            + "".join(f"      '{rule}',\n" for rule in BT_RULES)
            + "    ],\n"
            "  },\n"
        )
        text = replace_once(text, begin_marker, begin_marker + group, path)

    verify_js(text, path)
    return text


def patch_static_text(text, path):
    group_marker = "  - name: 'BT'\n"
    if text.count(group_marker) > 1:
        raise RuntimeError(f"{path}: duplicate BT group")
    if group_marker not in text:
        marker = "  - name: 'Google'\n"
        group = (
            "  - name: 'BT'\n"
            "    <<: [*group_common_select, *proxies_direct]\n"
            "    default-selected: '直连'\n\n"
        )
        text = replace_once(text, marker, group + marker, path)

    present = [rule for rule in BT_RULES if f"  - {rule}\n" in text]
    if present and len(present) != len(BT_RULES):
        missing = sorted(set(BT_RULES) - set(present))
        raise RuntimeError(f"{path}: partial BT rules: {missing}")
    if not present:
        marker = "  # 广告拦截\n"
        block = "  # BT / DHT 下载（默认直连；进程识别取决于内核环境）\n"
        block += "".join(f"  - {rule}\n" for rule in BT_RULES) + "\n"
        text = replace_once(text, marker, block + marker, path)

    verify_static(text, path)
    return text


def verify_js(text, path):
    if text.count("  BT: true,") != 1 or text.count("    name: 'BT',") != 1:
        raise RuntimeError(f"{path}: BT option/group missing or duplicated")
    start = text.find("    name: 'BT',")
    end = text.find("\n  },", start)
    if start < 0 or end < 0:
        raise RuntimeError(f"{path}: BT group boundary missing")
    block = text[start:end]
    for expected in ("    direct: true,", "    defaultSelected: '直连',"):
        if expected not in block:
            raise RuntimeError(f"{path}: BT default direct selection missing")
    for rule in BT_RULES:
        if block.count(f"'{rule}'") != 1:
            raise RuntimeError(f"{path}: BT rule missing or duplicate: {rule}")
    if text.find("    name: 'BT',") > text.find("    name: 'Google',"):
        raise RuntimeError(f"{path}: BT group must precede generic Google group")


def verify_static(text, path):
    if text.count("  - name: 'BT'\n") != 1:
        raise RuntimeError(f"{path}: expected exactly one BT group")
    start = text.find("  - name: 'BT'\n")
    end = text.find("\n  - name:", start + 3)
    if end < 0:
        raise RuntimeError(f"{path}: BT group boundary missing")
    group = text[start:end]
    if "*proxies_direct" not in group or "default-selected: '直连'" not in group:
        raise RuntimeError(f"{path}: BT group must default to existing 直连 option")
    for rule in BT_RULES:
        if text.count(f"  - {rule}\n") != 1:
            raise RuntimeError(f"{path}: BT rule missing or duplicated: {rule}")
    if text.index(f"  - {BT_RULES[0]}\n") > text.index("  - RULE-SET,geolocation-!cn,默认代理\n"):
        raise RuntimeError(f"{path}: BT rules must precede foreign fallback")


def main():
    for path in STATIC_PATHS:
        path.write_text(patch_static_text(path.read_text(encoding="utf-8"), path), encoding="utf-8")
    for path in JS_PATHS:
        path.write_text(patch_js_text(path.read_text(encoding="utf-8"), path), encoding="utf-8")
    print("NetWeave BT groups and DHT/process rules preserved in all four variants")


if __name__ == "__main__":
    main()
