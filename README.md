# ULTRON - PC + Android Personal AI Assistant

**Antigravity Build Specification Implementation**  
Voice-first, hybrid AI assistant for Windows PC (ASUS ROG Strix G16) and Android (Infinix GT 30 Pro 5G) with balanced autonomy, permission policies, audit logging, emergency-stop controls, and typed tool registries.

---

## Architecture & Phased Roadmap

As specified in the build blueprint:
1. **Phase 1: Core Safety & Policy Engine** *(Completed & Verified)*
   - FastAPI Orchestration Service (`services/api/main.py`)
   - Policy Gateway with Balanced Autonomy tiers R0–R4 (`services/policy/engine.py`)
   - Persistent Emergency Stop Manager (`services/policy/emergency_stop.py`)
   - One-Time Parameter-Bound Approval Tickets (`services/policy/approvals.py`)
   - Append-Only SQLite Audit Logger with Secret Redaction (`services/audit/logger.py`)
   - Strict Pydantic Tool Schemas & Registry (`services/registry/`)
2. **Phase 2: Gemini Brain & Unified Cross-Device Operator** *(Completed & Verified)*
   - Google Gemini provider adapter with automatic model failover pool (`gemini-3.1-flash-lite`, `gemini-3.5-flash-lite`, `gemini-flash-latest`).
   - Native Python tool-calling connecting Gemini directly to registered device actions.
3. **Phase 3: Windows Device Agent** *(Completed & Verified)*
   - Windows UI Automation and process management (`services/devices/windows_agent.py`):
     - `apps.list`, `apps.open`, `apps.close`
     - `windows.list`, `windows.focus`
     - `files.search`, `files.read`, `files.create`, `files.edit`, `files.organize`
     - `browser.open`, `browser.inspect`
     - `screen.capture`, `screen.ocr`, `screen.summarize`
     - `process.list`, `process.status`
     - `project.inspect`, `code.edit`, `tests.run`, `build.run`
4. **Phase 4: Android Companion Agent** *(Completed & Verified)*
   - Native companion bridge (`services/devices/android_agent.py`):
     - `android.apps.open` (Intents & UI automation)
     - `android.notifications.read` (Consent-based dumpsys reader)
     - `android.screen.capture` (ADB screencap with PC pull)
     - `android.permissions.status` (Real-time capability reporting)
     - Direct dialing, WhatsApp instant delivery, Clock alarm setting
5. **Phase 5: Unified Cross-Device Workflows & Emergency Stop** *(Completed & Verified)*
   - `devices.list`, `devices.status`
   - `workflow.create`, `workflow.run`, `workflow.pause`, `workflow.cancel`
   - `safety.stop`, `safety.status`, `safety.resume`
   - Instant voice interruption: *"Stop all automation immediately"* triggers persistent emergency stop.
6. **Phase 6: Multilingual Voice & Audio Engine** *(Completed & Verified)*
   - Whisper multilingual listener + ElevenLabs & Edge Neural TTS (`en-US-AvaMultilingualNeural` & `ta-IN-PallaviNeural`).

---

## Balanced Autonomy Model

| Tier | Policy | Description |
| :--- | :--- | :--- |
| **R0 — Read-only** | Automatic within scope | System status, file listing, public web search, window listing, project inspection. |
| **R1 — Routine** | Automatic if allowlisted | Allowlisted apps, window focus, tests run, vocal replies. |
| **R2 — Significant** | Preview & approval required | File edits, file organizing, screen capture, workflow execution. |
| **R3 — High Impact** | Fresh confirmation required | Sending messages, deleting data, configuration changes. |
| **R4 — Prohibited** | Always denied | Credential theft, arbitrary shell injection, bypassing UAC. |

---

## Running Verification Tests

Execute all 25 unit and integration tests across Policy, Audit, Registry, Windows Agent, and Android Companion:
```powershell
.\.venv\Scripts\pytest tests/ -v
```
Output:
```
25 passed in 2.26s
```

---

## Starting Services

### 1. Launch FastAPI Orchestration Backend
```powershell
.\.venv\Scripts\uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Audit Trail: `http://127.0.0.1:8000/audit`

### 2. Launch ULTRON Voice & Autonomous Assistant (Console Mode)
```powershell
.\run_ultron.bat
```
- Personalized for **Luffy**
- Wake Trigger: **Double Clap** or wake word
- Bilingual: English & Tamil (`base` Whisper + ElevenLabs / Edge-TTS)

### 3. Launch ULTRON Holographic 3D Desktop Operator (Native Iron Man UI)
```powershell
.\run_ultron_desktop.bat
```
- **Native Desktop Application**: Runs directly as a dedicated Windows window (not a web browser).
- **Holographic 3D Orb**: High-fidelity Three.js core spiral, wireframe shells, bloom shaders, and orbiting particles ported from Sagar's design.
- **Bi-directional Bridge**: Connected via `QWebChannel` to Gemini reasoning, continuous Whisper ear listener, Edge/ElevenLabs speech, and real device tools (`apps.*`, `files.*`, `android.*`, `workflow.*`).
- **Interactive HUD**: Live telemetry badges (PC CPU/RAM, Android ADB status, Gemini status), operator transcript terminal, quick command dock, and emergency STOP control.
