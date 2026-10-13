"""Small, dependency-free and fail-closed NetWeave semantic patch helpers."""

import ast
import re

TW_REGION = '台湾'
TW_PATTERN = '🇹🇼|台湾|台北|高雄|(?<![A-Za-z])TWN?(?![A-Za-z])|taiwan'
TW_DIRECT_ICON = 'https://fastly.jsdelivr.net/gh/AIsouler/MyClash@main/Icons/svg/Taiwan.svg'


def parse_string_list_field(text, key):
    """Read only a bracket-style YAML string sequence; never consume later fields.

    Returns the literal entries, field-start offset and offset after closing ']'.
    Unknown layouts fail rather than silently corrupting an unrelated DNS option.
    """
    matches = list(re.finditer(r'(?m)^  ' + re.escape(key) + r':[ \t]*', text))
    if len(matches) != 1:
        raise RuntimeError(f'{key}: expected exactly one DNS field, found {len(matches)}')
    label_start = matches[0].start()
    cursor = matches[0].end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor == len(text) or text[cursor] != '[':
        raise RuntimeError(f'{key}: unsupported YAML sequence layout (expected [..])')

    start = cursor
    quoted = None
    depth = 0
    end = None
    while cursor < len(text):
        ch = text[cursor]
        if quoted:
            if ch == '\\' and quoted == '"':
                cursor += 2
                continue
            if ch == quoted:
                if quoted == "'" and cursor + 1 < len(text) and text[cursor + 1] == "'":
                    cursor += 2
                    continue
                quoted = None
        elif ch in ("'", '"'):
            quoted = ch
        elif ch == '[':
            depth += 1
            if depth > 1:
                raise RuntimeError(f'{key}: nested YAML sequences are unsupported')
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end = cursor + 1
                break
        cursor += 1
    if end is None or quoted:
        raise RuntimeError(f'{key}: unterminated YAML sequence')
    trailing = text[end:text.find('\n', end) if '\n' in text[end:] else len(text)]
    if trailing.strip() and not trailing.lstrip().startswith('#'):
        raise RuntimeError(f'{key}: unexpected content after sequence')
    try:
        entries = ast.literal_eval(text[start:end])
    except (SyntaxError, ValueError) as exc:
        raise RuntimeError(f'{key}: non-literal string sequence') from exc
    if not isinstance(entries, list) or any(not isinstance(item, str) for item in entries):
        raise RuntimeError(f'{key}: all sequence items must be literal strings')
    return entries, label_start, end


def _insert_region_into_group(text, start_marker, end_marker, label):
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start == -1 or end == -1:
        raise RuntimeError(f'{label}: group boundaries missing')
    block = text[start:end]
    if "'台湾'" in block:
        return text
    if "'新加坡'," not in block:
        raise RuntimeError(f'{label}: cannot find Singapore anchor')
    block = block.replace("'新加坡',", "'新加坡', '台湾',", 1)
    return text[:start] + block + text[end:]


def _remove_legacy_tw(text, path):
    for name in ('台湾省', '台湾省-自动选择'):
        marker = f"  - name: '{name}'\n"
        if text.count(marker) > 1:
            raise RuntimeError(f'{path}: duplicate legacy group {name}')
        if marker in text:
            pos = text.index(marker)
            following = re.search(r"(?m)^  - name: '[^']+'\n", text[pos + len(marker):])
            if not following:
                raise RuntimeError(f'{path}: missing group boundary for {name}')
            stop = pos + len(marker) + following.start()
            text = text[:pos] + text[stop:]
    return text.replace("'台湾省',", '').replace("'台湾省-自动选择',", '')


def ensure_static_tw(text, path):
    """Keep TW filter, memberships and both static groups even if upstream deletes them."""
    text = _remove_legacy_tw(text, path)
    if "  TW_filter:" not in text:
        m = re.search(r'(?m)^  SG_filter:.*\n', text)
        if not m:
            raise RuntimeError(f'{path}: SG_filter anchor missing for TW restoration')
        text = (
            text[:m.end()]
            + f"  TW_filter: &TW_filter {{ filter: '(?i)({TW_PATTERN})' }}\n"
            + text[m.end():]
        )

    exclude = re.search(r"(?m)^(?P<indent>\s*)exclude-filter: '(?P<pattern>[^'\n]+)'(?P<suffix>,?)$", text)
    if not exclude:
        raise RuntimeError(f'{path}: exclude-filter structure not recognized')
    value = exclude.group('pattern')
    if 'taiwan' not in value:
        if not value.endswith(')'):
            raise RuntimeError(f'{path}: exclude-filter is not a parenthesized regex')
        value = value[:-1] + '|' + TW_PATTERN + ')'
        text = text[:exclude.start('pattern')] + value + text[exclude.end('pattern'):]

    for start, end, label in [
        ('  proxies_default:', '  proxies_direct:', 'proxies_default'),
        ('  proxies_direct:', '  proxies_reject:', 'proxies_direct'),
        ("  - name: '默认代理'\n", "  - name: '手动选择'\n", '默认代理'),
    ]:
        text = _insert_region_into_group(text, start, end, f'{path}: {label}')

    select = "  - name: '台湾'\n"
    auto = "  - name: '台湾-自动选择'\n"
    if (select not in text or auto not in text):
        if select in text or auto in text:
            raise RuntimeError(f'{path}: partial TW group; refusing to guess')
        anchor = "  - name: '低倍率节点'\n"
        if anchor not in text:
            raise RuntimeError(f'{path}: rate group anchor missing for TW restoration')
        group = (
            "  - name: '台湾'\n"
            "    <<: [*group_common_select, *TW_filter]\n"
            "    include-all: true\n"
            "    proxies: ['台湾-自动选择']\n"
            f"    icon: '{TW_DIRECT_ICON}'\n"
            "  - name: '台湾-自动选择'\n"
            "    <<: [*group_common_auto, *TW_filter]\n\n"
        )
        text = text.replace(anchor, group + anchor, 1)
    return text


