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

CONDITIONAL_GOOGLEFCM = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\.\.\.\(\s*ruleOptionsEnable\[['\"]FCM['\"]\]\s*"
    r"\?\s*\[\s*['\"]rule-set:googlefcm['\"]\s*\]\s*:\s*\[\s*\]\s*\),\s*$"
)


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
    if '\n  googlefcm:\n' in text:
        return text

    marker = '\n  geolocation-!cn:\n'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'{path}: rule-providers insertion point not found')

    block = (
        "\n  googlefcm:\n"
        "    <<: *rule_providers_domain\n"
        f"    url: '{GOOGLEFCM_URL}'\n"
        "    path: './ruleset/googlefcm.mrs'\n"
        "    path-in-bundle: 'geo/geosite/googlefcm.mrs'\n"
    )
    return text[:idx] + block + text[idx:]


def ensure_js_googlefcm_provider(text, path):
    start = text.find('const baseRuleProviders = {')
    end = text.find('// 策略组公共配置', start)
    if start == -1 or end == -1:
        raise RuntimeError(f'{path}: baseRuleProviders block not found')

    base_block = text[start:end]
    if '\n  googlefcm: {\n' in base_block:
        return text

    marker = "\n  'geolocation-!cn': {\n"
    relative = base_block.find(marker)
    if relative == -1:
        raise RuntimeError(f'{path}: baseRuleProviders insertion point not found')

    absolute = start + relative
    block = (
        "\n  googlefcm: {\n"
        "    ...ruleProviderCommonDomain,\n"
        f"    url: '{GOOGLEFCM_URL}',\n"
        "    path: './ruleset/googlefcm.mrs',\n"
        "    'path-in-bundle': 'geo/geosite/googlefcm.mrs',\n"
        "  },\n"
    )
    return text[:absolute] + block + text[absolute:]


def remove_between(text, start_marker, end_marker):
    start = text.find(start_marker)
    if start == -1:
        return text
    end = text.find(end_marker, start)
    if end == -1:
        raise RuntimeError(f'cannot find end marker after {start_marker!r}')
    return text[:start] + text[end:]


def remove_crypto_static(text):
    text = remove_between(text, '  cryptocurrency:\n', '  ehentai:\n')
    text = remove_between(text, "  - name: 'Crypto'\n", "  - name: 'EHentai'\n")
    text = text.replace('  - RULE-SET,cryptocurrency,Crypto\n', '')
    return text


def remove_crypto_js(text):
    text = re.sub(r"(?m)^  Crypto:\s*true,\s*//.*\n", '', text, count=1)
    text = remove_between(text, "  {\n    name: 'Crypto',\n", "  {\n    name: 'EHentai',\n")
    return text


def patch_static_fake_ip_filter(text, path):
    # 静态 YAML 没有可复用的 JS 常量，保留显式 hostname；只重建这一小段 DNS 字段。
    text = re.sub(r'(?m)^  # FCM .*\n', '', text, count=1)
    start = text.find('  fake-ip-filter:')
    end = text.find('  proxy-server-nameserver:', start)
    if start == -1 or end == -1:
        raise RuntimeError(f'{path}: fake-ip-filter section not found')

    entries = re.findall(r"'([^']+)'", text[start:end])
    ensure_after(entries, 'rule-set:geolocation-cn', GOOGLEFCM_RULESET)
    for domain in FCM_DOMAINS:
        if domain not in entries:
            entries.append(domain)

    rebuilt = (
        '  # FCM 使用 googlefcm rule-set 动态覆盖，并保留 Google 官方域名作为显式兜底\n'
        '  fake-ip-filter: [\n'
        + ''.join(f"      '{entry}',\n" for entry in entries)
        + '    ]\n'
    )
    return text[:start] + rebuilt + text[end:]


def ensure_fcm_fallback_constant(text, path):
    block = (
        '// FCM real-IP 显式兜底；googlefcm rule-set 负责动态覆盖。\n'
        'const fcmRealIpFallback = [\n'
        + ''.join(f"  '{domain}',\n" for domain in FCM_DOMAINS)
        + '];\n\n'
    )

    start = text.find('const fcmRealIpFallback = [')
    if start != -1:
        end = text.find('];', start)
        if end == -1:
            raise RuntimeError(f'{path}: fcmRealIpFallback closing marker not found')
        line_start = text.rfind('\n', 0, start) + 1
        comment_start = text.rfind('// FCM real-IP', 0, start)
        if comment_start >= line_start - 120:
            line_start = comment_start
        return text[:line_start] + block + text[end + 2:].lstrip('\n')

    marker = '// 直连节点'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'{path}: FCM fallback insertion marker not found')
    return text[:idx] + block + text[idx:]


