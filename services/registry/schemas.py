"""Strict Pydantic schemas for registered tools."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# 1. system.get_status
class SystemGetStatusInput(BaseModel):
    detailed: bool = Field(False, description="Include detailed process and network metrics")

class SystemGetStatusOutput(BaseModel):
    os: str
    cpu_percent: float
    memory_percent: float
    battery_percent: Optional[float] = None
    uptime_seconds: float
    status: str = "ok"

# 2. apps.open
class AppsOpenInput(BaseModel):
    app_name: str = Field(..., description="Allowlisted application name to open")

class AppsOpenOutput(BaseModel):
    app_name: str
    opened: bool
    message: str

# 3. files.list
class FilesListInput(BaseModel):
    directory_path: str = Field(..., description="Path to list files within approved directories")

class FilesListOutput(BaseModel):
    directory: str
    files: List[str]
    total_count: int

# 4. files.read
class FilesReadInput(BaseModel):
    file_path: str = Field(..., description="Path of file to read")
    max_lines: int = Field(200, description="Maximum lines to read")

class FilesReadOutput(BaseModel):
    file_path: str
    content: str
    lines_read: int

# 5. files.edit
class FilesEditInput(BaseModel):
    file_path: str = Field(..., description="Target file path to edit")
    content: str = Field(..., description="Content to write or append")
    mode: str = Field("append", description="Mode: 'write' or 'append'")

class FilesEditOutput(BaseModel):
    file_path: str
    bytes_written: int
    backup_path: Optional[str] = None
    message: str

# 6. browser.search
class BrowserSearchInput(BaseModel):
    query: str = Field(..., description="Web query to search")

class BrowserSearchOutput(BaseModel):
    query: str
    results: List[Dict[str, str]]
    source_urls: List[str]

# 7. browser.navigate
class BrowserNavigateInput(BaseModel):
    url: str = Field(..., description="Approved URL to navigate")

class BrowserNavigateOutput(BaseModel):
    url: str
    opened: bool
    title: Optional[str] = None

# 8. screen.capture
class ScreenCaptureInput(BaseModel):
    save_path: Optional[str] = Field(None, description="Optional path to save screenshot")

class ScreenCaptureOutput(BaseModel):
    saved_path: str
    captured: bool

# 9. voice.speak
class VoiceSpeakInput(BaseModel):
    text: str = Field(..., description="Text to speak aloud")
    language: str = Field("auto", description="Language: 'auto', 'en', 'ta'")

class VoiceSpeakOutput(BaseModel):
    spoken: bool
    provider: str
    text: str

# 10. messages.prepare
class MessagesPrepareInput(BaseModel):
    recipient: str = Field(..., description="Target contact or number")
    body: str = Field(..., description="Draft message text")

class MessagesPrepareOutput(BaseModel):
    draft_id: str
    recipient: str
    body: str
    status: str = "drafted"

# 11. messages.send
class MessagesSendInput(BaseModel):
    draft_id: str = Field(..., description="Draft ID to send after approval")
    recipient: str = Field(..., description="Confirmed recipient")
    body: str = Field(..., description="Confirmed message body")

class MessagesSendOutput(BaseModel):
    sent: bool
    recipient: str
    message_id: str

# 12. jobs.create
class JobsCreateInput(BaseModel):
    name: str = Field(..., description="Job identifier")
    schedule: str = Field(..., description="Cron or interval schedule")
    action: str = Field(..., description="Tool ID to run")
    params: Dict[str, Any] = Field(default_factory=dict)

class JobsCreateOutput(BaseModel):
    job_id: str
    name: str
    status: str = "scheduled"

# 13. home.device_control
class HomeDeviceControlInput(BaseModel):
    device_id: str = Field(..., description="Allowlisted smart device ID")
    command: str = Field(..., description="Command (turn_on, turn_off, toggle)")

class HomeDeviceControlOutput(BaseModel):
    device_id: str
    executed: bool
    state: str

# 14. system.command
class SystemCommandInput(BaseModel):
    command: str = Field(..., description="Shell command")

class SystemCommandOutput(BaseModel):
    exit_code: int
    output: str
    error: str

# 15. apps.list
class AppsListInput(BaseModel):
    limit: int = Field(50, description="Max applications to list")

class AppsListOutput(BaseModel):
    apps: List[str]
    total_count: int

# 16. apps.close
class AppsCloseInput(BaseModel):
    process_name: str = Field(..., description="Process name or app name to close")

class AppsCloseOutput(BaseModel):
    process_name: str
    closed: bool
    message: str

# 17. windows.list
class WindowsListInput(BaseModel):
    include_minimized: bool = Field(True, description="Include minimized windows")

class WindowsListOutput(BaseModel):
    windows: List[str]
    total_count: int

# 18. windows.focus
class WindowsFocusInput(BaseModel):
    window_title: str = Field(..., description="Title substring of window to focus")

class WindowsFocusOutput(BaseModel):
    window_title: str
    focused: bool
    message: str

# 19. files.search
class FilesSearchInput(BaseModel):
    directory: str = Field(..., description="Directory to search within")
    pattern: str = Field(..., description="Filename pattern or extension")
    max_results: int = Field(50, description="Max matches")

class FilesSearchOutput(BaseModel):
    directory: str
    pattern: str
    matches: List[str]
    count: int

# 20. files.create
class FilesCreateInput(BaseModel):
    file_path: str = Field(..., description="Target file path to create")
    content: str = Field("", description="Initial content")

class FilesCreateOutput(BaseModel):
    file_path: str
    created: bool
    bytes_written: int
    message: str

# 21. files.organize
class FilesOrganizeInput(BaseModel):
    directory_path: str = Field(..., description="Target folder to organize by file type (e.g. Downloads)")
    dry_run: bool = Field(False, description="Preview moves without touching disk")

class FilesOrganizeOutput(BaseModel):
    directory_path: str
    moved_count: int
    dry_run: bool
    summary: Dict[str, int]
    message: str

# 22. browser.open
class BrowserOpenInput(BaseModel):
    url: str = Field(..., description="URL to open in default browser")

class BrowserOpenOutput(BaseModel):
    url: str
    opened: bool

# 23. browser.inspect
class BrowserInspectInput(BaseModel):
    url: str = Field(..., description="URL to inspect / fetch text from")

class BrowserInspectOutput(BaseModel):
    url: str
    title: str
    content_snippet: str
    status_code: int

# 24. screen.ocr
class ScreenOcrInput(BaseModel):
    save_path: Optional[str] = Field(None, description="Path to captured screen or None for live capture")

class ScreenOcrOutput(BaseModel):
    extracted_text: str
    word_count: int

# 25. screen.summarize
class ScreenSummarizeInput(BaseModel):
    prompt: Optional[str] = Field(None, description="Custom instruction for screen summary")

class ScreenSummarizeOutput(BaseModel):
    summary: str
    active_window: str

# 26. process.list
class ProcessListInput(BaseModel):
    sort_by: str = Field("memory", description="Sort by 'memory' or 'cpu'")
    limit: int = Field(20, description="Number of processes to return")

class ProcessListOutput(BaseModel):
    processes: List[Dict[str, Any]]
    total_running: int

# 27. process.status
class ProcessStatusInput(BaseModel):
    process_name: str = Field(..., description="Name of process to inspect")

class ProcessStatusOutput(BaseModel):
    process_name: str
    running: bool
    instances: int
    memory_mb: float
    cpu_percent: float

# 28. project.inspect
class ProjectInspectInput(BaseModel):
    project_path: str = Field(..., description="Path to workspace/project")

class ProjectInspectOutput(BaseModel):
    project_path: str
    file_types: Dict[str, int]
    git_status: Optional[str] = None
    total_files: int

# 29. code.edit
class CodeEditInput(BaseModel):
    file_path: str = Field(..., description="Path of source file")
    old_snippet: str = Field(..., description="Exact snippet to replace")
    new_snippet: str = Field(..., description="New replacement code")

class CodeEditOutput(BaseModel):
    file_path: str
    edited: bool
    backup_path: Optional[str] = None
    message: str

# 30. tests.run
class TestsRunInput(BaseModel):
    test_path: Optional[str] = Field(None, description="Specific test file or folder")

class TestsRunOutput(BaseModel):
    command: str
    passed: bool
    summary: str
    output: str

# 31. build.run
class BuildRunInput(BaseModel):
    command: str = Field("python -m build", description="Approved build command")

class BuildRunOutput(BaseModel):
    command: str
    success: bool
    output: str

# 32. android.apps.open
class AndroidAppsOpenInput(BaseModel):
    app_name: str = Field(..., description="App name or package (e.g. 'camera', 'whatsapp', 'clock')")

class AndroidAppsOpenOutput(BaseModel):
    app_name: str
    opened: bool
    message: str

# 33. android.notifications.read
class AndroidNotificationsReadInput(BaseModel):
    limit: int = Field(10, description="Max notifications to read")

class AndroidNotificationsReadOutput(BaseModel):
    notifications: List[Dict[str, str]]
    total_count: int

# 34. android.screen.capture
class AndroidScreenCaptureInput(BaseModel):
    pull_to_pc: bool = Field(False, description="Whether to copy screenshot to PC")

class AndroidScreenCaptureOutput(BaseModel):
    captured: bool
    device_path: str
    local_path: Optional[str] = None

# 35. android.permissions.status
class AndroidPermissionsStatusInput(BaseModel):
    pass

class AndroidPermissionsStatusOutput(BaseModel):
    connected: bool
    serial: str
    model: str
    granted_permissions: List[str]

# 36. devices.list
class DevicesListInput(BaseModel):
    pass

class DevicesListOutput(BaseModel):
    devices: List[Dict[str, Any]]
    total_devices: int

# 37. devices.status
class DevicesStatusInput(BaseModel):
    device_id: str = Field(..., description="Device ID ('windows-primary' or 'android-companion')")

class DevicesStatusOutput(BaseModel):
    device_id: str
    online: bool
    battery: Optional[str] = None
    details: Dict[str, Any]

# 38. workflow.create
class WorkflowCreateInput(BaseModel):
    name: str = Field(..., description="Workflow title")
    steps: List[Dict[str, Any]] = Field(..., description="Ordered list of tool executions")

class WorkflowCreateOutput(BaseModel):
    workflow_id: str
    name: str
    total_steps: int
    status: str

# 39. workflow.run
class WorkflowRunInput(BaseModel):
    workflow_id: str = Field(..., description="Workflow identifier to execute")

class WorkflowRunOutput(BaseModel):
    workflow_id: str
    status: str
    completed_steps: int
    results: List[Dict[str, Any]]

# 40. workflow.pause
class WorkflowPauseInput(BaseModel):
    workflow_id: str = Field(..., description="Workflow identifier")

class WorkflowPauseOutput(BaseModel):
    workflow_id: str
    paused: bool

# 41. workflow.cancel
class WorkflowCancelInput(BaseModel):
    workflow_id: str = Field(..., description="Workflow identifier")

class WorkflowCancelOutput(BaseModel):
    workflow_id: str
    cancelled: bool

# 42. safety.stop
class SafetyStopInput(BaseModel):
    reason: str = Field("User initiated safety stop", description="Reason for stopping")

class SafetyStopOutput(BaseModel):
    stopped: bool
    reason: str
    timestamp: float

# 43. safety.status
class SafetyStatusInput(BaseModel):
    pass

class SafetyStatusOutput(BaseModel):
    is_stopped: bool
    reason: str
    stopped_by: str

# 44. safety.resume
class SafetyResumeInput(BaseModel):
    user: str = Field("Luffy", description="User resuming automation")

class SafetyResumeOutput(BaseModel):
    resumed: bool
    user: str

