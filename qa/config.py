"""Configuration and identity registry.

Credentials live in .env, which is gitignored, and never anywhere else. The
repo is public: assume the vendor reads every line of it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader. No dependency, no surprises, no shell expansion."""
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Identity:
    """A way of presenting ourselves to the platform.

    `scope` is enforced by the transport: a trade-scoped credential is refused
    on any test that is not MUTATE tier. Today no trade-scoped key exists, and
    that is the intended steady state.
    """

    name: str
    header: str | None = None
    value: str | None = None
    scope: str = "read"
    expected_trust: str = "unknown"

    @property
    def present(self) -> bool:
        return self.header is None or bool(self.value)

    def headers(self) -> dict[str, str]:
        if self.header and self.value:
            return {self.header: self.value}
        return {}


def identities() -> dict[str, Identity]:
    """The identity ladder.

    Testing whether the trust ladder gates anything requires calling the same
    endpoint as more than one identity and diffing the answers. A single
    credential cannot prove a gate exists -- it can only show what one tier
    happens to receive.
    """
    load_dotenv()
    return {
        "anon": Identity(name="anon", expected_trust="unknown"),
        "trusted": Identity(
            name="trusted",
            header="X-API-Key",
            value=os.environ.get("QA_TRUSTED_KEY") or None,
            scope="read",
            expected_trust="trusted",
        ),
        "recognized": Identity(
            name="recognized",
            header="X-API-Key",
            value=os.environ.get("QA_RECOGNIZED_KEY") or None,
            scope="read",
            expected_trust="recognized",
        ),
    }


def base_urls() -> dict[str, str]:
    import yaml
    with open(REPO_ROOT / "components.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)["base_urls"]


DEFAULT_TIMEOUT = float(os.environ.get("QA_TIMEOUT_SECONDS", "30"))
USER_AGENT = os.environ.get(
    "QA_USER_AGENT",
    "qa-cymetica/0.1 (independent QA; contact via vendor Telegram channel)",
)
