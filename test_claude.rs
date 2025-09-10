use sayu::collectors::{Collector, ClaudeCollector};
use std::path::Path;

#[tokio::main]
async fn main() {
    std::env::set_var("SAYU_DEBUG", "1");
    let collector = ClaudeCollector::new();
    let repo_root = Path::new("/Users/hwisookim/sayu");
    
    // Test with a recent timestamp (10 minutes ago)
    let since_ts = chrono::Utc::now().timestamp_millis() - 600000;
    
    println!("Testing Claude collector with since_ts: {}", since_ts);
    match collector.collect(repo_root, Some(since_ts)).await {
        Ok(events) => {
            println!("Found {} events", events.len());
            for (i, event) in events.iter().take(3).enumerate() {
                println!("Event {}: {:?}", i+1, event.text.chars().take(50).collect::<String>());
            }
        }
        Err(e) => println!("Error: {}", e),
    }
}
