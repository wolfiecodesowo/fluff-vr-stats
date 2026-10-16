"""Normie Mode tests. Run from the repo root:  python -m unittest discover -s tests -v"""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import main as core          # noqa: E402
import themes                # noqa: E402
import ui                    # noqa: E402


def _cfg(normie):
    cfg = copy.deepcopy(core.DEFAULT_CFG)
    cfg["style"]["normie"] = normie
    return cfg


def _digest(img):
    return hashlib.sha1(img.tobytes()).hexdigest()


class ThemeTests(unittest.TestCase):
    def test_default_is_off(self):
        self.assertFalse(core.DEFAULT_CFG["style"]["normie"])
        self.assertFalse(themes.normie_on(core.DEFAULT_CFG))

    def test_normie_theme_has_no_decorations(self):
        t = themes.get_theme(_cfg(True))
        self.assertTrue(t["normie"])
        self.assertEqual(t["ears"], "none")
        self.assertFalse(t["show_stripe"])

    def test_off_theme_unchanged(self):
        t = themes.get_theme(_cfg(False))
        self.assertFalse(t.get("normie", False))
        self.assertEqual(t["ears"], "cat")

    def test_key_differs_between_modes(self):
        self.assertNotEqual(themes.theme_key(_cfg(True)), themes.theme_key(_cfg(False)))

    def test_garbage_style_never_raises(self):
        for bad in (None, "x", 5, [], {"normie": "yes"}, {"normie": 1}, {"normie": None}):
            cfg = {"theme": "pride_pastel", "style": bad}
            themes.get_theme(cfg)
            self.assertFalse(themes.normie_on(cfg), bad)

    def test_mascot_visibility(self):
        cfg = _cfg(False)
        self.assertTrue(themes.mascot_on(cfg))
        cfg["style"]["normie"] = True
        self.assertFalse(themes.mascot_on(cfg))
        cfg["style"]["normie"] = False
        cfg["modules"]["wrist_kitty"] = False
        self.assertFalse(themes.mascot_on(cfg))        # her own switch still wins when Normie Mode is off
        self.assertFalse(themes.mascot_on({}))


class ConfigTests(unittest.TestCase):
    def _load(self, data):
        old = core.CFG_PATH
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "config.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write(data if isinstance(data, str) else json.dumps(data))
            core.CFG_PATH = path
            try:
                return core.load_cfg()
            finally:
                core.CFG_PATH = old

    def test_old_config_without_the_key(self):
        cfg = self._load({"style": {"accent": [1, 2, 3], "ears": "fox"}})
        self.assertIs(cfg["style"]["normie"], False)
        self.assertEqual(cfg["style"]["accent"], [1, 2, 3])          # unrelated choices are kept
        self.assertEqual(cfg["style"]["ears"], "fox")

    def test_corrupted_values_fall_back_to_off(self):
        for bad in ("yes", 1, None, [], {}):
            cfg = self._load({"style": {"normie": bad}})
            self.assertIs(cfg["style"]["normie"], False, bad)

    def test_style_not_a_dict(self):
        cfg = self._load({"style": "oops"})
        self.assertIs(cfg["style"]["normie"], False)

    def test_on_survives_load(self):
        cfg = self._load({"style": {"normie": True, "ears": "wolf"}})
        self.assertIs(cfg["style"]["normie"], True)
        self.assertEqual(cfg["style"]["ears"], "wolf")               # still there for when it is switched off

    def test_broken_json_does_not_crash(self):
        cfg = self._load("{not json")
        self.assertIs(cfg["style"]["normie"], False)


class RenderTests(unittest.TestCase):
    def _state(self, normie, tab="Home"):
        cfg = _cfg(normie)
        st = core.State(cfg)
        st.tab = tab
        return st

    def test_every_tab_renders_in_both_modes(self):
        for normie in (False, True):
            for tab in ui.TABS:
                st = self._state(normie, tab)
                img, hit = ui.render_dashboard(st)
                self.assertEqual(img.size, (ui.DASH_W, ui.DASH_H), (normie, tab))

    def test_hud_renders_in_both_modes(self):
        for normie in (False, True):
            img = ui.render_hud(self._state(normie))
            self.assertGreater(img.width, 100)

    def test_normie_hides_mascot_sticker(self):
        base, _ = ui.render_dashboard(self._state(True))
        self.assertEqual(_digest(ui.add_logo(base, 0, [], True)), _digest(base))
        self.assertNotEqual(_digest(ui.add_logo(base, 0, [], False)), _digest(base))   # sticker is pasted when off

    def test_toggling_leaves_no_residue(self):
        """flip 30 times: every render of a mode is byte-identical to the first one of that mode"""
        seen = {}
        for i in range(30):
            normie = bool(i % 2)
            img, _ = ui.render_dashboard(self._state(normie, "Settings"))
            d = _digest(img)
            self.assertEqual(seen.setdefault(normie, d), d, f"mode {normie} changed on flip {i}")
        self.assertNotEqual(seen[True], seen[False])

    def test_settings_page_has_the_toggle_wired_to_style_set(self):
        st = self._state(False, "Settings")
        _, hit = ui.render_dashboard(st)
        acts = list(hit.areas)
        flat = json.dumps(acts, default=str)
        self.assertIn("normie", flat)

    def test_normie_icon_tile(self):
        self.assertEqual(ui.make_normie_tile(64).size, (64, 64))


class RainTests(unittest.TestCase):
    def test_frame_size_and_motion(self):
        import coderain
        a, b = coderain.frame(300, 200, 0), coderain.frame(300, 200, 1.0)
        self.assertEqual(a.size, (300, 200))
        self.assertNotEqual(_digest(a), _digest(b))
        self.assertEqual(_digest(a), _digest(coderain.frame(300, 200, 0)))

    def test_behind_keeps_vr_edges_transparent(self):
        import coderain
        img, _ = ui.render_dashboard(RenderTests()._state(True))
        out = coderain.behind(img, 1.0)
        self.assertEqual(out.size, img.size)
        self.assertEqual(out.getpixel((0, 0))[3], 0)          # outside the card stays see-through in VR


if __name__ == "__main__":
    unittest.main()
