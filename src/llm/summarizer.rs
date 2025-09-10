use anyhow::{Result, Context};
use crate::domain::{Event, EventKind, Actor};
use crate::llm::LLMClient;
use crate::infra::config::Language;
use serde::{Deserialize, Serialize};
use serde_json;

const MAX_EVENTS: usize = 100;
const MAX_EVENT_LENGTH: usize = 10000; // Increased to capture more context

#[derive(Debug, Serialize, Deserialize)]
struct CommitSummary {
    intent: String,          // 의도
    changes: String,         // 변경된 내용
    conversation_flow: String, // 대화 흐름
}

pub struct EventSummarizer {
    client: LLMClient,
}

impl EventSummarizer {
    pub fn new() -> Result<Self> {
        Ok(Self {
            client: LLMClient::new()?,
        })
    }
    
    pub async fn summarize_for_commit(
        &mut self,
        events: Vec<Event>,
        commit_message: &str,
        language: Language,
    ) -> Result<String> {
        // Filter and prepare events
        let filtered_events = self.filter_relevant_events(events);
        let context = self.format_events_as_context(&filtered_events);
        
        // Generate prompt based on language
        let prompt = match language {
            Language::Ko => self.generate_prompt_korean(&context, commit_message),
            Language::En => self.generate_prompt_english(&context, commit_message),
        };
        
        // Get LLM response with structured output
        let response = self.client.complete(&prompt, true).await?;
        
        // Parse JSON response
        let summary = self.parse_response(&response)?;
        
        // Format as commit trailer
        Ok(self.format_as_trailer_structured(&summary, language))
    }
    
    fn parse_response(&self, response: &str) -> Result<CommitSummary> {
        // Try to extract JSON from the response
        // LLM might wrap it in markdown code blocks
        let json_str = if response.contains("```json") {
            response
                .split("```json")
                .nth(1)
                .and_then(|s| s.split("```").next())
                .unwrap_or(response)
                .trim()
        } else if response.contains("```") {
            response
                .split("```")
                .nth(1)
                .unwrap_or(response)
                .trim()
        } else {
            response.trim()
        };
        
        // Parse JSON
        serde_json::from_str::<CommitSummary>(json_str)
            .or_else(|_| {
                // Fallback: try to parse as plain text with the old format
                self.parse_plain_text_response(response)
            })
            .context("Failed to parse LLM response")
    }
    
    fn parse_plain_text_response(&self, response: &str) -> Result<CommitSummary> {
        let mut intent = String::new();
        let mut changes = String::new();
        let mut conversation_flow = String::new();
        
        let lines: Vec<&str> = response.lines().collect();
        let mut current_section = "";
        
        for line in lines {
            if line.starts_with("의도:") || line.starts_with("Intent:") {
                current_section = "intent";
                let content = line.splitn(2, ':').nth(1).unwrap_or("").trim();
                if !content.is_empty() {
                    intent.push_str(content);
                }
            } else if line.starts_with("변경된 내용:") || line.starts_with("Changes Made:") {
                current_section = "changes";
                let content = line.splitn(2, ':').nth(1).unwrap_or("").trim();
                if !content.is_empty() {
                    changes.push_str(content);
                }
            } else if line.starts_with("대화 흐름:") || line.starts_with("Conversation Flow:") {
                current_section = "flow";
                let content = line.splitn(2, ':').nth(1).unwrap_or("").trim();
                if !content.is_empty() {
                    conversation_flow.push_str(content);
                }
            } else if !line.trim().is_empty() {
                match current_section {
                    "intent" => {
                        if !intent.is_empty() {
                            intent.push(' ');
                        }
                        intent.push_str(line.trim());
                    }
                    "changes" => {
                        if !changes.is_empty() {
                            changes.push(' ');
                        }
                        changes.push_str(line.trim());
                    }
                    "flow" => {
                        if !conversation_flow.is_empty() {
                            conversation_flow.push(' ');
                        }
                        conversation_flow.push_str(line.trim());
                    }
                    _ => {}
                }
            }
        }
        
        Ok(CommitSummary {
            intent,
            changes,
            conversation_flow,
        })
    }
    
    fn filter_relevant_events(&self, mut events: Vec<Event>) -> Vec<Event> {
        // Sort by timestamp (most recent first)
        events.sort_by(|a, b| b.id.cmp(&a.id));
        
        // Take only the most recent events
        events.truncate(MAX_EVENTS);
        
        // Include all event types for better context
        events
    }
    
