"""Claude Code hook collector."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..core import Collector, Event, EventType


class ClaudeCodeCollector(Collector):
    """Collector for Claude Code conversations via hooks."""
    
    def __init__(self, hook_dir: Optional[Path] = None):
        """
        Initialize collector.
        
        Args:
            hook_dir: Directory to store hook scripts
        """
        self.hook_dir = hook_dir or Path.home() / ".sayu" / "hooks"
        self.event_file = self.hook_dir / "events.jsonl"
        
    def setup(self) -> None:
        """Set up Claude Code hooks."""
        self.hook_dir.mkdir(parents=True, exist_ok=True)
        
        # Create hook script
        hook_script = self.hook_dir / "claude_code_hook.py"
        hook_script.write_text(self._get_hook_script())
        hook_script.chmod(0o755)
        
        # Create .claude/settings.json in home directory for user-level hooks
        settings_dir = Path.home() / ".claude"
        settings_dir.mkdir(exist_ok=True)
        settings_path = settings_dir / "settings.json"
        
        # Define all 9 Claude Code event types
        event_types = [
            "PreToolUse",
            "PostToolUse",
            "UserPromptSubmit",
            "Stop",
            "SubagentStop",
            "PreCompact",
            "SessionStart",
            "SessionEnd",
            "Notification"
        ]
        
        # Create hook configuration for all event types
        hooks_config = {}
        for event_type in event_types:
            hooks_config[event_type] = [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": str(hook_script)
                        }
                    ]
                }
            ]
        
        settings = {"hooks": hooks_config}
        
        if settings_path.exists():
            # Merge with existing settings
            existing = json.loads(settings_path.read_text())
            existing.setdefault("hooks", {}).update(settings["hooks"])
            settings = existing
        
        settings_path.write_text(json.dumps(settings, indent=2))
        
    def teardown(self) -> None:
        """Remove Claude Code hooks."""
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
            if "hooks" in settings:
                # Remove all event types
                event_types = [
                    "PreToolUse", "PostToolUse", "UserPromptSubmit",
                    "Stop", "SubagentStop", "PreCompact",
                    "SessionStart", "SessionEnd", "Notification"
                ]
                for event_type in event_types:
                    settings["hooks"].pop(event_type, None)
                
                if not settings["hooks"]:
                    del settings["hooks"]
            
            if settings:
                settings_path.write_text(json.dumps(settings, indent=2))
            else:
                settings_path.unlink()
    
    def collect(self, since: Optional[datetime] = None) -> List[Event]:
        """Collect events from Claude Code hooks."""
        if not self.event_file.exists():
            return []
        
        events = []
        with open(self.event_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    
                    if since and timestamp <= since:
                        continue
                    
                    # Map metadata type to EventType
                    metadata = data.get("metadata", {})
                    meta_type = metadata.get("type", "")
                    
                    # Determine event type based on metadata
                    if meta_type == "user_request":
                        event_type = EventType.CONVERSATION
                    elif meta_type == "assistant":
                        event_type = EventType.CONVERSATION  
                    elif meta_type == "tool_use":
                        tool = metadata.get("tool", "")
                        if tool in ["Edit", "Write", "MultiEdit"]:
                            event_type = EventType.FILE_EDIT
                        elif tool in ["Bash"]:
                            event_type = EventType.COMMAND
                        else:
                            event_type = EventType.ACTION
                    else:
                        event_type = EventType.ACTION
                    
                    event = Event(
                        timestamp=timestamp,
                        type=event_type,
                        source=self.name,
                        content=data["content"],
                        metadata=metadata
                    )
                    events.append(event)
                except Exception as e:
                    print(f"Error parsing event: {e}")
                    continue
        
        return events
    
    @property
    def name(self) -> str:
        """Return collector name."""
        return "claude-code"
    
    def _get_hook_script(self) -> str:
        """Generate hook script content."""
        return f'''#!/usr/bin/env python3
"""Claude Code hook script for Sayu."""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def summarize_with_gemini(text, prompt_type="default", context=None):
    """Summarize text using Gemini API."""
    if not text:
        return text
    
    # Always try to summarize, even for short text
    # Create more specific prompts based on context
    if context and context.get("tool_name"):
        tool = context["tool_name"]
        if tool == "Bash":
            command = context.get("command", text)
            prompt = f"""다음 bash 명령어가 수행하는 작업을 한국어로 구체적으로 설명해주세요. 
