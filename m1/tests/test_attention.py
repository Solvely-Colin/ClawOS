import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "profile-overlay/airootfs/usr/lib/clawos/clawos_attention.py"
spec = importlib.util.spec_from_file_location("attention", path)
attention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(attention)


class AttentionTests(unittest.TestCase):
    def project(self, **changes):
        values = dict(machine=[], approvals=[], tasks=[], interrupted=[], activity={}, seen={})
        values.update(changes)
        return attention.project(**values)

    def test_mixed_sources_match_review_count(self):
        result = self.project(machine=[{}], approvals=[{}], interrupted=[{}],
                              tasks=[{"id": "failed", "status": "failed"}],
                              activity={"attention": {"count": 1}})
        self.assertEqual(result["reviewCount"], 4)
        self.assertEqual(attention.bar(result)["text"], "Review 4")
        self.assertIsNone(result["notice"])

    def test_failure_beyond_recent_ten_is_still_reviewable(self):
        tasks = [{"id": str(i), "status": "completed"} for i in range(12)]
        tasks.append({"id": "old-failure", "status": "failed"})
        result = self.project(tasks=tasks)
        self.assertEqual(len(result["recent"]), 10)
        self.assertEqual(result["failed"][0]["id"], "old-failure")

    def test_reviewed_and_skipped_work_not_attention(self):
        tasks = [{"id": "a", "status": "failed"}, {"id": "b", "status": "failed",
                 "runtime": "cron", "detail": {"status": "skipped"}}]
        self.assertEqual(self.project(tasks=tasks, seen={"taskIds": ["a"]})["reviewCount"], 0)

    def test_notice_acknowledgement_does_not_hide_next_event(self):
        seen = {"noticeIds": ["old"]}
        self.assertEqual(self.project(activity={"attention": {"count": 1, "id": "old"}}, seen=seen)["reviewCount"], 0)
        self.assertEqual(self.project(activity={"attention": {"count": 1, "id": "new"}}, seen=seen)["reviewCount"], 1)

    def test_failed_source_is_not_presented_as_empty(self):
        result = self.project(errors=["Cannot read tasks"])
        self.assertEqual(attention.bar(result)["text"], "Review 1")
        self.assertEqual(result["errors"], ["Cannot read tasks"])

    def test_acknowledge_preserves_other_items_and_is_private(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {"XDG_STATE_HOME": temporary}):
            attention.acknowledge("taskIds", "task")
            attention.acknowledge("noticeIds", "notice")
            seen = attention.read_json(attention.seen_path(), {})
            self.assertEqual(seen["taskIds"], ["task"])
            self.assertEqual(seen["noticeIds"], ["notice"])
            self.assertEqual(attention.seen_path().stat().st_mode & 0o777, 0o600)

    def test_surfaces_share_cached_queries_and_reproject_acknowledgements(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": temporary, "XDG_STATE_HOME": temporary,
        }), patch.object(attention, "query", return_value=[]) as query:
            attention.collect()
            attention.collect()
            self.assertEqual(query.call_count, 4)
            cache = Path(temporary) / "clawos/work-snapshot.json"
            self.assertEqual(cache.stat().st_mode & 0o777, 0o600)

    def test_pending_deployment_is_work_until_result_delivered(self):
        import json
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {
            'XDG_RUNTIME_DIR': temporary, 'XDG_STATE_HOME': temporary,
            'CLAWOS_DEPLOY_RECEIPTS_DIR': temporary,
        }), patch.object(attention, 'query', return_value=[]):
            path = Path(temporary) / 'job.json'
            path.write_text(json.dumps({'targetHash':'bound','state':'verifying','delivery':'pending'}))
            snapshot = attention.collect()
            self.assertTrue(snapshot['active'][0]['deployment'])
            path.write_text(json.dumps({'targetHash':'bound','state':'complete','delivery':'delivered'}))
            self.assertEqual(attention.collect()['active'], [])


if __name__ == "__main__":
    unittest.main()
