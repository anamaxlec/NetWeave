from pathlib import Path

FULL_JS = Path('Script/mihomoScript.js')
FULL_STATIC = Path('Config/mihomoConfig.yaml')

SERVICES = [
    {
        'name': 'Gemini',
        'provider': 'google_gemini',
        'url': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/google-gemini.mrs',
        'comment': 'Google Gemini / AI Studio / NotebookLM 等',
        'icon': 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/Google_Search.png',
        'default': '美国',
    },
    {
        'name': 'OpenAI',
        'provider': 'openai',
        'url': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/openai.mrs',
        'comment': 'OpenAI / ChatGPT / Codex',
        'icon': 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/ChatGPT.png',
        'default': '美国',
    },
    {
        'name': 'Anthropic',
        'provider': 'anthropic',
        'url': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/anthropic.mrs',
        'comment': 'Anthropic / Claude',
        'icon': 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/ChatGPT.png',
        'default': '美国',
    },
    {
        'name': 'GitHub',
        'provider': 'github',
        'url': 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta/geo/geosite/github.mrs',
        'comment': 'GitHub / Copilot',
        'icon': 'https://fastly.jsdelivr.net/gh/Koolson/Qure@master/IconSet/Color/GitHub.png',
        'default': None,
    },
]


def ensure_js_option(text, service):
    name = service['name']
    if f'  {name}: true,' in text:
        return text

    marker = '  Google: true,'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f'mihomoScript.js: Google option marker not found for {name}')

    line = f"  {name}: true, // {service['comment']}\n"
    return text[:idx] + line + text[idx:]


def js_service_block(service):
    default_line = f"    defaultSelected: '{service['default']}',\n" if service['default'] else ''
    filename = service['url'].rsplit('/', 1)[-1]
    return (
        "  {\n"
        f"    name: '{service['name']}',\n"
        "    baseOption: selectBaseOption,\n"
        f"{default_line}"
        "    providers: {\n"
        f"      {service['provider']}: {{\n"
        "        ...ruleProviderCommonDomain,\n"
        f"        url: '{service['url']}',\n"
        f"        path: './ruleset/{service['provider']}.mrs',\n"
        f"        'path-in-bundle': 'geo/geosite/{filename}',\n"
        "      },\n"
        "    },\n"
        f"    icon: '{service['icon']}',\n"
        f"    rules: ['RULE-SET,{service['provider']},{service['name']}'],\n"
        "  },\n"
    )


def ensure_js_service(text, service):
    if f"    name: '{service['name']}'," in text:
        return text

    marker = "  {\n    name: 'Google',\n"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f"mihomoScript.js: Google service marker not found for {service['name']}")
    return text[:idx] + js_service_block(service) + text[idx:]


def detach_github_from_microsoft_js(text):
    start_marker = "  {\n    name: 'Microsoft',\n"
    end_marker = "  {\n    name: 'Apple',\n"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start == -1 or end == -1:
        raise RuntimeError('mihomoScript.js: Microsoft/Apple service markers not found')

    block = text[start:end]
    github = next(service for service in SERVICES if service['name'] == 'GitHub')
    github_provider = (
        f"      {github['provider']}: {{\n"
        "        ...ruleProviderCommonDomain,\n"
        f"        url: '{github['url']}',\n"
        f"        path: './ruleset/{github['provider']}.mrs',\n"
        f"        'path-in-bundle': 'geo/geosite/{github['url'].rsplit('/', 1)[-1]}',\n"
        "      },\n"
    )

    block = block.replace(github_provider, '', 1)
    block = block.replace(
        "    rules: ['RULE-SET,github,默认代理', 'RULE-SET,microsoft,Microsoft'],\n",
        "    rules: ['RULE-SET,microsoft,Microsoft'],\n",
        1,
    )
    return text[:start] + block + text[end:]


def patch_js():
    text = FULL_JS.read_text(encoding='utf-8')
    for service in SERVICES:
        text = ensure_js_option(text, service)
    for service in SERVICES:
        text = ensure_js_service(text, service)

    text = detach_github_from_microsoft_js(text)
    FULL_JS.write_text(text, encoding='utf-8')


