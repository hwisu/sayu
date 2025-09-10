use anyhow::Result;
use crate::domain::{Event, EventKind, Actor};
use crate::llm::LLMClient;
use crate::infra::config::Language;

const MAX_EVENTS: usize = 100;
const MAX_EVENT_LENGTH: usize = 10000; // Increased to capture more context

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
        
        // Get LLM response
        let response = self.client.complete(&prompt, true).await?;
        
        // Format as commit trailer
        Ok(self.format_as_trailer(&response, language))
    }
    
    fn filter_relevant_events(&self, mut events: Vec<Event>) -> Vec<Event> {
        // Sort by timestamp (most recent first)
        events.sort_by(|a, b| b.id.cmp(&a.id));
        
        // Take only the most recent events
        events.truncate(MAX_EVENTS);
        
        // Include all event types for better context
        events.into_iter()
            .filter(|e| {
                // Keep all conversations, diffs, and important commands
                matches!(e.kind, EventKind::Conversation | EventKind::Diff) ||
                (matches!(e.kind, EventKind::Command) && !self.is_trivial_command(&e.text))
            })
            .collect()
    }
    
    fn is_trivial_command(&self, cmd: &str) -> bool {
        let trivial_commands = ["ls", "cd", "pwd", "git status", "git log", "clear"];
        trivial_commands.iter().any(|&t| cmd.starts_with(t))
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

위 정보를 바탕으로 이 커밋의 배경과 의도를 한국어로 요약해주세요. 응답은 다음 형식을 따라주세요:

의도:
(변경의 핵심 목적과 해결하려는 문제를 2-3문장으로 설명)

변경된 내용:
(실제로 수정된 내용을 간략히 요약)

대화 흐름:
(개발 과정에서 어떤 시행착오나 고민이 있었는지 설명)

---FIN---"#,
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

Based on this information, summarize the background and intent of this commit. Please follow this format:

Intent:
(Explain the core purpose and problem being solved in 2-3 sentences)

What Changed:
(Brief summary of actual modifications)

Conversation Flow:
(Describe any trial-and-error or considerations during development)

---END---"#,
            context, commit_message
        )
    }
    
    fn format_as_trailer(&self, summary: &str, language: Language) -> String {
        let header = match language {
            Language::Ko => "---사유---\n\n",
            Language::En => "---Reason---\n\n",
        };
        
        format!("\n\n{}\n{}", header, summary)
    }
}
