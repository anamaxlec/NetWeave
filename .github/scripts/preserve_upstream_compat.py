from pathlib import Path
import re

STATIC_FILES = [
    Path('Config/mihomoConfig.yaml'),
    Path('Config/mihomoConfigLite.yaml'),
]
JS_FILES = [
    Path('Script/Script.js'),
    Path('Script/mihomoScript.js'),
]

CHINA_DOH = [
    'https://223.5.5.5/dns-query#DIRECT',
    'https://1.12.12.12/dns-query#DIRECT',
]


def ensure_static_china_doh(text, path):
    if '&chinaDohDNS' in text:
        return text

    line = "  chinaDohDNS: &chinaDohDNS [" + ", ".join(f"'{item}'" for item in CHINA_DOH) + "]\n"

    if 'dns_common:\n' in text:
        marker = '\ndns:\n'
        idx = text.find(marker)
        if idx == -1:
            raise RuntimeError(f'{path}: dns section not found after dns_common')
        return text[:idx] + line + text[idx:]

    marker = '\ndns:\n'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'{path}: dns section not found')
    return text[:idx] + '\n' + line.lstrip() + text[idx:]


def patch_static_dns(text, path):
    text = ensure_static_china_doh(text, path)

    default_ns = re.compile(r"(?m)^(\s*)default-nameserver:\s*\*(?:defaultDNS|chinaDNS|chinaDohDNS)\s*$")
    if not default_ns.search(text):
        raise RuntimeError(f'{path}: supported default-nameserver layout not found')
    text = default_ns.sub(r"\1default-nameserver: *chinaDohDNS", text, count=1)

    proxy_ns = re.compile(r"(?m)^(\s*)proxy-server-nameserver:\s*\*(?:proxyServerDNS|chinaDNS|chinaDohDNS)\s*$")
    if not proxy_ns.search(text):
        raise RuntimeError(f'{path}: supported proxy-server-nameserver layout not found')
    text = proxy_ns.sub(r"\1proxy-server-nameserver: *chinaDohDNS", text, count=1)

    # preserve_downstream.py 的静态 fake-ip patch 以 proxy-server-nameserver
    # 作为 fake-ip-filter 的结束锚点；将上游的新字段顺序规范为安全顺序。
    new_order = (
        '  default-nameserver: *chinaDohDNS\n'
        '  proxy-server-nameserver: *chinaDohDNS\n'
    )
    safe_order = (
        '  proxy-server-nameserver: *chinaDohDNS\n'
        '  default-nameserver: *chinaDohDNS\n'
    )
    text = text.replace(new_order, safe_order, 1)

    return text


def patch_static_tun(text, path):
    start = text.find('\ntun:\n')
    if start == -1:
        raise RuntimeError(f'{path}: tun section not found')
    end = text.find('\n# ---', start)
    if end == -1:
        end = len(text)

    block = text[start:end]
    block = re.sub(r'(?m)^(\s*stack:)\s*mips\s*$', r'\1 system', block, count=1)
    return text[:start] + block + text[end:]


def ensure_js_china_doh(text, path):
    if 'const chinaDohDNS = [' in text:
        return text

    marker = '/**\n * hosts 匹配优先级'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'{path}: DNS constants insertion marker not found')

    block = (
        'const chinaDohDNS = [\n'
        + ''.join(f"  '{item}',\n" for item in CHINA_DOH)
        + '];\n\n'
    )
    return text[:idx] + block + text[idx:]


def patch_js_dns(text, path):
    text = ensure_js_china_doh(text, path)

    default_ns = re.compile(
        r"(?m)^(\s*)'default-nameserver':\s*(?:defaultDNS|chinaDNS|chinaDohDNS),\s*$"
    )
    if not default_ns.search(text):
        raise RuntimeError(f'{path}: supported default-nameserver layout not found')
    text = default_ns.sub(r"\1'default-nameserver': chinaDohDNS,", text, count=1)

    proxy_ns = re.compile(
        r"(?m)^(\s*)'proxy-server-nameserver':\s*(?:proxyServerDNS|chinaDNS|chinaDohDNS),\s*$"
    )
    if not proxy_ns.search(text):
        raise RuntimeError(f'{path}: supported proxy-server-nameserver layout not found')
    text = proxy_ns.sub(r"\1'proxy-server-nameserver': chinaDohDNS,", text, count=1)

    return text