def ensure_full_script_tw(text, path):
    if path.name != 'mihomoScript.js':
        return text
    text, legacy_count = re.subn(
        r"(?ms)^  \{\n    name: '台湾省',\n.*?^  \},\n",
        '',
        text,
    )
    if legacy_count > 1:
        raise RuntimeError(f'{path}: duplicate legacy TW regions')
    start = text.find('const regionDefinitions = [')
    end = text.find('\n];', start)
    if start == -1 or end == -1:
        raise RuntimeError(f'{path}: regionDefinitions boundaries missing')
    if "name: '台湾'" in text[start:end]:
        return text
    region = (
        "  {\n"
        "    name: '台湾',\n"
        "    flag: '🇹🇼',\n"
        "    regex: /" + TW_PATTERN + "/i,\n"
        "    icon: " + chr(96) + '$' + "{iconBaseUrl}Taiwan.svg" + chr(96) + ",\n"
        "  },\n"
    )
    return text[:end] + '\n' + region + text[end:]


def verify_tw_static(text, path):
    if any(label in text for label in ("  - name: '台湾省'\n", "  - name: '台湾省-自动选择'\n", "'台湾省',")):
        raise RuntimeError(f'{path}: legacy TW group remains')
    if text.count("  - name: '台湾'\n") != 1 or text.count("  - name: '台湾-自动选择'\n") != 1:
        raise RuntimeError(f'{path}: expected exactly one TW group pair')
    for value in ('  TW_filter:', "  - name: '台湾'\n", "  - name: '台湾-自动选择'\n"):
        if value not in text:
            raise RuntimeError(f'{path}: TW protection missing {value}')
    for start, end in [
        ('  proxies_default:', '  proxies_direct:'),
        ('  proxies_direct:', '  proxies_reject:'),
        ("  - name: '默认代理'\n", "  - name: '手动选择'\n"),
    ]:
        a, b = text.find(start), text.find(end, text.find(start))
        if a == -1 or b == -1 or "'台湾'" not in text[a:b]:
            raise RuntimeError(f'{path}: TW missing from an upstream shared group')


def verify_tw_full_js(text, path):
    if "name: '台湾省'" in text:
        raise RuntimeError(f'{path}: legacy TW region remains')
    start = text.find('const regionDefinitions = [')
    end = text.find('\n];', start)
    if start == -1 or end == -1 or "name: '台湾'" not in text[start:end]:
        raise RuntimeError(f'{path}: TW region missing from full script')

def verify_googlefcm_provider(text, path):
    """Check the always-available domain provider without pinning a CDN hostname.

    The source may be an upstream mirror URL or the script's ruleSetBaseUrl.
    The provider itself, its rule behavior and its bundle path must remain intact.
    """
    if path.suffix == '.yaml':
        found = re.search(
            r"(?ms)^  googlefcm:\n(?P<body>.*?)(?=^  [a-zA-Z0-9_-]+:\n|\Z)",
            text,
        )
        if not found:
            raise RuntimeError(f'{path}: googlefcm provider missing')
        block = found.group('body')
        required = ("<<: *rule_providers_domain", "path: './ruleset/googlefcm.mrs'",
                    "path-in-bundle: 'geo/geosite/googlefcm.mrs'")
        url = re.search(r"(?m)^    url: '(https?://[^']+)'\s*$", block)
        valid_url = url is not None and url.group(1).endswith('/geo/geosite/googlefcm.mrs')
    else:
        start = text.find('const baseRuleProviders = {')
        end = text.find('// 策略组公共配置', start)
        if start == -1 or end == -1:
            raise RuntimeError(f'{path}: baseRuleProviders boundaries missing')
        found = re.search(
            r"(?ms)^  googlefcm: \{\n(?P<body>.*?)^  \},\n",
            text[start:end],
        )
        if not found:
            raise RuntimeError(f'{path}: base googlefcm provider missing')
        block = found.group('body')
        required = ("...ruleProviderCommonDomain,", "path: './ruleset/googlefcm.mrs'",
                    "'path-in-bundle': 'geo/geosite/googlefcm.mrs'")
        url = re.search(r"(?m)^    url: (?:'([^']+)'|`([^`]+)`),\s*$", block)
        value = next((v for v in url.groups() if v), '') if url else ''
        valid_url = (
            value.startswith('https://') and value.endswith('/geo/geosite/googlefcm.mrs')
        ) or value == '$' + '{ruleSetBaseUrl}geosite/googlefcm.mrs'

    if not valid_url or not all(field in block for field in required):
        raise RuntimeError(f'{path}: googlefcm provider has unexpected URL, behavior or bundle path')