명령어의 목적, 대상, 예상 결과를 포함해서 설명하되, 2-3문장으로 작성해주세요:
명령어: {{command[:500]}}
응답 형식: [목적] ... [대상] ... [결과] ..."""
        elif tool == "Edit":
            file_name = Path(context.get("file_path", "")).name
            old_str = context.get("old_string", "")[:200]
            new_str = context.get("new_string", "")[:200]
            prompt = f"""{{file_name}} 파일 수정 내용을 한국어로 구체적으로 설명해주세요.
어떤 코드/내용이 어떻게 변경되었는지, 변경 이유가 무엇인지 2-3문장으로 설명해주세요:
변경 전: {{old_str}}
변경 후: {{new_str}}
응답 형식: [변경내용] ... [변경이유] ..."""
        elif tool == "Read":
            file_name = Path(context.get("file_path", "")).name
            prompt = f"""{{file_name}} 파일을 읽는 목적과 맥락을 한국어로 구체적으로 설명해주세요.
무엇을 확인하거나 분석하려는지, 어떤 정보를 찾고 있는지 2-3문장으로 설명해주세요:
파일: {{file_name}}
내용 일부: {{text[:300]}}
응답 형식: [목적] ... [찾는 정보] ..."""
        elif tool == "Grep":
            pattern = context.get("pattern", "")
            path = context.get("path", "")
            prompt = f"""다음 검색 작업의 목적과 맥락을 한국어로 구체적으로 설명해주세요.
무엇을 찾고 있는지, 왜 이 패턴으로 검색하는지 2-3문장으로 설명해주세요:
검색 패턴: {{pattern}}
검색 위치: {{path}}
응답 형식: [검색 목적] ... [찾으려는 것] ..."""
        else:
            prompt = f"""이 작업의 목적과 맥락을 한국어로 구체적으로 설명해주세요.
무엇을 하려는지, 왜 이 작업이 필요한지 2-3문장으로 설명해주세요:
작업 내용: {{text[:500]}}"""
    else:
        prompts = {{
            "user": """사용자의 요청 내용을 한국어로 구체적으로 요약해주세요.
사용자가 무엇을 원하는지, 어떤 문제를 해결하려는지 2-3문장으로 설명해주세요:
요청: """,
            "assistant": """어시스턴트의 응답 내용을 한국어로 구체적으로 요약해주세요.
어떤 해결책을 제시했는지, 무엇을 수행했는지 2-3문장으로 설명해주세요:
응답: """,
            "tool": """도구 사용 목적과 결과를 한국어로 구체적으로 설명해주세요.
왜 이 도구를 사용했는지, 어떤 결과를 얻었는지 2-3문장으로 설명해주세요:
내용: """,
            "default": """다음 내용을 한국어로 구체적으로 요약해주세요.
