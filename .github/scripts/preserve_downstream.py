from pathlib import Path
import re

from netweave_patch_helpers import (
    ensure_full_script_tw,
    ensure_static_tw,
    parse_string_list_field,
    verify_tw_full_js,
    verify_tw_static,
)

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
FAKE_IP_COMMENT = '// FCM 使用 googlefcm rule-set 动态覆盖，并保留 Google 官方域名作为显式兜底'
FCM_IPV6_PREFER_DIRECT = '🇨🇳 直连 | IPv6优先'

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


MINIMAL_MODE_GOOGLEFCM = re.compile(
    r"(?m)^(?P<indent>[ \t]*)\.\.\.\(\s*minimalModeEnabled\s*\?\s*\[\s*\]\s*:\s*"
    r"ruleOptionsEnable\[['\"]FCM['\"]\]\s*\?\s*\[\s*['\"]rule-set:googlefcm['\"]\s*\]\s*"
    r":\s*\[\s*\]\s*\),\s*$"
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
    # Read only the literal fake-ip-filter sequence, never adjacent DNS settings.
    # Keep the original trailing newline and subsequent fields exactly intact.
    text = re.sub(r'(?m)^  # FCM .*\n', '', text)
    entries, field_start, field_end = parse_string_list_field(text, 'fake-ip-filter')
    ensure_after(entries, 'rule-set:geolocation-cn', GOOGLEFCM_RULESET)
    for domain in FCM_DOMAINS:
        if domain not in entries:
            entries.append(domain)

    rebuilt = (
        '  # FCM 使用 googlefcm rule-set 动态覆盖，并保留 Google 官方域名作为显式兜底\n'
        '  fake-ip-filter:\n'
        '    [\n'
        + ''.join(f"      '{entry}',\n" for entry in entries)
        + '    ]'
    )
    return text[:field_start] + rebuilt + text[field_end:]


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
    # 普通模式保持 googlefcm real-IP 保护；极简模式遵循上游语义，
    # 不额外注入 FCM fake-IP 规则。
    def normalize_conditional(match):
        return f"{match.group('indent')}'rule-set:googlefcm',"

    def normalize_minimal_conditional(match):
        return f"{match.group('indent')}...(minimalModeEnabled ? [] : ['rule-set:googlefcm']),"

    text = CONDITIONAL_GOOGLEFCM.sub(normalize_conditional, text)
    text = MINIMAL_MODE_GOOGLEFCM.sub(normalize_minimal_conditional, text)
    text = re.sub(rf'(?m)^[ \t]*{re.escape(FAKE_IP_COMMENT)}\n', '', text)

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
    filtered_lines = []
    has_minimal_googlefcm = False
    for line in prefix.splitlines(keepends=True):
        if "'rule-set:googlefcm'" in line:
            if 'minimalModeEnabled' in line:
                filtered_lines.append(line)
                has_minimal_googlefcm = True
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
    if not has_minimal_googlefcm:
        if path.name == 'Script.js':
            filtered_lines.insert(
                geo_index + 1,
                f"{item_indent}...(ruleOptionsEnable.极简模式 ? [] : ['rule-set:googlefcm']),\n",
            )
        else:
            filtered_lines.insert(geo_index + 1, f"{item_indent}'rule-set:googlefcm',\n")

    spread_indent = re.match(r'\s*', text[spread_line_start:spread_pos]).group(0)
    rebuilt = ''.join(filtered_lines) + f'{spread_indent}...fcmRealIpFallback,\n'
    comment = f'{item_indent[:-2]}{FAKE_IP_COMMENT}\n'
    return text[:line_start] + comment + rebuilt + text[spread_line_start:]


def ensure_static_foreign_nameserver(text, path):
    dns_start = text.find('\ndns:\n')
    hosts_start = text.find('\nhosts:\n', dns_start)
    if dns_start == -1 or hosts_start == -1:
        raise RuntimeError(f'{path}: dns/hosts section boundaries not found')

    block = text[dns_start:hosts_start]
    if '  nameserver: *foreignDNS\n' in block:
        return text

    marker = '  nameserver-policy:\n'
    relative = block.find(marker)
    if relative == -1:
        raise RuntimeError(f'{path}: nameserver-policy insertion point not found')

    absolute = dns_start + relative
    return text[:absolute] + '  nameserver: *foreignDNS\n' + text[absolute:]


def ensure_js_foreign_nameserver(text, path):
    dns_start = text.find('  const dns = {')
    hosts_start = text.find('  const hosts = {', dns_start)
    if dns_start == -1 or hosts_start == -1:
        raise RuntimeError(f'{path}: generated dns/hosts block boundaries not found')

    block = text[dns_start:hosts_start]
    if '    nameserver: foreignDNS,\n' in block:
        return text

    marker = "    'nameserver-policy': {\n"
    relative = block.find(marker)
    if relative == -1:
        raise RuntimeError(f'{path}: generated nameserver-policy insertion point not found')

    absolute = dns_start + relative
    return text[:absolute] + '    nameserver: foreignDNS,\n' + text[absolute:]


def ensure_static_fcm_ipv6_prefer(text, path):
    if path.name != 'mihomoConfig.yaml':
        return text

    direct_start = text.find('  proxies_direct:\n')
    direct_end = text.find('  proxies_reject:', direct_start)
    if direct_start == -1 or direct_end == -1:
        raise RuntimeError(f'{path}: proxies_direct block not found')
    direct_block = text[direct_start:direct_end]
    direct_options = re.findall(r"'([^']+)'", direct_block)
    if '直连' not in direct_options:
        raise RuntimeError(f'{path}: proxies_direct does not contain 直连')

    fcm_start = text.find("  - name: 'FCM'\n")
    fcm_end = text.find("  - name: 'YouTube'\n", fcm_start)
    if fcm_start == -1 or fcm_end == -1:
        raise RuntimeError(f'{path}: FCM proxy group block not found')
    fcm_block = text[fcm_start:fcm_end]
    icon_match = re.search(r"(?m)^    icon: .+$", fcm_block)
    if not icon_match:
        raise RuntimeError(f'{path}: FCM icon line not found')

    options = [FCM_IPV6_PREFER_DIRECT] + [item for item in direct_options if item != FCM_IPV6_PREFER_DIRECT]
    rebuilt = (
        "  - name: 'FCM'\n"
        "    <<: *group_common_select\n"
        "    proxies:\n"
        "      [\n"
        + ''.join(f"        '{item}',\n" for item in options)
        + "      ]\n"
        f"    default-selected: '{FCM_IPV6_PREFER_DIRECT}'\n"
        f"{icon_match.group(0)}\n\n"
    )
    return text[:fcm_start] + rebuilt + text[fcm_end:]


def ensure_js_fcm_ipv6_prefer(text, path):
    if path.name != 'mihomoScript.js':
        return text

    fcm_start = text.find("    name: 'FCM',")
    fcm_end = text.find("  {\n    name: 'YouTube',", fcm_start)
    if fcm_start == -1 or fcm_end == -1:
        raise RuntimeError(f'{path}: FCM service config block not found')

    block_start = text.rfind('  {\n', 0, fcm_start)
    block = text[block_start:fcm_end]
    block = re.sub(
        r"(?m)^    defaultSelected: '[^']+',\s*$",
        f"    defaultSelected: '{FCM_IPV6_PREFER_DIRECT}',",
        block,
        count=1,
    )
    if '    preferredDirect:' not in block:
        marker = '    direct: true,\n'
        if marker not in block:
            raise RuntimeError(f'{path}: FCM direct marker not found')
        block = block.replace(
            marker,
            marker + f"    preferredDirect: '{FCM_IPV6_PREFER_DIRECT}',\n",
            1,
        )
    text = text[:block_start] + block + text[fcm_end:]

    loop_start = text.find('  for (const svc of serviceConfigs) {')
    loop_end = text.find("  functionalGroups.push({\n    ...selectBaseOption,\n    name: '漏网之鱼'", loop_start)
    if loop_start == -1 or loop_end == -1:
        raise RuntimeError(f'{path}: service group construction loop not found')
    loop = text[loop_start:loop_end]
    preferred_block = (
        "    if (svc.preferredDirect && !groupProxies.includes(svc.preferredDirect)) {\n"
        "      groupProxies.unshift(svc.preferredDirect);\n"
        "    }\n\n"
    )
    if preferred_block not in loop:
        marker = '    functionalGroups.push({\n'
        pos = loop.find(marker)
        if pos == -1:
            raise RuntimeError(f'{path}: service group push marker not found')
        loop = loop[:pos] + preferred_block + loop[pos:]
        text = text[:loop_start] + loop + text[loop_end:]

    return text


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
    text = ensure_static_tw(text, path)
    text = patch_static_fake_ip_filter(text, path)
    text = ensure_static_foreign_nameserver(text, path)
    text = ensure_static_fcm_ipv6_prefer(text, path)
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
    text = ensure_full_script_tw(text, path)
    text = ensure_fcm_fallback_constant(text, path)
    text = patch_js_fake_ip_filter(text, path)
    text = ensure_js_foreign_nameserver(text, path)
    text = ensure_js_fcm_ipv6_prefer(text, path)
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
        verify_tw_static(text, path)
        for domain in FCM_DOMAINS:
            if domain not in text:
                raise RuntimeError(f'{path}: missing protected FCM domain {domain}')
        required = [
            'default-nameserver: *chinaDohDNS',
            'nameserver: *foreignDNS',
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
            'nameserver: foreignDNS,',
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
verify_tw_full_js(full_js, Path('Script/mihomoScript.js'))

static_fcm_start = full_static.find("  - name: 'FCM'\n")
static_fcm_end = full_static.find("  - name: 'YouTube'\n", static_fcm_start)
js_fcm_start = full_js.find("    name: 'FCM',")
js_fcm_end = full_js.find("  {\n    name: 'YouTube',", js_fcm_start)
if static_fcm_start == -1 or static_fcm_end == -1 or js_fcm_start == -1 or js_fcm_end == -1:
    raise RuntimeError('FCM IPv6-prefer downstream protection failed: FCM block missing')
static_fcm = full_static[static_fcm_start:static_fcm_end]
js_fcm = full_js[js_fcm_start:js_fcm_end]
for required in [
    FCM_IPV6_PREFER_DIRECT,
    f"default-selected: '{FCM_IPV6_PREFER_DIRECT}'",
]:
    if required not in static_fcm:
        raise RuntimeError(f'FCM IPv6-prefer downstream protection failed: static group missing {required}')
for required in [
    f"preferredDirect: '{FCM_IPV6_PREFER_DIRECT}'",
    f"defaultSelected: '{FCM_IPV6_PREFER_DIRECT}'",
]:
    if required not in js_fcm:
        raise RuntimeError(f'FCM IPv6-prefer downstream protection failed: JS service config missing {required}')
if 'groupProxies.unshift(svc.preferredDirect)' not in full_js:
    raise RuntimeError('FCM IPv6-prefer downstream protection failed: preferredDirect injection missing')

for forbidden in ["name: 'Crypto'", 'RULE-SET,cryptocurrency,Crypto', 'category-cryptocurrency.mrs']:
    if forbidden in full_static or forbidden in full_js:
        raise RuntimeError(f'Crypto downstream removal failed: still contains {forbidden}')

print('NetWeave downstream semantic patches verified for all four files')
