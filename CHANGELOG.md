# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Sayu
- AI-powered commit message generation
- Support for Claude, Cursor, and CLI collectors
- Interactive configuration system
- Git hooks management
- Local data storage with SQLite
- Privacy-focused design

### Security
- Implemented shell command sanitization
- Added API key protection
- Enforced local-only data storage

### Changed
- Migrated from complex to simple configuration system
- Improved error handling and user feedback
- Removed git notes dependency

### Fixed
- Shell injection vulnerabilities
- Type safety issues
- Platform-specific bugs