핵심 내용과 맥락을 2-3문장으로 설명해주세요:
내용: """
        }}
        prompt = prompts.get(prompt_type, prompts["default"]) + text[:500]
    
    # Try Gemini 2.0-flash API
    gemini_api_key = os.environ.get("SAYU_GEMINI_API_KEY", "")
    if gemini_api_key:
        try:
            # Create JSON payload for Gemini API
            import json as json_module
            payload = {{
                "contents": [{{
                    "parts": [{{"text": prompt}}]
                }}],
                "generationConfig": {{
                    "temperature": 0.3,
                    "maxOutputTokens": 200
                }}
            }}
            
            # Call Gemini API using curl with 2.0-flash model
            cmd = [
                "curl", "-s",
                "-X", "POST",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={{gemini_api_key}}",
                "-H", "Content-Type: application/json",
                "-d", json_module.dumps(payload)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                response = json_module.loads(result.stdout)
                if "candidates" in response and response["candidates"]:
                    content = response["candidates"][0]["content"]["parts"][0]["text"]
                    return content.strip()
                elif "error" in response:
                    with open("$HOME/.sayu/hooks/debug.log", "a") as f:
                        f.write(f"Gemini API error: {{response.get('error')}}\\n")
        except Exception as e:
            with open("$HOME/.sayu/hooks/debug.log", "a") as f:
                f.write(f"Gemini summarization error: {{e}}\\n")
    
    # If Gemini fails, return original text with prefix
    # This preserves the original content for later processing
    if context and context.get("tool_name"):
        prefix = get_tool_prefix(context.get("tool_name"))
        return f"{{prefix}} {{text[:200]}}..." if len(text) > 200 else f"{{prefix}} {{text}}"
    
    return text[:200] + "..." if len(text) > 200 else text

def get_tool_prefix(tool_name):
    """Get Korean prefix for tool type."""
    prefixes = {{
        "Bash": "[명령]",
        "Edit": "[편집]",
        "Read": "[읽기]",
        "Write": "[작성]",
        "Grep": "[검색]",
        "MultiEdit": "[다중편집]",
        "Glob": "[파일검색]",
        "LS": "[목록]",
        "Task": "[작업]",
        "TodoWrite": "[할일]",
        "WebFetch": "[웹조회]"
    }}
    return prefixes.get(tool_name, f"[{{tool_name}}]")

def create_manual_summary(text, context):
    """Create manual summary when Gemini is not available."""
    tool = context.get("tool_name", "")
    
    if tool == "Bash":
        command = context.get("command", text)
        if "git" in command:
            if "commit" in command:
                msg = command.split("-m")[-1].strip() if "-m" in command else ""
                return f"Git 커밋을 생성하여 변경사항을 저장합니다. {{f'커밋 메시지: {{msg[:50]}}' if msg else '변경된 파일들을 버전 관리 시스템에 기록합니다.'}}"
            elif "status" in command:
                return "Git 저장소의 현재 상태를 확인합니다. 변경된 파일, 스테이징된 파일, 추적되지 않는 파일들을 파악하여 작업 상황을 점검합니다."
            elif "diff" in command:
                return "Git 변경사항을 상세히 확인합니다. 코드의 추가, 삭제, 수정 내용을 라인 단위로 검토하여 정확한 변경 내역을 파악합니다."
            elif "log" in command:
                return "Git 커밋 히스토리를 조회합니다. 이전 작업 내역과 커밋 메시지를 확인하여 프로젝트의 변경 이력을 추적합니다."
        elif "npm" in command or "yarn" in command:
            if "install" in command:
                pkg = command.split()[-1] if len(command.split()) > 2 else ""
                return f"NPM 패키지를 설치합니다. {{f'{{pkg}} 패키지를 프로젝트에 추가하여' if pkg and pkg != 'install' else '프로젝트의 의존성 패키지들을 설치하여'}} 개발 환경을 구성합니다."
            elif "run" in command:
                script = command.split("run")[-1].strip() if "run" in command else ""
                return f"NPM 스크립트를 실행합니다. {{f'{{script}} 작업을 수행하여' if script else '정의된 작업을 실행하여'}} 빌드, 테스트, 또는 개발 서버를 동작시킵니다."
            elif "test" in command:
                return "테스트 스위트를 실행합니다. 작성된 테스트 케이스들을 실행하여 코드의 정확성과 안정성을 검증합니다."
        elif "sayu" in command:
            if "collect" in command:
                return "Sayu 이벤트 수집을 시작합니다. AI 대화 기록과 작업 내역을 수집하여 데이터베이스에 저장하고 나중에 활용할 수 있도록 준비합니다."
            elif "timeline" in command:
                opts = "-v" if "-v" in command else ""
                return f"Sayu 타임라인을 확인합니다. 수집된 이벤트들을 시간순으로 정렬하여 {{f'상세한 내용과 함께' if opts else '요약된 형태로'}} 작업 흐름을 시각화합니다."
        elif "ls" in command:
            path = command.split()[-1] if len(command.split()) > 1 else "현재"
            return f"{{path}} 디렉토리의 내용을 확인합니다. 파일과 폴더 목록을 조회하여 프로젝트 구조를 파악하고 필요한 파일을 찾습니다."
        elif "rm" in command:
            target = command.split()[-1] if len(command.split()) > 1 else "파일"
            return f"{{target}}을(를) 삭제합니다. 더 이상 필요하지 않은 파일이나 디렉토리를 제거하여 프로젝트를 정리합니다."
        elif "mv" in command:
            parts = command.split()
            return f"파일 또는 디렉토리를 이동합니다. {{f'{{parts[1]}}을(를) {{parts[2]}}로' if len(parts) > 2 else '파일을 새로운 위치로'}} 옮겨 프로젝트 구조를 재구성합니다."
        elif "cp" in command:
            return "파일 또는 디렉토리를 복사합니다. 백업을 생성하거나 유사한 파일을 만들기 위해 기존 파일의 복제본을 생성합니다."
        elif "echo" in command:
            return "텍스트를 출력하거나 파일에 기록합니다. 디버깅 메시지를 표시하거나 설정 파일에 내용을 추가하는 작업을 수행합니다."
        elif "grep" in command or "rg" in command:
            pattern = command.split()[1] if len(command.split()) > 1 else "패턴"
            return f"{{pattern}} 패턴을 검색합니다. 파일 내용에서 특정 텍스트나 패턴을 찾아 코드의 위치를 파악하고 분석합니다."
        return f"명령을 실행합니다: {{command[:50]}}. 시스템 작업을 수행하여 필요한 결과를 얻거나 환경을 설정합니다."
    
    elif tool == "Edit":
        file_name = Path(context.get("file_path", "")).name
        old_str = context.get("old_string", "")
        new_str = context.get("new_string", "")
        
        if "def " in old_str or "def " in new_str:
            func_name = old_str.split("def ")[-1].split("(")[0] if "def " in old_str else new_str.split("def ")[-1].split("(")[0]
            return f"{{file_name}} 파일의 {{func_name}} 함수를 수정합니다. 함수의 로직을 개선하거나 새로운 기능을 추가하여 코드의 동작을 변경합니다."
        elif "class " in old_str or "class " in new_str:
            class_name = old_str.split("class ")[-1].split(":")[0] if "class " in old_str else new_str.split("class ")[-1].split(":")[0]
            return f"{{file_name}} 파일의 {{class_name}} 클래스를 수정합니다. 클래스 구조나 메서드를 변경하여 객체의 동작을 개선합니다."
        elif "import " in old_str or "import " in new_str:
            return f"{{file_name}} 파일의 import 문을 수정합니다. 필요한 모듈을 추가하거나 불필요한 의존성을 제거하여 코드 구조를 정리합니다."
        elif "hook" in file_name.lower():
            return f"훅 스크립트를 개선합니다. 이벤트 처리 로직을 향상시켜 더 정확하고 유용한 정보를 수집하도록 기능을 강화합니다."
        elif "prompt" in old_str.lower() or "prompt" in new_str.lower():
            return f"{{file_name}} 파일의 프롬프트를 개선합니다. 더 명확하고 상세한 지시사항을 제공하여 AI의 응답 품질을 향상시킵니다."
        return f"{{file_name}} 파일을 수정합니다. 코드나 설정을 변경하여 기능을 개선하거나 버그를 수정합니다."
    
    elif tool == "Read":
        file_name = Path(context.get("file_path", "")).name
        if "README" in file_name:
            return "프로젝트 문서를 확인합니다. README 파일을 읽어 프로젝트의 개요, 사용법, 설치 방법 등 중요한 정보를 파악합니다."
        elif ".py" in file_name:
            return f"{{file_name}} Python 코드를 분석합니다. 함수, 클래스, 변수들의 구조와 로직을 파악하여 코드의 동작 방식을 이해합니다."
        elif ".json" in file_name:
            return f"{{file_name}} 설정 파일을 확인합니다. JSON 형식의 구성 정보를 읽어 시스템이나 애플리케이션의 설정 상태를 파악합니다."
        elif ".log" in file_name:
            return f"{{file_name}} 로그 파일을 확인합니다. 시스템이나 애플리케이션의 실행 기록을 분석하여 오류나 동작 패턴을 파악합니다."
        elif ".md" in file_name:
            return f"{{file_name}} 마크다운 문서를 읽습니다. 프로젝트 문서나 가이드를 확인하여 필요한 정보를 수집합니다."
        elif ".txt" in file_name:
            return f"{{file_name}} 텍스트 파일을 읽습니다. 저장된 정보나 데이터를 확인하여 작업에 필요한 내용을 파악합니다."
        return f"{{file_name}} 파일을 읽습니다. 파일의 내용을 확인하여 필요한 정보를 수집하고 다음 작업을 준비합니다."
    
    elif tool == "Grep":
        pattern = context.get("pattern", "")
        path = context.get("path", "")
        return f"'{{pattern}}' 패턴을 {{path}}에서 검색합니다. 코드베이스 전체에서 특정 함수, 변수, 또는 텍스트의 위치를 찾아 관련 코드를 분석할 수 있도록 준비합니다."
    
    elif tool == "Write":
        file_name = Path(context.get("file_path", "")).name
        return f"{{file_name}} 파일을 생성하거나 덮어씁니다. 새로운 코드나 설정을 작성하여 프로젝트에 필요한 파일을 만들거나 기존 파일을 완전히 재작성합니다."
    
    elif tool == "MultiEdit":
        file_name = Path(context.get("file_path", "")).name
        edits = context.get("edits", [])
        return f"{{file_name}} 파일에 {{len(edits)}}개의 수정 사항을 적용합니다. 여러 부분을 동시에 변경하여 코드를 효율적으로 리팩토링하거나 기능을 개선합니다."
    
    elif tool == "Glob":
        pattern = context.get("pattern", "")
        return f"'{{pattern}}' 패턴으로 파일을 검색합니다. 프로젝트 내에서 특정 유형이나 이름의 파일들을 찾아 작업 대상을 파악합니다."
    
    elif tool == "LS":
        path = context.get("path", "")
        return f"{{path}} 디렉토리의 내용을 나열합니다. 파일과 폴더 구조를 확인하여 프로젝트 구성을 파악합니다."
    
    elif tool == "WebFetch":
        url = context.get("url", "")
        return f"{{url}} 웹 페이지의 내용을 가져옵니다. 온라인 문서나 API 정보를 조회하여 필요한 참고 자료를 수집합니다."
    
    elif tool == "Task":
        description = context.get("description", "")
        return f"작업을 실행합니다: {{description}}. 복잡한 작업을 자동화하거나 여러 단계의 프로세스를 수행합니다."
    
    return text[:200] + "..." if len(text) > 200 else text

def main():
    # Log execution
    log_file = Path("$HOME/.sayu/hooks/debug.log")
    with open(log_file, "a") as f:
        f.write(f"\\n[{{datetime.now()}}] Hook script executed\\n")
    
    # Read hook data from stdin
    try:
        input_data = sys.stdin.read()
        with open(log_file, "a") as f:
            f.write(f"Input data: {{input_data[:200]}}\\n")
        hook_data = json.loads(input_data)
    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"Error parsing JSON: {{e}}\\n")
        return
    
    # Extract hook event type
    hook_event = hook_data.get("hook_event_name", "")
    
    # Log the actual hook event for debugging
    with open(log_file, "a") as f:
        f.write(f"Hook event: {{hook_event}}\\n")
        f.write(f"Available keys: {{list(hook_data.keys())}}\\n")
    
    # Create event based on hook type
    event = {{
        "timestamp": datetime.now().isoformat(),
        "hook_event": hook_event,
        "session_id": hook_data.get("session_id", ""),
        "cwd": hook_data.get("cwd", "")
    }}
    
    # Handle different hook events and prepare content/metadata for sayu
    if hook_event == "PreToolUse":
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {{}})
        
        # Format content for sayu with better descriptions
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown"
            content = f"[Pre] Editing {{file_name}}"
        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown"
            content = f"[Pre] Reading {{file_name}}"
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            content = f"[Pre] {{command}}"
        else:
            content = f"[Pre] {{tool_name}}"
        
        metadata = {{
            "type": "tool_use",
            "tool": tool_name,
            "hook": "PreToolUse",
            "phase": "pre"
        }}
        
    elif hook_event == "PostToolUse":
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {{}})
        tool_response = hook_data.get("tool_response", "")
        
        # Create context for summarization
        context = {{
            "tool_name": tool_name,
            "command": tool_input.get("command", ""),
            "file_path": tool_input.get("file_path", ""),
            "old_string": tool_input.get("old_string", ""),
            "new_string": tool_input.get("new_string", ""),
        }}
        
        # Use tool response to get better context
        response_summary = ""
        if tool_response and isinstance(tool_response, str):
            # For long responses, summarize them
            if len(tool_response) > 200:
                response_summary = summarize_with_gemini(tool_response, "tool", context)
            else:
                response_summary = tool_response.strip()
        
        # Create informative content based on tool and response
        if tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown"
            old_str = tool_input.get("old_string", "")
            new_str = tool_input.get("new_string", "")
            
            # Try to understand what was changed
            change_context = ""
            if response_summary:
                change_context = f" - {{response_summary}}"
            else:
                change_context = create_manual_summary("", context)
            
            content = f"[수정] {{file_name}}{{change_context}}"
            
        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown"
            
            # Infer purpose from response
            purpose = ""
            if response_summary:
                purpose = f" - {{response_summary}}"
            else:
                purpose = " - " + create_manual_summary("", context)
            
            content = f"[읽기] {{file_name}}{{purpose}}"
            
        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            desc = tool_input.get("description", "")
            
            # Use description or summarize command purpose
            if desc:
                content = f"[실행] {{desc}}"
            else:
                purpose = create_manual_summary(command, context)
                content = f"[실행] {{purpose}}"
            
            # Add result summary if available
            if response_summary and "Error" not in response_summary:
                content += f" → {{response_summary[:100]}}"
                
        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            path = tool_input.get("path", ".")
            
            # Summarize what was found
            found_info = ""
            if response_summary:
                found_info = f" → {{response_summary}}"
            
            content = f"[검색] '{{pattern}}' in {{path}}{{found_info}}"
            
        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown"
            content = f"[생성/수정] {{file_name}}"
            
        elif tool_name == "WebFetch":
            url = tool_input.get("url", "")
            prompt = tool_input.get("prompt", "")
            
            content = f"[웹 조회] {{url}}"
            if prompt:
                content += f" - {{prompt[:50]}}"
                
        elif tool_name == "MultiEdit":
            file_path = tool_input.get("file_path", "")
            file_name = Path(file_path).name if file_path else "unknown"
            edits = tool_input.get("edits", [])
            edit_count = len(edits)
            content = f"[다중 수정] {{file_name}} ({{edit_count}}개 변경)"
            
        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            path = tool_input.get("path", ".")
            content = f"[파일 검색] '{{pattern}}' in {{path}}"
            
        elif tool_name == "LS":
            path = tool_input.get("path", ".")
            content = f"[디렉토리 목록] {{path}}"
            
        elif tool_name == "Task":
            description = tool_input.get("description", "")
            content = f"[작업 실행] {{description}}"
            
        elif tool_name == "TodoWrite":
            content = "[할 일 목록 업데이트]"
            
        elif tool_name == "NotebookRead" or tool_name == "NotebookEdit":
            notebook_path = tool_input.get("notebook_path", "")
            notebook_name = Path(notebook_path).name if notebook_path else "unknown"
            action = "읽기" if tool_name == "NotebookRead" else "편집"
            content = f"[노트북 {{action}}] {{notebook_name}}"
            
        else:
            # Default formatting with context
            content = f"[{{tool_name}}]"
            if response_summary:
                content += f" - {{response_summary[:100]}}"
        
        metadata = {{
            "type": "tool_use",
            "tool": tool_name,
            "hook": "PostToolUse",
            "has_response": bool(tool_response),
            "tool_input": tool_input,  # Store original input
            "summarized": response_summary and response_summary != tool_response  # Track if summarized
        }}
        
    elif hook_event == "UserPromptSubmit":
        prompt = hook_data.get("prompt", "")
        # Keep original prompt and also create summary
        original_prompt = prompt
        summary = summarize_with_gemini(prompt, "user")
        
        # Use summary as primary content, but store original in metadata
        content = f"[사용자 요청] {{summary}}"
        metadata = {{
            "type": "user_request", 
            "hook": "UserPromptSubmit",
            "original_text": original_prompt,  # Store full original
            "summarized": summary != original_prompt  # Track if summarized
        }}
        
    elif hook_event == "Stop":
        # Read transcript to get assistant response
        transcript_path = hook_data.get("transcript_path", "")
        content = "[어시스턴트 응답]"
        
        if transcript_path and Path(transcript_path).exists():
            try:
                with open(transcript_path, "r") as f:
                    lines = f.readlines()
                    # Collect all assistant messages from the last exchange
                    assistant_messages = []
                    in_last_exchange = False
                    
                    # Read from end to find the last assistant response(s)
                    for line in reversed(lines):
                        if line.strip():
                            data = json.loads(line)
                            role = data.get("role", "")
                            
                            if role == "assistant" and not in_last_exchange:
                                in_last_exchange = True
                                assistant_messages.append(data.get("content", ""))
                            elif role == "assistant" and in_last_exchange:
                                assistant_messages.append(data.get("content", ""))
                            elif role == "user" and in_last_exchange:
                                # Stop when we hit a user message
                                break
                    
                    # Combine assistant messages and summarize
                    if assistant_messages:
                        combined_text = " ".join(reversed(assistant_messages))
                        summary = summarize_with_gemini(combined_text, "assistant")
                        content = f"[어시스턴트 응답] {{summary}}"
                    
            except Exception as e:
                with open(log_file, "a") as f:
                    f.write(f"Error reading transcript: {{e}}\\n")
                content = "[어시스턴트 응답] (읽기 실패)"
        
        metadata = {{"type": "assistant", "hook": "Stop"}}
        
    elif hook_event == "SubagentStop":
        # Similar to Stop but for subagents
        content = "Subagent completed"
        metadata = {{"type": "subagent", "hook": "SubagentStop"}}
        
    elif hook_event == "Notification":
        content = hook_data.get("notification", "")
        metadata = {{"type": "notification", "hook": "Notification"}}
        
    elif hook_event == "PreCompact":
        content = "Compact operation starting"
        metadata = {{"type": "system", "hook": "PreCompact"}}
        
    elif hook_event == "SessionStart":
        content = "Session started"
        metadata = {{"type": "session", "hook": "SessionStart"}}
        
    elif hook_event == "SessionEnd":
        content = "Session ended"  
        metadata = {{"type": "session", "hook": "SessionEnd"}}
        
    else:
        # Unknown event type
        content = f"Unknown event: {{hook_event}}"
        metadata = {{"type": "unknown", "hook": hook_event}}
    
    # Create final event in sayu format
    sayu_event = {{
        "timestamp": datetime.now().isoformat(),
        "content": content,
        "metadata": metadata
    }}
    
    # Append to events file
    event_file = Path("{self.event_file}")
    event_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(event_file, "a") as f:
        f.write(json.dumps(sayu_event) + "\\n")

if __name__ == "__main__":
    main()
'''
