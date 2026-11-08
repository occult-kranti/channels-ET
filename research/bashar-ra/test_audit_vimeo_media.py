"""Synthetic timeline fixtures; no fixture is an acquired source."""
import copy
import unittest
from audit_vimeo_media import packet_summary

class PacketIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.probe={'format':{'duration':'0.064'},'packets':[
            {'pts_time':'0.0','duration_time':'0.0'},
            {'pts_time':'0.021333','duration_time':'0.021333'},
            {'pts_time':'0.042666','duration_time':'0.021333'}]}
    def test_initial_zero_duration_uses_observed_aac_duration(self):
        row=packet_summary(self.probe)
        self.assertEqual(row['gaps_over_tolerance'],[])
        self.assertEqual(row['boundary_anomalies'],[])
    def test_missing_middle_fragment_is_detected(self):
        self.probe['packets'][2]['pts_time']='6.042666';self.probe['format']['duration']='6.064'
        row=packet_summary(self.probe)
        self.assertAlmostEqual(row['max_gap_seconds'],6.0,places=5)
    def test_missing_initial_fragment_is_detected(self):
        self.probe['packets']=self.probe['packets'][2:];self.probe['packets'][0]['pts_time']='1.0';self.probe['format']['duration']='1.021333'
        self.assertEqual(packet_summary(self.probe)['boundary_anomalies'][0]['kind'],'nonzero_initial_pts')
    def test_missing_terminal_fragment_is_detected(self):
        self.probe['format']['duration']='1.0'
        self.assertEqual(packet_summary(self.probe)['boundary_anomalies'][0]['kind'],'terminal_pts_vs_container')
    def test_reordered_audio_packets_are_not_silently_sorted(self):
        self.probe['packets'][2]['pts_time']='0.0'
        with self.assertRaisesRegex(ValueError,'Nonmonotonic'):packet_summary(self.probe)
    def test_empty_packet_list_is_not_complete_audio(self):
        self.probe['packets']=[]
        with self.assertRaisesRegex(ValueError,'No audio packets'):packet_summary(self.probe)
if __name__=='__main__':unittest.main()
