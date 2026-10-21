"""
Configuration management for the CrewAI service.

All credentials are read from environment variables (populate them via a
``.env`` file — see ``env.example`` — or your host's secret store). There is
deliberately no file-based fallback.
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def load_secret(secret_name: str, env_var_name: str = None) -> Optional[str]:
    """Load a credential from the environment.

    Resolution order:
      1. Explicit env var (``env_var_name``)
      2. ``secret_name`` upper-cased as an env var
    Returns ``None`` when neither is set. Never reads files.
    """
    if env_var_name:
        env_value = os.getenv(env_var_name)
        if env_value and env_value.strip():
            return env_value.strip()

    env_value = os.getenv(secret_name.upper())
    if env_value and env_value.strip():
        return env_value.strip()

    return None


def load_api_key(key_name: str) -> Optional[str]:
    """Convenience wrapper: read the ``{KEY_NAME}_API_KEY`` env var."""
    return load_secret(f"{key_name}_api_key", f"{key_name.upper()}_API_KEY")


# Credentials the service can use. Only the first three are required.
_KNOWN_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "BRAVE_API_KEY",
    "FIRECRAWL_API_KEY",
    "SERPER_API_KEY",
    "ANTHROPIC_API_KEY",
]


def ensure_env_secrets() -> None:
    """Log which credentials are present at startup (names only, never values).

    Kept as the single startup hook for credential checks; it no longer loads
    anything from disk.
    """
    present = [v for v in _KNOWN_ENV_VARS if os.getenv(v)]
    missing = [v for v in _KNOWN_ENV_VARS if not os.getenv(v)]
    logger.info(f"Credentials present in environment: {', '.join(present) or 'none'}")
    if missing:
        logger.info(f"Credentials not set (features needing them degrade gracefully): {', '.join(missing)}")


class Config:
    """Configuration manager for the CrewAI service"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        self._load_configuration()
    
    def _load_secret(self, secret_name: str, env_var_name: str = None) -> Optional[str]:
        """Load a secret — delegates to the standalone ``load_secret()``."""
        return load_secret(secret_name, env_var_name)
    
    def _load_configuration(self):
        """Load all configuration values"""
        # Supabase configuration
        self.supabase_url = self._load_secret("supabase_url", "SUPABASE_URL")
        self.supabase_service_key = self._load_secret("supabase_service_key", "SUPABASE_SERVICE_KEY")
        self.supabase_anon_key = self._load_secret("supabase_key", "SUPABASE_ANON_KEY") or self._load_secret("supabase_anon_key", "SUPABASE_ANON_KEY")
        self.supabase_access_token = self._load_secret("supabase_access_token", "SUPABASE_ACCESS_TOKEN")
        
        # API Keys
        self.openai_api_key = self._load_secret("openai_api_key", "OPENAI_API_KEY")
        self.gemini_api_key = self._load_secret("gemini_api_key", "GEMINI_API_KEY")
        self.anthropic_api_key = self._load_secret("anthropic_api_key", "ANTHROPIC_API_KEY")
        self.serper_api_key = self._load_secret("serper_api_key", "SERPER_API_KEY")
        self.brave_api_key = self._load_secret("brave_api_key", "BRAVE_API_KEY")
        self.uspto_api_key = self._load_secret("uspto_api_key", "USPTO_API_KEY")
        
        # Application configuration
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        
    
    def get_supabase_url(self) -> str:
        """Get Supabase URL"""
        if not self.supabase_url:
            raise ValueError("Supabase URL not configured")
        return self.supabase_url
    
    def get_supabase_key(self) -> str:
        """Get Supabase key (prefers service key for server operations)"""
        key = self.supabase_service_key or self.supabase_anon_key
        if not key:
            raise ValueError("Supabase key not configured")
        return key
    
    def get_supabase_service_key(self) -> str:
        """Get Supabase service key specifically"""
        if not self.supabase_service_key:
            raise ValueError("Supabase service key not configured")
        return self.supabase_service_key
    
    def get_supabase_anon_key(self) -> str:
        """Get Supabase anon key specifically"""
        if not self.supabase_anon_key:
            raise ValueError("Supabase anon key not configured")
        return self.supabase_anon_key
    
    def get_supabase_access_token(self) -> str:
        """Get Supabase access token for MCP"""
        if not self.supabase_access_token:
            raise ValueError("Supabase access token not configured")
        return self.supabase_access_token
    
    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key"""
        return self.openai_api_key
    
    def get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key"""
        return self.gemini_api_key
    
    def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key"""
        return self.anthropic_api_key
    
    def get_serper_api_key(self) -> Optional[str]:
        """Get Serper API key"""
        return self.serper_api_key
    
    def get_brave_api_key(self) -> Optional[str]:
        """Get Brave API key"""
        return self.brave_api_key
    
    def get_uspto_api_key(self) -> Optional[str]:
        """Get USPTO API key"""
        return self.uspto_api_key
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled"""
        return self.debug_mode
    
    def get_log_level(self) -> str:
        """Get configured log level"""
        return self.log_level
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration (without sensitive data)"""
        return {
            "environment": self.environment,
            "log_level": self.log_level,
            "debug_mode": self.debug_mode,
            "supabase_configured": bool(self.supabase_url and (self.supabase_service_key or self.supabase_anon_key)),
            "supabase_url_configured": bool(self.supabase_url),
            "supabase_service_key_configured": bool(self.supabase_service_key),
            "supabase_anon_key_configured": bool(self.supabase_anon_key),
            "supabase_access_token_configured": bool(self.supabase_access_token),
            "openai_api_key_configured": bool(self.openai_api_key),
            "gemini_api_key_configured": bool(self.gemini_api_key),
            "anthropic_api_key_configured": bool(self.anthropic_api_key),
            "serper_api_key_configured": bool(self.serper_api_key),
            "brave_api_key_configured": bool(self.brave_api_key),
            "uspto_api_key_configured": bool(self.uspto_api_key)
        }
    
    def validate_required_config(self) -> Dict[str, bool]:
        """Validate that required configuration is present"""
        return {
            "supabase_url": bool(self.supabase_url),
            "supabase_key": bool(self.supabase_service_key or self.supabase_anon_key),
            "at_least_one_llm_key": bool(self.openai_api_key or self.gemini_api_key or self.anthropic_api_key)
        }
    
    def get_missing_config(self) -> list[str]:
        """Get list of missing required configuration"""
        validation = self.validate_required_config()
        missing = []
        
        if not validation["supabase_url"]:
            missing.append("SUPABASE_URL")
        if not validation["supabase_key"]:
            missing.append("SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY")
        if not validation["at_least_one_llm_key"]:
            missing.append("At least one LLM API key (OPENAI_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY)")
        
        return missing


def print_config_summary():
    """Print a summary of the current configuration"""
    config = Config()
    summary = config.get_configuration_summary()
    
    print("🔧 Configuration Summary")
    print("=" * 40)
    print(f"Environment: {summary['environment']}")
    print(f"Log Level: {summary['log_level']}")
    print(f"Debug Mode: {summary['debug_mode']}")
    print()
    
    print("📊 Service Configuration:")
    print(f"  Supabase URL: {'✅' if summary['supabase_url_configured'] else '❌'}")
    print(f"  Supabase Service Key: {'✅' if summary['supabase_service_key_configured'] else '❌'}")
    print(f"  Supabase Anon Key: {'✅' if summary['supabase_anon_key_configured'] else '❌'}")
    print(f"  Supabase Access Token: {'✅' if summary['supabase_access_token_configured'] else '❌'}")
    print()
    
    print("🤖 LLM API Keys:")
    print(f"  OpenAI: {'✅' if summary['openai_api_key_configured'] else '❌'}")
    print(f"  Gemini: {'✅' if summary['gemini_api_key_configured'] else '❌'}")
    print(f"  Anthropic: {'✅' if summary['anthropic_api_key_configured'] else '❌'}")
    print()
    
    print("🔍 Search API Keys:")
    print(f"  Serper: {'✅' if summary['serper_api_key_configured'] else '❌'}")
    print(f"  Brave: {'✅' if summary['brave_api_key_configured'] else '❌'}")
    print(f"  USPTO: {'✅' if summary['uspto_api_key_configured'] else '❌'}")
    
    # Check for missing required config
    missing = config.get_missing_config()
    if missing:
        print()
        print("⚠️  Missing Required Configuration:")
        for item in missing:
            print(f"  - {item}")
    else:
        print()
        print("✅ All required configuration is present!")


# Global config instance
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


if __name__ == "__main__":
    print_config_summary()
