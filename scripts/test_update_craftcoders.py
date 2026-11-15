import hashlib
import io
import stat
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import update_craftcoders as updater


class CraftcodersTest(unittest.TestCase):
    def setUp(self):
        self.archives = {name: name.encode() for name in updater.archive_names("v1.2.3")}
        self.hashes = {name: hashlib.sha256(data).hexdigest() for name, data in self.archives.items()}
        self.manifest = "".join(f"{digest}  {name}\n" for name, digest in self.hashes.items())
        self.release = {"tag_name": "v1.2.3", "draft": False, "prerelease": False,
                        "assets": [{"name": name} for name in ["checksums.txt", *self.archives]]}

    def download(self, tag, name, directory):
        self.assertEqual(tag, "v1.2.3")
        (directory / name).write_bytes(self.manifest.encode() if name == "checksums.txt" else self.archives[name])

    def attempt(self, target, **kwargs):
        with patch.object(updater, "latest_release", return_value=kwargs.get("release", self.release)), \
                patch.object(updater, "download", side_effect=kwargs.get("download", self.download)):
            updater.update(target)

    def preserve(self, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "craftcoders.rb"
            target.write_bytes(b"previous formula\n")
            with self.assertRaises((ValueError, OSError, subprocess.CalledProcessError)):
                self.attempt(target, **kwargs)
            self.assertEqual(target.read_bytes(), b"previous formula\n")
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_all_platform_urls_digests_and_install_contract(self):
        formula = updater.render("v1.2.3", self.hashes)
        for name, digest in self.hashes.items():
            self.assertIn(f'https://github.com/{updater.REPO}/releases/download/v1.2.3/{name}', formula)
            self.assertIn(digest, formula)
        for text in ('class Craftcoders < Formula', 'on_macos do', 'on_linux do', 'on_arm do', 'on_intel do',
                     'license "MIT"', 'bin.install "craftcoders"',
                     'assert_equal "craftcoders #{version}\\n", shell_output("#{bin}/craftcoders --version")'):
            self.assertIn(text, formula)
        self.assertNotIn("depends_on", formula)
        self.assertNotRegex(formula, r'(?m)^\s*version "')


    def test_unstable_unsafe_tags_preserve_formula(self):
        for tag in ("1.2.3", "v01.2.3", "v1.02.3", "v1.2.03", "v1.2.3-rc1", "v1.2.3+meta", "v1/2/3", "v1.2.3\n", None):
            with self.subTest(tag=tag):
                self.preserve(release=self.release | {"tag_name": tag})

    def test_drafts_prereleases_missing_duplicate_assets_preserve_formula(self):
        changes = [{"draft": True}, {"prerelease": True}]
        for name in ["checksums.txt", *self.archives]:
            changes += [{"assets": [a for a in self.release["assets"] if a["name"] != name]},
                        {"assets": self.release["assets"] + [{"name": name}]}]
        for change in changes:
            with self.subTest(change=change):
                self.preserve(release=self.release | change)

    def test_manifest_normalizes_case_binary_marker_and_blanks(self):
        manifest = "\n" + "\n".join(f"{digest.upper()} *{name}" for name, digest in self.hashes.items()) + "\n\n"
        self.assertEqual(updater.parse_checksums(manifest), self.hashes)

    def test_invalid_manifests_preserve_formula(self):
        first = next(iter(self.hashes))
        digest = self.hashes[first]
        invalid = ["", "missing-name", self.manifest.replace(digest, "a" * 63),
                   self.manifest.replace(digest, "g" * 64), self.manifest + f"{digest}  {first}\n"]
        for name in ("../" + first, "folder/" + first, "folder\\" + first, "unexpected.tar.gz", ".", ".."):
            invalid.append(self.manifest.replace(first, name))
        invalid += ["\n".join(self.manifest.splitlines()[1:]), self.manifest.replace("1.2.3_darwin", "2.0.0_darwin")]
        for manifest in invalid:
            with self.subTest(manifest=manifest):
                self.manifest = manifest
                self.preserve()
        # All checks fail before atomic replacement regardless of malformed format.

    def test_render_rejects_missing_extra_and_bad_digests(self):
        for hashes in ({}, self.hashes | {"extra": "a" * 64}, dict.fromkeys(self.hashes, "bad")):
            with self.subTest(hashes=hashes), self.assertRaises(ValueError):
                updater.render("v1.2.3", hashes)

    def test_each_corrupt_archive_preserves_formula(self):
        for name in self.archives:
            original = self.archives[name]
            self.archives[name] = b"corruption"
            with self.subTest(name=name):
                self.preserve()
            self.archives[name] = original

    def test_each_download_failure_preserves_formula(self):
        for failed in ["checksums.txt", *self.archives]:
            def fail(tag, name, directory):
                if name == failed:
                    raise OSError("download failed")
                self.download(tag, name, directory)
            with self.subTest(name=failed):
                self.preserve(download=fail)

    def test_all_verified_before_atomic_replace_and_identical_no_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Formula/craftcoders.rb"
            self.attempt(target, release=self.release | {"assets": self.release["assets"] + [{"name": "unrelated"}]})
            self.assertEqual(target.read_text(), updater.render("v1.2.3", self.hashes))
            before = target.stat().st_mtime_ns
            with patch.object(updater.os, "replace", side_effect=AssertionError("identical rewrite")):
                self.attempt(target)
            self.assertEqual(target.stat().st_mtime_ns, before)

    def test_new_and_replacement_formula_are_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "craftcoders.rb"
            self.attempt(target)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
            target.write_text("previous formula")
            target.chmod(0o600)
            self.attempt(target)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
            self.assertEqual(target.read_text(), updater.render("v1.2.3", self.hashes))

    def test_identical_formula_with_restricted_permissions_is_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "craftcoders.rb"
            formula = updater.render("v1.2.3", self.hashes)
            target.write_text(formula)
            target.chmod(0o600)
            self.attempt(target)
            self.assertEqual(target.read_text(), formula)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)

    def test_identical_formula_chmod_failure_preserves_bytes_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "craftcoders.rb"
            formula = updater.render("v1.2.3", self.hashes)
            target.write_text(formula)
            target.chmod(0o600)
            with patch.object(updater.Path, "chmod", side_effect=OSError("chmod failed")), self.assertRaises(OSError):
                self.attempt(target)
            self.assertEqual(target.read_text(), formula)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(list(Path(directory).iterdir()), [target])

    def test_chmod_failure_preserves_formula_and_cleans_temporary(self):
        with patch.object(updater.Path, "chmod", side_effect=OSError("chmod failed")):
            self.preserve()

    def test_atomic_replace_failure_preserves_formula_and_cleans_temporary(self):
        with patch.object(updater.os, "replace", side_effect=OSError("replace failed")):
            self.preserve()

    def test_atomic_write_failure_preserves_formula_and_cleans_temporary(self):
        real = tempfile.NamedTemporaryFile
        def failing_file(*args, **kwargs):
            output = real(*args, **kwargs)
            output.write = lambda text: (_ for _ in ()).throw(OSError("write failed"))
            return output
        with patch.object(updater.tempfile, "NamedTemporaryFile", side_effect=failing_file):
            self.preserve()

    def test_first_release_absent_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "Formula/craftcoders.rb"
            self.attempt(target, release=None)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_only_exact_404_skips(self):
        for stderr in ("gh: Not Found (HTTP 404)", "(HTTP 401)", "(HTTP 403)", "(HTTP 500)", "HTTP 404", "(HTTP 4040)", "(HTTP 404) (HTTP 500)", None):
            with self.subTest(stderr=stderr), patch.object(updater.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "gh", stderr=stderr)):
                if stderr == "gh: Not Found (HTTP 404)":
                    self.assertIsNone(updater.latest_release())
                else:
                    with self.assertRaises(subprocess.CalledProcessError):
                        updater.latest_release()

    def test_api_failures_preserve_existing_formula(self):
        for status in (401, 403, 500):
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "craftcoders.rb"
                target.write_text("previous formula")
                with patch.object(updater.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "gh", stderr=f"(HTTP {status})")), self.assertRaises(subprocess.CalledProcessError):
                    updater.update(target)
                self.assertEqual(target.read_text(), "previous formula")

    def test_invalid_assets_do_not_download(self):
        with patch.object(updater, "latest_release", return_value=self.release | {"assets": []}), patch.object(updater, "download") as download, self.assertRaises(ValueError):
            updater.update()
        download.assert_not_called()

    def test_latest_json_and_fixed_endpoint(self):
        with patch.object(updater.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(self.release))) as run:
            self.assertEqual(updater.latest_release(), self.release)
        self.assertEqual(run.call_args.args[0], ["gh", "api", "repos/veryshyjelly/craftcoders-cli/releases/latest"])

    def test_download_constructs_only_trusted_urls_and_never_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ["checksums.txt", *self.archives]:
                with patch.object(updater.urllib.request, "urlopen", return_value=io.BytesIO(b"archive")) as request:
                    updater.download("v1.2.3", name, directory)
                self.assertEqual(request.call_args.args[0], f"https://github.com/{updater.REPO}/releases/download/v1.2.3/{name}")
                self.assertEqual((Path(directory) / name).read_bytes(), b"archive")
            for tag, name in (("v1.2.3", "../../bad"), ("v1.2.3-rc1", "checksums.txt")):
                with self.assertRaises(ValueError):
                    updater.download(tag, name, directory)


if __name__ == "__main__":
    unittest.main()
