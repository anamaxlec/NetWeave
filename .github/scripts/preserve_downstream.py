from pathlib import Path
import re

FCM_DOMAINS = [
    'mtalk.google.com',
    'mtalk4.google.com',
    'mtalk-dev.google.com',
    'mtalk-staging.google.com',
    'alt1-mtalk.google.com',
    'alt2-mtalk.google.com',
    'alt3-mtalk.google.com',
    'alt4-mtalk.google.com',
    'alt5-mtalk.google.com',
    'alt6-mtalk.google.com',
    'alt7-mtalk.google.com',
    'alt8-mtalk.google.com',
    'android.apis.google.com',
    'device-provisioning.googleapis.com',
    'firebaseinstallations.googleapis.com',
]

STATIC_FILES = [
    Path('Config/mihomoConfig.yaml'),
    Path('Config/mihomoConfigLite.yaml'),
]
JS_FILES = [
    Path('Script/Script.js'),
    Path('Script/mihomoScript.js'),
]

GOOGLEFCM_RULESET = 'rule-set:googlefcm'
GOOGLEFCM_URL = 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/googlefcm.mrs'
QUIC_RULE = "AND,((NETWORK,UDP),(DST-PORT,443),(NOT,((OR,((RULE-SET,geolocation-cn),(RULE-SET,cn_additional),(RULE-SET,cn_ip,no-resolve)))))),REJECT"
OLD_QUIC_RULE = "AND,((NETWORK,UDP),(DST-PORT,443),(NOT,((OR,((RULE-SET,cn_additional),(RULE-SET,cn_ip,no-resolve)))))),REJECT"

STATIC_HEADERS = {
    Path('Config/mihomoConfig.yaml'): """#  ---------说明---------
#  NetWeave - mihomo配置（全量版）
#  维护：anamaxlec
#  原作者：AIsouler
#  项目仓库：https://github.com/anamaxlec/NetWeave
#  配置链接：https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Config/mihomoConfig.yaml
#  上游项目：https://github.com/AIsouler/MyClash
#  友情推荐，非常好用、省电且内存占用低的代理软件：https://github.com/appshubcc/Bettbox
#  ---------------------
""",
    Path('Config/mihomoConfigLite.yaml'): """#  ---------说明---------
#  NetWeave - mihomo配置（精简版）
#  维护：anamaxlec
#  原作者：AIsouler
#  项目仓库：https://github.com/anamaxlec/NetWeave
#  配置链接：https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Config/mihomoConfigLite.yaml
#  上游项目：https://github.com/AIsouler/MyClash
#  友情推荐，非常好用、省电且内存占用低的代理软件：https://github.com/appshubcc/Bettbox
#  ---------------------
""",
}

JS_HEADERS = {
    Path('Script/Script.js'): """/**
 * NetWeave - mihomo配置覆写脚本（精简版）
 * 维护：anamaxlec
 * 原作者：AIsouler
 * 项目仓库：https://github.com/anamaxlec/NetWeave
 * 脚本链接：https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Script/Script.js
 * 上游项目：https://github.com/AIsouler/MyClash
 * 友情推荐，非常好用、省电且内存占用低的代理软件：https://github.com/appshubcc/Bettbox
 */
""",
    Path('Script/mihomoScript.js'): """/**
 * NetWeave - mihomo配置覆写脚本（全量版）
 * 维护：anamaxlec
 * 原作者：AIsouler
 * 项目仓库：https://github.com/anamaxlec/NetWeave
 * 脚本链接：https://raw.githubusercontent.com/anamaxlec/NetWeave/main/Script/mihomoScript.js
 * 上游项目：https://github.com/AIsouler/MyClash
 * 友情推荐，非常好用、省电且内存占用低的代理软件：https://github.com/appshubcc/Bettbox
 */
""",
}


def ensure_after(entries, anchor, value):
    if value in entries:
        return entries
    if anchor in entries:
        entries.insert(entries.index(anchor) + 1, value)
    else:
        entries.append(value)
    return entries


