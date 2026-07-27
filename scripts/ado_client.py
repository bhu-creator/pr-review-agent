"""
ado_client.py — All Azure DevOps REST API interactions in one place.
Swap this class out to support a different Git platform (GitHub, GitLab, etc.)
without touching any other code.
"""

import base64
import os
import requests


class AdoClient:
    """Handles all communication with the Azure DevOps REST API."""

    API_VERSION = "7.1"

    def __init__(self, org_url: str, project: str, repo: str,
                 pr_id: str, access_token: str) -> None:
        self._base = f"{org_url}/{project}/_apis/git/repositories/{repo}"
        self._pr   = f"{self._base}/pullRequests/{pr_id}"
        self._headers = {
            "Authorization": "Basic " + base64.b64encode(
                f":{access_token}".encode()
            ).decode(),
            "Content-Type": "application/json",
        }

    # ── Public methods ────────────────────────────────────────────────────────

    def get_pr_details(self) -> dict:
        """Return PR metadata (title, author, branches, last commit)."""
        return self._get(self._pr)

    def get_changed_files(self, skip_extensions: frozenset) -> list[dict]:
        """Return list of {path, changeType} for non-deleted code files."""
        iteration_id = self._get_latest_iteration_id()
        url  = f"{self._pr}/iterations/{iteration_id}/changes"
        data = self._get(url)

        results = []
        for entry in data.get("changeEntries", []):
            path        = entry.get("item", {}).get("path", "")
            change_type = entry.get("changeType", "")
            ext         = os.path.splitext(path)[1].lower()

            if path and change_type != "delete" and ext not in skip_extensions:
                results.append({"path": path, "changeType": change_type})
        return results

    def get_file_content(self, path: str, commit_id: str) -> str:
        """Fetch raw text content of a file at a specific commit."""
        params = {
            "path":        path,
            "version":     commit_id,
            "versionType": "commit",
            "$format":     "text",
            "api-version": self.API_VERSION,
        }
        headers = {**self._headers, "Content-Type": "text/plain"}
        resp = requests.get(
            self._build_items_url(), headers=headers, params=params, timeout=30
        )
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        return resp.text

    def post_review_thread(self, comment: str) -> None:
        """Post a PR-level review comment thread."""
        url  = f"{self._pr}/threads?api-version={self.API_VERSION}"
        body = {
            "comments": [{
                "parentCommentId": 0,
                "content":         comment,
                "commentType":     1,
            }],
            "status": 1,
        }
        self._post(url, body)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_latest_iteration_id(self) -> int:
        data       = self._get(f"{self._pr}/iterations")
        iterations = data.get("value", [])
        if not iterations:
            raise RuntimeError("No PR iterations found.")
        return iterations[-1]["id"]

    def _build_items_url(self) -> str:
        # self._base = "{org}/{project}/_apis/git/repositories/{repo}"
        # Produces:   "{org}/{project}/_apis/git/repositories/{repo}/items"
        parts = self._base.split("/_apis/")
        return f"{parts[0]}/_apis/{parts[1]}/items"

    def _get(self, url: str, params: dict = None) -> dict:
        params = {**(params or {}), "api-version": self.API_VERSION}
        resp   = requests.get(url, headers=self._headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, body: dict) -> dict:
        resp = requests.post(url, headers=self._headers, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
