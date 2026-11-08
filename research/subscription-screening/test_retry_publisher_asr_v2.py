"""Run the unchanged fallback contract against the second exact held source."""
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

F = load('fallback_second_source', ROOT / 'retry_publisher_asr_v2.py')
shared = load('fallback_second_source_contract', ROOT / 'test_retry_publisher_asr.py')
shared.F = F
original_fixture = shared.held_fixture

def second_fixture(root, source):
    ledger, hold, old = original_fixture(root, source)
    hold['reason_code'] = 'multiple_segments_outside_audio'
    return ledger, hold, old

shared.held_fixture = second_fixture

class SecondFallbackTests(shared.FallbackTests):
    def test_only_source_and_reason_change_from_frozen_predecessor(self):
        previous = (ROOT / 'retry_publisher_asr.py').read_bytes()
        self.assertEqual(hashlib.sha256(previous).hexdigest(),
                         '1db7a61b40155b4df06d020889d8e6004982d51c85bfbdc2671f7e8e87501b1d')
        expected = previous.decode().replace(
            "SOURCE_ID='publisher-rss:akanksshaa:rss:f35e0cfac4d68e2c'",
            "SOURCE_ID='publisher-rss:akanksshaa:rss:b9fd4b8c29ce9611'"
        ).replace("h['reason_code']!='repeated_output_with_timestamp_overflow'",
                  "h['reason_code']!='multiple_segments_outside_audio'")
        self.assertEqual((ROOT / 'retry_publisher_asr_v2.py').read_text(), expected)
        self.assertEqual(F.SOURCE_ID, 'publisher-rss:akanksshaa:rss:b9fd4b8c29ce9611')

if __name__ == '__main__':
    unittest.main()
