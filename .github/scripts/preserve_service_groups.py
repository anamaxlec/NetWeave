from pathlib import Path
import re

FULL_JS = Path('Script/mihomoScript.js')
FULL_STATIC = Path('Config/mihomoConfig.yaml')

PROVIDERS = {
    'google_gemini': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/google-gemini.mrs',
    'openai': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/openai.mrs',
    'anthropic': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/anthropic.mrs',
    'github': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/github.mrs',
}


def ensure_js_option(text, name, comment):
    if re.search(rf'(?m)^  {re.escape(name)}:\s*true,', text):
        return text
    marker = re.search(r'(?m)^  Google:\s*true,.*$', text)
    if not marker:
        raise RuntimeError('mihomoScript.js: Google option marker not found')
    line = f'  {name}: true, // {comment}\n'
    return text[:marker.start()] + line + text[marker.start():]


def js_service_block(name, provider, url, icon, default_selected=None):
    default_line = f"    defaultSelected: '{default_selected}',\n" if default_selected else ''
    return (
        "  {\n"
        f"    name: '{name}',\n"
        "    baseOption: selectBaseOption,\n"
        f"{default_line}"
        "    providers: {\n"
        f"      {provider}: {{\n"
        "        ...ruleProviderCommonDomain,\n"
        f"        url: '{url}',\n"
        f"        path: './ruleset/{provider}.mrs',\n"
        f"        'path-in-bundle': 'geo/geosite/{url.rsplit('/', 1)[-1]}',\n"
        "      },\n"
        "    },\n"
        f"    icon: '{icon}',\n"
        f"    rules: ['RULE-SET,{provider},{name}'],\n"
        "  },\n"
    )


def ensure_js_service(text, name, block):
    if re.search(rf"(?m)^    name: '{re.escape(name)}',$", text):
        return text
    marker = re.search(r"(?m)^  \{\n    name: 'Google',\n", text)
    if not marker:
        raise RuntimeError(f'mihomoScript.js: insertion point for {name} not found')
    return text[:marker.start()] + block + text[marker.start():]


def detach_github_from_microsoft_js(text):
    match = re.search(
        r"(?ms)^  \{\n    name: 'Microsoft',\n.*?^  \},\n(?=  \{\n    name: 'Apple',)",
        text,
    )
    if not match:
        raise RuntimeError('mihomoScript.js: Microsoft service block not found')
    block = match.group(0)
    block = re.sub(
        r"(?ms)^      github: \{\n.*?^      \},\n(?=      microsoft:)",
        '',
        block,
        count=1,
    )
    block = block.replace(
        "rules: ['RULE-SET,github,默认代理', 'RULE-SET,microsoft,Microsoft']",
        "rules: ['RULE-SET,microsoft,Microsoft']",
    )
    return text[:match.start()] + block + text[match.end():]


def patch_js():
    text = FULL_JS.read_text(encoding='utf-8')
    text = ensure_js_option(text, 'Gemini', 'Google Gemini / AI Studio / NotebookLM 等')
    text = ensure_js_option(text, 'OpenAI', 'OpenAI / ChatGPT / Codex')
    text = ensure_js_option(text, 'Anthropic', 'Anthropic / Claude')
    text = ensure_js_option(text, 'GitHub', 'GitHub / Copilot')

    services = [
        (
            'Gemini',
            js_service_block(
                'Gemini',
                'google_gemini',
                PROVIDERS['google_gemini'],
                'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Google_Search.png',
                '美国',
            ),
        ),
        (
            'OpenAI',
            js_service_block(
                'OpenAI',
                'openai',
                PROVIDERS['openai'],
                'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/ChatGPT.png',
                '美国',
            ),
        ),
        (
            'Anthropic',
            js_service_block(
                'Anthropic',
                'anthropic',
                PROVIDERS['anthropic'],
                'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/ChatGPT.png',
                '美国',
            ),
        ),
        (
            'GitHub',
            js_service_block(
                'GitHub',
                'github',
                PROVIDERS['github'],
                'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/GitHub.png',
            ),
        ),
    ]
    for name, block in services:
        text = ensure_js_service(text, name, block)

    text = detach_github_from_microsoft_js(text)
    FULL_JS.write_text(text, encoding='utf-8')


def static_provider_block(name, url):
    filename = url.rsplit('/', 1)[-1]
    return (
        f"  {name}:\n"
        "    <<: *rule_providers_domain\n"
        f"    url: '{url}'\n"
        f"    path: './ruleset/{name}.mrs'\n"
        f"    path-in-bundle: 'geo/geosite/{filename}'\n"
    )