def replace_static_header(text, path):
    marker = '# --- 锚点定义 (通用属性) ---'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'{path}: static header marker not found')
    return STATIC_HEADERS[path].rstrip() + '\n\n' + text[idx:]


def replace_js_header(text, path):
    marker = '// --- 静态配置区域 ---'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'{path}: JS header marker not found')
    return JS_HEADERS[path].rstrip() + '\n\n' + text[idx:]


def ensure_static_googlefcm_provider(text, path):
    if re.search(r'(?m)^  googlefcm:\s*$', text):
        return text

    marker = re.search(r"(?m)^  geolocation-!cn:\s*$", text)
    if not marker:
        raise RuntimeError(f'{path}: rule-providers insertion point not found')

    block = (
        "  googlefcm:\n"
        "    <<: *rule_providers_domain\n"
        f"    url: '{GOOGLEFCM_URL}'\n"
        "    path: './ruleset/googlefcm.mrs'\n"
        "    path-in-bundle: 'geo/geosite/googlefcm.mrs'\n"
    )
    return text[:marker.start()] + block + text[marker.start():]


def ensure_js_googlefcm_provider(text, path):
    start = text.find('const baseRuleProviders = {')
    end = text.find('// 策略组公共配置', start)
    if start == -1 or end == -1:
        raise RuntimeError(f'{path}: baseRuleProviders block not found')

    base_block = text[start:end]
    if re.search(r'(?m)^  googlefcm:\s*\{', base_block):
        return text

    marker = re.search(r"(?m)^  'geolocation-!cn':\s*\{", base_block)
    if not marker:
        raise RuntimeError(f'{path}: baseRuleProviders insertion point not found')

    absolute = start + marker.start()
    block = (
        "  googlefcm: {\n"
        "    ...ruleProviderCommonDomain,\n"
        f"    url: '{GOOGLEFCM_URL}',\n"
        "    path: './ruleset/googlefcm.mrs',\n"
        "    'path-in-bundle': 'geo/geosite/googlefcm.mrs',\n"
        "  },\n"
    )
    return text[:absolute] + block + text[absolute:]


def remove_crypto_static(text):
    # Crypto 仅存在于全量静态配置；在精简版上这些替换是 no-op。
    text = re.sub(
        r"(?ms)^  cryptocurrency:\n.*?(?=^  ehentai:)",
        '',
        text,
        count=1,
    )
    text = re.sub(
        r"(?ms)^  - name: 'Crypto'\n.*?(?=^  - name: 'EHentai')",
        '',
        text,
        count=1,
    )
    text = re.sub(r"(?m)^\s*- RULE-SET,cryptocurrency,Crypto\s*\n", '', text, count=1)
    return text


def remove_crypto_js(text):
    # 移除 Bettbox 开关与完整 serviceConfigs 定义；精简脚本没有 Crypto 时为 no-op。
    text = re.sub(r"(?m)^  Crypto:\s*true,\s*//.*\n", '', text, count=1)
    text = re.sub(
        r"(?ms)^  \{\n    name: 'Crypto',\n.*?^  \},\n(?=  \{\n    name: 'EHentai',)",
        '',
        text,
        count=1,
    )
    return text


