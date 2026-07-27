"""
webhook_server.py — FastAPI webhook receiver for Azure DevOps Service Hooks.

Azure DevOps sends a POST request to this server whenever a PR is
created or updated (org-level, covers ALL projects/repos automatically).
The server extracts PR details from the payload and triggers the AI review.

Deploy this to any host with a public URL:
  - Azure App Service  (recommended — same ecosystem)
  - Azure Container App
  - Any Linux VM / Docker host
"""

import hmac
import hashlib
import os

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from config          import load_config
from ado_client      import AdoClient
from gemini_client   import GeminiReviewer
from comment_builder import build_pr_comment


app = FastAPI(title="AI PR Review Webhook", version="1.0.0")

# Optional: shared secret configured in the ADO service hook settings
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Azure App Service / load balancer health probe."""
    return {"status": "ok", "service": "AI PR Review Agent"}


# ── Main webhook endpoint ─────────────────────────────────────────────────────

@app.post("/webhook/pr-review")
async def pr_review_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives Azure DevOps service hook events.
    Accepts: git.pullrequest.created | git.pullrequest.updated
    """
    # Read body once and reuse — calling request.body() twice would block
    raw_body = await request.body()

    # ── Optional HMAC signature verification ────────────────────────────────
    if WEBHOOK_SECRET:
        _verify_signature(request.headers.get("X-Hub-Signature", ""), raw_body)

    # Parse JSON from the already-read body
    try:
        import json
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    # ── Only process PR events ───────────────────────────────────────────────
    event_type = payload.get("eventType", "")
    if event_type not in ("git.pullrequest.created", "git.pullrequest.updated"):
        return JSONResponse({"message": f"Event '{event_type}' ignored."}, status_code=200)

    # ── Extract PR details from the service hook payload ─────────────────────
    pr_context = _extract_pr_context(payload)
    if not pr_context:
        raise HTTPException(status_code=400, detail="Could not extract PR context from payload.")

    print(f"[webhook] {event_type} — PR #{pr_context['pr_id']} "
          f"in {pr_context['project']}/{pr_context['repo']}")

    # ── Queue review in background — return 202 immediately ──────────────────
    # ADO service hooks time out at 5 seconds; the review takes ~30–60 seconds.
    background_tasks.add_task(run_review, pr_context)

    return JSONResponse({
        "message": "Review queued.",
        "pr_id":   pr_context["pr_id"],
        "repo":    pr_context["repo"],
    }, status_code=202)


# ── Review orchestration ──────────────────────────────────────────────────────

def run_review(pr_context: dict) -> None:
    """Full review flow — runs in a background thread after webhook returns."""
    try:
        cfg = load_config()

        ado = AdoClient(
            org_url=pr_context["org_url"],
            project=pr_context["project"],
            repo=pr_context["repo"],
            pr_id=pr_context["pr_id"],
            access_token=cfg.access_token,
        )

        pr_details    = ado.get_pr_details()
        changed_files = ado.get_changed_files(cfg.skip_extensions)

        print(f"[review] '{pr_details.get('title')}' | "
              f"{len(changed_files)} file(s) to review")

        if not changed_files:
            ado.post_review_thread(
                "## 🤖 AI PR Review\nNo reviewable code files found. Skipping."
            )
            return

        reviewer  = GeminiReviewer(cfg.gemini_api_key, cfg.max_file_chars)
        commit_id = pr_details["lastMergeSourceCommit"]["commitId"]

        file_reviews: list[tuple[str, str]] = []
        for i, file in enumerate(changed_files, 1):
            path    = file["path"]
            print(f"[review] [{i}/{len(changed_files)}] {path}")
            content = ado.get_file_content(path, commit_id)
            if content.strip():
                review = reviewer.review_file(path, content)
                file_reviews.append((path, review))

        if file_reviews:
            comment = build_pr_comment(pr_details, file_reviews)
            ado.post_review_thread(comment)
            print(f"[review] ✅ Posted review for PR #{pr_context['pr_id']}")
        else:
            print("[review] All files were empty. Nothing posted.")

    except Exception as exc:
        # Log the full error — never crash the server process
        print(f"[review] ❌ Error for PR #{pr_context.get('pr_id')}: {exc!r}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_pr_context(payload: dict) -> dict | None:
    """
    Extract PR fields from the ADO service hook payload.

    Payload shape (git.pullrequest.created):
    {
      "eventType": "git.pullrequest.created",
      "resource": {
        "pullRequestId": 42,
        "repository": {
          "name": "my-repo",
          "project": { "name": "MyProject" }
        }
      },
      "resourceContainers": {
        "collection": { "baseUrl": "https://dev.azure.com/myorg/" }
      }
    }
    """
    try:
        resource = payload["resource"]
        return {
            "pr_id":   str(resource["pullRequestId"]),
            "repo":    resource["repository"]["name"],
            "project": resource["repository"]["project"]["name"],
            "org_url": payload["resourceContainers"]["collection"]["baseUrl"].rstrip("/"),
        }
    except (KeyError, TypeError):
        return None


def _verify_signature(signature_header: str, body: bytes) -> None:
    """Validate the HMAC-SHA1 signature sent by ADO service hook."""
    if not signature_header.startswith("sha1="):
        raise HTTPException(status_code=401, detail="Missing or invalid signature header.")
    expected = "sha1=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha1
    ).hexdigest()
    if not hmac.compare_digest(signature_header, expected):
        raise HTTPException(status_code=401, detail="Signature mismatch — request rejected.")
