"""Small integration and negative tests for the exported protocol records."""
import copy
import unittest

import verify_protocol


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = verify_protocol.load_inputs()
        cls.cohort = verify_protocol.check_cohorts(cls.data)

    def test_complete_package_records(self):
        result = verify_protocol.verify(self.data)
        self.assertTrue(result["checks_passed"])
        self.assertEqual(result["entity_join"]["model_incidents"], 358)

    def test_entity_subset_requires_all_selected_cases(self):
        changed = dict(self.data)
        changed["entities"] = self.data["entities"][:-1]
        with self.assertRaisesRegex(ValueError, "complete observed repeat-consistent subset"):
            verify_protocol.check_entity_join(changed, self.cohort)

    def test_entity_correctness_must_match_core(self):
        changed = dict(self.data)
        changed["entities"] = copy.deepcopy(self.data["entities"])
        response = changed["entities"][0]["responses"]["P"]
        response["benchmark_correct"] = not response["benchmark_correct"]
        with self.assertRaisesRegex(ValueError, "correctness join mismatch"):
            verify_protocol.check_entity_join(changed, self.cohort)

    def test_modified_message_hash_breaks_protocol_join(self):
        changed = dict(self.data)
        changed["preservation"] = copy.deepcopy(self.data["preservation"])
        changed["preservation"]["scientific_messages"][0]["canonical_scientific_message_hash"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "scientific hash differs"):
            verify_protocol.verify(changed)

    def test_duplicate_case_is_rejected(self):
        changed = dict(self.data)
        changed["cases"] = self.data["cases"] + [self.data["cases"][0]]
        with self.assertRaisesRegex(ValueError, "duplicate keys"):
            verify_protocol.check_cohorts(changed)


if __name__ == "__main__":
    unittest.main()
