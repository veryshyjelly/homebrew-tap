import unittest
from update import render


class FormulaTest(unittest.TestCase):
    def test_current_release_source_fallback(self):
        formula = render('v1.1.0', {'eitri_1.1.0_source.tar.gz': 'a' * 64})
        self.assertIn('depends_on "go" => :build', formula)
        self.assertIn('/v1.1.0/eitri_1.1.0_source.tar.gz', formula)
        self.assertIn('main.version=#{version}', formula)

    def test_binary_release_selects_four_platforms_without_go(self):
        hashes = {f'eitri_1.2.3_{os}_{arch}.tar.gz': str(i) * 64
                  for i, (os, arch) in enumerate((os, arch) for os in ('darwin', 'linux')
                                                for arch in ('arm64', 'amd64'))}
        formula = render('v1.2.3', hashes)
        for name, digest in hashes.items():
            self.assertIn(name, formula)
            self.assertIn(digest, formula)
        self.assertIn('bin.install "eitri"', formula)
        self.assertNotIn('depends_on "go"', formula)

    def test_partial_binary_release_and_unstable_tag_rejected(self):
        with self.assertRaises(ValueError):
            render('v1.2.3', {'eitri_1.2.3_darwin_arm64.tar.gz': 'a' * 64})
        for tag in ['v1.2.3-rc1', 'v01.2.3', '1.2.3']:
            with self.assertRaises(ValueError):
                render(tag, {})
