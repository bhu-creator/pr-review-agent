# AI PR Review Agent — Complete Documentation

## Table of Contents
1. [What Is This Agent?](#1-what-is-this-agent)
2. [How It Works](#2-how-it-works)
3. [Project Structure](#3-project-structure)
4. [Module Responsibilities](#4-module-responsibilities)
5. [Deployment Options](#5-deployment-options)
6. [Option 2 — Service Hook Setup (Recommended for Microservices)](#6-option-2--service-hook-setup-recommended-for-microservices)
7. [Prerequisites Checklist](#7-prerequisites-checklist)
8. [Environment Variables Reference](#8-environment-variables-reference)
9. [.NET Standards the Agent Reviews](#9-net-standards-the-agent-reviews)
10. [Review Comment Format](#10-review-comment-format)
11. [Running Locally](#11-running-locally)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What Is This Agent?

The **AI PR Review Agent** is an automated code reviewer that:

- **Triggers automatically** when a Pull Request is raised or updated
- **Reads every changed `.cs` file** in the PR
- **Sends the code to Google Gemini AI** (free tier — no cost)
- **Reviews against .NET / C# coding standards** (naming, async/await, SOLID, EF Core, null safety, etc.)
- **Posts a structured review comment** on the PR with found issues and a corrected code fix for each one
- **Gives a final verdict**: ✅ Approve / 🟠 Request Changes / 🔴 Critical Issues

> No human reviewer needs to manually trigger anything. It works fully automatically.

---

## 2. How It Works

### End-to-End Flow

```
Developer opens/updates PR
         │
         ▼
Azure DevOps Service Hook fires (org-level — covers ALL repos/projects)
         │
         ▼
POST request sent to Webhook Server (webhook_server.py)
    payload contains: PR ID, Repo name, Project name, Org URL
         │
         ▼
Webhook Server (FastAPI)
    → Extracts PR details from payload
    → Returns HTTP 202 immediately (so ADO doesn't time out)
    → Starts review in background thread
         │
         ▼
AdoClient (ado_client.py)
    → Fetches PR metadata (title, author, last commit)
    → Gets list of changed files (skips .json, .yml, .csproj etc.)
    → Downloads full content of each .cs file
         │
         ▼
GeminiReviewer (gemini_client.py)
    → Sends each file + .NET standards prompt to Gemini 1.5 Flash (free)
    → Receives structured review with issues + fix suggestions
         │
         ▼
CommentBuilder (comment_builder.py)
    → Assembles all file reviews into one Markdown document
    → Calculates overall verdict based on severity counts
         │
         ▼
AdoClient posts the review as a comment thread on the PR
         │
         ▼
🎉 Developer sees the AI review in the PR Overview tab
```

---

## 3. Project Structure

```
pr-review-agent/
│
├── azure-pipelines-pr-review.yml   ← (Optional) Pipeline YAML for Options 1 & 3
├── Dockerfile                      ← Container for deploying the webhook server
├── setup.ps1                       ← One-click local setup script (Windows)
├── .env.example                    ← Template for environment variables
├── .env                            ← Your actual secrets (NOT committed to git)
├── .gitignore                      ← Protects .env and .venv from git
│
└── scripts/
    ├── pr_review_agent.py          ← Entry point / orchestrator (50 lines)
    ├── webhook_server.py           ← FastAPI webhook receiver (Option 2)
    ├── config.py                   ← Environment loading + Config dataclass
    ├── ado_client.py               ← Azure DevOps REST API client
    ├── gemini_client.py            ← Google Gemini AI client
    ├── review_prompt.py            ← .NET review prompt (edit to customise)
    ├── comment_builder.py          ← Markdown comment formatter
    └── requirements.txt            ← Python dependencies
```

---

## 4. Module Responsibilities

| File | Responsibility | Change this when... |
|---|---|---|
| `pr_review_agent.py` | Wires all modules together, orchestrates the flow | Changing the overall review workflow |
| `webhook_server.py` | Receives ADO service hook HTTP payloads | Changing trigger mechanism or adding auth |
| `config.py` | Loads env vars, exposes typed `Config` object | Adding new configuration options |
| `ado_client.py` | All HTTP calls to Azure DevOps REST API | Fixing API issues or switching platforms |
| `gemini_client.py` | Sends code to Gemini, returns review text | Switching to a different AI model |
| `review_prompt.py` | The .NET standards review prompt text | Changing what standards are reviewed |
| `comment_builder.py` | Formats the final Markdown PR comment | Changing the look of review comments |

> **Key design principle:** Each file does exactly one thing. Changing the AI model only touches `gemini_client.py`. Changing comment style only touches `comment_builder.py`.

---

## 5. Deployment Options

| Option | What runs where | Files needed in microservice repos | Best for |
|---|---|---|---|
| **Option 1** — Centralized Pipeline | Single ADO pipeline with parameters; triggered manually or via REST API | None | Small teams, on-demand reviews |
| **Option 2 — Service Hook + Webhook** ✅ | Webhook server hosted externally; ADO fires it for every PR org-wide | **None** | Microservices — fully automatic, zero changes per repo |
| **Option 3** — YAML Template Reference | One template file; each repo references it with 2 lines | 2 lines in each repo's pipeline | Teams that prefer pipeline-based approach |

---

## 6. Option 2 — Service Hook Setup (Recommended for Microservices)

### Architecture

```
ADO Organization-Level Service Hook
    [fires for EVERY PR in EVERY project/repo]
         │
         │  HTTP POST (JSON payload with PR details)
         ▼
Your Webhook Server
(Azure App Service / Container App / any public URL)
running: webhook_server.py
```

### Step-by-Step Setup

#### A) Deploy the Webhook Server

**Using Docker (quickest):**
```bash
docker build -t pr-review-agent .
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY="your_key" \
  -e SYSTEM_ACCESSTOKEN="your_ado_pat" \
  -e WEBHOOK_SECRET="optional_secret" \
  pr-review-agent
```

**Using Azure App Service:**
1. Push this repo to a container registry (Azure Container Registry or Docker Hub)
2. Create an Azure App Service (Linux, B1 tier is fine)
3. Set the container image
4. Add environment variables in **App Service → Configuration → Application Settings**

You need a **public HTTPS URL** — e.g. `https://pr-review-agent.azurewebsites.net`

#### B) Create the ADO Service Hook

```
Azure DevOps → Organization Settings (gear icon, top-right)
    → Service Hooks → + Subscription

1. TRIGGER
   Publisher:    Azure DevOps
   Event:        "Pull request created"
   Repository filters: (leave blank = all repos) ✅

2. ACTION
   Action:  Web Hooks
   URL:     https://your-server.com/webhook/pr-review
   Content: application/json
   Secret:  (optional — match WEBHOOK_SECRET env var)

→ Click "Finish"
```

Repeat for event `"Pull request updated"` to re-review on new commits.

#### C) Verify It Works

1. Open any PR in any of your microservice repos
2. Check your webhook server logs — you should see `[webhook] Received git.pullrequest.created for PR #...`
3. Check the PR in Azure DevOps — the AI review comment appears in the **Overview** tab within ~30–60 seconds

---

## 7. Prerequisites Checklist

### One-Time Setup

| # | Prerequisite | How to get it | Who does it |
|---|---|---|---|
| 1 | **Google Gemini API Key** (free) | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Create API Key | You |
| 2 | **Azure DevOps PAT** with correct scopes | ADO → User Settings → Personal Access Tokens → New Token | You |
| 3 | **Public HTTPS URL** for the webhook server | Azure App Service / any host | DevOps / Infra |
| 4 | **ADO Org-Level Service Hook** configured | Organization Settings → Service Hooks | ADO Admin |
| 5 | **Build Service permission** (if using pipeline) | Project Settings → Repos → Security → "Contribute to pull requests" = Allow | ADO Admin |

### PAT Scopes Required

When creating the Azure DevOps PAT (`SYSTEM_ACCESSTOKEN`):

| Scope | Permission | Why |
|---|---|---|
| Code | **Read** | To fetch file contents and PR changes |
| Pull Request Threads | **Read & Write** | To post review comments on the PR |

> **Important:** For Option 2 (service hook), the PAT must be **org-scoped** (not project-scoped) since it accesses PRs across all projects.

### Server Requirements (for Option 2)

| Requirement | Minimum |
|---|---|
| Python | 3.11+ |
| RAM | 512 MB |
| Public internet access | Required (ADO needs to reach it) |
| HTTPS certificate | Required (ADO service hooks reject HTTP) |

---

## 8. Environment Variables Reference

| Variable | Required | Where it comes from | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | You create + set | Google Gemini API key |
| `SYSTEM_ACCESSTOKEN` | ✅ Yes | Org-level ADO PAT | Auth for Azure DevOps API calls |
| `ADO_ORG_URL` | Pipeline only | Auto (Azure Pipelines) | e.g. `https://dev.azure.com/myorg` |
| `ADO_PROJECT` | Pipeline only | Auto (Azure Pipelines) | Project name |
| `ADO_REPO_NAME` | Pipeline only | Auto (Azure Pipelines) | Repository name |
| `ADO_PR_ID` | Pipeline only | Auto (Azure Pipelines) | Pull request number |
| `WEBHOOK_SECRET` | ❌ Optional | You create + set | Shared secret for HMAC signature validation |

> In **Option 2** (service hook), the org URL/project/repo/PR ID come from the service hook payload — the webhook server extracts them automatically. You only need `GEMINI_API_KEY`, `SYSTEM_ACCESSTOKEN`, and optionally `WEBHOOK_SECRET`.

---

## 9. .NET Standards the Agent Reviews

| # | Category | What it checks |
|---|---|---|
| 1 | **Naming Conventions** | PascalCase on classes/methods/props, `_camelCase` on private fields, `I` prefix on interfaces, `Async` suffix on async methods |
| 2 | **Async / Await** | No `.Result` or `.Wait()` (deadlock risk), all async calls awaited, `CancellationToken` parameters, `ConfigureAwait(false)` in libraries |
| 3 | **SOLID Principles** | Single responsibility, constructor injection over `new`, thin controllers, interfaces on repositories |
| 4 | **Exception Handling** | No empty `catch` blocks, catch specific types not `Exception`, log before swallowing, `using` for resource cleanup |
| 5 | **Null Safety** | `#nullable enable`, null-check parameters with `ArgumentNullException`, use `?.` and `??`, `string.IsNullOrWhiteSpace()` |
| 6 | **Entity Framework** | Async EF methods (`.ToListAsync()`), `.AsNoTracking()` for read-only, `.Include()` for related data, DTOs in API responses |
| 7 | **Code Quality** | No magic numbers/strings, methods under 20 lines, no dead code, XML docs on public APIs |

---

## 10. Review Comment Format

Every PR gets a single comment with this structure:

```markdown
# 🤖 AI Code Review — .NET Standards

| | |
|---|---|
| PR       | Add user authentication service |
| Author   | Jane Doe |
| Branch   | feature/auth → main |
| Files    | 3 reviewed |
| Reviewer | Gemini 1.5 Flash (AI) |

---

## 📄 `Services/UserService.cs`

### ❌ Issue 1: Missing Async suffix on async method
**Category**: Naming Conventions
**Severity**: 🟠 Major
**Line(s)**: 24
**Problem**: The method `GetUser` is async but does not follow the
convention of appending "Async" to its name, reducing code readability.

**Suggested Fix**:
\```csharp
// ❌ Before
public async Task<User> GetUser(int id) { ... }

// ✅ After
public async Task<User> GetUserAsync(int id) { ... }
\```

---

## 📋 Summary for `Services/UserService.cs`
- **Total**: 2 (🔴 0 Critical | 🟠 1 Major | 🟡 1 Minor)
- **Assessment**: Minor naming and code quality improvements needed.

---

## 🟡 Overall Verdict
**Needs Discussion** — Some issues found. Consider addressing before merge.
```

---

## 11. Running Locally

Useful for testing the agent against a specific PR before deploying.

```powershell
# 1. Run the one-click setup
cd pr-review-agent
.\setup.ps1

# 2. Fill in your credentials
notepad .env

# 3. Run the agent (reviews the PR defined in ADO_PR_ID in .env)
.\.venv\Scripts\python.exe scripts\pr_review_agent.py

# 4. (Option 2) Start the webhook server locally
.\.venv\Scripts\python.exe -m uvicorn scripts.webhook_server:app --reload --port 8000
# Use ngrok or similar to expose it: ngrok http 8000
```

---

## 12. Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| `403 Forbidden` when posting comment | Build Service lacks permission | Project Settings → Repos → Security → "Contribute to pull requests" = Allow |
| `GEMINI_API_KEY is not set` | Missing env var | Add to `.env` (local) or App Service settings (server) |
| Webhook not receiving events | Service hook URL wrong or HTTPS missing | Verify URL, ensure HTTPS, check ADO service hook logs |
| Review comment is empty | All files were in the skip list | Change `skip_extensions` in `config.py` |
| `401 Unauthorized` on ADO API | PAT expired or wrong scopes | Regenerate PAT with Code (Read) + PR Threads (Read & Write) |
| Review truncated for large files | File exceeds 28,000 chars limit | Increase `max_file_chars` in `config.py` |
| ADO service hook times out | Review is taking > 5 seconds | Already handled — webhook returns 202 immediately, review runs async |
