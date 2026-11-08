import unittest
from crawl_publisher_archive import extract, ROOT


class ArchiveLinks(unittest.TestCase):
    def test_short_and_live_are_discovered_without_duration_filter(self):
        _, videos = extract('<a href="https://www.youtube.com/shorts/y5i2MrCorXI">Golden Arc</a><a href="https://www.youtube.com/live/Abcde123_-x">Live</a>', ROOT)
        self.assertEqual(set(videos), {'y5i2MrCorXI', 'Abcde123_-x'})

    def test_video_routes_deduplicate(self):
        _, videos = extract('<a href="https://www.youtube.com/watch?v=Abcde123_-x&amp;t=1">Watch</a><a href="https://youtu.be/Abcde123_-x">Link</a><iframe src="https://www.youtube-nocookie.com/embed/Abcde123_-x"></iframe>', ROOT)
        self.assertEqual(set(videos), {'Abcde123_-x'})
        self.assertIn('Watch', videos['Abcde123_-x'])

    def test_only_explicit_publisher_archive_pagination(self):
        pages, videos = extract('<a href="/video-archive---page-22.html">Next</a><a href="https://other.example/video-archive---page-23.html">Other</a><a href="https://youtu.be/notvalid">Bad ID</a>', ROOT)
        self.assertEqual(pages, {'https://www.magentapixie.com/video-archive---page-22.html'})
        self.assertFalse(videos)


if __name__ == '__main__':
    unittest.main()
