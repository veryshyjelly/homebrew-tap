class Craftcoders < Formula
  desc "Local CLI for CodeCrafters challenges"
  homepage "https://github.com/veryshyjelly/craftcoders-cli"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/veryshyjelly/craftcoders-cli/releases/download/v0.1.0/craftcoders_0.1.0_darwin_arm64.tar.gz"
      sha256 "84bc5d3062e32d55d259a4839aac683a5510327dd231ce2dc16e4fdcc93cebd1"
    end

    on_intel do
      url "https://github.com/veryshyjelly/craftcoders-cli/releases/download/v0.1.0/craftcoders_0.1.0_darwin_amd64.tar.gz"
      sha256 "c34ab7109242bd9300af04ef93eb27980ac8871a48413481fbfd2e2b77d7b8c1"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/veryshyjelly/craftcoders-cli/releases/download/v0.1.0/craftcoders_0.1.0_linux_arm64.tar.gz"
      sha256 "e5184d6f785615ac3aa88e08d4623e156e7f9860d2ee22342764325572bda99f"
    end

    on_intel do
      url "https://github.com/veryshyjelly/craftcoders-cli/releases/download/v0.1.0/craftcoders_0.1.0_linux_amd64.tar.gz"
      sha256 "c9bf55c12359255f53ab7d4cf3796856f1addd9ebc9cc607fedf03494fe70285"
    end
  end

  def install
    bin.install "craftcoders"
  end

  test do
    assert_equal "craftcoders #{version}\n", shell_output("#{bin}/craftcoders --version")
  end
end
