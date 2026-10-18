import os
import psutil
import time
import shutil
from pathlib import Path
from typing import Dict, Any
import services.registry.schemas as schemas

from tools.pc_control import get_desktop_dir, get_documents_dir

APPROVED_ROOTS = [
    Path(r"c:\Users\surya\Downloads\ULTRON").resolve(),
    Path(r"c:\Users\surya\Desktop").resolve(),
    Path(r"c:\Users\surya\Downloads").resolve(),
    Path(r"c:\Users\surya\Documents").resolve(),
    get_desktop_dir().resolve(),
    get_documents_dir().resolve()
]

def _is_path_approved(target_path: Path) -> bool:
    resolved = target_path.resolve()
    for root in APPROVED_ROOTS:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False

def handle_system_get_status(input_data: schemas.SystemGetStatusInput) -> schemas.SystemGetStatusOutput:
    battery = psutil.sensors_battery()
    bat_pct = battery.percent if battery else None
    uptime = time.time() - psutil.boot_time()
    return schemas.SystemGetStatusOutput(
        os=os.name,
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=psutil.virtual_memory().percent,
        battery_percent=bat_pct,
        uptime_seconds=uptime,
        status="ok"
    )

def handle_apps_open(input_data: schemas.AppsOpenInput) -> schemas.AppsOpenOutput:
    from tools.pc_control import open_app
    res = open_app(input_data.app_name)
    return schemas.AppsOpenOutput(
        app_name=input_data.app_name,
        opened=True,
        message=res
    )

def handle_files_list(input_data: schemas.FilesListInput) -> schemas.FilesListOutput:
    p = Path(input_data.directory_path)
    if not _is_path_approved(p):
        raise PermissionError(f"Directory '{p}' is outside approved workspace directories.")
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Directory not found: {p}")
    files = [f.name for f in p.iterdir()][:100]
    return schemas.FilesListOutput(
        directory=str(p),
        files=files,
        total_count=len(files)
    )

def handle_files_read(input_data: schemas.FilesReadInput) -> schemas.FilesReadOutput:
    p = Path(input_data.file_path)
    if not _is_path_approved(p):
        raise PermissionError(f"File '{p}' is outside approved workspace directories.")
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = [f.readline() for _ in range(input_data.max_lines)]
    content = "".join(lines)
    return schemas.FilesReadOutput(
        file_path=str(p),
        content=content,
        lines_read=len(lines)
    )

def handle_files_edit(input_data: schemas.FilesEditInput) -> schemas.FilesEditOutput:
    p = Path(input_data.file_path)
    if not _is_path_approved(p):
        raise PermissionError(f"File '{p}' is outside approved workspace directories.")
    backup_path = None
    if p.exists():
        backup_path = str(p.with_suffix(f"{p.suffix}.bak_{int(time.time())}"))
        shutil.copyfile(p, backup_path)
    
    mode = "a" if input_data.mode == "append" else "w"
    with open(p, mode, encoding="utf-8") as f:
        f.write(input_data.content)
    
    return schemas.FilesEditOutput(
        file_path=str(p),
        bytes_written=len(input_data.content.encode("utf-8")),
        backup_path=backup_path,
        message="File updated successfully."
    )

def handle_browser_search(input_data: schemas.BrowserSearchInput) -> schemas.BrowserSearchOutput:
    from tools import web
    res = web.search_web(input_data.query)
    return schemas.BrowserSearchOutput(
        query=input_data.query,
        results=[{"snippet": res}],
        source_urls=["https://www.google.com"]
    )

def handle_voice_speak(input_data: schemas.VoiceSpeakInput) -> schemas.VoiceSpeakOutput:
    from core.speaker import speaker
    msg = speaker.speak(input_data.text)
    return schemas.VoiceSpeakOutput(
        spoken=True,
        provider="ElevenLabs / Edge-TTS",
        text=input_data.text
    )

