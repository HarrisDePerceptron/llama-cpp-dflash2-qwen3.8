from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

UPSTREAM = "https://github.com/HarrisDePerceptron/llama-cpp-dflash2-qwen3.8"


def _xdg_home(env: str, fallback: str) -> Path:
    return Path(os.environ.get(env) or Path.home() / fallback)


def default_instance_dir() -> Path:
    return _xdg_home("XDG_DATA_HOME", ".local/share") / "localllm"


def state_dir() -> Path:
    return _xdg_home("XDG_STATE_HOME", ".local/state") / "localllm"


@dataclass(frozen=True)
class Instance:
    path: Path
    mode: str  # "dev" | "installed"

    @property
    def run_sh(self) -> Path:
        return self.path / "run.sh"

    @property
    def service_sh(self) -> Path:
        return self.path / "service.sh"

    @property
    def setup_sh(self) -> Path:
        return self.path / "setup.sh"

    @property
    def setup_opencode_sh(self) -> Path:
        return self.path / "setup-opencode.sh"

    @property
    def llama_cpp_dir(self) -> Path:
        return self.path / "llama.cpp"

    @property
    def llama_server_bin(self) -> Path:
        return self.llama_cpp_dir / "build" / "bin" / "llama-server"

    @property
    def built(self) -> bool:
        return self.llama_server_bin.exists()


def _looks_like_instance(p: Path) -> bool:
    return (p / "run.sh").is_file() and (p / "service.sh").is_file()


def ensure_cloned(d: Path) -> None:
    if (d / ".git").is_dir() or _looks_like_instance(d):
        return
    if shutil.which("git") is None:
        raise SystemExit("error: git is required to clone the stack")
    d.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", UPSTREAM, str(d)], check=True)


def resolve_instance(home: str | None = None) -> Instance:
    if home:
        p = Path(home).expanduser().resolve()
        if not _looks_like_instance(p):
            raise SystemExit(
                f"error: {p} does not look like a localllm instance (missing run.sh/service.sh)"
            )
        return Instance(p, "dev")

    env = os.environ.get("LOCALLLM_HOME")
    if env:
        return resolve_instance(env)

    # dev mode: running from a source checkout (editable install)
    src = Path(__file__).resolve().parent.parent
    if _looks_like_instance(src):
        return Instance(src, "dev")

    d = default_instance_dir()
    ensure_cloned(d)
    return Instance(d, "installed")
