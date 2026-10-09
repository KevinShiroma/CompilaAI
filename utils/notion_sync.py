import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger("instabot")

PAGE_HUB_ID = "3f4cbae044b580e48ee2d138ee614c91"

CATEGORIAS_CONFIG = {
    "Lugares em SP": {
        "nome": "📍 Lugares em SP",
        "emoji": "📍",
        "cover": "https://images.unsplash.com/photo-1543051932-6ef9fecfbc80?q=80&w=2000&auto=format&fit=crop",
        "page_id": "3f4cbae0-44b5-81e2-a1ff-cacd23a0c2b6"
    },
    "Reforma & Apartamento": {
        "nome": "🔨 Reforma & Apartamento",
        "emoji": "🔨",
        "cover": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=2000&auto=format&fit=crop",
        "page_id": "3f4cbae0-44b5-8106-94e8-c7a50008d53b"
    },
    "Culinária & Receitas": {
        "nome": "🍝 Culinária & Receitas",
        "emoji": "🍝",
        "cover": "https://images.unsplash.com/photo-1556910103-1c02745aae4d?q=80&w=2000&auto=format&fit=crop",
        "page_id": "3f4cbae0-44b5-8142-87bf-f4bcb1eb5bc2"
    },
    "Treino & Saúde": {
        "nome": "🏋️ Treino & Saúde",
        "emoji": "🏋️",
        "cover": "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=2000&auto=format&fit=crop",
        "page_id": "3f4cbae0-44b5-817a-bc5b-cb0238cdeac2"
    },
    "Finanças": {
        "nome": "💰 Finanças & Investimentos",
        "emoji": "💰",
        "cover": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=2000&auto=format&fit=crop",
        "page_id": "3f4cbae0-44b5-81f1-b90b-dc3ff475d44e"
    },
    "Dicas Gerais": {
        "nome": "💡 Dicas Gerais & Outros",
        "emoji": "💡",
        "cover": "https://images.unsplash.com/photo-1507925921958-8a62f3d1a50d?q=80&w=2000&auto=format&fit=crop",
        "page_id": "3f4cbae0-44b5-81ad-9db1-fdf4e7c2bf39"
    }
}

def normalizar_categoria(cat_raw: str, titulo: str = "", subcategoria: str = "") -> tuple[str, str, str, Optional[str]]:
    """Retorna o nome formatado, emoji, imagem de capa e ID fixo da subpágina."""
    texto_busca = f"{cat_raw} {titulo} {subcategoria}".lower()
    if any(k in texto_busca for k in ["lugar", "sp", "são paulo", "café", "restaurante", "roteiro", "passeio"]):
        conf = CATEGORIAS_CONFIG["Lugares em SP"]
        return conf["nome"], conf["emoji"], conf["cover"], conf.get("page_id")
    elif any(k in texto_busca for k in ["reforma", "apartamento", "apê", "obra", "construir", "construção", "decoração", "marcenaria", "gesso", "tomada"]):
        conf = CATEGORIAS_CONFIG["Reforma & Apartamento"]
        return conf["nome"], conf["emoji"], conf["cover"], conf.get("page_id")
    elif any(k in texto_busca for k in ["culinária", "receita", "doce", "bolo", "cozinha", "prato"]):
        conf = CATEGORIAS_CONFIG["Culinária & Receitas"]
        return conf["nome"], conf["emoji"], conf["cover"], conf.get("page_id")
    elif any(k in texto_busca for k in ["treino", "saúde", "fitness", "exercício", "dieta", "musculação"]):
        conf = CATEGORIAS_CONFIG["Treino & Saúde"]
        return conf["nome"], conf["emoji"], conf["cover"], conf.get("page_id")
    elif any(k in texto_busca for k in ["finança", "investimento", "dinheiro", "economia"]):
        conf = CATEGORIAS_CONFIG["Finanças"]
        return conf["nome"], conf["emoji"], conf["cover"], conf.get("page_id")

    conf_geral = CATEGORIAS_CONFIG["Dicas Gerais"]
    return conf_geral["nome"], conf_geral["emoji"], conf_geral["cover"], conf_geral.get("page_id")

def obter_ou_criar_pagina_categoria(notion_token: str, hub_id: str, nome_cat: str, emoji: str, cover_url: str, pre_id: Optional[str] = None) -> Optional[str]:
    """Busca ou cria uma subpágina dedicada para a categoria dentro do Hub CompilaAI."""
    if pre_id:
        return pre_id

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        r = requests.get(f"https://api.notion.com/v1/blocks/{hub_id}/children", headers=headers, timeout=15)
        if r.status_code == 200:
            target_clean = nome_cat.replace("📍", "").replace("🔨", "").replace("🍝", "").replace("🏋️", "").replace("💰", "").replace("💡", "").strip().lower()
            for b in r.json().get("results", []):
                if b.get("type") == "child_page":
                    p_title = b.get("child_page", {}).get("title", "").strip().lower()
                    if p_title == target_clean or nome_cat.lower() in p_title:
                        return b.get("id")

        # Cria a página com capa e ícone se realmente não existir
        data = {
            "parent": {"page_id": hub_id},
            "properties": {
                "title": [{"text": {"content": nome_cat}}]
            },
            "icon": {"emoji": emoji},
            "cover": {
                "type": "external",
                "external": {"url": cover_url}
            }
        }
        r_create = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data, timeout=15)
        if r_create.status_code == 200:
            cat_page_id = r_create.json().get("id")
            logger.info(f"Página da categoria '{nome_cat}' criada com sucesso (ID: {cat_page_id})")
            return cat_page_id
        else:
            logger.error(f"Erro ao criar página de categoria: {r_create.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao obter/criar página de categoria: {e}")
        return None

