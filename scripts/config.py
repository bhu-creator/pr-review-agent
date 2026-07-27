"""
config.py — Load and expose all configuration from environment variables.
The .env file is loaded automatically when running locally.
"""

import os
from dataclasses import dataclass, field


# ── .env loader (local dev only) ─────────────────────────────────────────────

def _load_dotenv() -> None:
    """Read a .env file two levels above this script and set env vars.
    Variables already set (e.g. in CI) are never overwritten."""
    env_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", ".env")
    )
    if not os.path.isfile(env_path):
        return

    print(f"[local] Loading .env from: {env_path}")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass
class Config:
    """All settings needed to run the PR review agent."""
    ado_org_url:    str
    ado_project:    str
    ado_repo:       str
    pr_id:          str
    access_token:   str
    gemini_api_key: str
    max_file_chars: int = field(default=28_000)

    # File extensions the agent will skip (config / assets / docs)
    skip_extensions: frozenset = field(default_factory=lambda: frozenset({
        ".json", ".xml", ".csproj", ".sln", ".md", ".txt",
        ".png", ".jpg", ".svg", ".ico", ".lock", ".yaml", ".yml",
    }))


def load_config() -> Config:
    """Load config from environment. Call once at startup."""
    _load_dotenv()
    required = {
        "ADO_ORG_URL":        "Azure DevOps org URL (e.g. https://dev.azure.com/myorg)",
        "ADO_PROJECT":        "Azure DevOps project name",
        "ADO_REPO_NAME":      "Repository name",
        "ADO_PR_ID":          "Pull Request ID (set automatically by Azure Pipelines)",
        "SYSTEM_ACCESSTOKEN": "Azure DevOps PAT or System.AccessToken",
    }
    missing = [f"  {key}  ({desc})" for key, desc in required.items() if not os.environ.get(key)]
    if missing:
        raise EnvironmentError(
            "Missing required environment variables:\n" + "\n".join(missing)
            + "\n\nSee .env.example for reference."
        )
    return Config(
        ado_org_url=os.environ["ADO_ORG_URL"].rstrip("/"),
        ado_project=os.environ["ADO_PROJECT"],
        ado_repo=os.environ["ADO_REPO_NAME"],
        pr_id=os.environ["ADO_PR_ID"],
        access_token=os.environ["SYSTEM_ACCESSTOKEN"],
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