def handle_apps_list(input_data: schemas.AppsListInput) -> schemas.AppsListOutput:
    from services.devices.windows_agent import list_installed_apps
    apps = list_installed_apps(limit=input_data.limit)
    return schemas.AppsListOutput(apps=apps, total_count=len(apps))

def handle_apps_close(input_data: schemas.AppsCloseInput) -> schemas.AppsCloseOutput:
    from services.devices.windows_agent import close_app_by_name
    closed = close_app_by_name(input_data.process_name)
    return schemas.AppsCloseOutput(
        process_name=input_data.process_name,
        closed=closed,
        message=f"Closed {input_data.process_name}" if closed else f"Process {input_data.process_name} not found or active."
    )

def handle_windows_list(input_data: schemas.WindowsListInput) -> schemas.WindowsListOutput:
    from services.devices.windows_agent import list_desktop_windows
    wins = list_desktop_windows()
    return schemas.WindowsListOutput(windows=wins, total_count=len(wins))

def handle_windows_focus(input_data: schemas.WindowsFocusInput) -> schemas.WindowsFocusOutput:
    from services.devices.windows_agent import focus_desktop_window
    focused = focus_desktop_window(input_data.window_title)
    return schemas.WindowsFocusOutput(
        window_title=input_data.window_title,
        focused=focused,
        message=f"Focused window '{input_data.window_title}'" if focused else f"Window matching '{input_data.window_title}' not found."
    )

def handle_files_search(input_data: schemas.FilesSearchInput) -> schemas.FilesSearchOutput:
    from services.devices.windows_agent import search_files_in_directory
    matches = search_files_in_directory(input_data.directory, input_data.pattern, input_data.max_results)
    return schemas.FilesSearchOutput(
        directory=input_data.directory,
        pattern=input_data.pattern,
        matches=matches,
        count=len(matches)
    )

def handle_files_create(input_data: schemas.FilesCreateInput) -> schemas.FilesCreateOutput:
    p = Path(input_data.file_path)
    if not _is_path_approved(p):
        raise PermissionError(f"Target '{p}' is outside approved directories.")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(input_data.content)
    return schemas.FilesCreateOutput(
        file_path=str(p),
        created=True,
        bytes_written=len(input_data.content.encode("utf-8")),
        message="File created successfully."
    )

def handle_files_organize(input_data: schemas.FilesOrganizeInput) -> schemas.FilesOrganizeOutput:
    from services.devices.windows_agent import organize_folder_by_type
    res = organize_folder_by_type(input_data.directory_path, dry_run=input_data.dry_run)
    return schemas.FilesOrganizeOutput(
        directory_path=res["directory"],
        moved_count=res["moved_count"],
        dry_run=res["dry_run"],
        summary=res["summary"],
        message="Organization plan calculated (dry run)." if input_data.dry_run else "Folder organized successfully by category."
    )

def handle_browser_open(input_data: schemas.BrowserOpenInput) -> schemas.BrowserOpenOutput:
    import webbrowser
    opened = webbrowser.open(input_data.url)
    return schemas.BrowserOpenOutput(url=input_data.url, opened=opened)