def normalize_js_fake_ip_filter(text, path):
    marker = "'fake-ip-filter': ["
    pos = text.find(marker)
    if pos == -1:
        raise RuntimeError(f'{path}: fake-ip-filter not found before downstream patch')

    line_start = text.rfind('\n', 0, pos) + 1
    line_end = text.find('\n', pos)
    if line_end == -1:
        line_end = len(text)

    # Lite 上游会把整个数组压成单行；主 patch 按条目行处理，所以先展开成和全量版一致的格式。
    line = text[line_start:line_end]
    open_bracket = line.find('[')
    close_bracket = line.rfind(']')
    if open_bracket != -1 and close_bracket > open_bracket:
        indent = line[: len(line) - len(line.lstrip())]
        prop = line[:open_bracket].rstrip()
        inner = line[open_bracket + 1 : close_bracket]
        entries = [item.strip() for item in inner.split(',') if item.strip()]
        if not any(item == '...proxyFakeIpFilter' for item in entries):
            if 'const proxyFakeIpFilter =' not in text:
                raise RuntimeError(f'{path}: proxyFakeIpFilter variable and spread are both missing')
            entries.append('...proxyFakeIpFilter')

        rebuilt = (
            f'{prop}[\n'
            + ''.join(f'{indent}  {entry},\n' for entry in entries)
            + f'{indent}],'
        )
        return text[:line_start] + rebuilt + text[line_end:]

    # 多行布局只需确认 spread 存在；若上游删除但变量仍存在，则补到数组结尾。
    spread_pos = text.find('...proxyFakeIpFilter,', pos)
    if spread_pos != -1:
        return text

    if 'const proxyFakeIpFilter =' not in text:
        raise RuntimeError(f'{path}: proxyFakeIpFilter variable and spread are both missing')

    close = text.find('\n    ],', pos)
    if close == -1:
        raise RuntimeError(f'{path}: fake-ip-filter closing bracket not found')
    return text[:close] + '\n      ...proxyFakeIpFilter,' + text[close:]


def patch_js_tun(text, path):
    marker = "newConfig['tun'] = {"
    start = text.find(marker)
    if start == -1:
        raise RuntimeError(f'{path}: generated tun block not found')
    end = text.find('\n  };', start)
    if end == -1:
        raise RuntimeError(f'{path}: generated tun block end not found')

    block = text[start:end]
    block = re.sub(r"(?m)^(\s*stack:)\s*'mips',\s*$", r"\1 'system',", block, count=1)
    return text[:start] + block + text[end:]


def patch_static(path):
    text = path.read_text(encoding='utf-8')
    text = patch_static_dns(text, path)
    text = patch_static_tun(text, path)
    path.write_text(text, encoding='utf-8')


def patch_js(path):
    text = path.read_text(encoding='utf-8')
    text = patch_js_dns(text, path)
    text = normalize_js_fake_ip_filter(text, path)
    text = patch_js_tun(text, path)
    path.write_text(text, encoding='utf-8')


for file in STATIC_FILES:
    patch_static(file)
for file in JS_FILES:
    patch_js(file)

for file in STATIC_FILES:
    text = file.read_text(encoding='utf-8')
    if 'default-nameserver: *chinaDohDNS' not in text:
        raise RuntimeError(f'{file}: encrypted default DNS policy not preserved')
    if 'proxy-server-nameserver: *chinaDohDNS' not in text:
        raise RuntimeError(f'{file}: encrypted proxy-server DNS policy not preserved')
    if re.search(r'(?m)^\s*stack:\s*mips\s*$', text):
        raise RuntimeError(f'{file}: invalid top-level TUN stack mips remains')

for file in JS_FILES:
    text = file.read_text(encoding='utf-8')
    if "'default-nameserver': chinaDohDNS," not in text:
        raise RuntimeError(f'{file}: encrypted default DNS policy not preserved')
    if "'proxy-server-nameserver': chinaDohDNS," not in text:
        raise RuntimeError(f'{file}: encrypted proxy-server DNS policy not preserved')
    fake_ip_pos = text.find("'fake-ip-filter': [")
    spread_pos = text.find('...proxyFakeIpFilter,', fake_ip_pos)
    if fake_ip_pos == -1 or spread_pos == -1:
        raise RuntimeError(f'{file}: proxyFakeIpFilter spread is unavailable before downstream patch')
    tun_start = text.find("newConfig['tun'] = {")
    tun_end = text.find('\n  };', tun_start)
    if tun_start == -1 or tun_end == -1:
        raise RuntimeError(f'{file}: generated tun block not found during validation')
    if "stack: 'mips'" in text[tun_start:tun_end]:
        raise RuntimeError(f'{file}: invalid top-level TUN stack mips remains')

print('Upstream DNS layout, fake-ip layout and top-level TUN compatibility verified')
