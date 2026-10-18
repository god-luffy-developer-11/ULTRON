"""Permission scopes for ULTRON capabilities."""
from enum import Enum
from typing import Set

class Scope(str, Enum):
    SYSTEM_READ = "system:read"
    SYSTEM_CONTROL = "system:control"
    APPS_OPEN = "apps:open"
    APPS_LIST = "apps:list"
    APPS_CLOSE = "apps:close"
    WINDOWS_LIST = "windows:list"
    WINDOWS_FOCUS = "windows:focus"
    FILES_READ = "files:read"
    FILES_WRITE = "files:write"
    FILES_SEARCH = "files:search"
    FILES_ORGANIZE = "files:organize"
    BROWSER_SEARCH = "browser:search"
    BROWSER_NAVIGATE = "browser:navigate"
    BROWSER_INSPECT = "browser:inspect"
    SCREEN_CAPTURE = "screen:capture"
    SCREEN_OCR = "screen:ocr"
    SCREEN_SUMMARIZE = "screen:summarize"
    PROCESS_LIST = "process:list"
    PROCESS_STATUS = "process:status"
    PROJECT_INSPECT = "project:inspect"
    CODE_EDIT = "code:edit"
    TESTS_RUN = "tests:run"
    BUILD_RUN = "build:run"
    ANDROID_APPS_OPEN = "android:apps:open"
    ANDROID_NOTIFICATIONS_READ = "android:notifications:read"
    ANDROID_SCREEN_CAPTURE = "android:screen:capture"
    ANDROID_PERMISSIONS_STATUS = "android:permissions:status"
    DEVICES_LIST = "devices:list"
    DEVICES_STATUS = "devices:status"
    WORKFLOW_MANAGE = "workflow:manage"
    SAFETY_STOP = "safety:stop"
    VOICE_SPEAK = "voice:speak"
    NOTIFICATIONS_READ = "notifications:read"
    MESSAGES_DRAFT = "messages:draft"
    MESSAGES_SEND = "messages:send"
    JOBS_MANAGE = "jobs:manage"
    HOME_CONTROL = "home:control"
    SHELL_EXECUTE = "shell:execute"

# Default scopes granted to local primary user session
DEFAULT_USER_SCOPES: Set[str] = {
    Scope.SYSTEM_READ.value,
    Scope.SYSTEM_CONTROL.value,
    Scope.APPS_OPEN.value,
    Scope.APPS_LIST.value,
    Scope.APPS_CLOSE.value,
    Scope.WINDOWS_LIST.value,
    Scope.WINDOWS_FOCUS.value,
    Scope.FILES_READ.value,
    Scope.FILES_WRITE.value,
    Scope.FILES_SEARCH.value,
    Scope.FILES_ORGANIZE.value,
    Scope.BROWSER_SEARCH.value,
    Scope.BROWSER_NAVIGATE.value,
    Scope.BROWSER_INSPECT.value,
    Scope.SCREEN_CAPTURE.value,
    Scope.SCREEN_OCR.value,
    Scope.SCREEN_SUMMARIZE.value,
    Scope.PROCESS_LIST.value,
    Scope.PROCESS_STATUS.value,
    Scope.PROJECT_INSPECT.value,
    Scope.CODE_EDIT.value,
    Scope.TESTS_RUN.value,
    Scope.BUILD_RUN.value,
    Scope.ANDROID_APPS_OPEN.value,
    Scope.ANDROID_NOTIFICATIONS_READ.value,
    Scope.ANDROID_SCREEN_CAPTURE.value,
    Scope.ANDROID_PERMISSIONS_STATUS.value,
    Scope.DEVICES_LIST.value,
    Scope.DEVICES_STATUS.value,
    Scope.WORKFLOW_MANAGE.value,
    Scope.SAFETY_STOP.value,
    Scope.VOICE_SPEAK.value,
    Scope.MESSAGES_DRAFT.value,
    Scope.JOBS_MANAGE.value,
}
