use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserConfig {
    pub language: Language,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Language {
    Ko,
    En,
}

impl Default for UserConfig {
    fn default() -> Self {
        Self {
            language: Language::Ko,
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
            let config: UserConfig = serde_yaml::from_str(&contents)?;
            Ok(config)
        } else {
            Ok(UserConfig::default())
        }
    }

    pub fn get(&self) -> UserConfig {
        // Check environment variable override for language
        if let Ok(lang) = std::env::var("SAYU_LANG") {
            let language = match lang.to_lowercase().as_str() {
                "en" => Language::En,
                "ko" => Language::Ko,
                _ => self.config.language.clone(),
            };
            UserConfig { language }
        } else {
            self.config.clone()
        }
    }

    pub fn get_language(&self) -> Language {
        // Check environment variable override
        if let Ok(lang) = std::env::var("SAYU_LANG") {
            match lang.to_lowercase().as_str() {
                "en" => Language::En,
                "ko" => Language::Ko,
                _ => self.config.language.clone(),
            }
        } else {
            self.config.language.clone()
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
"#;

        std::fs::write(&config_path, default_content)?;
        println!("Created config at {}", config_path.display());
        
        Ok(())
    }
}