def criar_bloco_toggle_post(dica: Dict[str, Any]) -> Dict[str, Any]:
    """Cria um bloco contraído (Toggle) com os detalhes internos do post."""
    titulo = dica.get("titulo") or "Post Salvo"
    url = dica.get("url") or ""
    autor = dica.get("autor") or "Instagram"
    data_analise = dica.get("criado_em") or datetime.now().strftime("%d/%m/%Y às %H:%M")
    resumo = dica.get("resumo_executivo") or ""
    dicas_lista = dica.get("dicas_ou_passos") or dica.get("passos_ou_checklist") or []
    alertas = dica.get("alertas") or dica.get("erros_ou_alertas") or []

    filhos = []

    # 1. Link direto do Instagram
    if url:
        filhos.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"🔗 Link: "}},
                    {"type": "text", "text": {"content": f"@{autor}", "link": {"url": url}}},
                    {"type": "text", "text": {"content": f" ({url})", "link": {"url": url}}}
                ]
            }
        })

    # 2. Resumo/Contexto
    if resumo:
        filhos.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": f"💡 {resumo}"}}],
                "icon": {"emoji": "💡"},
                "color": "gray_background"
            }
        })

    # 3. Dicas / Lugares em bullet points limpos
    if dicas_lista:
        for item in dicas_lista:
            filhos.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": str(item)[:2000]}}]
                }
            })

    # 4. Alertas (se houver)
    if alertas:
        for alerta in alertas:
            filhos.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": f"⚠️ {str(alerta)[:2000]}"}, "annotations": {"color": "red"}}
                    ]
                }
            })

    # Bloco Toggle Heading (vem contraído por padrão no Notion)
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [
                {"type": "text", "text": {"content": f"📌 {titulo} "}, "annotations": {"bold": True}},
                {"type": "text", "text": {"content": f"({data_analise})"}, "annotations": {"italic": True, "color": "gray"}}
            ],
            "is_toggleable": True,
            "children": filhos
        }
    }

def adicionar_post_na_pagina_categoria(notion_token: str, cat_page_id: str, dica: Dict[str, Any]) -> bool:
    """Insere o post dentro da página da categoria em formato Toggle (setinha contraída)."""
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    bloco_toggle = criar_bloco_toggle_post(dica)

    try:
        r = requests.patch(
            f"https://api.notion.com/v1/blocks/{cat_page_id}/children",
            headers=headers,
            json={"children": [bloco_toggle, {"object": "block", "type": "divider", "divider": {}}]},
            timeout=15
        )
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Erro ao adicionar toggle na página da categoria: {e}")
        return False

def sincronizar_com_notion(dica: Dict[str, Any]) -> bool:
    """
    Sincroniza a anotação:
    1. Insere na tabela Master (Central de Anotações).
    2. Insere na Subpágina da Categoria em formato Toggle contraído.
    """
    load_dotenv(override=True)
    notion_token = os.getenv("NOTION_API_KEY", "").strip()
    database_id = os.getenv("NOTION_DATABASE_ID", "").strip()

    if not notion_token or not database_id:
        logger.info("Notion não configurado no .env.")
        return False

    try:
        titulo = dica.get("titulo") or "Nova Anotação"
        categoria_raw = dica.get("categoria", "Dicas Gerais")
        subcategoria = dica.get("subcategoria") or ""
        nome_cat_formatada, emoji_cat, cover_cat, pre_page_id = normalizar_categoria(categoria_raw, titulo=titulo, subcategoria=subcategoria)
        url_post = dica.get("url", "")
        autor = dica.get("autor", "Instagram")
        resumo = dica.get("resumo_executivo", "")
        dicas_lista = dica.get("dicas_ou_passos") or dica.get("passos_ou_checklist") or []
        alertas = dica.get("alertas") or dica.get("erros_ou_alertas") or []

        # 1. Linha na Base de Dados Master
        children_db = []
        if resumo:
            children_db.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": resumo}}],
                    "icon": {"emoji": "💡"}
                }
            })
        for item in dicas_lista:
            children_db.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": str(item)[:2000]}}]}
            })

        properties_db: Dict[str, Any] = {
            "Nome": {"title": [{"type": "text", "text": {"content": titulo[:100]}}]},
            "Categoria": {"select": {"name": nome_cat_formatada[:100]}},
            "Tópico": {"rich_text": [{"type": "text", "text": {"content": subcategoria[:100]}}]},
            "Autor": {"rich_text": [{"type": "text", "text": {"content": f"@{autor}"[:100]}}]}
        }
        if url_post:
            properties_db["Link"] = {"url": url_post}

        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json={"parent": {"database_id": database_id}, "properties": properties_db, "children": children_db},
            timeout=15
        )

        # 2. Insere na Subpágina da Categoria em formato Toggle contraído
        cat_page_id = obter_ou_criar_pagina_categoria(notion_token, PAGE_HUB_ID, nome_cat_formatada, emoji_cat, cover_cat, pre_id=pre_page_id)
        if cat_page_id:
            adicionar_post_na_pagina_categoria(notion_token, cat_page_id, dica)

        logger.info(f"Dica '{titulo}' sincronizada na tabela e na página '{nome_cat_formatada}' (Toggle contraído)!")
        return True

    except Exception as e:
        logger.error(f"Erro ao sincronizar com o Notion: {e}")
        return False
