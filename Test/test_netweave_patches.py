"""Regression checks for NetWeave's no-dependency upstream compatibility helpers."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github' / 'scripts'))
from netweave_patch_helpers import (  # noqa: E402
    TW_PATTERN,
    ensure_full_script_tw,
    ensure_static_tw,
    parse_string_list_field,
    verify_tw_full_js,
    verify_tw_static,
    verify_googlefcm_provider,
)


class NetWeavePatchTests(unittest.TestCase):
    def test_googlefcm_provider_accepts_upstream_cdn_changes(self):
        static = (ROOT / 'Config' / 'mihomoConfig.yaml').read_text(encoding='utf-8')
        js = (ROOT / 'Script' / 'Script.js').read_text(encoding='utf-8')
        original = 'https://fastly.jsdelivr.net/gh/appshubcc/bett-rules@meta'
        alternate = 'https://cdn.jsdmirror.com/gh/appshubcc/bett-rules@meta'
        verify_googlefcm_provider(static, Path('Config/mihomoConfig.yaml'))
        verify_googlefcm_provider(js, Path('Script/Script.js'))
        verify_googlefcm_provider(static.replace(original, alternate), Path('Config/mihomoConfig.yaml'))
        verify_googlefcm_provider(js.replace(original, alternate), Path('Script/Script.js'))

    def test_googlefcm_provider_rejects_mismatched_rule_file(self):
        static = (ROOT / 'Config' / 'mihomoConfig.yaml').read_text(encoding='utf-8')
        js = (ROOT / 'Script' / 'Script.js').read_text(encoding='utf-8')
        with self.assertRaises(RuntimeError):
            verify_googlefcm_provider(
                static.replace('geo/geosite/googlefcm.mrs', 'geo/geosite/youtube.mrs'),
                Path('Config/mihomoConfig.yaml'),
            )
        with self.assertRaises(RuntimeError):
            verify_googlefcm_provider(
                js.replace("path: './ruleset/googlefcm.mrs'", "path: './ruleset/youtube.mrs'"),
                Path('Script/Script.js'),
            )

    def test_only_fake_ip_entries_are_extracted(self):
        src = (
            "dns:\n  fake-ip-filter:\n"
            "    ['rule-set:private', 'mtalk.google.com']\n"
            "  newly-added-policy:\n    'example.org': 'malicious-entry'\n"
            "  proxy-server-nameserver: ['223.5.5.5']\n"
        )
        entries, start, end = parse_string_list_field(src, 'fake-ip-filter')
        self.assertEqual(entries, ['rule-set:private', 'mtalk.google.com'])
        self.assertEqual(src[start:end].strip().splitlines()[0], 'fake-ip-filter:')
        self.assertNotIn('malicious-entry', entries)
        self.assertTrue(src[end:].startswith('\n  newly-added-policy:'))

    def test_unknown_yaml_list_structure_fails_closed(self):
        with self.assertRaises(RuntimeError):
            parse_string_list_field("dns:\n  fake-ip-filter:\n    - 'mtalk.google.com'\n", 'fake-ip-filter')
        with self.assertRaises(RuntimeError):
            parse_string_list_field("dns:\n  fake-ip-filter: [['nested']]\n", 'fake-ip-filter')

    def test_tw_restored_after_full_script_upstream_removal(self):
        original = (ROOT / 'Script' / 'mihomoScript.js').read_text(encoding='utf-8')
        without_tw = re.sub(
            r"  \{\n    name: '台湾',\n.*?  \},\n",
            '',
            original,
            count=1,
            flags=re.S,
        )
        self.assertNotEqual(without_tw, original)
        restored = ensure_full_script_tw(without_tw, Path('Script/mihomoScript.js'))
        verify_tw_full_js(restored, Path('Script/mihomoScript.js'))
        self.assertEqual(ensure_full_script_tw(restored, Path('Script/mihomoScript.js')), restored)

    def test_tw_restored_if_static_upstream_drops_region(self):
        for name in ('mihomoConfig.yaml', 'mihomoConfigLite.yaml'):
            with self.subTest(name=name):
                original = (ROOT / 'Config' / name).read_text(encoding='utf-8')
                without_tw = re.sub(r'(?m)^  TW_filter:.*\n', '', original, count=1)
                without_tw = re.sub(
                    r"(?ms)^  - name: '台湾'\n.*?(?=  - name: '低倍率节点'\n)",
                    '',
                    without_tw,
                    count=1,
                )
                self.assertNotEqual(without_tw, original)
                without_tw = without_tw.replace("'台湾',", '')
                without_tw = without_tw.replace('|' + TW_PATTERN, '')
                restored = ensure_static_tw(without_tw, Path(name))
                verify_tw_static(restored, Path(name))
                self.assertEqual(ensure_static_tw(restored, Path(name)), restored)

    def test_legacy_tw_groups_are_deduplicated(self):
        for filename in ('mihomoConfig.yaml', 'mihomoConfigLite.yaml'):
            original = (ROOT / 'Config' / filename).read_text(encoding='utf-8')
            # Exercise the exact migration from a previous NetWeave build.
            legacy = (
                "  - name: '台湾省'\n"
                "    <<: [*group_common_select, *TW_filter]\n"
                "    include-all: true\n"
                "    proxies: ['台湾省-自动选择']\n"
                "    icon: 'https://example.com/Taiwan.svg'\n"
                "  - name: '台湾省-自动选择'\n"
                "    <<: [*group_common_auto, *TW_filter]\n"
            )
            fixture = original.replace("  - name: '低倍率节点'\n", legacy + "  - name: '低倍率节点'\n", 1)
            fixture = fixture.replace("'台湾',", "'台湾省', '台湾',", 1)
            result = ensure_static_tw(fixture, Path(filename))
            verify_tw_static(result, Path(filename))
            self.assertNotIn("  - name: '台湾省'\n", result)
            self.assertEqual(result, ensure_static_tw(result, Path(filename)))

        js = (ROOT / 'Script' / 'mihomoScript.js').read_text(encoding='utf-8')
        legacy_js = (
            "  {\n"
            "    name: '台湾省',\n"
            "    flag: '🇹🇼',\n"
            "    regex: /🇹🇼|台湾|taiwan/i,\n"
            "    icon: 'https://example.com/Taiwan.svg',\n"
            "  },\n"
        )
        fixture = js.replace("  {\n    name: '台湾',\n", legacy_js + "  {\n    name: '台湾',\n", 1)
        result = ensure_full_script_tw(fixture, Path('mihomoScript.js'))
        verify_tw_full_js(result, Path('mihomoScript.js'))
        self.assertEqual(result, ensure_full_script_tw(result, Path('mihomoScript.js')))



if __name__ == '__main__':
    unittest.main()
