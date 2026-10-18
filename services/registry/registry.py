"""Tool Registry for typed, risk-classified tools in ULTRON."""
from dataclasses import dataclass
from typing import Dict, Any, Type, Callable, List, Optional
from pydantic import BaseModel
from services.policy.risk import RiskTier
from services.policy.scopes import Scope
import services.registry.schemas as schemas

@dataclass
class RegisteredTool:
    tool_id: str
    version: str
    description: str
    risk: RiskTier
    required_scopes: List[str]
    allowed_devices: List[str]
    input_schema: Type[BaseModel]
    output_schema: Type[BaseModel]
    handler: Optional[Callable[[BaseModel], Any]] = None
    enabled: bool = True

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}
        self._register_default_tools()

    def register_tool(self, tool: RegisteredTool):
        """Register a tool. Rejects duplicate tool IDs."""
        if tool.tool_id in self._tools:
            raise ValueError(f"Duplicate tool ID: '{tool.tool_id}' is already registered.")
        self._tools[tool.tool_id] = tool
        print(f"[Registry] Registered tool: {tool.tool_id} (Risk: {tool.risk.value})")

    def get_tool(self, tool_id: str) -> Optional[RegisteredTool]:
        tool = self._tools.get(tool_id)
        if tool and tool.enabled:
            return tool
        return None

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "tool_id": t.tool_id,
                "version": t.version,
                "description": t.description,
                "risk": t.risk.value,
                "required_scopes": t.required_scopes,
                "allowed_devices": t.allowed_devices,
                "enabled": t.enabled
            }
            for t in self._tools.values()
        ]

    def validate_input(self, tool_id: str, raw_args: Dict[str, Any]) -> BaseModel:
        tool = self.get_tool(tool_id)
        if not tool:
            raise KeyError(f"Tool '{tool_id}' not found in registry.")
        return tool.input_schema(**raw_args)

    def _register_default_tools(self):
        # 1. system.get_status (R0)
        self.register_tool(RegisteredTool(
            tool_id="system.get_status",
            version="1.0",
            description="Read CPU, memory, battery, uptime, and device status.",
            risk=RiskTier.R0,
            required_scopes=[Scope.SYSTEM_READ.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.SystemGetStatusInput,
            output_schema=schemas.SystemGetStatusOutput
        ))

        # 2. apps.open (R1)
        self.register_tool(RegisteredTool(
            tool_id="apps.open",
            version="1.0",
            description="Open an allowlisted Windows app or Android intent.",
            risk=RiskTier.R1,
            required_scopes=[Scope.APPS_OPEN.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.AppsOpenInput,
            output_schema=schemas.AppsOpenOutput
        ))

        # 3. files.list (R0)
        self.register_tool(RegisteredTool(
            tool_id="files.list",
            version="1.0",
            description="List files in approved workspace directories.",
            risk=RiskTier.R0,
            required_scopes=[Scope.FILES_READ.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.FilesListInput,
            output_schema=schemas.FilesListOutput
        ))

        # 4. files.read (R0)
        self.register_tool(RegisteredTool(
            tool_id="files.read",
            version="1.0",
            description="Read text file within approved directories.",
            risk=RiskTier.R0,
            required_scopes=[Scope.FILES_READ.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.FilesReadInput,
            output_schema=schemas.FilesReadOutput
        ))

        # 5. files.edit (R2)
        self.register_tool(RegisteredTool(
            tool_id="files.edit",
            version="1.0",
            description="Edit file with diff preview, backup, and approval.",
            risk=RiskTier.R2,
            required_scopes=[Scope.FILES_WRITE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.FilesEditInput,
            output_schema=schemas.FilesEditOutput
        ))

        # 6. browser.search (R0)
        self.register_tool(RegisteredTool(
            tool_id="browser.search",
            version="1.0",
            description="Search the web and preserve source URLs.",
            risk=RiskTier.R0,
            required_scopes=[Scope.BROWSER_SEARCH.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.BrowserSearchInput,
            output_schema=schemas.BrowserSearchOutput
        ))

        # 7. browser.navigate (R1)
        self.register_tool(RegisteredTool(
            tool_id="browser.navigate",
            version="1.0",
            description="Navigate approved URL in browser.",
            risk=RiskTier.R1,
            required_scopes=[Scope.BROWSER_NAVIGATE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.BrowserNavigateInput,
            output_schema=schemas.BrowserNavigateOutput
        ))

        # 8. screen.capture (R2)
        self.register_tool(RegisteredTool(
            tool_id="screen.capture",
            version="1.0",
            description="Capture screen with consent.",
            risk=RiskTier.R2,
            required_scopes=[Scope.SCREEN_CAPTURE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.ScreenCaptureInput,
            output_schema=schemas.ScreenCaptureOutput
        ))

        # 9. voice.speak (R1)
        self.register_tool(RegisteredTool(
            tool_id="voice.speak",
            version="1.0",
            description="Speak aloud text using ElevenLabs or Edge TTS in English or Tamil.",
            risk=RiskTier.R1,
            required_scopes=[Scope.VOICE_SPEAK.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.VoiceSpeakInput,
            output_schema=schemas.VoiceSpeakOutput
        ))

        # 10. messages.prepare (R1)
        self.register_tool(RegisteredTool(
            tool_id="messages.prepare",
            version="1.0",
            description="Draft a message without sending.",
            risk=RiskTier.R1,
            required_scopes=[Scope.MESSAGES_DRAFT.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.MessagesPrepareInput,
            output_schema=schemas.MessagesPrepareOutput
        ))

        # 11. messages.send (R3)
        self.register_tool(RegisteredTool(
            tool_id="messages.send",
            version="1.0",
            description="Send a message (Requires fresh explicit confirmation).",
            risk=RiskTier.R3,
            required_scopes=[Scope.MESSAGES_SEND.value],
            allowed_devices=["android-companion"],
            input_schema=schemas.MessagesSendInput,
            output_schema=schemas.MessagesSendOutput
        ))

        # 12. jobs.create (R2)
        self.register_tool(RegisteredTool(
            tool_id="jobs.create",
            version="1.0",
            description="Create bounded background job schedule.",
            risk=RiskTier.R2,
            required_scopes=[Scope.JOBS_MANAGE.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.JobsCreateInput,
            output_schema=schemas.JobsCreateOutput
        ))

        # 13. home.device_control (R2)
        self.register_tool(RegisteredTool(
            tool_id="home.device_control",
            version="1.0",
            description="Control allowlisted smart home device.",
            risk=RiskTier.R2,
            required_scopes=[Scope.HOME_CONTROL.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.HomeDeviceControlInput,
            output_schema=schemas.HomeDeviceControlOutput
        ))

        # 14. system.command (R3) - Disabled by default
        self.register_tool(RegisteredTool(
            tool_id="system.command",
            version="1.0",
            description="Arbitrary shell execution (Disabled by default as safety non-goal).",
            risk=RiskTier.R3,
            required_scopes=[Scope.SHELL_EXECUTE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.SystemCommandInput,
            output_schema=schemas.SystemCommandOutput,
            enabled=False
        ))

        # 15. apps.list (R0)
        self.register_tool(RegisteredTool(
            tool_id="apps.list",
            version="1.0",
            description="List installed/available applications.",
            risk=RiskTier.R0,
            required_scopes=[Scope.APPS_LIST.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.AppsListInput,
            output_schema=schemas.AppsListOutput
        ))

        # 16. apps.close (R1)
        self.register_tool(RegisteredTool(
            tool_id="apps.close",
            version="1.0",
            description="Close an application process.",
            risk=RiskTier.R1,
            required_scopes=[Scope.APPS_CLOSE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.AppsCloseInput,
            output_schema=schemas.AppsCloseOutput
        ))

        # 17. windows.list (R0)
        self.register_tool(RegisteredTool(
            tool_id="windows.list",
            version="1.0",
            description="List active desktop window titles.",
            risk=RiskTier.R0,
            required_scopes=[Scope.WINDOWS_LIST.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.WindowsListInput,
            output_schema=schemas.WindowsListOutput
        ))

        # 18. windows.focus (R1)
        self.register_tool(RegisteredTool(
            tool_id="windows.focus",
            version="1.0",
            description="Bring specific window to foreground.",
            risk=RiskTier.R1,
            required_scopes=[Scope.WINDOWS_FOCUS.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.WindowsFocusInput,
            output_schema=schemas.WindowsFocusOutput
        ))

        # 19. files.search (R0)
        self.register_tool(RegisteredTool(
            tool_id="files.search",
            version="1.0",
            description="Search files in approved folders by pattern.",
            risk=RiskTier.R0,
            required_scopes=[Scope.FILES_SEARCH.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.FilesSearchInput,
            output_schema=schemas.FilesSearchOutput
        ))

        # 20. files.create (R2)
        self.register_tool(RegisteredTool(
            tool_id="files.create",
            version="1.0",
            description="Create new file in approved directories.",
            risk=RiskTier.R2,
            required_scopes=[Scope.FILES_WRITE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.FilesCreateInput,
            output_schema=schemas.FilesCreateOutput
        ))

        # 21. files.organize (R2)
        self.register_tool(RegisteredTool(
            tool_id="files.organize",
            version="1.0",
            description="Organize folder files into categories.",
            risk=RiskTier.R2,
            required_scopes=[Scope.FILES_ORGANIZE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.FilesOrganizeInput,
            output_schema=schemas.FilesOrganizeOutput
        ))

        # 22. browser.open (R1)
        self.register_tool(RegisteredTool(
            tool_id="browser.open",
            version="1.0",
            description="Open URL in default web browser.",
            risk=RiskTier.R1,
            required_scopes=[Scope.BROWSER_NAVIGATE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.BrowserOpenInput,
            output_schema=schemas.BrowserOpenOutput
        ))

        # 23. browser.inspect (R0)
        self.register_tool(RegisteredTool(
            tool_id="browser.inspect",
            version="1.0",
            description="Inspect/read web page text content.",
            risk=RiskTier.R0,
            required_scopes=[Scope.BROWSER_INSPECT.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.BrowserInspectInput,
            output_schema=schemas.BrowserInspectOutput
        ))

        # 24. screen.ocr (R1)
        self.register_tool(RegisteredTool(
            tool_id="screen.ocr",
            version="1.0",
            description="Extract text from screen capture using OCR.",
            risk=RiskTier.R1,
            required_scopes=[Scope.SCREEN_OCR.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.ScreenOcrInput,
            output_schema=schemas.ScreenOcrOutput
        ))

        # 25. screen.summarize (R1)
        self.register_tool(RegisteredTool(
            tool_id="screen.summarize",
            version="1.0",
            description="Summarize visible screen and active window context.",
            risk=RiskTier.R1,
            required_scopes=[Scope.SCREEN_SUMMARIZE.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.ScreenSummarizeInput,
            output_schema=schemas.ScreenSummarizeOutput
        ))

        # 26. process.list (R0)
        self.register_tool(RegisteredTool(
            tool_id="process.list",
            version="1.0",
            description="List running processes and resource usage.",
            risk=RiskTier.R0,
            required_scopes=[Scope.PROCESS_LIST.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.ProcessListInput,
            output_schema=schemas.ProcessListOutput
        ))

        # 27. process.status (R0)
        self.register_tool(RegisteredTool(
            tool_id="process.status",
            version="1.0",
            description="Check process status, memory, and CPU.",
            risk=RiskTier.R0,
            required_scopes=[Scope.PROCESS_STATUS.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.ProcessStatusInput,
            output_schema=schemas.ProcessStatusOutput
        ))

        # 28. project.inspect (R0)
        self.register_tool(RegisteredTool(
            tool_id="project.inspect",
            version="1.0",
            description="Inspect project structure, files, and git status.",
            risk=RiskTier.R0,
            required_scopes=[Scope.PROJECT_INSPECT.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.ProjectInspectInput,
            output_schema=schemas.ProjectInspectOutput
        ))

        # 29. code.edit (R2)
        self.register_tool(RegisteredTool(
            tool_id="code.edit",
            version="1.0",
            description="Edit code snippet with verification and backup.",
            risk=RiskTier.R2,
            required_scopes=[Scope.CODE_EDIT.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.CodeEditInput,
            output_schema=schemas.CodeEditOutput
        ))

        # 30. tests.run (R1)
        self.register_tool(RegisteredTool(
            tool_id="tests.run",
            version="1.0",
            description="Run pytest test suite in repository.",
            risk=RiskTier.R1,
            required_scopes=[Scope.TESTS_RUN.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.TestsRunInput,
            output_schema=schemas.TestsRunOutput
        ))

        # 31. build.run (R2)
        self.register_tool(RegisteredTool(
            tool_id="build.run",
            version="1.0",
            description="Run approved build workflow.",
            risk=RiskTier.R2,
            required_scopes=[Scope.BUILD_RUN.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.BuildRunInput,
            output_schema=schemas.BuildRunOutput
        ))

        # 32. android.apps.open (R1)
        self.register_tool(RegisteredTool(
            tool_id="android.apps.open",
            version="1.0",
            description="Launch application or intent on Android phone.",
            risk=RiskTier.R1,
            required_scopes=[Scope.ANDROID_APPS_OPEN.value],
            allowed_devices=["android-companion"],
            input_schema=schemas.AndroidAppsOpenInput,
            output_schema=schemas.AndroidAppsOpenOutput
        ))

        # 33. android.notifications.read (R1)
        self.register_tool(RegisteredTool(
            tool_id="android.notifications.read",
            version="1.0",
            description="Read permitted Android notifications.",
            risk=RiskTier.R1,
            required_scopes=[Scope.ANDROID_NOTIFICATIONS_READ.value],
            allowed_devices=["android-companion"],
            input_schema=schemas.AndroidNotificationsReadInput,
            output_schema=schemas.AndroidNotificationsReadOutput
        ))

        # 34. android.screen.capture (R2)
        self.register_tool(RegisteredTool(
            tool_id="android.screen.capture",
            version="1.0",
            description="Capture Android screen with consent.",
            risk=RiskTier.R2,
            required_scopes=[Scope.ANDROID_SCREEN_CAPTURE.value],
            allowed_devices=["android-companion"],
            input_schema=schemas.AndroidScreenCaptureInput,
            output_schema=schemas.AndroidScreenCaptureOutput
        ))

        # 35. android.permissions.status (R0)
        self.register_tool(RegisteredTool(
            tool_id="android.permissions.status",
            version="1.0",
            description="Inspect Android companion connection and permissions.",
            risk=RiskTier.R0,
            required_scopes=[Scope.ANDROID_PERMISSIONS_STATUS.value],
            allowed_devices=["android-companion"],
            input_schema=schemas.AndroidPermissionsStatusInput,
            output_schema=schemas.AndroidPermissionsStatusOutput
        ))

        # 36. devices.list (R0)
        self.register_tool(RegisteredTool(
            tool_id="devices.list",
            version="1.0",
            description="List registered paired devices (PC and Android).",
            risk=RiskTier.R0,
            required_scopes=[Scope.DEVICES_LIST.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.DevicesListInput,
            output_schema=schemas.DevicesListOutput
        ))

        # 37. devices.status (R0)
        self.register_tool(RegisteredTool(
            tool_id="devices.status",
            version="1.0",
            description="Check connectivity and health of specific device.",
            risk=RiskTier.R0,
            required_scopes=[Scope.DEVICES_STATUS.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.DevicesStatusInput,
            output_schema=schemas.DevicesStatusOutput
        ))

        # 38. workflow.create (R1)
        self.register_tool(RegisteredTool(
            tool_id="workflow.create",
            version="1.0",
            description="Create a multi-step task plan across devices.",
            risk=RiskTier.R1,
            required_scopes=[Scope.WORKFLOW_MANAGE.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.WorkflowCreateInput,
            output_schema=schemas.WorkflowCreateOutput
        ))

        # 39. workflow.run (R2)
        self.register_tool(RegisteredTool(
            tool_id="workflow.run",
            version="1.0",
            description="Execute multi-step workflow with verification.",
            risk=RiskTier.R2,
            required_scopes=[Scope.WORKFLOW_MANAGE.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.WorkflowRunInput,
            output_schema=schemas.WorkflowRunOutput
        ))

        # 40. workflow.pause (R1)
        self.register_tool(RegisteredTool(
            tool_id="workflow.pause",
            version="1.0",
            description="Pause active workflow execution.",
            risk=RiskTier.R1,
            required_scopes=[Scope.WORKFLOW_MANAGE.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.WorkflowPauseInput,
            output_schema=schemas.WorkflowPauseOutput
        ))

        # 41. workflow.cancel (R1)
        self.register_tool(RegisteredTool(
            tool_id="workflow.cancel",
            version="1.0",
            description="Cancel active workflow execution.",
            risk=RiskTier.R1,
            required_scopes=[Scope.WORKFLOW_MANAGE.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.WorkflowCancelInput,
            output_schema=schemas.WorkflowCancelOutput
        ))

        # 42. safety.stop (R0)
        self.register_tool(RegisteredTool(
            tool_id="safety.stop",
            version="1.0",
            description="Trigger persistent emergency stop.",
            risk=RiskTier.R0,
            required_scopes=[Scope.SAFETY_STOP.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.SafetyStopInput,
            output_schema=schemas.SafetyStopOutput
        ))

        # 43. safety.status (R0)
        self.register_tool(RegisteredTool(
            tool_id="safety.status",
            version="1.0",
            description="Get emergency stop safety status.",
            risk=RiskTier.R0,
            required_scopes=[Scope.SAFETY_STOP.value],
            allowed_devices=["windows-primary", "android-companion"],
            input_schema=schemas.SafetyStatusInput,
            output_schema=schemas.SafetyStatusOutput
        ))

        # 44. safety.resume (R2)
        self.register_tool(RegisteredTool(
            tool_id="safety.resume",
            version="1.0",
            description="Resume automation after emergency stop.",
            risk=RiskTier.R2,
            required_scopes=[Scope.SAFETY_STOP.value],
            allowed_devices=["windows-primary"],
            input_schema=schemas.SafetyResumeInput,
            output_schema=schemas.SafetyResumeOutput
        ))

tool_registry = ToolRegistry()

# Connect handlers
from services.registry.handlers import register_all_handlers
register_all_handlers(tool_registry)

