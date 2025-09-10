"""LLM summary generator for commit context"""

import json
import re
from typing import List, Dict, Any

import os
from domain.events.types import Event
from infra.api.llm_factory import LLMFactory
from i18n import i18n
from shared.constants import (
    MAX_CONVERSATION_COUNT, MAX_CONVERSATION_LENGTH
)


class LLMSummaryGenerator:
    """Generate AI summaries using LLM"""
    
    @staticmethod
    def generate(llm_events: List[Event], staged_files: List[str], diff_stats: str) -> str:
        """Generate main LLM summary"""
        try:
            prompt = LLMSummaryGenerator._build_prompt(llm_events, staged_files, diff_stats)
            response = LLMFactory.call_llm(prompt)
            
            # Handle None or invalid response
            if response is None:
                return LLMSummaryGenerator._format_raw_response("No response from LLM")
        except Exception as e:
            import traceback
            print(f"[Sayu] LLM Error: {type(e).__name__}: {e}")
            if os.getenv('SAYU_DEBUG'):
                traceback.print_exc()
            return LLMSummaryGenerator._format_raw_response(f"LLM Error: {e}")
        
        # Ensure response is a string
        if not isinstance(response, str):
            return LLMSummaryGenerator._format_raw_response(str(response))
        
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
        # 66 conversations for simplified mode (2/3 of MAX_CONVERSATION_COUNT)
        recent_conversations = llm_events[-66:]
        conversations_text = '\n'.join([
            f"[{event.actor.value if event.actor else 'unknown'}]: {event.text[:2000]}"  # 2000 chars for simplified (1/10 of MAX_CONVERSATION_LENGTH)
            for event in recent_conversations
        ])
        
        i18n_manager = i18n()
        simple_prompt = i18n_manager.get_simplified_analysis_prompt(
            conversations_text, staged_files, diff_stats
        )
        response = LLMFactory.call_llm(simple_prompt)
        
        # Handle None or invalid response
        if response is None:
            return LLMSummaryGenerator._format_raw_response("No response from LLM")
        
        # Ensure response is a string
        if not isinstance(response, str):
            return LLMSummaryGenerator._format_raw_response(str(response))
        
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
        recent_events = llm_events[-MAX_CONVERSATION_COUNT:]
        conversations = '\n'.join([
            f"[{event.actor.value if event.actor else 'unknown'}]: {event.text[:MAX_CONVERSATION_LENGTH]}"
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
        
        lines.append('---思惟---\n\n'.rstrip())  # Summary separator
        
        # Handle intent
        if parsed.get('intent'):
            lines.append(outputs['trailer_labels']['intent'])
            intent_value = parsed['intent']
            # Convert to string if it's not
            if isinstance(intent_value, list):
                intent_value = ' '.join(str(item) for item in intent_value)
            lines.append(LLMSummaryGenerator._wrap_text(str(intent_value), 2))
            lines.append('')
        
        # Handle what_changed
        if parsed.get('what_changed'):
            lines.append(outputs['trailer_labels']['what_changed'])
            what_changed_value = parsed['what_changed']
            # Convert to string if it's not
            if isinstance(what_changed_value, list):
                what_changed_value = ' '.join(str(item) for item in what_changed_value)
            lines.append(LLMSummaryGenerator._wrap_text(str(what_changed_value), 2))
            lines.append('')
        
        # Handle conversation_flow
        if parsed.get('conversation_flow'):
            lines.append(outputs['trailer_labels']['conversation_flow'])
            conversation_flow_value = parsed['conversation_flow']
            # Convert to string if it's not
            if isinstance(conversation_flow_value, list):
                conversation_flow_value = ' '.join(str(item) for item in conversation_flow_value)
            lines.append(LLMSummaryGenerator._wrap_text(str(conversation_flow_value), 2))
            lines.append('')
        
        lines.append('\n---FIN---'.strip())  # Summary footer
        
        return '\n'.join(lines)
    
    @staticmethod
    def _wrap_text(text: str, indent: int = 0) -> str:
        """Wrap text to specified line length with indentation, preserving original line breaks"""
        max_line_length = 100  # Maximum line length in commit trailer (Git standard)
        indent_str = ' ' * indent
        
        # Ensure text is a string
        if not isinstance(text, str):
            if isinstance(text, list):
                # If it's a list, join elements
                text = ' '.join(str(item) for item in text)
                print(f"⚠️ Warning: _wrap_text received list instead of string, converted to: {text[:50]}...")
            else:
                text = str(text)
        
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
        lines.append('---思惟---\n\n'.rstrip())  # Summary separator
        
        # Ensure text is a string
        if not isinstance(text, str):
            text = str(text) if text is not None else "No response"
        
        clean_text = re.sub(r'[\n\r]+', ' ', text).strip()
        if len(clean_text) > 10000:  # Maximum raw response length
            lines.append(f"Summary: {clean_text[:10000]}...")
        else:
            lines.append(f"Summary: {clean_text}")
        
        lines.append('\n---FIN---'.strip())  # Summary footer
        
        return '\n'.join(lines)
    
    @staticmethod
    def _analyze_conversation_process(llm_events: List[Event]) -> str:
        """Analyze conversation patterns to capture development flow"""
        if not llm_events:
            return "No conversations: Direct code changes only"
        
        analysis = []
        
        user_events = [e for e in llm_events if e.actor and e.actor.value == 'user']
        assistant_events = [e for e in llm_events if e.actor and e.actor.value == 'assistant']
        
        # Basic conversation stats
        analysis.append(f"Total {len(llm_events)} exchanges (User: {len(user_events)}, Assistant: {len(assistant_events)})")
        
        # Development flow analysis
        flow_patterns = []
        
        # Initial approach detection
        if user_events:
            first_request = user_events[0].text[:100]
            if any(word in first_request.lower() for word in ['implement', 'create', 'add', 'build', 'fix']):
                flow_patterns.append("Started with clear implementation goal")
            elif any(word in first_request.lower() for word in ['why', 'how', 'what', 'debug', 'error']):
                flow_patterns.append("Started with debugging/investigation")
        
        # Questions and clarifications
        questions = [e for e in user_events if '?' in e.text or any(word in e.text.lower() for word in ['how', 'why', 'what', 'where'])]
        if questions:
            flow_patterns.append(f"{len(questions)} clarification points")
        
        # Problem solving journey
        problem_keywords = ['error', 'bug', 'issue', 'problem', 'fail', 'wrong', 'broken', 'not working']
        problem_events = [e for e in llm_events 
                         if any(keyword in e.text.lower() for keyword in problem_keywords)]
        if problem_events:
            flow_patterns.append(f"Encountered {len(problem_events)} challenges")
        
        # Solution attempts
        solution_keywords = ['try', 'attempt', 'let me', 'how about', 'what if', 'maybe', 'could', 'should']
        solution_events = [e for e in llm_events 
                          if any(keyword in e.text.lower() for keyword in solution_keywords)]
        if solution_events:
            flow_patterns.append(f"{len(solution_events)} solution attempts")
        
        # Iterations and refinements
        iteration_keywords = ['again', 'retry', 'another', 'different', 'instead', 'actually', 'wait']
        iteration_events = [e for e in llm_events 
                           if any(keyword in e.text.lower() for keyword in iteration_keywords)]
        if iteration_events:
            flow_patterns.append(f"{len(iteration_events)} iterations/refinements")
        
        # Tool and resource usage
        tool_events = [e for e in llm_events if any(marker in e.text for marker in ['[Tool:', 'Running:', 'Executing:', '```'])]
        if tool_events:
            flow_patterns.append(f"{len(tool_events)} tool/code executions")
        
        # Documentation/reference mentions
        doc_keywords = ['documentation', 'docs', 'reference', 'guide', 'example', 'stackoverflow', 'github']
        doc_events = [e for e in llm_events 
                     if any(keyword in e.text.lower() for keyword in doc_keywords)]
        if doc_events:
            flow_patterns.append(f"Referenced external resources {len(doc_events)} times")
        
        # Decision points
        decision_keywords = ['decided', 'choosing', 'better', 'instead of', 'rather than', 'because', 'since']
        decision_events = [e for e in llm_events 
                          if any(keyword in e.text.lower() for keyword in decision_keywords)]
        if decision_events:
            flow_patterns.append(f"{len(decision_events)} key decisions made")
        
        # Testing and verification
        test_keywords = ['test', 'verify', 'check', 'confirm', 'ensure', 'validate']
        test_events = [e for e in llm_events 
                      if any(keyword in e.text.lower() for keyword in test_keywords)]
        if test_events:
            flow_patterns.append(f"{len(test_events)} verification steps")
        
        # Session characteristics
        session_info = []
        
        if len(llm_events) > 50:
            session_info.append(f"Extended session ({len(llm_events)} exchanges)")
        elif len(llm_events) < 10:
            session_info.append("Quick resolution")
        
        # Complexity indicators
        if problem_events and len(problem_events) > 5:
            session_info.append("Complex debugging process")
        
        if iteration_events and len(iteration_events) > 3:
            session_info.append("Multiple approach changes")
        
        # Key topics analysis
        all_text = ' '.join(e.text for e in llm_events).lower()
        topic_keywords = {
            'performance': ['performance', 'optimize', 'speed', 'efficiency', 'memory'],
            'architecture': ['structure', 'design', 'pattern', 'refactor', 'organize'],
            'debugging': ['debug', 'error', 'exception', 'stacktrace', 'logs'],
            'testing': ['test', 'unit', 'integration', 'coverage', 'assert'],
            'configuration': ['config', 'setting', 'environment', 'setup', 'install']
        }
        
        main_topics = []
        for topic, keywords in topic_keywords.items():
            count = sum(1 for keyword in keywords if keyword in all_text)
            if count > 2:
                main_topics.append(topic)
        
        if main_topics:
            session_info.append(f"Focus areas: {', '.join(main_topics)}")
        
        # Combine all analysis
        if flow_patterns:
            analysis.append(f"Development flow: {' → '.join(flow_patterns)}")
        
        if session_info:
            analysis.append(f"Session: {', '.join(session_info)}")
        
        return ' | '.join(analysis)
    
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
