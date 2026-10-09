import os
import json
import base64
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger("instabot")

PROMPT_SISTEMA_CURADOR = """
Você é o "CompilaAI", um Curador Pessoal de Conteúdo de altíssima precisão e concisão.
O usuário salva posts e Reels do Instagram para ter um acervo organizado sem perder tempo anotando.

Sua missão é extrair a lista exata de DICAS, LUGARES, PASSOS, INGREDIENTES ou ESCOLHAS mostradas no post/imagens.

REGRAS CRÍTICAS E OBRIGATÓRIAS:
1. NUNCA EXTRAIA FRASES DE ENGAJAMENTO OU REDES SOCIAIS:
   - IGNORE COMPLETAMENTE: "Passa pro lado", "Arraste para o lado", "Marque quem vai com você", "Comente aqui", "Siga nosso perfil", "Link na bio", "Compartilhe esse post", etc.
   - Isso NUNCA é conteúdo nem dica!

2. LEIA O CONTEÚDO REAL DAS IMAGENS E DO ÁUDIO:
   - Se for um post de LUGARES / RESTAURANTES / CAFÉS: Extraia o NOME e detalhes de CADA lugar citado em cada slide das fotos! (Ex: 'Caffé Ristoro', 'Café Teatro', 'Les Deux Magots', 'Café Mestiço', etc.).
   - Se for um post de REFORMA / OBRA: Extraia a lista de etapas reais ou escolhas feitas (ex: '01. Pega as chaves', '02. Demolição', 'Bancada em L').
   - Se for CULINÁRIA: Extraia os ingredientes e o modo de preparo.

3. CLASSIFICAÇÃO DE CATEGORIAS:
   - Se o post for sobre restaurantes, bares, cafés, passeios ou roteiros em SP, classifique ESTRITAMENTE como 'Lugares em SP'.
   - Opções válidas de categoria:
     * Lugares em SP
     * Reforma & Apartamento
     * Culinária & Receitas
     * Treino & Saúde
     * Finanças
     * Dicas Gerais

4. DIRETO AO PONTO:
   - O usuário quer bater o olho e ler a lista limpa em bullet points.
   - Resumo curto: 1 linha apenas de contexto.

Responda ESTRITAMENTE em formato JSON:
{
  "titulo": "Título objetivo (ex: 6 Cafés Charmosos e Fofos em São Paulo)",
  "categoria": "Lugares em SP",
  "subcategoria": "Cafés & Gastronomia",
  "resumo_executivo": "1 linha curta de contexto",
  "dicas_ou_passos": [
    "Nome ou dica 1...",
    "Nome ou dica 2..."
  ],
  "alertas": []
}
"""

class AnalisadorDeConteudo:
    def __init__(self):
        load_dotenv(override=True)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://ai-foundry-kevin.services.ai.azure.com/openai/v1")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-nano")

        if not self.api_key:
            logger.warning("Credenciais do Azure OpenAI não configuradas no .env!")
            self.client = None
        else:
            self.client = OpenAI(
                base_url=self.endpoint,
                api_key=self.api_key
            )

    def analisar_post(
        self, 
        url: str, 
        autor: str, 
        legenda: str, 
        transcricao_audio: Optional[str] = None,
        imagens_bytes: Optional[List[bytes]] = None
    ) -> Dict[str, Any]:
        """Processa as informações do post e gera anotações objetivas em bullet points com conteúdo real."""
        if not self.client:
            raise ValueError("Azure OpenAI não está configurado. Verifique o arquivo .env.")

        prompt_texto = f"URL DO POST: {url}\nAUTOR: @{autor}\n\nLEGENDA DO POST:\n{legenda}\n"
        if transcricao_audio:
            prompt_texto += f"\nTRANSCRIÇÃO DO ÁUDIO DO VÍDEO/REELS:\n{transcricao_audio}\n"

        conteudo_mensagem = [{"type": "text", "text": prompt_texto}]

        if imagens_bytes:
            logger.info(f"Analisando {len(imagens_bytes)} slide(s) de imagem com visão no {self.model}...")
            for img_byte in imagens_bytes:
                b64 = base64.b64encode(img_byte).decode("utf-8")
                conteudo_mensagem.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                })

        logger.info(f"Enviando post para análise no Azure Foundry ({self.model})...")
        
        resposta = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA_CURADOR},
                {"role": "user", "content": conteudo_mensagem}
            ],
            temperature=0.1
        )
        texto_resposta = resposta.choices[0].message.content.strip()

        if texto_resposta.startswith("```"):
            linhas = texto_resposta.split("\n")
            if linhas[0].startswith("```"):
                linhas = linhas[1:]
            if linhas and linhas[-1].startswith("```"):
                linhas = linhas[:-1]
            texto_resposta = "\n".join(linhas).strip()

        try:
            dados = json.loads(texto_resposta)
        except Exception as e:
            logger.error(f"Falha ao decodificar JSON retornado pelo modelo: {texto_resposta}. Erro: {e}")
            dados = {
                "titulo": "Anotação de Post Salvo",
                "categoria": "Dicas Gerais",
                "subcategoria": "Geral",
                "resumo_executivo": legenda[:200] if legenda else "",
                "dicas_ou_passos": [],
                "alertas": []
            }

        # Filtro de segurança adicional: remove itens que contenham 'passa pro lado' ou 'marca quem' caso o modelo ainda erre
        itens_filtrados = []
        for item in dados.get("dicas_ou_passos", []):
            item_lower = item.lower()
            if "passa" in item_lower and "lado" in item_lower:
                continue
            if "marca" in item_lower and "quem" in item_lower:
                continue
            if "siga @" in item_lower:
                continue
            itens_filtrados.append(item)
        dados["dicas_ou_passos"] = itens_filtrados

        dados["url"] = url
        dados["autor"] = autor
        dados["transcricao"] = transcricao_audio or ""
        agora = datetime.now()
        dados["criado_em"] = agora.strftime("%d/%m/%Y às %H:%M")
        dados["data_iso"] = agora.strftime("%Y-%m-%d")

        # Compatibilidade com campos antigos
        dados["passos_ou_checklist"] = dados["dicas_ou_passos"]
        dados["erros_ou_alertas"] = dados.get("alertas", [])

        return dados
