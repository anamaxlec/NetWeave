"""Small, dependency-free and fail-closed NetWeave semantic patch helpers."""

import ast
import re

TW_REGION = '台湾省'
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
    if "'台湾省'" in block:
        return text
    if "'新加坡'," not in block:
        raise RuntimeError(f'{label}: cannot find Singapore anchor')
    block = block.replace("'新加坡',", "'新加坡', '台湾省',", 1)
    return text[:start] + block + text[end:]


def ensure_static_tw(text, path):
    """Keep TW filter, memberships and both static groups even if upstream deletes them."""
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

    select = "  - name: '台湾省'\n"
    auto = "  - name: '台湾省-自动选择'\n"
    if (select not in text or auto not in text):
        if select in text or auto in text:
            raise RuntimeError(f'{path}: partial TW group; refusing to guess')
        anchor = "  - name: '低倍率节点'\n"
        if anchor not in text:
            raise RuntimeError(f'{path}: rate group anchor missing for TW restoration')
        group = (
            "  - name: '台湾省'\n"
            "    <<: [*group_common_select, *TW_filter]\n"
            "    include-all: true\n"
            "    proxies: ['台湾省-自动选择']\n"
            f"    icon: '{TW_DIRECT_ICON}'\n"
            "  - name: '台湾省-自动选择'\n"
            "    <<: [*group_common_auto, *TW_filter]\n\n"
        )
        text = text.replace(anchor, group + anchor, 1)
    return text


def ensure_full_script_tw(text, path):
    if path.name != 'mihomoScript.js':
        return text
    start = text.find('const regionDefinitions = [')
    end = text.find('\n];', start)
    if start == -1 or end == -1:
        raise RuntimeError(f'{path}: regionDefinitions boundaries missing')
    if "name: '台湾省'" in text[start:end]:
        return text
    region = (
        "  {\n"
        "    name: '台湾省',\n"
        "    flag: '🇹🇼',\n"
        "    regex: /" + TW_PATTERN + "/i,\n"
        "    icon: " + chr(96) + '$' + "{iconBaseUrl}Taiwan.svg" + chr(96) + ",\n"
        "  },\n"
    )
    return text[:end] + '\n' + region + text[end:]


def verify_tw_static(text, path):
    for value in ('  TW_filter:', "  - name: '台湾省'\n", "  - name: '台湾省-自动选择'\n"):
        if value not in text:
            raise RuntimeError(f'{path}: TW protection missing {value}')
    for start, end in [
        ('  proxies_default:', '  proxies_direct:'),
        ('  proxies_direct:', '  proxies_reject:'),
        ("  - name: '默认代理'\n", "  - name: '手动选择'\n"),
    ]:
        a, b = text.find(start), text.find(end, text.find(start))
        if a == -1 or b == -1 or "'台湾省'" not in text[a:b]:
            raise RuntimeError(f'{path}: TW missing from an upstream shared group')


def verify_tw_full_js(text, path):
    start = text.find('const regionDefinitions = [')
    end = text.find('\n];', start)
    if start == -1 or end == -1 or "name: '台湾省'" not in text[start:end]:
        raise RuntimeError(f'{path}: TW region missing from full script')