def static_provider_block(service):
    filename = service['url'].rsplit('/', 1)[-1]
    return (
        f"  {service['provider']}:\n"
        "    <<: *rule_providers_domain\n"
        f"    url: '{service['url']}'\n"
        f"    path: './ruleset/{service['provider']}.mrs'\n"
        f"    path-in-bundle: 'geo/geosite/{filename}'\n"
    )


def ensure_static_provider(text, service):
    marker = f"  {service['provider']}:\n"
    if marker in text:
        return text

    google_marker = '  google:\n'
    idx = text.find(google_marker)
    if idx == -1:
        raise RuntimeError(f"mihomoConfig.yaml: Google provider marker not found for {service['name']}")
    return text[:idx] + static_provider_block(service) + text[idx:]


def static_group_block(service):
    default_line = f"    default-selected: '{service['default']}'\n" if service['default'] else ''
    return (
        f"  - name: '{service['name']}'\n"
        f"{default_line}"
        "    <<: [*group_common_select, *proxies_default]\n"
        f"    icon: '{service['icon']}'\n\n"
    )


def ensure_static_group(text, service):
    if f"  - name: '{service['name']}'\n" in text:
        return text

    marker = "  - name: 'Google'\n"
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f"mihomoConfig.yaml: Google group marker not found for {service['name']}")
    return text[:idx] + static_group_block(service) + text[idx:]


def ensure_rule_before_google(text, service):
    line = f"  - RULE-SET,{service['provider']},{service['name']}\n"
    if line in text:
        return text

    marker = '  - RULE-SET,google,Google\n'
    idx = text.find(marker)
    if idx == -1:
        raise RuntimeError(f"mihomoConfig.yaml: Google rule marker not found for {service['name']}")
    return text[:idx] + line + text[idx:]


def patch_static():
    text = FULL_STATIC.read_text(encoding='utf-8')
    for service in SERVICES:
        text = ensure_static_provider(text, service)
    for service in SERVICES:
        text = ensure_static_group(text, service)

    text = text.replace('  - RULE-SET,github,默认代理\n', '')
    for service in SERVICES:
        text = ensure_rule_before_google(text, service)

    FULL_STATIC.write_text(text, encoding='utf-8')


patch_js()
patch_static()

js = FULL_JS.read_text(encoding='utf-8')
yaml = FULL_STATIC.read_text(encoding='utf-8')

for service in SERVICES:
    name = service['name']
    provider = service['provider']
    if f"name: '{name}'" not in js or f'{name}: true' not in js:
        raise RuntimeError(f'mihomoScript.js: missing {name} option/group')
    if f'RULE-SET,{provider},{name}' not in js:
        raise RuntimeError(f'mihomoScript.js: missing {name} rule')
    if f"- name: '{name}'" not in yaml or f'RULE-SET,{provider},{name}' not in yaml:
        raise RuntimeError(f'mihomoConfig.yaml: missing {name} group/rule')
    if service['url'] not in js or service['url'] not in yaml:
        raise RuntimeError(f'missing provider URL for {name}')

if 'RULE-SET,github,默认代理' in js or 'RULE-SET,github,默认代理' in yaml:
    raise RuntimeError('GitHub is still routed directly to 默认代理')

js_order = [js.index(f"name: '{service['name']}'") for service in SERVICES]
js_order.extend([js.index("name: 'Google'"), js.index("name: 'AI'")])
if js_order != sorted(js_order):
    raise RuntimeError('mihomoScript.js: dedicated service order is incorrect')

yaml_rule_order = [yaml.index(f"RULE-SET,{service['provider']},{service['name']}") for service in SERVICES]
yaml_rule_order.extend([yaml.index('RULE-SET,google,Google'), yaml.index('RULE-SET,ai,AI')])
if yaml_rule_order != sorted(yaml_rule_order):
    raise RuntimeError('mihomoConfig.yaml: dedicated rule order is incorrect')

print('Dedicated Gemini/OpenAI/Anthropic/GitHub groups verified with minimal patches')
