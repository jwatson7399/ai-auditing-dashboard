"""Parser tests for the V2 Artificial Analysis lists.

Samples follow the published response shapes at
https://artificialanalysis.ai/data-api/docs/reference
(Pro language model, Free language model, and media Elo). No live key is required.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rebuild


def envelope(models, page, has_more, tier="pro", version=5):
    return {
        "tier": tier,
        "intelligence_index_version": version,
        "pagination": {"page": page, "page_size": 200, "total_pages": 2 if has_more else page, "has_more": has_more},
        "data": models,
    }


PRO_MODEL = {
    "id": "cd684ea4-b475-4269-b001-d469d06d8a7a",
    "name": "GLM-5.3 (Max)",
    "slug": "glm-5-3",
    "evaluations": {
        "artificial_analysis_intelligence_index": 31.7,
        "terminalbench_v2_1": 0.839,
        "scicode": 0.59,
        "tau_banking": 0.503,
        "aa_lcr": 0.797,
        "gdpval_aa_normalized": 0.579,
        "aa_omniscience_accuracy": 0.323,
        "aa_omniscience_non_hallucination_rate": 0.611,
        "gdp_pdf": 0.112,
    },
    "pricing": {
        "price_1m_blended_3_to_1": 2.15,
        "price_1m_input_tokens": 1.4,
        "price_1m_output_tokens": 4.4,
    },
    "performance": {
        "median_output_tokens_per_second": 80.07,
        "median_time_to_first_token_seconds": 2.22,
        "median_time_to_first_answer_token_seconds": 27.19,
    },
}

FREE_MODEL = {
    "id": "free-1",
    "name": "GLM-5.3 (Max)",
    "slug": "glm-5-3",
    "evaluations": {
        "artificial_analysis_intelligence_index": 31.7,
        "artificial_analysis_coding_index": None,
    },
    "pricing": {
        "price_1m_input_tokens": 1.4,
        "price_1m_output_tokens": 4.4,
    },
    "performance": {
        "median_output_tokens_per_second": 80.07,
        "median_time_to_first_token_seconds": 2.22,
        "median_time_to_first_answer_token_seconds": 27.19,
    },
}

FLAT_MODEL = {
    "id": "flat-1",
    "name": "GLM-5.3 (Max)",
    "evaluations": dict(PRO_MODEL["evaluations"], lcr=0.797),
    "pricing": {"price_1m_blended_3_to_1": 2.15, "price_1m_input_tokens": 1.4, "price_1m_output_tokens": 4.4},
    "median_output_tokens_per_second": 80.07,
    "median_time_to_first_answer_token": 27.19,
    "median_time_to_first_token_seconds": 2.22,
}


class Response:
    def __init__(self, payload, text=None):
        self._payload = payload
        self.text = text if text is not None else (payload if isinstance(payload, str) else json.dumps(payload))

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


class FetchRoutingTests(unittest.TestCase):
    def route(self, handler):
        calls = []

        def http_get(url, headers=None, timeout=60, params=None):
            calls.append({"url": url, "headers": headers or {}, "params": params or {}})
            status, payload, text = handler(url, params or {})
            return status, Response(payload, text)

        return calls, http_get

    def assert_no_legacy(self, calls):
        for call in calls:
            self.assertNotIn("/api/v2/data/", call["url"])
            self.assertNotIn("api-key", str(call["params"]))
            self.assertEqual(call["headers"].get("x-api-key"), "fixture")

    def test_pro_pages_match_documented_fields_and_skip_public_metrics(self):
        page2 = {
            "id": "page-2",
            "name": "Claude Fable 5 (high)",
            "evaluations": {
                "artificial_analysis_intelligence_index": 40,
                "terminalbench_v2_1": 0.5,
                "lcr": 0.4,
                "aa_lcr": 0.9,
            },
            "pricing": {"price_1m_blended_3_to_1": 8},
            "performance": {
                "median_output_tokens_per_second": 10,
                "median_time_to_first_token_seconds": 1,
                "median_time_to_first_answer_token_seconds": 9,
            },
        }

        def handler(url, params):
            self.assertEqual(url, rebuild.AA_LLMS_PRO)
            self.assertEqual(params.get("prompt_type"), "medium")
            if params.get("page") == 1:
                return 200, envelope([PRO_MODEL], 1, True), None
            self.assertEqual(params.get("page"), 2)
            return 200, envelope([PRO_MODEL, page2], 2, False), None

        calls, http_get = self.route(handler)
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            bench, eff, meta, raw = rebuild.fetch_aa_llms("fixture")
        self.assert_no_legacy(calls)
        self.assertEqual([c["params"]["page"] for c in calls], [1, 2])
        self.assertEqual(len(raw["data"]), 2)  # repeated Pro id is not stored twice
        self.assertEqual(raw["pagination"]["pages_fetched"], 2)
        self.assertFalse(raw["pagination"]["has_more"])
        self.assertEqual(bench["terminal"]["d"]["GLM-5.3"], 83.9)
        self.assertEqual(bench["terminal"]["settings"]["GLM-5.3"], "Max")
        self.assertEqual(bench["scicode"]["d"]["GLM-5.3"], 59.0)
        self.assertEqual(bench["tau"]["d"]["GLM-5.3"], 50.3)
        self.assertEqual(bench["lcr"]["d"]["GLM-5.3"], 79.7)
        self.assertEqual(bench["lcr"]["d"]["Claude Fable 5"], 40.0)  # lcr wins over aa_lcr
        self.assertEqual(meta["fields"]["lcr"], "lcr")
        self.assertEqual(bench["gdppdf"]["d"]["GLM-5.3"], 11.2)
        self.assertNotIn("gdpval", bench)
        self.assertNotIn("omni", bench)
        self.assertNotIn("nohalluc", bench)
        row = next(r for r in eff if r["model"] == "GLM-5.3")
        self.assertEqual(row["score"], 31.7)
        self.assertEqual(row["price_1m"], 2.15)
        self.assertEqual(row["speed"], 80.07)
        self.assertEqual(row["wait_s"], 27.19)
        self.assertEqual(row["effort"], "Max")
        self.assertEqual(meta["index"], "Artificial Analysis Intelligence Index v5.0")
        self.assertEqual(meta["tier"], "pro")
        self.assertEqual(meta["endpoint"], rebuild.AA_LLMS_PRO)
        self.assertEqual(meta["prompt_type"], "medium")
        self.assertEqual(meta["price_label"], rebuild.PRICE_LABEL)

    def test_flat_retired_shape_parses_to_the_same_scores(self):
        def handler(url, params):
            body = {"data": [FLAT_MODEL]}
            return 200, body, None

        calls, http_get = self.route(handler)
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            bench, eff, meta, _raw = rebuild.fetch_aa_llms("fixture")
        self.assertEqual(len(calls), 1)
        row = eff[0]
        self.assertEqual(row["score"], 31.7)
        self.assertEqual(row["price_1m"], 2.15)
        self.assertEqual(row["speed"], 80.07)
        self.assertEqual(row["wait_s"], 27.19)
        self.assertEqual(bench["terminal"]["d"]["GLM-5.3"], 83.9)
        self.assertEqual(bench["lcr"]["d"]["GLM-5.3"], 79.7)
        self.assertEqual(meta["fields"]["lcr"], "lcr")
        self.assertIn("version not exposed", meta["index"])

    def test_free_fallback_derives_blend_and_omits_pro_benchmarks(self):
        def handler(url, params):
            if url == rebuild.AA_LLMS_PRO:
                self.assertEqual(params.get("prompt_type"), "medium")
                return 403, {"error": "subscription"}, '{"error":"subscription"}'
            self.assertEqual(url, rebuild.AA_LLMS_FREE)
            self.assertNotIn("prompt_type", params)
            self.assertEqual(params.get("page"), 1)
            return 200, envelope([FREE_MODEL], 1, False, tier="free"), None

        calls, http_get = self.route(handler)
        buf = io.StringIO()
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(buf):
            bench, eff, meta, _raw = rebuild.fetch_aa_llms("fixture")
        self.assert_no_legacy(calls)
        self.assertIn("retrying the Free endpoint", buf.getvalue())
        self.assertEqual(meta["tier"], "free")
        self.assertEqual(meta["endpoint"], rebuild.AA_LLMS_FREE)
        self.assertIsNone(meta["prompt_type"])
        self.assertEqual(eff[0]["price_1m"], 2.15)
        self.assertEqual(eff[0]["speed"], 80.07)
        self.assertEqual(eff[0]["wait_s"], 27.19)
        for key in ("terminal", "scicode", "tau", "lcr", "gdppdf"):
            self.assertNotIn(key, bench)

    def test_non_403_does_not_fall_back(self):
        def handler(url, params):
            return 401, {"error": "unauthorized"}, "unauthorized"

        calls, http_get = self.route(handler)
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError) as caught:
                rebuild.fetch_aa_llms("fixture")
        self.assertEqual(len(calls), 1)
        self.assertIn("401", str(caught.exception))
        self.assertIn(rebuild.AA_LLMS_PRO, str(caught.exception))
        self.assertNotIn("/api/v2/data/", str(caught.exception))

    def test_second_page_error_fails_the_fetch(self):
        def handler(url, params):
            if params.get("page") == 1:
                return 200, envelope([PRO_MODEL], 1, True), None
            return 500, {"error": "unavailable"}, "unavailable"

        _calls, http_get = self.route(handler)
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError) as caught:
                rebuild.fetch_aa_llms("fixture")
        self.assertIn("500", str(caught.exception))

    def test_empty_pro_list_is_an_error(self):
        def handler(url, params):
            return 200, envelope([], 1, False), None

        _calls, http_get = self.route(handler)
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                rebuild.fetch_aa_llms("fixture")

    def test_media_elo_and_free_fallback(self):
        image = {"id": "img-1", "name": "GPT Image 2 (high)", "slug": "gpt-image-2", "elo": 1189, "ci_95": 11}
        video = {"id": "vid-1", "name": "Grok Imagine Video 1.5", "slug": "grok-imagine-video", "elo": 1104.4}

        def handler(url, params):
            if url == rebuild.AA_MEDIA_PRO["text-to-image"]:
                self.assertEqual(params.get("include_categories"), "true")
                return 200, {"tier": "pro", "data": [image, image]}, None
            if url == rebuild.AA_MEDIA_PRO["text-to-video"]:
                return 403, {"error": "subscription"}, "subscription"
            if url == rebuild.AA_MEDIA_FREE["text-to-video"]:
                self.assertNotIn("include_categories", params)
                return 200, {"tier": "free", "data": [video]}, None
            raise AssertionError(url)

        calls, http_get = self.route(handler)
        with tempfile.TemporaryDirectory() as folder, patch.object(rebuild, "ROOT", folder), \
                patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            image_scores = rebuild.fetch_aa_media("fixture", "text-to-image")
            video_scores = rebuild.fetch_aa_media("fixture", "text-to-video")
            saved = json.loads(Path(folder, "data", "raw", "aa-media-text-to-image.json").read_text())
        self.assert_no_legacy(calls)
        self.assertEqual(image_scores, {"GPT Image 2 (high)": 1189})
        self.assertEqual(video_scores, {"Grok Imagine Video 1.5": 1104})
        self.assertEqual(len(saved["data"]), 1)
        self.assertEqual(saved["endpoint"], rebuild.AA_MEDIA_PRO["text-to-image"])

    def test_best_effort_on_a_later_page_wins(self):
        low = {
            "id": "low",
            "name": "GLM-5.3 (low)",
            "evaluations": {"artificial_analysis_intelligence_index": 10, "terminalbench_v2_1": 0.1},
            "pricing": {"price_1m_blended_3_to_1": 1},
            "performance": {"median_output_tokens_per_second": 1, "median_time_to_first_answer_token_seconds": 2},
        }

        def handler(url, params):
            if params.get("page") == 1:
                return 200, envelope([low], 1, True), None
            return 200, envelope([PRO_MODEL], 2, False), None

        _calls, http_get = self.route(handler)
        with patch.object(rebuild, "http_get", http_get), contextlib.redirect_stdout(io.StringIO()):
            bench, eff, _meta, _raw = rebuild.fetch_aa_llms("fixture")
        self.assertEqual(bench["terminal"]["d"]["GLM-5.3"], 83.9)
        self.assertEqual(bench["terminal"]["settings"]["GLM-5.3"], "Max")
        self.assertEqual(sorted(r["effort"] for r in eff), ["Max", "low"])


if __name__ == "__main__":
    unittest.main()
