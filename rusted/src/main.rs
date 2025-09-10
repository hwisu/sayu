use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    sayu::cli::run().await
}