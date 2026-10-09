import os
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from utils.helpers import listar_dicas
from openai import OpenAI

logger = logging.getLogger("instabot")

PROMPT_SISTEMA_COMPILADOR = """
Você é o "AnotaAí", um Curador Pessoal de Conhecimento.
O usuário salvou diversas dicas, tutoriais ou receitas nos últimos dias pelo Instagram.
Sua missão é sintetizar essas anotações em um GUIA / DOSSIÊ CONSOLIDADO, claro, prático e agradável de ler.

Diretrizes:
1. Elimine redundâncias e junte conteúdos complementares.
2. Agrupe de forma lógica (ex: se forem receitas, divida em etapas ou tipos; se for reforma, divida por cômodos/etapas de obra).
3. Seja prático: use listas, checklists e passos numerados claros.
4. Adicione uma seção de '💡 PONTOS CHAVE & ALERTAS' com as melhores dicas que o usuário não pode esquecer.
"""

def obter_resumo_estatisticas() -> str:
    """Retorna um resumo da quantidade de dicas salvas por categoria."""
    dicas = listar_dicas()
    if not dicas:
        return "📭 Nenhuma anotação salva ainda. Envie links de posts ou reels do Instagram para eu fichar para você!"

    contagem = Counter([d.get("categoria", "Geral") for d in dicas])
    total = len(dicas)

    linhas = [f"📊 **Suas Anotações Salvas ({total} posts arquivados):**\n"]
    for cat, qtd in contagem.most_common():
        linhas.append(f"• **{cat}**: {qtd} anotação(ões)")

    linhas.append("\n💡 *Use `/compilado` para gerar um resumo geral ou `/compilado [tema]` (ex: `/compilado receita` ou `/compilado reforma`)*")
    return "\n".join(linhas)

def compilar_guia(categoria_filtro: Optional[str] = None) -> str:
    """
    Consolida as anotações salvas (geral ou filtrado por categoria) utilizando o modelo da Azure Foundry.
    """
    dicas = listar_dicas()
    if not dicas:
        return "📭 Nenhuma anotação salva ainda para compilar."

    if categoria_filtro:
        filtro_lower = categoria_filtro.lower()
        dicas_filtradas = [
            d for d in dicas 
            if filtro_lower in d.get("categoria", "").lower() or filtro_lower in d.get("subcategoria", "").lower()
        ]
        if not dicas_filtradas:
            return f"🔎 Nenhuma anotação encontrada para o filtro '{categoria_filtro}'. Use /categorias para ver as opções salvas."
        dicas = dicas_filtradas

    # Monta texto consolidado para enviar à IA
    bloco_conteudo = []
    for idx, d in enumerate(dicas, 1):
        bloco = (
            f"--- ITEM #{idx} ---\n"
            f"Título: {d.get('titulo') or d.get('titulo_dica')}\n"
            f"Categoria: {d.get('categoria')} ({d.get('subcategoria') or d.get('comodo_ou_etapa')})\n"
            f"Resumo: {d.get('resumo_executivo')}\n"
            f"Passos/Checklist: {'; '.join(d.get('passos_ou_checklist') or d.get('checklist_pratico') or [])}\n"
            f"Alertas/Erros: {'; '.join(d.get('erros_ou_alertas') or d.get('erros_comuns_a_evitar') or [])}\n"
        )
        bloco_conteudo.append(bloco)

    prompt_usuario = (
        f"Abaixo estão {len(dicas)} itens arquivados pelo usuário.\n"
        f"Gere um guia compilado e estruturado:\n\n"
        + "\n".join(bloco_conteudo)
    )

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://ai-foundry-kevin.services.ai.azure.com/openai/v1")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-nano")

    if not api_key:
        return "⚠️ Chave do Azure OpenAI não configurada no .env."

    try:
        client = OpenAI(base_url=endpoint, api_key=api_key)
        logger.info(f"Gerando dossiê compilado via Azure Foundry ({model})...")
        
        resposta = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA_COMPILADOR},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.3
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erro ao compilar guia com IA: {e}")
        return f"⚠️ Ocorreu um erro ao gerar o compilado: {e}"
