"""Regression tests for the opt-in airport DNS protection patch."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / '.github' / 'scripts' / 'preserve_airport_dns.py'
spec = importlib.util.spec_from_file_location('airport_dns_patch', PATCH)
airport_dns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(airport_dns)


class AirportDnsPatchTest(unittest.TestCase):
    def test_scripts_are_patched_idempotently(self):
        for path in airport_dns.JS_FILES:
            with self.subTest(path=str(path)):
                text = (ROOT / path).read_text(encoding='utf-8')
                self.assertEqual(airport_dns.patch_js(text, path), text)
                self.assertIn('优先机场DNS: false', text)
                self.assertIn('buildAirportNodeDnsPolicy(originalDnsConfig, proxyDomains, shouldRewriteByHosts)', text)
                self.assertIn("'proxy-server-nameserver-policy': effectiveProxyServerPolicy", text)

    def test_missing_toggle_is_restored(self):
        for path in airport_dns.JS_FILES:
            with self.subTest(path=str(path)):
                original = (ROOT / path).read_text(encoding='utf-8')
                missing = original.replace(airport_dns.TOGGLE, '', 1)
                self.assertNotEqual(original, missing)
                self.assertEqual(airport_dns.patch_js(missing, path), original)

    def test_duplicate_toggle_rejected(self):
        path = airport_dns.JS_FILES[0]
        original = (ROOT / path).read_text(encoding='utf-8')
        duplicate = original.replace(airport_dns.TOGGLE, airport_dns.TOGGLE * 2, 1)
        with self.assertRaises(RuntimeError):
            airport_dns.patch_js(duplicate, path)


if __name__ == '__main__':
    unittest.main()
