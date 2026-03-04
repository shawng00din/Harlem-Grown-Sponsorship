from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    COMPANIES_API_KEY: str = ""
    COMPANIES_API_BASE_URL: str = "https://api.thecompaniesapi.com/v2"

    DOUBLE_THE_DONATION_API_KEY: str = ""
    DOUBLE_THE_DONATION_BASE_URL: str = "https://doublethedonation.com/api/v2"

    # Set to true only in production — each run triggers an extra LLM call
    # to extract and store conversation learnings. Keep false during development.
    ENABLE_LEARNING: bool = False

    OUTPUTS_DIR: str = "./outputs"
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"
    SEED_LIST_PATH: str = "./seed/curated_seed_list.json"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def outputs_path(self, subfolder: str = "") -> Path:
        p = Path(self.OUTPUTS_DIR)
        if subfolder:
            p = p / subfolder
        p.mkdir(parents=True, exist_ok=True)
        return p

    def kb_path(self) -> Path:
        return Path(self.KNOWLEDGE_BASE_DIR)


settings = Settings()
