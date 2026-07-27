# AI PR Review Agent — Azure DevOps Setup Guide

Automatically reviews every PR targeting `main` using **Google Gemini 1.5 Flash** (free tier) and posts a structured code-review comment focused on **.NET / C# coding standards**, complete with **fix suggestions** for each issue found.

---

## 📁 File Structure

Place these files in the **root of your Azure DevOps repository**:

```
your-repo/
├── azure-pipelines-pr-review.yml   ← Pipeline definition file
└── scripts/
    ├── pr_review_agent.py           ← Main AI review agent
    ├── requirements.txt             ← Python dependencies
    └── README.md                    ← This file
```

---

## 🔑 Step 1 — Get a Gemini API Key (Free)

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **"Create API Key"** — it's free, no credit card needed
3. Copy the key

---

## 🔒 Step 2 — Add Secret to Azure DevOps

### Option A: Variable Group (Recommended)

1. Go to your Azure DevOps project → **Pipelines → Library**
2. Click **"+ Variable group"**
3. Name it exactly: `pr-review-secrets`
4. Add a variable:
   - **Name**: `GEMINI_API_KEY`
   - **Value**: *paste your Gemini API key*
   - **Lock icon**: ✅ click it (marks it as secret)
5. Click **Save**

### Option B: Pipeline Variable (Quick)

1. Open the pipeline → **Edit → Variables**
2. Add `GEMINI_API_KEY` as a secret variable

---

## ⚙️ Step 3 — Create the Pipeline in Azure DevOps

1. Go to **Pipelines → New Pipeline**
2. Select your repository
3. Choose **"Existing Azure Pipelines YAML file"**
4. Select `/azure-pipelines-pr-review.yml`
5. Click **"Save"** (don't run yet)

---

## 🔐 Step 4 — Grant Repository Permissions

The pipeline's build service needs permission to **post comments on PRs**:

1. Go to **Project Settings → Repositories → [Your Repo]**
2. Click the **Security** tab
3. Find **"[Project] Build Service ([Org])"**
4. Set **"Contribute to pull requests"** → ✅ **Allow**

---

## ✅ Step 5 — Test It

1. Create a feature branch and push any `.cs` file change
2. Open a **Pull Request** targeting `main`
3. Watch the pipeline trigger automatically under the **Checks** tab
4. The AI review comment will appear in the PR's **Overview / Comments** section

---

## 💬 What the Review Comment Looks Like

```markdown
# 🤖 AI Code Review — .NET Standards

| Field        | Details                        |
|---|---|
| PR Title     | Add user authentication        |
| Author       | John Doe                       |
| Branch       | feature/auth → main            |
| Files Reviewed | 3                            |

---

## 📄 `Services/UserService.cs`

### ❌ Issue 1: Deadlock-prone async usage
**Category**: Async/Await  
**Severity**: 🔴 Critical  
**Line(s)**: 42  
**Problem**: Using `.Result` on a Task blocks the thread and can cause deadlocks in ASP.NET Core.

**Suggested Fix**:
\```csharp
// ❌ Before
var user = GetUserAsync(id).Result;

// ✅ After
var user = await GetUserAsync(id);
\```

---

## 🔴 Overall Verdict
**Request Changes** — Critical issues must be resolved before merging.
```

---

## 🎛️ Customization

### Change which files are reviewed

Edit `pr_review_agent.py` → `get_changed_files()`:

```python
skip_extensions = {".json", ".xml", ".csproj", ...}  # add/remove extensions here
```

### Adjust the review prompt

Edit `scripts/pr_review_agent.py` → `DOTNET_REVIEW_PROMPT` to add/remove standards.

### Switch to a different free Gemini model

Edit `pr_review_agent.py` → `init_gemini()`:

```python
return genai.GenerativeModel("gemini-2.0-flash")   # or "gemini-1.5-flash"
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| Pipeline doesn't trigger on PR | Ensure the YAML file is on `main` (not just your feature branch) and the pipeline is saved |
| `403 Forbidden` when posting comment | Grant **"Contribute to pull requests"** to the Build Service in repo security settings |
| `GEMINI_API_KEY not set` error | Check the variable group name matches `pr-review-secrets` exactly |
| Review is empty / truncated | File may exceed 28,000 chars — large files are partially reviewed. Increase `MAX_DIFF_CHARS` in the script |
