"""Generate CraftCoders formula only after verifying all stable release archives."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import urllib.request

REPO = "veryshyjelly/craftcoders-cli"
STABLE_TAG = r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
ARCHIVE = r"craftcoders_((?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))_(darwin|linux)_(arm64|amd64)\.tar\.gz"


def archive_names(tag):
    if not isinstance(tag, str) or not re.fullmatch(STABLE_TAG, tag):
        raise ValueError("expected a stable vX.Y.Z release tag")
    return [f"craftcoders_{tag[1:]}_{system}_{arch}.tar.gz"
            for system in ("darwin", "linux") for arch in ("arm64", "amd64")]


def parse_checksums(text):
    checksums = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([a-fA-F0-9]{64})[ \t]+\*?(\S+)", line)
        if not match:
            raise ValueError("invalid checksum line")
        digest, name = match.groups()
        if not re.fullmatch(ARCHIVE, name) or name in checksums:
            raise ValueError("unexpected or duplicate archive checksum")
        checksums[name] = digest.lower()
    if not checksums:
        raise ValueError("missing archive checksums")
    version = re.fullmatch(ARCHIVE, next(iter(checksums))).group(1)
    if set(checksums) != set(archive_names("v" + version)):
        raise ValueError("missing or unexpected archive checksums")
    return checksums


def render(tag, checksums):
    names = archive_names(tag)
    if set(checksums) != set(names) or any(
            not re.fullmatch(r"[a-f0-9]{64}", checksums[name]) for name in names):
        raise ValueError("missing, unexpected or invalid archive checksums")
    platforms = []
    for system, block in (("darwin", "on_macos"), ("linux", "on_linux")):
        branches = []
        for arch, condition in (("arm64", "on_arm"), ("amd64", "on_intel")):
            name = f"craftcoders_{tag[1:]}_{system}_{arch}.tar.gz"
            branches.append(f'''    {condition} do
      url "https://github.com/{REPO}/releases/download/{tag}/{name}"
      sha256 "{checksums[name]}"
    end''')
        platforms.append(f"  {block} do\n" + "\n\n".join(branches) + "\n  end")
    return f'''class Craftcoders < Formula
  desc "Local CLI for CodeCrafters challenges"
  homepage "https://github.com/{REPO}"
  license "MIT"

{(chr(10) * 2).join(platforms)}

  def install
    bin.install "craftcoders"
  end

  test do
    assert_equal "craftcoders #{{version}}\\n", shell_output("#{{bin}}/craftcoders --version")
  end
end
'''


def latest_release():
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{REPO}/releases/latest"],
            check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        statuses = re.findall(r"\(HTTP ([0-9]{3})\)", error.stderr or "")
        if statuses == ["404"]:
            print("No published CraftCoders release yet; skipping formula update.")
            return None
        raise
    return json.loads(result.stdout)


def download(tag, name, directory):
    allowed = {"checksums.txt", *archive_names(tag)}
    if name not in allowed:
        raise ValueError("unexpected release asset")
    url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    # Only trusted fixed-repository URLs are constructed; contents are never executed.
    with urllib.request.urlopen(url) as response, (Path(directory) / name).open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def update(target=None):
    release = latest_release()
    if release is None:
        return
    if release["draft"] or release["prerelease"]:
        raise ValueError("expected a published stable release")
    tag = release["tag_name"]
    names = archive_names(tag)
    assets = [asset["name"] for asset in release["assets"]]
    if any(assets.count(name) != 1 for name in ["checksums.txt", *names]):
        raise ValueError("release has missing or duplicate required assets")
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        download(tag, "checksums.txt", directory)
        checksums = parse_checksums((directory / "checksums.txt").read_text())
        formula = render(tag, checksums)
        for name in names:
            download(tag, name, directory)
            with (directory / name).open("rb") as archive:
                actual = hashlib.file_digest(archive, "sha256").hexdigest()
            if actual != checksums[name]:
                raise ValueError("checksum mismatch: " + name)
    target = Path(target) if target is not None else Path(__file__).resolve().parent.parent / "Formula/craftcoders.rb"
    if (target.exists() and target.read_text() == formula
            and stat.S_IMODE(target.stat().st_mode) == 0o644):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=".craftcoders-", delete=False) as output:
            temporary = Path(output.name)
            output.write(formula)
            output.flush()
        temporary.chmod(0o644)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("Updated CraftCoders formula to", tag)


if __name__ == "__main__":
    update()
