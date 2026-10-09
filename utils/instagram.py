import os
import re
import uuid
import logging
from typing import Dict, Any, Optional, List
import requests
import yt_dlp
import instaloader
from utils.helpers import TEMP_MEDIA_DIR

logger = logging.getLogger("instabot")

PADRAO_INSTAGRAM = re.compile(r"https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/([a-zA-Z0-9_-]+)")

def extrair_url_instagram(texto: str) -> Optional[str]:
    """Identifica e extrai a URL do Instagram dentro de uma mensagem de texto."""
    match = PADRAO_INSTAGRAM.search(texto)
    if match:
        return match.group(0)
    return None

def extrair_shortcode(url: str) -> Optional[str]:
    """Extrai o shortcode único do post (ex: DeLNRBDDArP)."""
    match = PADRAO_INSTAGRAM.search(url)
    if match:
        return match.group(1)
    return None

def processar_link_instagram(url: str) -> Dict[str, Any]:
    """
    Extrai metadados, legendas, áudio (se vídeo) e imagens dos slides (se carrossel/foto).
    Suporta tanto Reels com áudio quanto posts com carrossel de fotos informativas.
    """
    logger.info(f"Processando link do Instagram: {url}")
    shortcode = extrair_shortcode(url)

    resultado = {
        "url": url,
        "titulo": "",
        "legenda": "",
        "autor": "Instagram",
        "arquivo_midia": None,
        "imagens_bytes": [],
        "sucesso": False,
        "erro": None
    }

    # 1. Tenta carregar informações estruturadas via Instaloader (excelente para carrosséis e fotos)
    if shortcode:
        try:
            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False
            )
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            resultado["autor"] = post.owner_username or post.owner_profile.full_name or "Instagram"
            resultado["legenda"] = post.caption or ""
            resultado["titulo"] = post.title or f"Post por @{resultado['autor']}"

            # Se for Carrossel de fotos (GraphSidecar)
            if post.typename == "GraphSidecar":
                logger.info(f"Post identificado como CARROSSEL DE FOTOS ({shortcode}). Baixando imagens dos slides...")
                nodes = list(post.get_sidecar_nodes())
                # Pega até 8 slides para leitura visual com IA
                for node in nodes[:8]:
                    img_url = node.display_url
                    if img_url:
                        try:
                            resp = requests.get(img_url, timeout=10)
                            if resp.status_code == 200:
                                resultado["imagens_bytes"].append(resp.content)
                        except Exception as e_img:
                            logger.warning(f"Falha ao baixar imagem do slide: {e_img}")
                resultado["sucesso"] = True
                return resultado

            # Se for foto única
            elif not post.is_video and post.url:
                logger.info(f"Post identificado como FOTO ÚNICA ({shortcode}). Baixando imagem...")
                try:
                    resp = requests.get(post.url, timeout=10)
                    if resp.status_code == 200:
                        resultado["imagens_bytes"].append(resp.content)
                except Exception as e_img:
                    logger.warning(f"Falha ao baixar imagem: {e_img}")
                resultado["sucesso"] = True
                return resultado

        except Exception as e_insta:
            logger.warning(f"Instaloader não conseguiu processar diretamente ({e_insta}). Tentando via yt-dlp...")

    # 2. Se for Vídeo/Reels (ou fallback), usa yt-dlp para baixar áudio
    identificador = str(uuid.uuid4())[:8]
    output_template = os.path.join(TEMP_MEDIA_DIR, f"ig_{identificador}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'format': 'bestaudio/best',
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                if not resultado["legenda"]:
                    resultado["legenda"] = info.get("description", "") or info.get("title", "")
                if not resultado["titulo"]:
                    resultado["titulo"] = info.get("title", "")
                if resultado["autor"] == "Instagram":
                    resultado["autor"] = info.get("uploader", "") or info.get("channel", "") or "Instagram"

                for ext in ["mp4", "m4a", "webm", "mp3", "ogg"]:
                    candidato = os.path.join(TEMP_MEDIA_DIR, f"ig_{identificador}.{ext}")
                    if os.path.exists(candidato):
                        resultado["arquivo_midia"] = candidato
                        break

                resultado["sucesso"] = True
                return resultado
    except Exception as e_ytdl:
        logger.error(f"Erro no download com yt-dlp: {e_ytdl}")

    if resultado["legenda"] or resultado["imagens_bytes"]:
        resultado["sucesso"] = True
    else:
        resultado["erro"] = "Não foi possível extrair dados nem mídia do link informado."

    return resultado

def limpar_arquivo_temporario(caminho: Optional[str]):
    """Remove arquivos temporários de mídia após processamento."""
    if caminho and os.path.exists(caminho):
        try:
            os.remove(caminho)
        except Exception:
            pass