def patch_static(path):
    text = path.read_text(encoding='utf-8')
    text = replace_static_header(text, path)
    text = ensure_static_googlefcm_provider(text, path)
    text = remove_crypto_static(text)

    match = re.search(r"(?m)^  fake-ip-filter:\s*(\[[\s\S]*?\])", text)
    if not match:
        raise RuntimeError(f'{path}: fake-ip-filter not found')

    entries = re.findall(r"'([^']+)'", match.group(1))
    ensure_after(entries, 'rule-set:geolocation-cn', GOOGLEFCM_RULESET)
    for domain in FCM_DOMAINS:
        if domain not in entries:
            entries.append(domain)

    rebuilt = '[\n' + ''.join(f"      '{entry}',\n" for entry in entries) + '    ]'
    text = text[:match.start(1)] + rebuilt + text[match.end(1):]

    comment = '  # FCM 使用 googlefcm rule-set 动态覆盖，并保留 Google 官方域名作为显式兜底'
    if re.search(r'(?m)^  # FCM .*$', text):
        text = re.sub(r'(?m)^  # FCM .*$', comment, text, count=1)
    else:
        text = text.replace('  fake-ip-filter:', comment + '\n  fake-ip-filter:', 1)

    # bootstrap/default、cn、geolocation-cn 全部使用国内 DoH。
    default_ns = re.compile(r"(?m)^(\s*)default-nameserver:\s*\*(?:chinaDNS|chinaDohDNS)\s*$")
    if not default_ns.search(text):
        raise RuntimeError(f'{path}: default-nameserver not found')
    text = default_ns.sub(r"\1default-nameserver: *chinaDohDNS", text, count=1)

    cn_policy = re.compile(r"(?m)^(\s*)'rule-set:cn':\s*\*(?:chinaDNS|chinaDohDNS)\s*$")
    m = cn_policy.search(text)
    if not m:
        raise RuntimeError(f'{path}: nameserver-policy rule-set:cn not found')
    indent = m.group(1)
    text = cn_policy.sub(f"{indent}'rule-set:cn': *chinaDohDNS", text, count=1)

    geo_policy = re.compile(r"(?m)^\s*'rule-set:geolocation-cn':\s*\*(?:chinaDNS|chinaDohDNS)\s*$")
    if geo_policy.search(text):
        text = geo_policy.sub(f"{indent}'rule-set:geolocation-cn': *chinaDohDNS", text, count=1)
    else:
        text = text.replace(
            f"{indent}'rule-set:cn': *chinaDohDNS",
            f"{indent}'rule-set:cn': *chinaDohDNS\n{indent}'rule-set:geolocation-cn': *chinaDohDNS",
            1,
        )

    if QUIC_RULE not in text:
        if OLD_QUIC_RULE not in text:
            raise RuntimeError(f'{path}: QUIC rule not found')
        text = text.replace(OLD_QUIC_RULE, QUIC_RULE, 1)

    path.write_text(text, encoding='utf-8')


