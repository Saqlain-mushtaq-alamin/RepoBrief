# 📚 RepoBrief Documentation Center

Welcome to the documentation center for **RepoBrief** — a lightweight codebase-to-context packer and chat interface for LLMs.

---

## 🗂️ Core Documentation Guides

- 📖 **[User Guide](./USER_GUIDE.md)**  
  Complete guide covering installation, export mode (`pack`), chat mode (`chat`), cloud API keys (Claude/GPT), local offline Ollama usage, secret detection/redaction, and configuration.

- 🏗️ **[Architecture & How It Works](./ARCHITECTURE_HOW_IT_WORKS.md)**  
  Technical deep dive into the 6-stage pipeline architecture (Scanner, Secret Detection, Token Counting & Scoring, Packer/Formatter, LLM Backends, and CLI).

- 🧪 **[Test Report](./TEST_REPORT.md)**  
  Full test execution report detailing test suite breakdown across all 8 test modules (111 / 111 tests passing).

---

## 📋 Phase Implementation Notes

Detailed notes for each implementation phase of the RepoBrief development roadmap:

| Phase | Description | Implementation Notes |
|-------|-------------|----------------------|
| **Phase 1** | Project Setup & Scaffolding | [Phase 1 Notes](./PHASE_1_IMPLEMENTATION_NOTES.md) |
| **Phase 2** | Core Repository Scanner | [Phase 2 Notes](./PHASE_2_IMPLEMENTATION_NOTES.md) |
| **Phase 3** | Secret Detection & Redaction | [Phase 3 Notes](./PHASE_3_IMPLEMENTATION_NOTES.md) |
| **Phase 4** | Token Counting & File Scoring | [Phase 4 Notes](./PHASE_4_IMPLEMENTATION_NOTES.md) |
| **Phase 5** | Packing & Output Formatting | [Phase 5 Notes](./PHASE_5_IMPLEMENTATION_NOTES.md) |
| **Phase 6** | CLI Wiring & Export Mode | [Phase 6 Notes](./PHASE_6_IMPLEMENTATION_NOTES.md) |
| **Phase 7** | Cloud Backend (Claude + GPT) | [Phase 7 Notes](./PHASE_7_IMPLEMENTATION_NOTES.md) |
| **Phase 8** | Ollama Local Backend | [Phase 8 Notes](./PHASE_8_IMPLEMENTATION_NOTES.md) |
| **Phase 9** | Error Handling & Polish | [Phase 9 Notes](./PHASE_9_IMPLEMENTATION_NOTES.md) |
| **Phase 10** | Packaging, Release & Documentation | [Phase 10 Notes](./PHASE_10_IMPLEMENTATION_NOTES.md) |

---

## 🚀 Quick Commands

```bash
# Run full test suite
pytest

# Run linter
ruff check src/ tests/

# Try RepoBrief packing locally
repobrief pack . --max-tokens 50000 -o digest.md
```
