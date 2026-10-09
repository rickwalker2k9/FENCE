import json
import os
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from faith import EstimateError, estimate
from faith.server import Handler


def qty(r, key):
    return sum(m["qty"] for m in r["materials"] if m["key"] == key)


class DemoJob(unittest.TestCase):
    """The Master-Halco demo: 180 ft of 6 ft board-on-board with a 4 ft walk gate."""

    def setUp(self):
        self.r = estimate({"total_feet": 180, "height_ft": 6, "style": "board_on_board", "gates": [{"width_ft": 4}], "location": "OKC"})

    def test_layout(self):
        lay = self.r["layout"]
        self.assertEqual(lay["fence_ft"], 176)
        self.assertEqual(lay["bays"], 22)
        self.assertEqual(lay["on_center_ft"], [8.0])
        self.assertEqual(lay["posts"], {"line": 20, "end": 2, "corner": 0, "gate": 2, "total": 24})

    def test_materials(self):
        self.assertEqual(qty(self.r, "wood_post_4x4x8"), 22)
        self.assertEqual(qty(self.r, "wood_post_4x4x10"), 2)
        self.assertEqual(qty(self.r, "rail_2x4x8"), 73 + 3)  # 66 + 10% waste, plus the gate frame
        self.assertEqual(qty(self.r, "picket_6ft"), 535)  # 180 ft x 2.7 x 1.10
        self.assertEqual(qty(self.r, "wood_walk_gate_kit"), 1)
        self.assertEqual(self.r["concrete"]["bags"], 52)

    def test_spoken_uses_digits_and_okie811(self):
        self.assertIn("535 pickets", self.r["spoken"])
        self.assertLessEqual(len(self.r["spoken"].split()), 60)
        self.assertTrue(any("OKIE811" in q for q in self.r["questions"]))


class Spacing(unittest.TestCase):
    def test_symmetric_on_center(self):
        r = estimate({"total_feet": 180})
        self.assertEqual(r["layout"]["bays"], 23)
        self.assertEqual(r["layout"]["on_center_ft"], [7.83])
        self.assertEqual(r["layout"]["posts"]["total"], 24)  # bays + 1

    def test_exact_multiple_does_not_add_a_bay(self):
        self.assertEqual(estimate({"total_feet": 80})["layout"]["bays"], 10)

    def test_corners_share_posts(self):
        r = estimate({"runs": [40, 40, 40]})
        self.assertEqual(r["layout"]["posts"], {"line": 12, "end": 2, "corner": 2, "gate": 0, "total": 16})

    def test_gate_flush_at_run_start_reuses_end_post(self):
        r = estimate({"runs": [44], "gates": [{"width_ft": 4, "at_ft": 0}]})
        self.assertEqual(r["layout"]["posts"], {"line": 4, "end": 1, "corner": 0, "gate": 2, "total": 7})


class Wood(unittest.TestCase):
    def test_side_by_side_rate(self):
        r = estimate({"total_feet": 100, "style": "side_by_side", "waste_pct": 0})
        self.assertEqual(qty(r, "picket_6ft"), 219)  # 100 x 12 / 5.5 = 218.2

    def test_stepped_slope_lengthens_posts_and_waste(self):
        r = estimate({"total_feet": 120, "terrain": "stepped", "grade_pct": 15})
        self.assertEqual(qty(r, "wood_post_4x4x10"), 16)  # 6 + 2 + 1.2 ft step
        self.assertEqual(r["waste_pct"], 15)

    def test_stepped_needs_grade(self):
        with self.assertRaises(EstimateError):
            estimate({"total_feet": 120, "terrain": "stepped"})


class ChainLink(unittest.TestCase):
    def test_hardware(self):
        r = estimate({"fence_type": "chain_link", "height_ft": 6, "runs": [100, 100]})
        posts = r["layout"]["posts"]
        self.assertEqual(posts, {"line": 18, "end": 2, "corner": 1, "gate": 0, "total": 21})
        self.assertEqual(qty(r, "cl_tension_bar"), 4)  # 2 ends + corner counts twice
        self.assertEqual(qty(r, "cl_tension_band"), 20)  # 5 bands each at 6 ft
        self.assertEqual(qty(r, "cl_fabric_roll"), 5)  # 200 ft + 10% = 220 ft
        self.assertEqual(qty(r, "cl_top_rail"), 10)

    def test_wide_gate_is_double(self):
        r = estimate({"fence_type": "chain_link", "total_feet": 100, "gates": [12]})
        self.assertEqual(qty(r, "cl_double_gate"), 1)
        self.assertEqual(qty(r, "cl_gate_hinge"), 4)


class Server(unittest.TestCase):
    def setUp(self):
        os.environ["FAITH_ASSISTANT_KEY"] = "test-key"
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/tools/fence_estimate"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    def post(self, body, key="test-key"):
        req = urllib.request.Request(self.url, json.dumps(body).encode(), {"x-faith-key": key, "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_estimate(self):
        status, body = self.post({"total_feet": 180, "gates": [4]})
        self.assertEqual(status, 200)
        self.assertIn("spoken", body)

    def test_missing_info_is_a_question(self):
        status, body = self.post({})
        self.assertEqual(status, 200)
        self.assertIn("How many total feet", body["spoken"])

    def test_rejects_wrong_key(self):
        self.assertEqual(self.post({"total_feet": 10}, key="nope")[0], 401)


if __name__ == "__main__":
    unittest.main()
