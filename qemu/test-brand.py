#!/usr/bin/env python3
"""Exercise brand switching and persistence without vendor files or a VM."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).parent / "overrides/opt/ccnc-qemu/brand-state.py"
spec = importlib.util.spec_from_file_location("brand_state", SOURCE)
brand_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brand_state)


class BrandStateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = self.root / "etc/sw_feature/sw_feature.json"
        self.marker = self.root / "esp/variant_version"
        self.profile = {"SW.CAR_BRAND": {"candidate": ["HYUNDAI", "KIA"], "elected": "HYUNDAI"},
                        "SW.OTHER_FEATURE": {"elected": "ON"}}
        brand_state.write_json(self.config, self.profile)
        self.marker.parent.mkdir(parents=True)
        self.marker.write_text("existing vendor cache")

    def test_switch_both_directions_preserves_other_features(self):
        for brand, value in [("kia", "KIA"), ("hyundai", "HYUNDAI")]:
            with self.subTest(brand=brand):
                self.marker.write_text("previous brand cache")
                self.assertEqual(brand_state.apply_brand(self.root, brand), value)
                expected = json.loads(json.dumps(self.profile))
                expected["SW.CAR_BRAND"]["elected"] = value
                self.assertEqual(json.loads(self.config.read_text()), expected)
                self.assertFalse(self.marker.exists())

    def test_saved_brand_restores_after_payload_replaces_config(self):
        brand_state.apply_brand(self.root, "kia")
        brand_state.write_json(self.config, self.profile)
        self.marker.write_text("stale cache")
        self.assertEqual(brand_state.apply_brand(self.root), "KIA")
        self.assertEqual(json.loads(self.config.read_text())["SW.CAR_BRAND"]["elected"], "KIA")
        self.assertFalse(self.marker.exists())
        self.marker.write_text("current Kia cache")
        brand_state.apply_brand(self.root)
        self.assertEqual(self.marker.read_text(), "current Kia cache")

    def test_no_selection_keeps_firmware_and_cache(self):
        before = self.config.read_bytes()
        self.assertIsNone(brand_state.apply_brand(self.root))
        self.assertEqual(self.config.read_bytes(), before)
        self.assertTrue(self.marker.exists())
        self.assertFalse((self.root / "ccos/data/ccnc-qemu/brand.json").exists())

    def test_invalid_selection_does_not_write(self):
        before = self.config.read_bytes()
        with self.assertRaises(ValueError):
            brand_state.apply_brand(self.root, "../kia")
        self.assertEqual(self.config.read_bytes(), before)
        self.assertTrue(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
