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

# LLM 설정 (환경변수로도 설정 가능)
# SAYU_OPENROUTER_API_KEY: OpenRouter API 키 (권장)
# SAYU_GEMINI_API_KEY: Google Gemini API 키
# SAYU_LLM_MODEL: 사용할 모델 (기본값: anthropic/claude-3.5-haiku)
# SAYU_LLM_TEMPERATURE: 창의성 수준 (0.0-1.0, 기본값: 0.7)
# SAYU_LLM_MAX_TOKENS: 최대 토큰 수 (기본값: 1000)

# 인기 있는 OpenRouter 모델들:
# - anthropic/claude-3.5-haiku (빠르고 비용 효율적)
# - anthropic/claude-3.5-sonnet (균형잡힌 성능)
# - openai/gpt-4o-mini (빠르고 저렴)
# - meta-llama/llama-3.1-8b-instruct (오픈소스)
"#;

        std::fs::write(&config_path, default_content)?;
        println!("Created config at {}", config_path.display());
        
        Ok(())
    }
}
