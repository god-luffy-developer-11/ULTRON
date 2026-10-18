"""Windows UI Automation and system operator functions for ULTRON."""
import os
import psutil
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from tools.pc_control import get_desktop_dir, get_documents_dir

APPROVED_ROOTS = [
    Path(r"c:\Users\surya\Downloads\ULTRON").resolve(),
    Path(r"c:\Users\surya\Desktop").resolve(),
    Path(r"c:\Users\surya\Downloads").resolve(),
    Path(r"c:\Users\surya\Documents").resolve(),
    get_desktop_dir().resolve(),
    get_documents_dir().resolve()
]

def is_path_approved(target_path: Path) -> bool:
    resolved = target_path.resolve()
    for root in APPROVED_ROOTS:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False

def list_installed_apps(limit: int = 50) -> List[str]:
    """List common applications installed or available on Windows."""
    apps = [
        "notepad", "calculator", "chrome", "brave", "edge", "spotify", 
        "discord", "code", "explorer", "powershell", "cmd", "taskmgr"
    ]
    # Check running processes to find active desktop apps
    running = set()
    for p in psutil.process_iter(['name']):
        try:
            name = p.info['name']
            if name and name.endswith('.exe'):
                running.add(name[:-4].lower())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    combined = apps + [r for r in sorted(list(running)) if r not in apps]
    return combined[:limit]

def close_app_by_name(process_name: str) -> bool:
    """Close an application process cleanly."""
    clean = process_name.lower().replace(".exe", "").strip()
    closed = False
    for p in psutil.process_iter(['name', 'pid']):
        try:
            p_name = p.info['name'].lower().replace(".exe", "")
            if clean in p_name:
                p.terminate()
                closed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return closed

def list_desktop_windows() -> List[str]:
    """List open top-level window titles using Windows PowerShell."""
    ps_cmd = 'Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | Select-Object -ExpandProperty MainWindowTitle'
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        titles = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        return titles
    except Exception:
        return []

def focus_desktop_window(window_title: str) -> bool:
    """Bring a desktop window to the foreground."""
    ps_cmd = f'''
    $w = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{window_title}*"}} | Select-Object -First 1
    if ($w) {{
        $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
        $type = Add-Type -MemberDefinition $sig -Name Win32SetForegroundWindow -Namespace Win32 -PassThru
        $type::SetForegroundWindow($w.MainWindowHandle)
        "focused"
    }} else {{
        "not_found"
    }}
    '''
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)
        return "focused" in res.stdout
    except Exception:
        return False

def search_files_in_directory(directory: str, pattern: str, max_results: int = 50) -> List[str]:
    p = Path(directory)
    if not is_path_approved(p):
        raise PermissionError(f"Directory '{p}' is outside approved directories.")
    if not p.exists() or not p.is_dir():
        return []
    matches = []
    for f in p.rglob(pattern):
        matches.append(str(f))
        if len(matches) >= max_results:
            break
    return matches

def organize_folder_by_type(directory_path: str, dry_run: bool = False) -> Dict[str, Any]:
    p = Path(directory_path)
    if not is_path_approved(p):
        raise PermissionError(f"Directory '{p}' is outside approved directories.")
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Folder '{p}' not found.")
    
    categories = {
        "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".md", ".csv"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"],
        "Audio_Video": [".mp3", ".mp4", ".wav", ".mkv", ".mov", ".avi"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Code_Scripts": [".py", ".js", ".ts", ".html", ".css", ".json", ".bat", ".ps1"]
    }
    
    summary = {cat: 0 for cat in categories}
    summary["Other"] = 0
    moved_count = 0
    
    for item in p.iterdir():
        if item.is_file():
            ext = item.suffix.lower()
            target_cat = "Other"
            for cat, exts in categories.items():
                if ext in exts:
                    target_cat = cat
                    break
            
            summary[target_cat] += 1
            moved_count += 1
            if not dry_run:
                target_folder = p / target_cat
                target_folder.mkdir(exist_ok=True)
                dest = target_folder / item.name
                if not dest.exists():
                    item.rename(dest)
    
    return {
        "directory": str(p),
        "moved_count": moved_count,
        "dry_run": dry_run,
        "summary": summary
    }

def inspect_process_status(process_name: str) -> Dict[str, Any]:
    clean = process_name.lower().replace(".exe", "").strip()
    instances = 0
    total_mem = 0.0
    total_cpu = 0.0
    for p in psutil.process_iter(['name', 'memory_info', 'cpu_percent']):
        try:
            p_name = p.info['name'].lower().replace(".exe", "")
            if clean in p_name:
                instances += 1
                total_mem += p.info['memory_info'].rss / (1024 * 1024)
                total_cpu += p.info['cpu_percent'] or 0.0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {
        "process_name": process_name,
        "running": instances > 0,
        "instances": instances,
        "memory_mb": round(total_mem, 2),
        "cpu_percent": round(total_cpu, 2)
    }

def inspect_project_repo(project_path: str) -> Dict[str, Any]:
    p = Path(project_path)
    if not is_path_approved(p):
        raise PermissionError(f"Project '{p}' is outside approved directories.")
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Project path '{p}' not found.")
    
    file_types: Dict[str, int] = {}
    total_files = 0
    for root, dirs, files in os.walk(p):
        # Skip .git and venv
        if ".git" in dirs: dirs.remove(".git")
        if ".venv" in dirs: dirs.remove(".venv")
        if "__pycache__" in dirs: dirs.remove("__pycache__")
        for f in files:
            ext = Path(f).suffix.lower() or "no_ext"
            file_types[ext] = file_types.get(ext, 0) + 1
            total_files += 1

    git_status = None
    git_dir = p / ".git"
    if git_dir.exists():
        try:
            res = subprocess.run(["git", "status", "-s"], cwd=str(p), capture_output=True, text=True, timeout=5)
            git_status = res.stdout.strip() or "clean"
        except Exception:
            git_status = "git_installed_but_unreachable"
            
    return {
        "project_path": str(p),
        "file_types": file_types,
        "git_status": git_status,
        "total_files": total_files
    }