def patch_js(path):
    text = path.read_text(encoding='utf-8')
    text = replace_js_header(text, path)
    text = ensure_js_googlefcm_provider(text, path)
    text = remove_crypto_js(text)

    match = re.search(r"(?m)^(\s*)'fake-ip-filter':\s*\[([\s\S]*?)\]", text)
    if not match:
        raise RuntimeError(f'{path}: fake-ip-filter not found')

    indent = match.group(1)
    inner = match.group(2)
    entries = re.findall(r"'([^']+)'", inner)
    spreads = re.findall(r"\.\.\.[A-Za-z_$][\w$]*", inner)
    ensure_after(entries, 'rule-set:geolocation-cn', GOOGLEFCM_RULESET)
    for domain in FCM_DOMAINS:
        if domain not in entries:
            entries.append(domain)

    item_indent = indent + '  '
    rebuilt = (
        f"{indent}'fake-ip-filter': [\n"
        + ''.join(f"{item_indent}'{entry}',\n" for entry in entries)
        + ''.join(f"{item_indent}{spread},\n" for spread in spreads)
        + f'{indent}]'
    )
    text = text[:match.start()] + rebuilt + text[match.end():]

    comment = indent + '// FCM 使用 googlefcm rule-set 动态覆盖，并保留 Google 官方域名作为显式兜底'
    block_pos = text.find("'fake-ip-filter':")
    block_start = text.rfind('\n', 0, block_pos) + 1
    before = text[:block_start]
    old_comment = re.compile(r'(?m)^\s*// FCM .*$')
    if old_comment.search(before[-300:]):
        start = max(0, len(before) - 300)
        tail = old_comment.sub(comment, before[start:], count=1)
        text = before[:start] + tail + text[block_start:]
    else:
        text = text[:block_start] + comment + '\n' + text[block_start:]

    default_ns = re.compile(r"(?m)^(\s*)'default-nameserver':\s*(?:chinaDNS|chinaDohDNS),\s*$")
    if not default_ns.search(text):
        raise RuntimeError(f'{path}: default-nameserver not found')
    text = default_ns.sub(r"\1'default-nameserver': chinaDohDNS,", text, count=1)

    cn_policy = re.compile(r"(?m)^(\s*)'rule-set:cn':\s*(?:chinaDNS|chinaDohDNS),\s*$")
    m = cn_policy.search(text)
    if not m:
        raise RuntimeError(f'{path}: nameserver-policy rule-set:cn not found')
    policy_indent = m.group(1)
    text = cn_policy.sub(f"{policy_indent}'rule-set:cn': chinaDohDNS,", text, count=1)

    geo_policy = re.compile(r"(?m)^\s*'rule-set:geolocation-cn':\s*(?:chinaDNS|chinaDohDNS),\s*$")
    if geo_policy.search(text):
        text = geo_policy.sub(
            f"{policy_indent}'rule-set:geolocation-cn': chinaDohDNS,",
            text,
            count=1,
        )
    else:
        text = text.replace(
            f"{policy_indent}'rule-set:cn': chinaDohDNS,",
            f"{policy_indent}'rule-set:cn': chinaDohDNS,\n{policy_indent}'rule-set:geolocation-cn': chinaDohDNS,",
            1,
        )

    if QUIC_RULE not in text:
        if OLD_QUIC_RULE not in text:
            raise RuntimeError(f'{path}: QUIC rule not found')
        text = text.replace(OLD_QUIC_RULE, QUIC_RULE, 1)

    path.write_text(text, encoding='utf-8')


for file in STATIC_FILES:
    patch_static(file)
for file in JS_FILES:
    patch_js(file)

for path in STATIC_FILES + JS_FILES:
    text = path.read_text(encoding='utf-8')
    if 'NetWeave' not in text.splitlines()[1]:
        raise RuntimeError(f'{path}: NetWeave header was not preserved')
    if GOOGLEFCM_RULESET not in text:
        raise RuntimeError(f'{path}: missing {GOOGLEFCM_RULESET} in fake-ip-filter')
    if GOOGLEFCM_URL not in text:
        raise RuntimeError(f'{path}: missing always-available googlefcm provider')
    for domain in FCM_DOMAINS:
        if domain not in text:
            raise RuntimeError(f'{path}: missing protected FCM domain {domain}')
    if QUIC_RULE not in text:
        raise RuntimeError(f'{path}: missing protected China QUIC rule')

    if path.suffix == '.yaml':
        required = [
            'default-nameserver: *chinaDohDNS',
            "'rule-set:cn': *chinaDohDNS",
            "'rule-set:geolocation-cn': *chinaDohDNS",
        ]
    else:
        required = [
            "'default-nameserver': chinaDohDNS,",
            "'rule-set:cn': chinaDohDNS,",
            "'rule-set:geolocation-cn': chinaDohDNS,",
        ]
    for item in required:
        if item not in text:
            raise RuntimeError(f'{path}: missing protected DNS setting {item}')

# Crypto 是 NetWeave 明确删除的下游策略；每次同步后都必须保持不存在。
full_static = Path('Config/mihomoConfig.yaml').read_text(encoding='utf-8')
full_js = Path('Script/mihomoScript.js').read_text(encoding='utf-8')
for forbidden in ["name: 'Crypto'", 'RULE-SET,cryptocurrency,Crypto', 'category-cryptocurrency.mrs']:
    if forbidden in full_static or forbidden in full_js:
        raise RuntimeError(f'Crypto downstream removal failed: still contains {forbidden}')

print('NetWeave downstream patches verified for all four files')
