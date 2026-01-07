import unittest
from app.utils.sanitization import sanitize_filename


class TestSanitization(unittest.TestCase):
    def test_basic_alphanumeric(self):
        self.assertEqual(sanitize_filename("SongTitle"), "SongTitle")
        self.assertEqual(sanitize_filename("Artist Name"), "Artist Name")

    def test_windows_restricted_chars(self):
        # Testing characters illegal on Windows: < > : " / \ | ? *
        self.assertEqual(
            sanitize_filename("AC/DC: Back in Black"), "AC_DC_ Back in Black"
        )
        self.assertEqual(sanitize_filename('Song "Title"'), "Song _Title_")
        self.assertEqual(sanitize_filename("Star*"), "Star_")
        self.assertEqual(sanitize_filename("Question?"), "Question_")

    def test_paths(self):
        # Should replace path separators
        self.assertEqual(sanitize_filename("folder/file"), "folder_file")
        self.assertEqual(sanitize_filename("folder\\file"), "folder_file")

    def test_reserved_names_windows(self):
        # Windows forbids names ending with . or space
        self.assertEqual(sanitize_filename("file. "), "file")
        self.assertEqual(sanitize_filename("file."), "file")

    def test_empty_input(self):
        self.assertEqual(sanitize_filename(""), "unnamed")
        self.assertEqual(sanitize_filename("   "), "unnamed")
        self.assertEqual(
            sanitize_filename("?"), "_"
        )  # If it becomes empty after strip, ideally handle it. My function returns '_' which strips to empty?
        # Let's verify my implementation logic: "_" -> strip -> "_" ok.
        # "?" -> "_" -> strip -> "_" ok.
        # "   " -> strip -> "" -> "unnamed".

    def test_long_filename(self):
        long_name = "a" * 300
        sanitized = sanitize_filename(long_name)
        self.assertEqual(len(sanitized), 255)


if __name__ == "__main__":
    unittest.main()