def patch_js_fake_ip_filter(text, path):
    # 跟随上游的声明式数组结构，只做最小语义差异：googlefcm 永久在线 + fallback spread。
    def normalize_conditional(match):
        return f"{match.group('indent')}'rule-set:googlefcm',"

    text = CONDITIONAL_GOOGLEFCM.sub(normalize_conditional, text)
    text = re.sub(r'(?m)^\s*// FCM .*\n', '', text, count=1)

    marker = "'fake-ip-filter': ["
    pos = text.find(marker)
    if pos == -1:
        raise RuntimeError(f'{path}: fake-ip-filter not found')
    line_start = text.rfind('\n', 0, pos) + 1

    spread_pos = text.find('...proxyFakeIpFilter,', pos)
    if spread_pos == -1:
        raise RuntimeError(f'{path}: proxyFakeIpFilter spread not found')
    spread_line_start = text.rfind('\n', 0, spread_pos) + 1

    prefix = text[line_start:spread_line_start]
    if 'ruleOptionsEnable' in prefix and 'googlefcm' in prefix:
        raise RuntimeError(f'{path}: unsupported conditional googlefcm syntax; refusing to rewrite nested JS')

    filtered_lines = []
    for line in prefix.splitlines(keepends=True):
        if "'rule-set:googlefcm'" in line:
            continue
        if '...fcmRealIpFallback' in line:
            continue
        if any(f"'{domain}'" in line for domain in FCM_DOMAINS):
            continue
        filtered_lines.append(line)

    geo_index = next(
        (i for i, line in enumerate(filtered_lines) if "'rule-set:geolocation-cn'" in line),
        None,
    )
    if geo_index is None:
        raise RuntimeError(f'{path}: geolocation-cn entry not found in fake-ip-filter')

    item_indent = re.match(r'\s*', filtered_lines[geo_index]).group(0)
    filtered_lines.insert(geo_index + 1, f"{item_indent}'rule-set:googlefcm',\n")

    spread_indent = re.match(r'\s*', text[spread_line_start:spread_pos]).group(0)
    rebuilt = ''.join(filtered_lines) + f'{spread_indent}...fcmRealIpFallback,\n'
    comment = f'{item_indent[:-2]}// FCM 使用 googlefcm rule-set 动态覆盖，并保留 Google 官方域名作为显式兜底\n'
    return text[:line_start] + comment + rebuilt + text[spread_line_start:]


def ensure_static_service_before_cn_fallback(text, path):
    # NetWeave 保持具体服务分流优先；geolocation-cn 只作为兜底，避免 Google 等全局域名误分类后被提前直连。
    rule = '  - RULE-SET,geolocation-cn,直连\n'
    text = text.replace(rule, '')
    anchor = '  - RULE-SET,geolocation-!cn,默认代理\n'
    if anchor not in text:
        raise RuntimeError(f'{path}: geolocation-!cn fallback not found')
    return text.replace(anchor, anchor + rule, 1)


def ensure_js_service_before_cn_fallback(text, path):
    prefix_start = text.find('const prefixRules = [')
    prefix_end = text.find('];', prefix_start)
    if prefix_start == -1 or prefix_end == -1:
        raise RuntimeError(f'{path}: prefixRules block not found')

    prefix = text[prefix_start:prefix_end]
    prefix = prefix.replace("  'RULE-SET,geolocation-cn,直连',\n", '')
    text = text[:prefix_start] + prefix + text[prefix_end:]

    rule = "    'RULE-SET,geolocation-cn,直连',\n"
    text = text.replace(rule, '')
    anchor = "    'RULE-SET,geolocation-!cn,默认代理',\n"
    if anchor not in text:
        raise RuntimeError(f'{path}: geolocation-!cn fallback not found')
    return text.replace(anchor, anchor + rule, 1)


