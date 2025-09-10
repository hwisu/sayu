# Sayu (Rust Version)

Personal local blackbox for recording 'why' in commits - Rust implementation

## Key Changes from Python Version

### Simplified Configuration
- `enabled`, `commitTrailer`, and connector settings are now **hardcoded defaults** (always enabled)
- Only `language` setting remains configurable via `.sayu.yml` or `SAYU_LANG` environment variable
- This reduces configuration complexity while maintaining core functionality

### Default Settings
```rust
// Always enabled (not configurable)
enabled: true
commit_trailer: true
connectors: {
    claude: true,
    cursor: true,
    cli_mode: ZshPreexec,
    git: true
}

// Configurable
language: ko  // or en
```

## Building

```bash
cd rusted
cargo build --release
```

## Installation

```bash
# Build and install to system
cargo install --path .

# Or use the binary directly
./target/release/sayu init
```

## Usage

```bash
# Initialize in a git repository
sayu init

# Check system health
sayu health

# Show recent events
sayu show -n 10

# Uninstall from repository
sayu uninstall
```

## Project Structure

```
rusted/
├── src/
│   ├── domain/       # Core domain types (Event, EventKind, etc.)
│   ├── infra/        # Infrastructure (Config, Storage)
│   ├── cli/          # CLI commands and handlers
│   ├── lib.rs        # Library root
│   └── main.rs       # Binary entry point
└── Cargo.toml        # Dependencies
```

## Architecture Decisions

1. **Hardcoded Defaults**: Most settings are now compile-time constants for simplicity
2. **SQLite Storage**: Using rusqlite for event storage
3. **Async Runtime**: Tokio for future extensibility
4. **Error Handling**: anyhow for simplified error management

## Migration from Python

This Rust version maintains compatibility with the existing `.sayu/` directory structure:
- Same database schema
- Same config file location (`.sayu.yml`)
- Same Git hook integration

You can switch between Python and Rust versions without data loss.