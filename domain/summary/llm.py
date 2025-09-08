"""LLM summary generator for commit context"""

import json
import re
from typing import List, Dict, Any

from domain.events.types import Event, LLMSummaryResponse
from infra.api.llm import LLMApiClient
from i18n import i18n
from shared.constants import TextConstants


class LLMSummaryGenerator:
    """Generate AI summaries using LLM"""
    
    @staticmethod
    def generate(llm_events: List[Event], staged_files: List[str], diff_stats: str) -> str:
        """Generate main LLM summary"""
        prompt = LLMSummaryGenerator._build_prompt(llm_events, staged_files, diff_stats)
        response = LLMApiClient.call_llm(prompt)
        
        try:
            # Try to extract JSON from markdown code blocks
            json_content = LLMSummaryGenerator._extract_json_from_response(response)
            parsed = json.loads(json_content)
            return LLMSummaryGenerator._format_commit_trailer(parsed)
        except (json.JSONDecodeError, ValueError) as e:
            print(f'[Sayu] JSON parse failed: {e}, using raw response')
            return LLMSummaryGenerator._format_raw_response(response)
    
    @staticmethod
    def generate_simplified(llm_events: List[Event], staged_files: List[str], diff_stats: str) -> str:
        """Generate simplified LLM summary"""
        recent_conversations = llm_events[-TextConstants.MAX_SIMPLIFIED_CONVERSATIONS:]
        conversations_text = '\n'.join([
            f"[{event.actor.value if event.actor else 'unknown'}]: {event.text[:TextConstants.MAX_SIMPLIFIED_LENGTH]}"
            for event in recent_conversations
        ])
        
        i18n_manager = i18n()
        simple_prompt = i18n_manager.get_simplified_analysis_prompt(
            conversations_text, staged_files, diff_stats
        )
        response = LLMApiClient.call_llm(simple_prompt)
        
        try:
            # Try to extract JSON from markdown code blocks
            json_content = LLMSummaryGenerator._extract_json_from_response(response)
            parsed = json.loads(json_content)
            return LLMSummaryGenerator._format_commit_trailer(parsed)
        except (json.JSONDecodeError, ValueError) as e:
            print(f'[Sayu] JSON parse failed: {e}, using raw response')
            return LLMSummaryGenerator._format_raw_response(response)
    
    @staticmethod
    def _build_prompt(llm_events: List[Event], staged_files: List[str], diff_stats: str) -> str:
        """Build main analysis prompt"""
        recent_events = llm_events[-TextConstants.MAX_CONVERSATION_COUNT:]
        conversations = '\n'.join([
            f"[{event.actor.value if event.actor else 'unknown'}]: {event.text[:TextConstants.MAX_CONVERSATION_LENGTH]}"
            for event in recent_events
        ])
        
        process_analysis = LLMSummaryGenerator._analyze_conversation_process(llm_events)
        
        i18n_manager = i18n()
        return i18n_manager.get_main_analysis_prompt(
            conversations, staged_files, diff_stats, process_analysis
        )
    
    @staticmethod
    def _format_commit_trailer(parsed: Dict[str, Any]) -> str:
        """Format parsed response as commit trailer"""
        lines = []
        i18n_manager = i18n()
        outputs = i18n_manager.get_outputs()
        
        lines.append('---')
        lines.append(outputs['trailer_header'])
        lines.append('')
        
        if parsed.get('intent'):
            lines.append(outputs['trailer_labels']['intent'])
            lines.append(LLMSummaryGenerator._wrap_text(parsed['intent'], 2))
            lines.append('')
        
        if parsed.get('changes'):
            lines.append(outputs['trailer_labels']['changes'])
            lines.append(LLMSummaryGenerator._wrap_text(parsed['changes'], 2))
            lines.append('')
        
        if parsed.get('context'):
            lines.append(outputs['trailer_labels']['context'])
            lines.append(LLMSummaryGenerator._wrap_text(parsed['context'], 2))
            lines.append('')
        
        lines.append('---')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _wrap_text(text: str, indent: int = 0) -> str:
        """Wrap text to specified line length with indentation, preserving original line breaks"""
        max_line_length = TextConstants.MAX_LINE_LENGTH
        indent_str = ' ' * indent
        
        # Split by original line breaks first to preserve LLM's intentional formatting
        original_lines = text.split('\n')
        final_lines = []
        
        for original_line in original_lines:
            original_line = original_line.strip()
            if not original_line:
                # Preserve empty lines
                final_lines.append('')
                continue
            
            # Wrap each original line if it's too long
            words = original_line.split(' ')
            current_line = indent_str
            
            for word in words:
                if len(current_line) + len(word) + 1 <= max_line_length:
                    if current_line == indent_str:
                        current_line += word
                    else:
                        current_line += ' ' + word
                else:
                    final_lines.append(current_line)
                    current_line = indent_str + word
            
            if current_line.strip():
                final_lines.append(current_line)
        
        return '\n'.join(final_lines)
    
    @staticmethod
    def _format_raw_response(text: str) -> str:
        """Format raw response as fallback"""
        lines = []
        lines.append('---')
        lines.append('AI-Context (sayu)')
        
        clean_text = re.sub(r'[\n\r]+', ' ', text).strip()
        if len(clean_text) > TextConstants.MAX_RAW_RESPONSE_LENGTH:
            lines.append(f"Summary: {clean_text[:TextConstants.MAX_RAW_RESPONSE_LENGTH]}...")
        else:
            lines.append(f"Summary: {clean_text}")
        
        lines.append('---')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _analyze_conversation_process(llm_events: List[Event]) -> str:
        """Analyze conversation patterns"""
        if not llm_events:
            return "대화 없음: 코드 변경만 수행됨"
        
        analysis = []
        
        user_events = [e for e in llm_events if e.actor and e.actor.value == 'user']
        assistant_events = [e for e in llm_events if e.actor and e.actor.value == 'assistant']
        
        analysis.append(f"대화 총 {len(llm_events)}회 (사용자: {len(user_events)}, 어시스턴트: {len(assistant_events)})")
        
        # Questions
        questions = [e for e in user_events if '?' in e.text or '어떻게' in e.text or '왜' in e.text]
        if questions:
            analysis.append(f"{len(questions)}개의 질문/문의사항 포함")
        
        # Problem solving
        problem_keywords = ['문제', '오류', '에러', '안됨', '실패', '버그']
        problem_events = [e for e in llm_events 
                         if any(keyword in e.text for keyword in problem_keywords)]
        if problem_events:
            analysis.append(f"문제 해결 과정: {len(problem_events)}회 언급")
        
        # Retries
        retry_keywords = ['다시', '재시도', '또', '한번 더']
        retry_events = [e for e in llm_events 
                       if any(keyword in e.text for keyword in retry_keywords)]
        if retry_events:
            analysis.append(f"반복/재시도 과정: {len(retry_events)}회 발생")
        
        # Tool usage
        tool_events = [e for e in llm_events if '[Tool:' in e.text]
        if tool_events:
            analysis.append(f"도구 사용: {len(tool_events)}회")
        
        # Unusual patterns
        unusual_patterns = []
        
        if len(llm_events) > 50:
            unusual_patterns.append(f"장시간 세션 ({len(llm_events)}회 대화)")
        
        short_responses = [e for e in user_events if len(e.text) < 10]
        if len(short_responses) > 3:
            unusual_patterns.append(f"짧은 응답 연속 ({len(short_responses)}회)")
        
        # Keyword analysis
        all_text = ' '.join(e.text for e in llm_events)
        keyword_counts = {}
        for keyword in ['최적화', '성능', '버그', '테스트', '리팩토링']:
            count = len(re.findall(keyword, all_text))
            if count > 3:
                keyword_counts[keyword] = count
        
        if keyword_counts:
            keywords = ', '.join(f"{word}({count}회)" for word, count in keyword_counts.items())
            unusual_patterns.append(f"반복 키워드: {keywords}")
        
        if unusual_patterns:
            analysis.append(f"특이점: {', '.join(unusual_patterns)}")
        
        return ' / '.join(analysis)
    
    @staticmethod
    def _extract_json_from_response(response: str) -> str:
        """Extract JSON from response, handling markdown code blocks"""
        # First try direct JSON parsing
        response = response.strip()
        if response.startswith('{') and response.endswith('}'):
            return response
        
        # Try to extract from markdown code blocks
        import re
        
        # Look for ```json ... ``` blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Look for { ... } blocks
        json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # If no JSON found, raise error
        raise ValueError(f"No JSON found in response: {response[:200]}...")
