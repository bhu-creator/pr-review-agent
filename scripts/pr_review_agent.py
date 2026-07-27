"""
pr_review_agent.py — Entry point and orchestrator.
This file only coordinates the other modules — no API calls, no AI, no formatting.
"""

import sys

from config          import load_config
from ado_client      import AdoClient
from gemini_client   import GeminiReviewer
from comment_builder import build_pr_comment


def run() -> None:
    # ── 1. Load configuration ─────────────────────────────────────────────────
    cfg = load_config()
    print(f"=== AI PR Review Agent ===")
    print(f"PR #{cfg.pr_id} | Repo: {cfg.ado_repo} | Project: {cfg.ado_project}")

    # ── 2. Connect to Azure DevOps ────────────────────────────────────────────
    ado = AdoClient(
        org_url=cfg.ado_org_url,
        project=cfg.ado_project,
        repo=cfg.ado_repo,
        pr_id=cfg.pr_id,
        access_token=cfg.access_token,
    )

    # ── 3. Fetch PR metadata and changed files ────────────────────────────────
    pr_details    = ado.get_pr_details()
    changed_files = ado.get_changed_files(cfg.skip_extensions)
    print(f"PR: {pr_details.get('title')}")
    print(f"Changed files to review: {len(changed_files)}")

    if not changed_files:
        ado.post_review_thread("## 🤖 AI PR Review\nNo reviewable code files found. Skipping.")
        return

    # ── 4. Review each file with Gemini ──────────────────────────────────────
    reviewer  = GeminiReviewer(cfg.gemini_api_key, cfg.max_file_chars)
    commit_id = pr_details["lastMergeSourceCommit"]["commitId"]
    file_reviews: list[tuple[str, str]] = []

    for i, file in enumerate(changed_files, 1):
        path    = file["path"]
        print(f"[{i}/{len(changed_files)}] Reviewing: {path}")
        content = ado.get_file_content(path, commit_id)
        if content.strip():
            review = reviewer.review_file(path, content)
            file_reviews.append((path, review))

    # ── 5. Post review comment on the PR ─────────────────────────────────────
    if file_reviews:
        comment = build_pr_comment(pr_details, file_reviews)
        ado.post_review_thread(comment)
        print("✅ Review posted on PR successfully!")
    else:
        print("All files were empty or unreadable. Nothing posted.")


if __name__ == "__main__":
    try:
        run()
    except EnvironmentError as exc:
        # Missing env vars — show a clean message, not a raw traceback
        print(f"\n❌ Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        # Any other failure — print and exit with failure code so pipeline marks step red
        print(f"\n❌ Unexpected error: {exc!r}", file=sys.stderr)
        sys.exit(1)