def patch_static(path):
    text = path.read_text(encoding='utf-8')
    text = replace_static_header(text, path)
    text = ensure_static_googlefcm_provider(text, path)
    text = remove_crypto_static(text)
    text = patch_static_fake_ip_filter(text, path)
    text = ensure_static_service_before_cn_fallback(text, path)

    default_ns = re.compile(r"(?m)^(\s*)default-nameserver:\s*\*(?:chinaDNS|chinaDohDNS)\s*$")
    if not default_ns.search(text):
        raise RuntimeError(f'{path}: default-nameserver not found')
    text = default_ns.sub(r"\1default-nameserver: *chinaDohDNS", text, count=1)

    cn_policy = re.compile(r"(?m)^(\s*)'rule-set:cn':\s*\*(?:chinaDNS|chinaDohDNS)\s*$")
    match = cn_policy.search(text)
    if not match:
        raise RuntimeError(f'{path}: nameserver-policy rule-set:cn not found')
    indent = match.group(1)
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
    text = ensure_fcm_fallback_constant(text, path)
    text = patch_js_fake_ip_filter(text, path)
    text = ensure_js_service_before_cn_fallback(text, path)

    default_ns = re.compile(r"(?m)^(\s*)'default-nameserver':\s*(?:chinaDNS|chinaDohDNS),\s*$")
    if not default_ns.search(text):
        raise RuntimeError(f'{path}: default-nameserver not found')
    text = default_ns.sub(r"\1'default-nameserver': chinaDohDNS,", text, count=1)

    cn_policy = re.compile(r"(?m)^(\s*)'rule-set:cn':\s*(?:chinaDNS|chinaDohDNS),\s*$")
    match = cn_policy.search(text)
    if not match:
        raise RuntimeError(f'{path}: nameserver-policy rule-set:cn not found')
    policy_indent = match.group(1)
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
    if QUIC_RULE not in text:
        raise RuntimeError(f'{path}: missing protected China QUIC rule')

    if path.suffix == '.yaml':
        for domain in FCM_DOMAINS:
            if domain not in text:
                raise RuntimeError(f'{path}: missing protected FCM domain {domain}')
        required = [
            'default-nameserver: *chinaDohDNS',
            "'rule-set:cn': *chinaDohDNS",
            "'rule-set:geolocation-cn': *chinaDohDNS",
        ]
        cn_rule = '  - RULE-SET,geolocation-cn,直连\n'
        foreign_rule = '  - RULE-SET,geolocation-!cn,默认代理\n'
    else:
        if 'const fcmRealIpFallback = [' not in text or '...fcmRealIpFallback,' not in text:
            raise RuntimeError(f'{path}: FCM fallback is not expressed as an upstream-style spread')
        for domain in FCM_DOMAINS:
            if domain not in text:
                raise RuntimeError(f'{path}: missing protected FCM domain {domain}')
        required = [
            "'default-nameserver': chinaDohDNS,",
            "'rule-set:cn': chinaDohDNS,",
            "'rule-set:geolocation-cn': chinaDohDNS,",
        ]
        cn_rule = "    'RULE-SET,geolocation-cn,直连',\n"
        foreign_rule = "    'RULE-SET,geolocation-!cn,默认代理',\n"

    for item in required:
        if item not in text:
            raise RuntimeError(f'{path}: missing protected DNS setting {item}')
    if text.find(cn_rule) < text.find(foreign_rule):
        raise RuntimeError(f'{path}: geolocation-cn must remain a fallback after specific service routing')

full_static = Path('Config/mihomoConfig.yaml').read_text(encoding='utf-8')
full_js = Path('Script/mihomoScript.js').read_text(encoding='utf-8')
for forbidden in ["name: 'Crypto'", 'RULE-SET,cryptocurrency,Crypto', 'category-cryptocurrency.mrs']:
    if forbidden in full_static or forbidden in full_js:
        raise RuntimeError(f'Crypto downstream removal failed: still contains {forbidden}')

print('NetWeave downstream semantic patches verified for all four files')