def ensure_static_provider(text, name, url):
    if re.search(rf'(?m)^  {re.escape(name)}:\s*$', text):
        return text
    marker = re.search(r'(?m)^  google:\s*$', text)
    if not marker:
        raise RuntimeError(f'mihomoConfig.yaml: provider insertion point for {name} not found')
    return text[:marker.start()] + static_provider_block(name, url) + text[marker.start():]


def static_group_block(name, icon, default_selected=None):
    default_line = f"    default-selected: '{default_selected}'\n" if default_selected else ''
    return (
        f"  - name: '{name}'\n"
        f"{default_line}"
        "    <<: [*group_common_select, *proxies_default]\n"
        f"    icon: '{icon}'\n\n"
    )


def ensure_static_group(text, name, block):
    if re.search(rf"(?m)^  - name: '{re.escape(name)}'$", text):
        return text
    marker = re.search(r"(?m)^  - name: 'Google'$", text)
    if not marker:
        raise RuntimeError(f'mihomoConfig.yaml: group insertion point for {name} not found')
    return text[:marker.start()] + block + text[marker.start():]


def ensure_rule_before_google(text, rule):
    line = f'  - {rule}\n'
    if line in text:
        return text
    marker = '  - RULE-SET,google,Google\n'
    if marker not in text:
        raise RuntimeError(f'mihomoConfig.yaml: Google rule insertion point missing for {rule}')
    return text.replace(marker, line + marker, 1)


def patch_static():
    text = FULL_STATIC.read_text(encoding='utf-8')
    for name in ['google_gemini', 'openai', 'anthropic']:
        text = ensure_static_provider(text, name, PROVIDERS[name])

    groups = [
        ('Gemini', static_group_block('Gemini', 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Google_Search.png', '美国')),
        ('OpenAI', static_group_block('OpenAI', 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/ChatGPT.png', '美国')),
        ('Anthropic', static_group_block('Anthropic', 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/ChatGPT.png', '美国')),
        ('GitHub', static_group_block('GitHub', 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/GitHub.png')),
    ]
    for name, block in groups:
        text = ensure_static_group(text, name, block)

    text = text.replace('  - RULE-SET,github,默认代理\n', '')
    for rule in [
        'RULE-SET,google_gemini,Gemini',
        'RULE-SET,openai,OpenAI',
        'RULE-SET,anthropic,Anthropic',
        'RULE-SET,github,GitHub',
    ]:
        text = ensure_rule_before_google(text, rule)

    FULL_STATIC.write_text(text, encoding='utf-8')


patch_js()
patch_static()

js = FULL_JS.read_text(encoding='utf-8')
yaml = FULL_STATIC.read_text(encoding='utf-8')

for name, provider in [('Gemini', 'google_gemini'), ('OpenAI', 'openai'), ('Anthropic', 'anthropic'), ('GitHub', 'github')]:
    if f"name: '{name}'" not in js or f"{name}: true" not in js:
        raise RuntimeError(f'mihomoScript.js: missing {name} option/group')
    if f"RULE-SET,{provider},{name}" not in js:
        raise RuntimeError(f'mihomoScript.js: missing {name} rule')
    if f"- name: '{name}'" not in yaml or f"RULE-SET,{provider},{name}" not in yaml:
        raise RuntimeError(f'mihomoConfig.yaml: missing {name} group/rule')

for name in ['google_gemini', 'openai', 'anthropic']:
    if PROVIDERS[name] not in js or PROVIDERS[name] not in yaml:
        raise RuntimeError(f'missing provider URL for {name}')

if 'RULE-SET,github,默认代理' in js or 'RULE-SET,github,默认代理' in yaml:
    raise RuntimeError('GitHub is still routed directly to 默认代理')

js_order = [js.index("name: 'Gemini'"), js.index("name: 'OpenAI'"), js.index("name: 'Anthropic'"), js.index("name: 'GitHub'"), js.index("name: 'Google'"), js.index("name: 'AI'")]
if js_order != sorted(js_order):
    raise RuntimeError('mihomoScript.js: dedicated service order is incorrect')

yaml_rule_order = [yaml.index('RULE-SET,google_gemini,Gemini'), yaml.index('RULE-SET,openai,OpenAI'), yaml.index('RULE-SET,anthropic,Anthropic'), yaml.index('RULE-SET,github,GitHub'), yaml.index('RULE-SET,google,Google'), yaml.index('RULE-SET,ai,AI')]
if yaml_rule_order != sorted(yaml_rule_order):
    raise RuntimeError('mihomoConfig.yaml: dedicated rule order is incorrect')

print('Dedicated Gemini/OpenAI/Anthropic/GitHub groups verified')
