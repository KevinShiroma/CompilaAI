import os
import json
import logging
from typing import Any, List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_MEDIA_DIR = os.path.join(BASE_DIR, "temp_media")
DICAS_PATH = os.path.join(DATA_DIR, "dicas.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_MEDIA_DIR, exist_ok=True)

def configurar_logger(log_filename: str = "bot.log") -> logging.Logger:
    """Configura logger gravando em console e em arquivo de log."""
    logger = logging.getLogger("instabot")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_path = os.path.join(BASE_DIR, log_filename)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def carregar_json(caminho: str, default: Any = None) -> Any:
    """Carrega dados de arquivo JSON de forma segura."""
    if not os.path.exists(caminho):
        return default if default is not None else []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.getLogger("instabot").error(f"Erro ao ler JSON {caminho}: {e}")
        return default if default is not None else []

def salvar_json(caminho: str, dados: Any) -> bool:
    """Salva dados em arquivo JSON de forma atômica."""
    temp_path = caminho + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, caminho)
        return True
    except Exception as e:
        logging.getLogger("instabot").error(f"Erro ao salvar JSON {caminho}: {e}")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False

def salvar_dica(dica: Dict[str, Any]) -> bool:
    """Adiciona uma nova dica processada à lista local em data/dicas.json."""
    dicas = carregar_json(DICAS_PATH, [])
    # Evita duplicar se o link do post já existir
    for idx, item in enumerate(dicas):
        if item.get("url") and item.get("url") == dica.get("url"):
            dicas[idx] = dica  # Atualiza
            return salvar_json(DICAS_PATH, dicas)
    
    dicas.append(dica)
    return salvar_json(DICAS_PATH, dicas)

def listar_dicas() -> List[Dict[str, Any]]:
    """Retorna todas as dicas salvas."""
    return carregar_json(DICAS_PATH, [])
