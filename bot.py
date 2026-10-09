import os
import sys
import logging
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from utils.helpers import configurar_logger, salvar_dica
from utils.instagram import extrair_url_instagram, processar_link_instagram, limpar_arquivo_temporario
from utils.voice import transcrever_audio
from utils.analyzer import AnalisadorDeConteudo
from utils.notion_sync import sincronizar_com_notion
from utils.compiler import obter_resumo_estatisticas, compilar_guia

load_dotenv()
logger = configurar_logger("bot.log")
analisador = AnalisadorDeConteudo()

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem inicial de boas-vindas do AnotaAí."""
    texto = (
        "✍️ **Olá! Eu sou o AnotaAí, seu Curador Pessoal de Instagram.**\n\n"
        "Cansado de salvar posts e Reels no Instagram e nunca mais abrir? Deixe comigo!\n\n"
        "Basta **compartilhar o link de qualquer post ou Reels** aqui comigo:\n"
        "• 🔨 **Reforma & Apê:** Eu anoto o checklist de obra e erros a evitar.\n"
        "• 🍝 **Culinária:** Eu anoto os ingredientes e o modo de preparo passo a passo.\n"
        "• 🏋️ **Treino & Saúde:** Eu ficho a execução correta e os cuidados.\n"
        "• ✈️ **Viagens, Finanças ou Tech:** Eu extraio o resumo mastigado.\n\n"
        "Tudo é transcrito por IA, catalogado e **salvo no seu Notion** em formato de checklist!\n\n"
        "📋 **Comandos úteis:**\n"
        "• `/categorias` - Veja seus posts arquivados por tema\n"
        "• `/compilado` - A IA cria um dossiê geral de tudo o que você salvou\n"
        "• `/compilado [tema]` - Ex: `/compilado reforma` ou `/compilado receitas`"
    )
    await update.message.reply_text(texto, parse_mode=ParseMode.MARKDOWN)

async def comando_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe estatísticas das anotações salvas."""
    resumo = obter_resumo_estatisticas()
    await update.message.reply_text(resumo, parse_mode=ParseMode.MARKDOWN)

async def comando_compilado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera um dossiê consolidado via IA."""
    termo_filtro = " ".join(context.args).strip() if context.args else None
    
    msg_status = await update.message.reply_text(
        f"⏳ Consultando a IA para compilar suas anotações{' sobre ' + termo_filtro if termo_filtro else ''}... Aguarde alguns instantes."
    )
    
    guia = compilar_guia(categoria_filtro=termo_filtro)
    
    # Divide mensagens se exceder o limite do Telegram (4096 caracteres)
    if len(guia) > 4000:
        partes = [guia[i:i+4000] for i in range(0, len(guia), 4000)]
        for parte in partes:
            await update.message.reply_text(parte, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(guia, parse_mode=ParseMode.MARKDOWN)

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa links do Instagram e orquestra extração, IA e Notion."""
    texto_usuario = update.message.text or ""
    url_instagram = extrair_url_instagram(texto_usuario)

    if not url_instagram:
        await update.message.reply_text(
            "Mande o link de um post ou Reels do Instagram para eu anotar para você, ou use `/compilado` para ver suas notas."
        )
        return

    msg_status = await update.message.reply_text("📥 Link recebido! Extraindo legenda e áudio do post...")

    midia_path = None
    try:
        # 1. Extração do Instagram
        info_ig = processar_link_instagram(url_instagram)
        if not info_ig.get("sucesso"):
            erro_msg = info_ig.get("erro", "Erro ao acessar o post do Instagram.")
            await msg_status.edit_text(f"⚠️ Não consegui acessar o post: {erro_msg}")
            return

        midia_path = info_ig.get("arquivo_midia")
        transcricao = None

        # 2. Transcrição de Áudio se houver vídeo/som
        if midia_path:
            await msg_status.edit_text("🎙️ Transcrevendo áudio do vídeo via Azure Speech AI...")
            transcricao = transcrever_audio(midia_path)
        elif info_ig.get("imagens_bytes"):
            qtd_slides = len(info_ig.get("imagens_bytes"))
            await msg_status.edit_text(f"🖼️ Lendo {qtd_slides} slide(s) do carrossel com visão computacional da IA...")

        # 3. Análise e Estruturação com Azure Foundry (GPT-4.1-nano)
        await msg_status.edit_text("🧠 Fichando o conteúdo com a IA: extraindo escolhas e pontos-chave...")
        analise = analisador.analisar_post(
            url=url_instagram,
            autor=info_ig.get("autor", "Instagram"),
            legenda=info_ig.get("legenda", ""),
            transcricao_audio=transcricao,
            imagens_bytes=info_ig.get("imagens_bytes")
        )

        # 4. Salva localmente (Backup garantido)
        salvar_dica(analise)

        # 5. Sincroniza com Notion se configurado
        notion_ok = sincronizar_com_notion(analise)

        # 6. Formata resposta amigável para o Telegram
        titulo = analise.get("titulo") or analise.get("titulo_dica") or "Nova Anotação"
        categoria = analise.get("categoria", "Geral")
        subcategoria = analise.get("subcategoria") or analise.get("comodo_ou_etapa") or ""
        resumo = analise.get("resumo_executivo", "")
        passos = analise.get("passos_ou_checklist") or analise.get("checklist_pratico") or []
        alertas = analise.get("erros_ou_alertas") or analise.get("erros_comuns_a_evitar") or []

        resposta = (
            f"✅ **Anotado com Sucesso!**\n\n"
            f"📌 **{titulo}**\n"
            f"🏷️ **Categoria:** {categoria}" + (f" ({subcategoria})\n\n" if subcategoria else "\n\n") +
            f"💡 **Resumo:**\n{resumo}\n\n"
        )

        if passos:
            header_passos = "📋 **Ingredientes / Passo a Passo:**\n" if "Culinária" in categoria else "📋 **Checklist / Passos Práticos:**\n"
            resposta += header_passos
            for item in passos:
                resposta += f"• {item}\n"
            resposta += "\n"

        if alertas:
            header_alerta = "💡 **Dica de Ouro:**\n" if "Culinária" in categoria else "⚠️ **Atenção / Erros a Evitar:**\n"
            resposta += header_alerta
            for alerta in alertas:
                resposta += f"• {alerta}\n"
            resposta += "\n"

        if notion_ok:
            resposta += "📝 *Card criado e arquivado no seu Notion!*\n"

        resposta += f"🔗 [Acessar Post Original]({url_instagram})"

        await msg_status.edit_text(resposta, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Erro no processamento da mensagem: {e}", exc_info=True)
        await msg_status.edit_text(f"❌ Ocorreu um erro ao processar o link: {str(e)[:200]}")
    finally:
        limpar_arquivo_temporario(midia_path)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("ERRO: TELEGRAM_BOT_TOKEN não configurado no .env!")
        print("⚠️ Defina a variável TELEGRAM_BOT_TOKEN no arquivo .env para iniciar.")
        return

    logger.info("Iniciando o AnotaAí Bot (Telegram)...")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("categorias", comando_categorias))
    app.add_handler(CommandHandler("compilado", comando_compilado))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))

    app.run_polling()

if __name__ == "__main__":
    main()
