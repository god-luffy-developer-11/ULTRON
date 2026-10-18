"""Unit tests for Windows device agent automation."""
import pytest
from pathlib import Path
from services.devices.windows_agent import (
    list_installed_apps,
    list_desktop_windows,
    search_files_in_directory,
    organize_folder_by_type,
    inspect_process_status,
    inspect_project_repo
)

def test_list_installed_apps():
    apps = list_installed_apps(limit=10)
    assert isinstance(apps, list)
    assert len(apps) > 0
    assert any(a in apps for a in ["notepad", "calculator", "explorer", "cmd", "powershell", "python"])

def test_list_desktop_windows():
    wins = list_desktop_windows()
    assert isinstance(wins, list)

def test_search_files_in_directory():
    matches = search_files_in_directory(r"c:\Users\surya\Downloads\ULTRON", "*.py", max_results=5)
    assert isinstance(matches, list)
    assert len(matches) > 0
    assert any("brain.py" in m or "main.py" in m for m in matches)

def test_organize_folder_dry_run():
    res = organize_folder_by_type(r"c:\Users\surya\Downloads\ULTRON", dry_run=True)
    assert res["dry_run"] is True
    assert "summary" in res
    assert "Code_Scripts" in res["summary"]

def test_inspect_process_status():
    stat = inspect_process_status("python")
    assert stat["process_name"] == "python"
    assert stat["running"] is True
    assert stat["instances"] >= 1

def test_inspect_project_repo():
    res = inspect_project_repo(r"c:\Users\surya\Downloads\ULTRON")
    assert res["project_path"].lower() == str(Path(r"c:\Users\surya\Downloads\ULTRON").resolve()).lower()
    assert ".py" in res["file_types"]
    assert res["total_files"] > 10
