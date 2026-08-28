from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


VERSION = "4.3.3"
RELEASE_BASE = f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{VERSION}"


@dataclass(frozen=True)
class Asset:
    name: str
    sha256: str


ASSETS = {
    ("linux", "x86_64"): Asset(
        "tailwindcss-linux-x64",
        "dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a",
    ),
    ("linux", "aarch64"): Asset(
        "tailwindcss-linux-arm64",
        "55fd0b241214eff3de1e8ee4f22796662f2d2e7a49bcfca7477cfd0bac398195",
    ),
    ("darwin", "x86_64"): Asset(
        "tailwindcss-macos-x64",
        "7922e0953f2110c05976e3bf58f14e643d90427575e766b7d433f5f80cbee7e1",
    ),
    ("darwin", "arm64"): Asset(
        "tailwindcss-macos-arm64",
        "cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d",
    ),
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSS = PROJECT_ROOT / "web" / "assets" / "tailwind.css"
OUTPUT_CSS = PROJECT_ROOT / "web" / "static" / "css" / "app.css"


def _cache_home() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".cache"


def _asset() -> Asset:
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "arm64": "arm64"}.get(machine, machine)
    try:
        return ASSETS[(system, machine)]
    except KeyError:
        supported = "Linux/macOS on x86-64 or ARM64"
        raise SystemExit(f"error: Tailwind standalone supports {supported}; got {system}/{machine}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_binary() -> Path:
    asset = _asset()
    binary = _cache_home() / "localllm" / "tailwind" / f"v{VERSION}" / "tailwindcss"
    if binary.is_file() and _sha256(binary) == asset.sha256:
        return binary

    binary.parent.mkdir(parents=True, exist_ok=True)
    print(f"localllm: downloading Tailwind CSS v{VERSION} ({asset.name})")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=binary.parent, delete=False) as target:
            temporary = Path(target.name)
            with urllib.request.urlopen(f"{RELEASE_BASE}/{asset.name}", timeout=120) as source:
                shutil.copyfileobj(source, target)
        actual = _sha256(temporary)
        if actual != asset.sha256:
            raise SystemExit(
                f"error: Tailwind download checksum mismatch: expected {asset.sha256}, got {actual}"
            )
        temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR)
        os.replace(temporary, binary)
    except (OSError, urllib.error.URLError) as error:
        raise SystemExit(f"error: could not download Tailwind CSS v{VERSION}: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return binary


def command(*, watch: bool = False) -> list[str]:
    if not INPUT_CSS.is_file():
        raise SystemExit(
            "error: Tailwind sources are only available in a localllm source checkout"
        )
    OUTPUT_CSS.parent.mkdir(parents=True, exist_ok=True)
    args = [
        str(ensure_binary()),
        "-i",
        str(INPUT_CSS),
        "-o",
        str(OUTPUT_CSS),
        "--minify",
    ]
    if watch:
        args.append("--watch=always")
    return args


def run(*, watch: bool = False) -> int:
    try:
        return subprocess.run(command(watch=watch), cwd=PROJECT_ROOT, check=False).returncode
    except KeyboardInterrupt:
        return 130


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build localllm's Tailwind CSS asset")
    parser.add_argument("action", choices=("build", "watch"))
    args = parser.parse_args(argv)
    return run(watch=args.action == "watch")


if __name__ == "__main__":
    raise SystemExit(main())
