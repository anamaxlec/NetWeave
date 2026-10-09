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
)


class NetWeavePatchTests(unittest.TestCase):
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
            r"  \{\n    name: '台湾省',\n.*?  \},\n",
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
                    r"(?ms)^  - name: '台湾省'\n.*?(?=  - name: '低倍率节点'\n)",
                    '',
                    without_tw,
                    count=1,
                )
                self.assertNotEqual(without_tw, original)
                without_tw = without_tw.replace("'台湾省',", '')
                without_tw = without_tw.replace('|' + TW_PATTERN, '')
                restored = ensure_static_tw(without_tw, Path(name))
                verify_tw_static(restored, Path(name))
                self.assertEqual(ensure_static_tw(restored, Path(name)), restored)


if __name__ == '__main__':
    unittest.main()
