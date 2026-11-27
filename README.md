# AI Agent Studio

A Windows-first, local-first multi-agent workspace. The language model, conversations, saved memory, uploaded files, and task records stay on the user's machine. External internet access is used only when the user explicitly submits a research query; chat history, files, and memory are not attached to that request.

## Current implementation

- Local FastAPI API and Next.js RTL interface.
- Ollama chat using a locally installed model.
- Five roles: Manager, Researcher, Developer, Analyst, and Reviewer. Manager delegates to a specialist and Reviewer checks the draft.
- SQLite storage for conversations, messages, memories, tasks, documents, and an activity audit log.
- FTS5 search indexes for saved memory and extracted local file text.
- Local file upload, listing, search, read, and delete for TXT, Markdown, CSV, JSON, source files, PDF, XLSX, and XLSM (10 MB upload limit).
- Background tasks run through the local Ollama model and store their result or error. Queued tasks can be cancelled.
- Explicit-query-only DuckDuckGo research. Only the search phrase is sent externally.
- Windows launcher binds the API to 127.0.0.1, not the public network.

## Requirements

- Windows 10/11
- Python 3.11+
- Node.js 20+
- Ollama installed and running
- A model installed locally in Ollama. The default is qwen2.5:3b; change OLLAMA_MODEL in backend/.env to a model already installed on the machine.

## Start on Windows

1. Install Python, Node.js, and Ollama.
2. In Ollama, download a model that fits the machine's RAM/VRAM. For the default model: ollama pull qwen2.5:3b.
3. Double-click scripts/start-windows.bat.
4. The launcher creates the Python environment, installs dependencies, starts the API and UI, and opens http://localhost:3000.

API health: http://127.0.0.1:8000/api/health.

Data is stored under the repository's data/ directory by default. Back up this folder to preserve local conversations, memories, task history, and uploaded files. Do not expose the API port to a public network.

## Privacy and safety boundaries

- No hosted model/API key is required.
- Chat, memory, and file text are processed by the local Ollama service.
- External research receives only the exact query entered in the Research screen.
- Uploaded files are treated as untrusted reference material, not instructions.
- The application does not provide a shell, arbitrary command execution, automatic software installation, or unrestricted computer control.
- Do not upload confidential material to a computer you do not control.

## Verification status

GitHub Actions checks Python compilation, backend unit tests, and a production frontend build. Those checks do not prove Ollama inference, Windows installation, GPU acceleration, or performance on a particular PC. Those still need a local end-to-end run on the target Windows machine.

## Known limitations

- Manager delegation is model-guided but does not yet provide autonomous tool execution.
- Research is a separate explicit-query feature; the Researcher role does not silently browse the internet.
- File retrieval adds searchable local excerpts only through the file-search API; the chat UI does not yet expose file selection or citation cards.
- Task execution is a single-process local queue, not a distributed worker system. A task interrupted by closing the app is re-queued on next startup; no progress checkpoint is retained.
- There is no multi-user authentication. Keep the local API bound to loopback and do not expose it to a LAN or public internet.
- Windows/Ollama end-to-end tests must be completed on the user's own device.

Development is isolated on phase-1-foundation. main is kept as the stable baseline until the feature branch passes review and CI.
