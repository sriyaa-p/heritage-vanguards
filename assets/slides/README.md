# 🎨 Heritage Sentinel AI — Presentation Slides

This folder contains all slide assets for the **Heritage Sentinel AI** Kaggle submission (Google × Kaggle AI Agents Intensive Capstone, June 2026).

---

## 📂 Current Slides (Aishwarya — MCP Server & ADK)

| File | Slide Title |
|------|-------------|
| `slide-mcp-server-from-pipeline-to-protocol.png` | MCP Server — From Pipeline to Protocol |
| `slide-mcp-server-6-tools-one-bridge.png` | 6 Tools. One Bridge. — What the MCP Server Exposes |
| `slide-antigravity-adk-integration.png` | Antigravity & ADK — Agentic Architecture & ADK Integration |
| `slide-29-tests-zero-failed.png` | Built for Trust — 29 Tests, Zero Failures |
| `slide-road-ahead-future-next-steps.png` | The Road Ahead — Future Mission & Next Steps |

---

## ⬇️ How to Download a Slide

1. Click on any `.png` file in this folder
2. Click the **Download raw file** button (top-right, arrow-down icon)
3. The image saves directly to your computer at full resolution

Or clone the whole repo and find the files at `assets/slides/`.

---

## ➕ How to Add Your Slides

**Option A — Via GitHub Web UI (no git required):**
1. Navigate to this folder: `assets/slides/`
2. Click **Add file → Upload files**
3. Drag and drop your slide images (PNG or JPG preferred for universal compatibility)
4. Use the naming convention: `slide-<your-topic>-<short-title>.png`
   - e.g. `slide-pipeline-overview.png`, `slide-dataset-audit.png`
5. Set commit message: `feat(slides): add <your name> slides — <topic>`
6. Commit directly to `main` (or open a PR if you prefer)

**Option B — Via git CLI:**
```bash
git pull origin main
cp your-slide.png assets/slides/slide-<topic>.png
git add assets/slides/
git commit -m "feat(slides): add <your name> slides — <topic>"
git push origin main
```

---

## 📋 Slide Naming Convention

```
slide-<topic-kebab-case>.png
```

Examples:
- `slide-problem-statement.png`
- `slide-architecture-overview.png`
- `slide-live-demo.png`
- `slide-dataset-pipeline.png`

---

## 🖼️ Format Guidelines

- **Preferred format:** PNG (lossless, best for text-heavy slides)
- **Fallback:** JPG / WEBP
- **Resolution:** Export at 1920×1080 or higher for crisp quality
- **Do NOT commit `.pptx` or `.key` binary files** — export as PNG/JPG and commit those instead (GitHub renders them inline and they're easier to review in PRs)

---

## 👥 Slide Ownership Tracker

| Teammate | Slides Committed | Status |
|----------|-----------------|--------|
| Aishwarya | MCP Server, 6 Tools, Antigravity & ADK, 29 Tests, Road Ahead | ✅ Done |
| Sriya | TBD | ⏳ Pending |
| Ujjwal | TBD | ⏳ Pending |
| Rujul | TBD | ⏳ Pending |
| Sanjana | TBD | ⏳ Pending |

---

*Last updated: July 2026*
