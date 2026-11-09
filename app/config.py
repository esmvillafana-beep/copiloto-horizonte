"""Configuración exclusivamente del servidor; sin claves predeterminadas."""
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    operations_key: str
    risk_key: str
    mode: str = "extractive"
    llm_base_url: str = "http://ollama:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen2.5:1.5b"
    llm_timeout: float = 90.0
    threshold: float = 0.18
    corpus_path: Path = Path(__file__).resolve().parents[1] / "data/corpus.json"

    def __post_init__(self):
        if min(len(self.operations_key), len(self.risk_key)) < 24:
            raise ValueError("Configura dos claves distintas de al menos 24 caracteres.")
        if self.operations_key == self.risk_key:
            raise ValueError("Las claves de los roles deben ser distintas.")
        if self.mode not in {"extractive", "llm"}:
            raise ValueError("ANSWER_MODE debe ser extractive o llm.")
        if not 0 < self.threshold <= 1:
            raise ValueError("RETRIEVAL_THRESHOLD debe pertenecer a (0,1].")
        if self.llm_timeout <= 0:
            raise ValueError("LLM_TIMEOUT debe ser positivo.")
        if self.mode == "llm" and not self.llm_base_url.startswith(("http://", "https://")):
            raise ValueError("LLM_BASE_URL debe ser una URL HTTP válida.")

    @classmethod
    def from_env(cls):
        return cls(
            operations_key=os.getenv("OPERACIONES_API_KEY", ""),
            risk_key=os.getenv("RIESGOS_API_KEY", ""),
            mode=os.getenv("ANSWER_MODE", "extractive"),
            llm_base_url=os.getenv("LLM_BASE_URL", "http://ollama:11434/v1"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "qwen2.5:1.5b"),
            llm_timeout=float(os.getenv("LLM_TIMEOUT", "90")),
            threshold=float(os.getenv("RETRIEVAL_THRESHOLD", "0.18")),
        )