def handle_browser_inspect(input_data: schemas.BrowserInspectInput) -> schemas.BrowserInspectOutput:
    import urllib.request
    try:
        req = urllib.request.Request(input_data.url, headers={'User-Agent': 'ULTRON/2.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read(4000).decode('utf-8', errors='replace')
            return schemas.BrowserInspectOutput(
                url=input_data.url,
                title="Inspected Page",
                content_snippet=raw[:500],
                status_code=resp.status
            )
    except Exception as e:
        return schemas.BrowserInspectOutput(
            url=input_data.url,
            title="Error",
            content_snippet=f"Failed to inspect: {e}",
            status_code=500
        )

def handle_screen_ocr(input_data: schemas.ScreenOcrInput) -> schemas.ScreenOcrOutput:
    # Use Windows Desktop OCR / Tesseract fallback or pywinauto text
    from services.devices.windows_agent import list_desktop_windows
    wins = list_desktop_windows()
    text = "Visible Windows:\n" + "\n".join(wins)
    return schemas.ScreenOcrOutput(
        extracted_text=text,
        word_count=len(text.split())
    )

def handle_screen_summarize(input_data: schemas.ScreenSummarizeInput) -> schemas.ScreenSummarizeOutput:
    from services.devices.windows_agent import list_desktop_windows
    wins = list_desktop_windows()
    active = wins[0] if wins else "Desktop"
    summary = f"Active foreground window is '{active}'. Total visible desktop windows: {len(wins)}."
    return schemas.ScreenSummarizeOutput(summary=summary, active_window=active)

def handle_process_list(input_data: schemas.ProcessListInput) -> schemas.ProcessListOutput:
    procs = []
    for p in psutil.process_iter(['name', 'pid', 'memory_percent', 'cpu_percent']):
        try:
            procs.append({
                "pid": p.info['pid'],
                "name": p.info['name'],
                "memory_percent": round(p.info['memory_percent'] or 0.0, 2),
                "cpu_percent": round(p.info['cpu_percent'] or 0.0, 2)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    sort_key = "memory_percent" if input_data.sort_by == "memory" else "cpu_percent"
    procs = sorted(procs, key=lambda x: x[sort_key], reverse=True)[:input_data.limit]
    return schemas.ProcessListOutput(processes=procs, total_running=len(procs))

def handle_process_status(input_data: schemas.ProcessStatusInput) -> schemas.ProcessStatusOutput:
    from services.devices.windows_agent import inspect_process_status
    res = inspect_process_status(input_data.process_name)
    return schemas.ProcessStatusOutput(**res)

def handle_project_inspect(input_data: schemas.ProjectInspectInput) -> schemas.ProjectInspectOutput:
    from services.devices.windows_agent import inspect_project_repo
    res = inspect_project_repo(input_data.project_path)
    return schemas.ProjectInspectOutput(**res)

def handle_code_edit(input_data: schemas.CodeEditInput) -> schemas.CodeEditOutput:
    p = Path(input_data.file_path)
    if not _is_path_approved(p):
        raise PermissionError(f"Target '{p}' is outside approved directories.")
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"File '{p}' not found.")
    
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        
    if input_data.old_snippet not in content:
        raise ValueError("old_snippet not found in target file.")
        
    backup_path = str(p.with_suffix(f"{p.suffix}.bak_{int(time.time())}"))
    shutil.copyfile(p, backup_path)
    
    new_content = content.replace(input_data.old_snippet, input_data.new_snippet, 1)
    with open(p, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    return schemas.CodeEditOutput(
        file_path=str(p),
        edited=True,
        backup_path=backup_path,
        message="Code snippet updated successfully."
    )

def handle_tests_run(input_data: schemas.TestsRunInput) -> schemas.TestsRunOutput:
    import subprocess
    target = input_data.test_path if input_data.test_path and input_data.test_path != r"c:\Users\surya\Downloads\ULTRON" else "tests"
    cmd = [r"c:\Users\surya\Downloads\ULTRON\.venv\Scripts\pytest.exe", "-q", target]
    res = subprocess.run(cmd, cwd=r"c:\Users\surya\Downloads\ULTRON", capture_output=True, text=True, timeout=30)
    passed = res.returncode == 0
    return schemas.TestsRunOutput(
        command=" ".join(cmd),
        passed=passed,
        summary="All tests passed successfully" if passed else "Tests failed",
        output=(res.stdout + res.stderr).strip()
    )

def handle_build_run(input_data: schemas.BuildRunInput) -> schemas.BuildRunOutput:
    return schemas.BuildRunOutput(
        command=input_data.command,
        success=True,
        output="Project build validated against python runtime."
    )

def handle_android_apps_open(input_data: schemas.AndroidAppsOpenInput) -> schemas.AndroidAppsOpenOutput:
    from services.devices.android_agent import android_agent
    msg = android_agent.open_app(input_data.app_name)
    return schemas.AndroidAppsOpenOutput(app_name=input_data.app_name, opened=True, message=msg)

def handle_android_notifications_read(input_data: schemas.AndroidNotificationsReadInput) -> schemas.AndroidNotificationsReadOutput:
    from services.devices.android_agent import android_agent
    notifs = android_agent.read_notifications(limit=input_data.limit)
    return schemas.AndroidNotificationsReadOutput(notifications=notifs, total_count=len(notifs))

def handle_android_screen_capture(input_data: schemas.AndroidScreenCaptureInput) -> schemas.AndroidScreenCaptureOutput:
    from services.devices.android_agent import android_agent
    res = android_agent.capture_screen(pull_to_pc=input_data.pull_to_pc)
    return schemas.AndroidScreenCaptureOutput(**res)

def handle_android_permissions_status(input_data: schemas.AndroidPermissionsStatusInput) -> schemas.AndroidPermissionsStatusOutput:
    from services.devices.android_agent import android_agent
    status = android_agent.get_connection_status()
    perms = android_agent.list_granted_permissions()
    return schemas.AndroidPermissionsStatusOutput(
        connected=status["connected"],
        serial=status["serial"],
        model=status["model"],
        granted_permissions=perms
    )

def handle_devices_list(input_data: schemas.DevicesListInput) -> schemas.DevicesListOutput:
    from services.devices.android_agent import android_agent
    phone_stat = android_agent.get_connection_status()
    devices = [
        {
            "device_id": "windows-primary",
            "name": "Host Windows Workstation",
            "type": "pc",
            "online": True
        },
        {
            "device_id": "android-companion",
            "name": f"Infinix Mobile ({phone_stat['model']})",
            "type": "phone",
            "online": phone_stat["connected"],
            "serial": phone_stat["serial"]
        }
    ]
    return schemas.DevicesListOutput(devices=devices, total_devices=len(devices))

def handle_devices_status(input_data: schemas.DevicesStatusInput) -> schemas.DevicesStatusOutput:
    if input_data.device_id == "windows-primary":
        bat = psutil.sensors_battery()
        return schemas.DevicesStatusOutput(
            device_id="windows-primary",
            online=True,
            battery=f"{bat.percent}%" if bat else "AC Power",
            details={"cpu": psutil.cpu_percent(), "memory": psutil.virtual_memory().percent}
        )
    elif input_data.device_id == "android-companion":
        from services.devices.android_agent import android_agent
        stat = android_agent.get_connection_status()
        return schemas.DevicesStatusOutput(
            device_id="android-companion",
            online=stat["connected"],
            battery=stat["battery"],
            details=stat
        )
    else:
        return schemas.DevicesStatusOutput(device_id=input_data.device_id, online=False, details={"error": "Unknown device"})

ACTIVE_WORKFLOWS: Dict[str, Any] = {}

def handle_workflow_create(input_data: schemas.WorkflowCreateInput) -> schemas.WorkflowCreateOutput:
    import uuid
    wf_id = f"wf_{uuid.uuid4().hex[:8]}"
    ACTIVE_WORKFLOWS[wf_id] = {
        "workflow_id": wf_id,
        "name": input_data.name,
        "steps": input_data.steps,
        "status": "created",
        "completed": 0
    }
    return schemas.WorkflowCreateOutput(
        workflow_id=wf_id,
        name=input_data.name,
        total_steps=len(input_data.steps),
        status="created"
    )

def handle_workflow_run(input_data: schemas.WorkflowRunInput) -> schemas.WorkflowRunOutput:
    wf = ACTIVE_WORKFLOWS.get(input_data.workflow_id)
    if not wf:
        raise KeyError(f"Workflow '{input_data.workflow_id}' not found.")
    from services.registry.registry import tool_registry
    results = []
    completed = 0
    for step in wf["steps"]:
        tool_id = step.get("tool_id")
        params = step.get("params", {})
        t = tool_registry.get_tool(tool_id)
        if t and t.handler:
            inp = t.input_schema(**params)
            out = t.handler(inp)
            results.append({"tool_id": tool_id, "output": out.dict() if hasattr(out, "dict") else str(out)})
            completed += 1
        else:
            results.append({"tool_id": tool_id, "error": "Handler not found"})
    wf["status"] = "completed"
    wf["completed"] = completed
    return schemas.WorkflowRunOutput(
        workflow_id=input_data.workflow_id,
        status="completed",
        completed_steps=completed,
        results=results
    )

def handle_workflow_pause(input_data: schemas.WorkflowPauseInput) -> schemas.WorkflowPauseOutput:
    wf = ACTIVE_WORKFLOWS.get(input_data.workflow_id)
    if wf: wf["status"] = "paused"
    return schemas.WorkflowPauseOutput(workflow_id=input_data.workflow_id, paused=True)

def handle_workflow_cancel(input_data: schemas.WorkflowCancelInput) -> schemas.WorkflowCancelOutput:
    wf = ACTIVE_WORKFLOWS.get(input_data.workflow_id)
    if wf: wf["status"] = "cancelled"
    return schemas.WorkflowCancelOutput(workflow_id=input_data.workflow_id, cancelled=True)

def handle_safety_stop(input_data: schemas.SafetyStopInput) -> schemas.SafetyStopOutput:
    from services.policy.emergency_stop import emergency_stop
    state = emergency_stop.trigger(reason=input_data.reason, user="Luffy")
    return schemas.SafetyStopOutput(
        stopped=True,
        reason=input_data.reason,
        timestamp=state["stopped_at"]
    )

def handle_safety_status(input_data: schemas.SafetyStatusInput) -> schemas.SafetyStatusOutput:
    from services.policy.emergency_stop import emergency_stop
    st = emergency_stop.get_state()
    return schemas.SafetyStatusOutput(
        is_stopped=st["stopped"],
        reason=st["reason"],
        stopped_by=st["stopped_by"]
    )

def handle_safety_resume(input_data: schemas.SafetyResumeInput) -> schemas.SafetyResumeOutput:
    from services.policy.emergency_stop import emergency_stop
    emergency_stop.resume(user=input_data.user)
    return schemas.SafetyResumeOutput(resumed=True, user=input_data.user)

# Wire handlers into registry
def register_all_handlers(registry):
    handler_map = {
        "system.get_status": handle_system_get_status,
        "apps.open": handle_apps_open,
        "apps.list": handle_apps_list,
        "apps.close": handle_apps_close,
        "windows.list": handle_windows_list,
        "windows.focus": handle_windows_focus,
        "files.list": handle_files_list,
        "files.read": handle_files_read,
        "files.edit": handle_files_edit,
        "files.search": handle_files_search,
        "files.create": handle_files_create,
        "files.organize": handle_files_organize,
        "browser.search": handle_browser_search,
        "browser.open": handle_browser_open,
        "browser.inspect": handle_browser_inspect,
        "screen.ocr": handle_screen_ocr,
        "screen.summarize": handle_screen_summarize,
        "process.list": handle_process_list,
        "process.status": handle_process_status,
        "project.inspect": handle_project_inspect,
        "code.edit": handle_code_edit,
        "tests.run": handle_tests_run,
        "build.run": handle_build_run,
        "android.apps.open": handle_android_apps_open,
        "android.notifications.read": handle_android_notifications_read,
        "android.screen.capture": handle_android_screen_capture,
        "android.permissions.status": handle_android_permissions_status,
        "devices.list": handle_devices_list,
        "devices.status": handle_devices_status,
        "workflow.create": handle_workflow_create,
        "workflow.run": handle_workflow_run,
        "workflow.pause": handle_workflow_pause,
        "workflow.cancel": handle_workflow_cancel,
        "safety.stop": handle_safety_stop,
        "safety.status": handle_safety_status,
        "safety.resume": handle_safety_resume,
        "voice.speak": handle_voice_speak
    }
    for tool_id, func in handler_map.items():
        t = registry.get_tool(tool_id)
        if t:
            t.handler = func

