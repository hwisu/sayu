use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserConfig {
    pub language: Language,
    // These are now hardcoded defaults, not configurable
    #[serde(skip)]
    pub enabled: bool,
    #[serde(skip)]
    pub commit_trailer: bool,
    #[serde(skip)]
    pub connectors: Connectors,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Language {
    Ko,
    En,
}

#[derive(Debug, Clone)]
pub struct Connectors {
    pub claude: bool,
    pub cursor: bool,
    pub cli_mode: CliMode,
    pub git: bool,
}

#[derive(Debug, Clone)]
pub enum CliMode {
    ZshPreexec,
    Off,
}

impl Default for UserConfig {
    fn default() -> Self {
        Self {
            language: Language::Ko,
            enabled: true,
            commit_trailer: true,
            connectors: Connectors::default(),
        }
    }
}

impl Default for Connectors {
    fn default() -> Self {
        Self {
            claude: true,
            cursor: true,
            cli_mode: CliMode::ZshPreexec,
            git: true,
        }
    }
}

pub struct ConfigManager {
    _repo_root: PathBuf,
    config: UserConfig,
}

impl ConfigManager {
    const CONFIG_FILE: &'static str = ".sayu.yml";

    pub fn new(repo_root: impl AsRef<Path>) -> Result<Self> {
        let repo_root = repo_root.as_ref().to_path_buf();
        let config = Self::load_config(&repo_root)?;
        
        Ok(Self {
            _repo_root: repo_root,
            config,
        })
    }

    fn load_config(repo_root: &Path) -> Result<UserConfig> {
        let config_path = repo_root.join(Self::CONFIG_FILE);
        
        if config_path.exists() {
            let contents = std::fs::read_to_string(&config_path)?;
            let partial_config: PartialConfig = serde_yaml::from_str(&contents)?;
            
            // Only language is configurable from file
            Ok(UserConfig {
                language: partial_config.language.unwrap_or(Language::Ko),
                ..Default::default()
            })
        } else {
            Ok(UserConfig::default())
        }
    }

    pub fn get(&self) -> &UserConfig {
        // Check environment variable override for language only
        if let Ok(_lang) = std::env::var("SAYU_LANG") {
            // For simplicity, returning the stored config
            // In a full implementation, we'd create a new config with the override
            &self.config
        } else {
            &self.config
        }
    }

    pub fn create_default(repo_root: impl AsRef<Path>) -> Result<()> {
        let config_path = repo_root.as_ref().join(Self::CONFIG_FILE);
        
        if config_path.exists() {
            return Ok(());
        }

        let default_content = r#"# Sayu Configuration
# 커밋에 '왜'를 남기는 개인 로컬 블랙박스

language: ko  # 언어 설정 (ko, en)

# Note: The following settings are now hardcoded defaults:
# - enabled: always true
# - commitTrailer: always true  
# - connectors: all enabled by default
"#;

        std::fs::write(&config_path, default_content)?;
        println!("Created config at {}", config_path.display());
        
        Ok(())
    }
}

// Helper struct for partial deserialization
#[derive(Deserialize)]
struct PartialConfig {
    language: Option<Language>,
}