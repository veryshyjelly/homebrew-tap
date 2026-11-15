import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from update_vocabulary_studio import latest_release, parse_checksums, render, update


class VocabularyStudioTest(unittest.TestCase):
    def setUp(self):
        self.archives = {
            f"vocabulary-studio_1.0.0_darwin_{arch}.zip": arch.encode()
            for arch in ("arm64", "amd64")
        }
        self.hashes = {name: hashlib.sha256(data).hexdigest()
                       for name, data in self.archives.items()}
        self.release = {
            "tag_name": "v1.0.0", "draft": False, "prerelease": False,
            "assets": [{"name": name} for name in ["checksums.txt", *self.archives]],
        }

    def download(self, tag, name, directory):
        if name == "checksums.txt":
            (directory / name).write_text("".join(
                f"{digest}  {archive}\n" for archive, digest in self.hashes.items()))
        else:
            (directory / name).write_bytes(self.archives[name])

    def test_cask_uses_both_architectures_and_versioned_url(self):
        cask = render("v1.0.0", self.hashes)
        for digest in self.hashes.values():
            self.assertIn(digest, cask)
        self.assertIn('arch arm: "arm64", intel: "amd64"', cask)
        self.assertIn('/v#{version}/vocabulary-studio_#{version}_darwin_#{arch}.zip', cask)
        self.assertIn('app "Vocabulary Studio.app"', cask)
        self.assertIn('depends_on macos: :ventura', cask)

    def test_unstable_or_unsafe_tags_rejected(self):
        for tag in ("1.0.0", "v1.0.0-rc1", "v01.0.0", 'v1.0.0"', "v1/0/0"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                render(tag, self.hashes)

    def test_missing_architecture_or_invalid_checksum_rejected(self):
        for checksums in ({}, {next(iter(self.hashes)): "a" * 64},
                          dict.fromkeys(self.hashes, "no_check")):
            with self.subTest(checksums=checksums), self.assertRaises(ValueError):
                render("v1.0.0", checksums)

    def test_checksum_manifest_validated_and_normalized(self):
        self.assertEqual(parse_checksums(f"\n{'A' * 64} *app.zip\n"), {"app.zip": "a" * 64})
        for text in ("bad  app.zip", "missing-name", f"{'a' * 64}  a.zip\n{'b' * 64}  a.zip"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_checksums(text)

    def test_both_downloads_verified_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Casks/vocabulary-studio.rb"
            with patch("update_vocabulary_studio.latest_release", return_value=self.release), \
                    patch("update_vocabulary_studio.download", side_effect=self.download):
                update(target)
            self.assertEqual(target.read_text(), render("v1.0.0", self.hashes))

    def test_corrupt_download_preserves_existing_cask(self):
        self.archives[next(iter(self.archives))] = b"corrupted"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "vocabulary-studio.rb"
            target.write_text("previous release")
            with patch("update_vocabulary_studio.latest_release", return_value=self.release), \
                    patch("update_vocabulary_studio.download", side_effect=self.download), \
                    self.assertRaisesRegex(ValueError, "checksum mismatch"):
                update(target)
            self.assertEqual(target.read_text(), "previous release")

    def test_incomplete_or_prerelease_does_not_download(self):
        for change in ({"assets": []}, {"prerelease": True}, {"draft": True}):
            with self.subTest(change=change), \
                    patch("update_vocabulary_studio.latest_release", return_value=self.release | change), \
                    patch("update_vocabulary_studio.download") as download, \
                    self.assertRaises(ValueError):
                update()
            download.assert_not_called()

    def test_no_release_skips_without_creating_cask(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "vocabulary-studio.rb"
            with patch("update_vocabulary_studio.latest_release", return_value=None):
                update(target)
            self.assertFalse(target.exists())

    def test_only_not_found_is_skipped(self):
        with patch("update_vocabulary_studio.subprocess.run", side_effect=
                   subprocess.CalledProcessError(1, "gh", stderr="gh: Not Found (HTTP 404)")):
            self.assertIsNone(latest_release())
        for status in (401, 403, 500):
            with self.subTest(status=status), \
                    patch("update_vocabulary_studio.subprocess.run", side_effect=
                          subprocess.CalledProcessError(1, "gh", stderr=f"(HTTP {status})")), \
                    self.assertRaises(subprocess.CalledProcessError):
                latest_release()


if __name__ == "__main__":
    unittest.main()