    fn format_events_as_context(&self, events: &[Event]) -> String {
        let mut context = String::new();
        
        for event in events {
            let truncated_text = if event.text.len() > MAX_EVENT_LENGTH {
                format!("{}...", &event.text[..MAX_EVENT_LENGTH])
            } else {
                event.text.clone()
            };
            
            match event.kind {
                EventKind::Conversation => {
                    let actor = match &event.actor {
                        Some(Actor::User) => "[User]",
                        Some(Actor::Assistant) => "[Assistant]",
                        None => "[Unknown]",
                    };
                    context.push_str(&format!("{}: {}\n", actor, truncated_text));
                }
                EventKind::Command => {
                    context.push_str(&format!("[Command]: {}\n", truncated_text));
                }
                EventKind::Diff => {
                    context.push_str(&format!("[File Changes]: {}\n", truncated_text));
                }
                _ => {}
            }
        }
        
        context
    }
    
    fn generate_prompt_korean(&self, context: &str, commit_message: &str) -> String {
        format!(
            r#"다음은 개발자가 코드를 변경하면서 나눈 대화와 실행한 명령어들입니다.

=== 개발 과정 ===
{}

=== 커밋 메시지 ===
{}

위 정보를 바탕으로 이 커밋의 배경과 의도를 분석하여 JSON 형식으로 응답해주세요.
다음 JSON 구조를 정확히 따라주세요:

{{
  "intent": "변경의 핵심 목적과 해결하려는 문제를 2-3문장으로 설명",
  "changes": "실제로 수정된 내용을 간략히 요약",
  "conversation_flow": "개발 과정에서 어떤 시행착오나 고민이 있었는지 설명"
}}

반드시 유효한 JSON 형식으로만 응답하고, 추가 설명이나 마크다운 포맷팅을 포함하지 마세요."#,
            context, commit_message
        )
    }
    
    fn generate_prompt_english(&self, context: &str, commit_message: &str) -> String {
        format!(
            r#"Here are the conversations and commands from the development process:

=== Development Process ===
{}

=== Commit Message ===
{}

Based on this information, analyze the background and intent of this commit and respond in JSON format.
Please follow this exact JSON structure:

{{
  "intent": "Explain the core purpose and problem being solved in 2-3 sentences",
  "changes": "Brief summary of what was actually modified",
  "conversation_flow": "Describe any trial-and-error or considerations during development"
}}

Respond only with valid JSON, without any additional explanation or markdown formatting."#,
            context, commit_message
        )
    }
    
    fn format_as_trailer_structured(&self, summary: &CommitSummary, language: Language) -> String {
        // Format the structured data as a readable trailer
        let formatted = match language {
            Language::Ko => {
                format!(
                    "의도:\n{}\n\n변경된 내용:\n{}\n\n대화 흐름:\n{}",
                    summary.intent, summary.changes, summary.conversation_flow
                )
            }
            Language::En => {
                format!(
                    "Intent:\n{}\n\nChanges Made:\n{}\n\nConversation Flow:\n{}",
                    summary.intent, summary.changes, summary.conversation_flow
                )
            }
        };
        
        // Wrap the formatted text to fit within 72 characters
        let lines: Vec<String> = formatted
            .lines()
            .flat_map(|line| {
                if line.trim().is_empty() {
                    vec![String::new()]
                } else {
                    self.wrap_line(line, 72)
                }
            })
            .collect();
        
        // Format as Git trailer with continuation lines
        let mut result = String::from("Sayu-Context: ");
        
        for (i, line) in lines.iter().enumerate() {
            if i == 0 {
                result.push_str(line);
            } else {
                result.push_str("\n ");
                result.push_str(line);
            }
        }
        
        result
    }
    
    fn wrap_line(&self, line: &str, max_width: usize) -> Vec<String> {
        if line.len() <= max_width {
            return vec![line.to_string()];
        }
        
        let mut wrapped = Vec::new();
        let mut current = String::new();
        
        for word in line.split_whitespace() {
            if current.is_empty() {
                current = word.to_string();
            } else if current.len() + 1 + word.len() <= max_width {
                current.push(' ');
                current.push_str(word);
            } else {
                wrapped.push(current);
                current = word.to_string();
            }
        }
        
        if !current.is_empty() {
            wrapped.push(current);
        }
        
        wrapped
    }
}