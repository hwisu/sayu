"""Cursor collector for extracting AI conversation data"""

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from domain.events.types import Event, EventSource, EventKind, Actor, Config, Connector


class CursorCollector:
    """Collect AI conversations from Cursor IDE"""
    
    id = 'cursor.ai'
    
    def __init__(self, repo_root: Optional[str] = None):
        """Initialize Cursor collector"""
        self.repo_root = repo_root or os.getcwd()
        self.cursor_base_path = Path.home() / 'Library' / 'Application Support' / 'Cursor'
        
    def discover(self, repo_root: str) -> bool:
        """Check if Cursor is available and has conversation data"""
        try:
            global_db = self.cursor_base_path / 'User' / 'globalStorage' / 'state.vscdb'
            if not global_db.exists():
                return False
            
            # Check if there are any workspace databases
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            if not workspace_dir.exists():
                return False
                
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            return len(workspace_dbs) > 0
            
        except Exception:
            return False
    
    def pull_since(self, since_ms: int, until_ms: int, cfg: Config) -> List[Event]:
        """Pull Cursor conversation events within time range"""
        events = []
        
        try:
            # Get all workspace databases
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            
            for db_path in workspace_dbs:
                try:
                    workspace_events = self._extract_from_workspace_db(
                        str(db_path), since_ms, until_ms
                    )
                    events.extend(workspace_events)
                except Exception as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error processing Cursor workspace DB {db_path}: {e}")
                        
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Cursor collector error: {e}")
        
        return events
    
    def health(self) -> Dict[str, Any]:
        """Health check for Cursor collector"""
        try:
            if not self.discover(self.repo_root):
                return {'ok': False, 'reason': 'Cursor not found or no conversation data'}
            
            # Count available conversations
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            
            total_conversations = 0
            for db_path in workspace_dbs:
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT value FROM ItemTable WHERE key = 'composer.composerData'"
                    )
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        data = json.loads(result[0])
                        total_conversations += len(data.get('allComposers', []))
                        
                except Exception:
                    continue
            
            return {
                'ok': True, 
                'conversations': total_conversations,
                'workspaces': len(workspace_dbs)
            }
            
        except Exception as e:
            return {'ok': False, 'reason': str(e)}
    
    def redact(self, event: Event, cfg: Config) -> Event:
        """Redact sensitive information from Cursor event"""
        if not cfg.privacy.maskSecrets:
            return event
        
        # Apply privacy masks
        text = event.text
        for pattern in cfg.privacy.masks:
            import re
            text = re.sub(pattern, '[REDACTED]', text)
        
        return Event(
            id=event.id,
            ts=event.ts,
            source=event.source,
            kind=event.kind,
            repo=event.repo,
            cwd=event.cwd,
            file=event.file,
            range=event.range,
            actor=event.actor,
            text=text,
            url=event.url,
            meta=event.meta
        )
    
    def _extract_from_workspace_db(
        self, db_path: str, since_ms: int, until_ms: int
    ) -> List[Event]:
        """Extract conversation events from a workspace database"""
        events = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Extract actual message content from aiService.generations
            cursor.execute(
                "SELECT value FROM ItemTable WHERE key = 'aiService.generations'"
            )
            generations_result = cursor.fetchone()
            
            if generations_result:
                try:
                    generations_data = json.loads(generations_result[0])
                    
                    for gen in generations_data:
                        try:
                            timestamp = gen.get('unixMs')
                            text_desc = gen.get('textDescription', '')
                            gen_uuid = gen.get('generationUUID', '')
                            gen_type = gen.get('type', 'unknown')
                            
                            if not timestamp or not text_desc:
                                continue
                            
                            # Check if within time range
                            if not (since_ms <= timestamp <= until_ms):
                                continue
                            
                            # Create event for user message
                            user_event = Event(
                                id=str(uuid.uuid4()),
                                ts=timestamp,
                                source=EventSource.LLM,
                                kind=EventKind.CHAT,
                                repo=self.repo_root,
                                cwd=self.repo_root,
                                file=None,
                                range=None,
                                actor=Actor.USER,
                                text=text_desc,
                                url=None,
                                meta={
                                    'generationUUID': gen_uuid,
                                    'type': gen_type,
                                    'tool': 'cursor',
                                    'source_table': 'aiService.generations'
                                }
                            )
                            events.append(user_event)
                            
                        except Exception as e:
                            if os.getenv('SAYU_DEBUG'):
                                print(f"Error processing generation {gen}: {e}")
                            continue
                            
                except json.JSONDecodeError as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error parsing aiService.generations: {e}")
            
            # Extract AI responses from aiService.prompts (timestamp 없는 경우 대응)
            cursor.execute(
                "SELECT value FROM ItemTable WHERE key = 'aiService.prompts'"
            )
            prompts_result = cursor.fetchone()
            
            if prompts_result:
                try:
                    prompts_data = json.loads(prompts_result[0])
                    
                    # Handle both list and dict formats
                    prompt_items = prompts_data if isinstance(prompts_data, list) else prompts_data.values()
                    
                    # 시간 범위 내의 사용자 메시지들과 AI 응답 매칭
                    user_events_in_range = [e for e in events if e.actor == Actor.USER and since_ms <= e.ts <= until_ms]
                    
                    # AI 응답 중에서 의미있는 것들만 필터링
                    meaningful_ai_responses = []
                    for prompt in prompt_items:
                        if not isinstance(prompt, dict):
                            continue
                        
                        text_content = prompt.get('text', '')
                        command_type = prompt.get('commandType', '')
                        
                        if not text_content or len(text_content.strip()) < 10:
                            continue
                        
                        # 의미있는 AI 응답만 필터링 (툴 사용, 간단 출력 제외)
                        is_meaningful_ai_response = (
                            len(text_content) > 300 and  # 적당한 길이 이상
                            not text_content.startswith('For the code present') and  # 에러 메시지 제외
                            not text_content.startswith('Cannot find') and  # 에러 메시지 제외
                            not text_content.startswith('Type \'') and  # 타입 에러 제외
                            not text_content.startswith('Argument of type') and  # 타입 에러 제외
                            not text_content.startswith('[HMR]') and  # 개발 로그 제외
                            not text_content.startswith('bootstrap:') and  # 개발 로그 제외
                            not text_content.startswith('Request URL') and  # 네트워크 로그 제외
                            not text_content.startswith('HTTP/1.1') and  # 네트워크 로그 제외
                            not text_content.startswith('Run ') and  # 명령어 실행 로그 제외
                            not '에러:' in text_content and  # 에러 관련 제외
                            not 'Error:' in text_content and  # 에러 관련 제외
                            (
                                'AI-Context' in text_content or  # 구조화된 AI 응답
                                text_content.startswith('아래는') or  # AI 설명 패턴  
                                'PRD' in text_content or  # 문서 생성
                                text_content.count('\n') > 3 or  # 여러 줄의 설명
                                len(text_content) > 800  # 충분히 긴 응답
                            )
                        )
                        
                        if is_meaningful_ai_response:
                            meaningful_ai_responses.append({
                                'text': text_content,
                                'commandType': command_type
                            })
                    
                    # 사용자 메시지 개수와 AI 응답 개수 매칭
                    num_user_messages = len(user_events_in_range)
                    num_ai_responses = min(len(meaningful_ai_responses), num_user_messages * 2)  # 최대 사용자 메시지의 2배
                    
                    if os.getenv('SAYU_DEBUG'):
                        print(f'매칭: 사용자 메시지 {num_user_messages}개, AI 응답 {num_ai_responses}개')
                    
                    # AI 응답들을 사용자 메시지 이후 시간으로 배치
                    for i, ai_response in enumerate(meaningful_ai_responses[:num_ai_responses]):
                        try:
                            # 해당하는 사용자 메시지의 시간 기준으로 AI 응답 시간 설정
                            user_idx = min(i // 2, len(user_events_in_range) - 1)  # 사용자 메시지 인덱스
                            base_timestamp = user_events_in_range[user_idx].ts
                            
                            # AI 응답은 사용자 메시지 30초~3분 후에 생성된다고 가정
                            ai_timestamp = base_timestamp + 30000 + (i % 2) * 60000  # 30초, 1분30초 후
                            
                            # 시간 범위 체크
                            if ai_timestamp > until_ms:
                                continue
                            
                            # Create event for AI response  
                            ai_event = Event(
                                id=str(uuid.uuid4()),
                                ts=ai_timestamp,
                                source=EventSource.LLM,
                                kind=EventKind.CHAT,
                                repo=self.repo_root,
                                cwd=self.repo_root,
                                file=None,
                                range=None,
                                actor=Actor.ASSISTANT,
                                text=ai_response['text'][:1500],  # 적당한 길이로 제한
                                url=None,
                                meta={
                                    'type': 'ai_response',
                                    'commandType': ai_response['commandType'],
                                    'tool': 'cursor',
                                    'source_table': 'aiService.prompts',
                                    'inferred_timestamp': True,
                                    'paired_with_user_msg': user_idx
                                }
                            )
                            events.append(ai_event)
                            
                        except Exception as e:
                            if os.getenv('SAYU_DEBUG'):
                                print(f"Error processing prompt {prompt}: {e}")
                            continue
                            
                except json.JSONDecodeError as e:
                    if os.getenv('SAYU_DEBUG'):
                        print(f"Error parsing aiService.prompts: {e}")
            
            conn.close()
            
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error reading Cursor workspace DB {db_path}: {e}")
        
        return events
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent conversations for debugging/inspection"""
        conversations = []
        
        try:
            since_ms = int((time.time() - hours * 3600) * 1000)
            workspace_dir = self.cursor_base_path / 'User' / 'workspaceStorage'
            workspace_dbs = list(workspace_dir.glob('*/state.vscdb'))
            
            for db_path in workspace_dbs:
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    cursor.execute(
                        "SELECT value FROM ItemTable WHERE key = 'composer.composerData'"
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        data = json.loads(result[0])
                        for composer in data.get('allComposers', []):
                            if composer.get('lastUpdatedAt', 0) >= since_ms:
                                conversations.append({
                                    'id': composer.get('composerId'),
                                    'name': composer.get('name'),
                                    'created': composer.get('createdAt'),
                                    'updated': composer.get('lastUpdatedAt'),
                                    'mode': composer.get('unifiedMode'),
                                    'workspace': str(db_path.parent.name)
                                })
                    
                    conn.close()
                    
                except Exception:
                    continue
                    
        except Exception as e:
            if os.getenv('SAYU_DEBUG'):
                print(f"Error getting recent conversations: {e}")
        
        return sorted(conversations, key=lambda x: x.get('updated', 0), reverse=True)
