# 🧠 CompilaAI — Seu Segundo Cérebro de Curadoria para o Instagram

O **CompilaAI** é um assistente pessoal no Telegram que resolve a dor do "cemitério de posts salvos". Ele processa links do Instagram (Reels e carrosséis de fotos), transcreve áudios com **Azure Speech AI**, lê textos das imagens com **Visão Computacional Multimodal (Azure OpenAI GPT-4.1-nano)** e cataloga tudo de forma estruturada no seu **Notion**, organizado em pastas por categoria com posts em tópicos contraídos (Toggles).

---

## 🎯 Por que o CompilaAI existe?
Diariamente somos bombardeados por excelentes recomendações no Instagram: cafés charmosos em SP, etapas de reforma do apartamento, receitas práticas, treinos e finanças. No entanto, quase ninguém abre os posts salvos depois por falta de tempo para reassistir aos vídeos e anotar.

O **CompilaAI** faz todo esse trabalho por você:
1. **Compartilhe o post no Telegram** direto do app do Instagram.
2. O bot:
   * **Se for vídeo/Reels:** Transcreve a fala do especialista via **Azure Speech AI**.
   * **Se for carrossel de fotos:** Baixa as imagens e lê o texto dos slides via **Visão Computacional**.
   * **Filtro Anti-Engajamento:** Ignora clichês de redes sociais (*"passa pro lado"*, *"marca quem vai"*) e extrai exclusivamente o conteúdo real.
3. Classifica na categoria correta:
   * 📍 **Lugares em SP** (cafés, restaurantes, bares e passeios)
   * 🔨 **Reforma & Apartamento** (etapas de obra, acabamentos e checklists)
   * 🍝 **Culinária & Receitas** (ingredientes e modo de preparo)
   * 🏋️ **Treino & Saúde** (exercícios e execução)
   * 💰 **Finanças & Investimentos**
   * 💡 **Dicas Gerais & Outros**
4. Cria uma pasta dedicada no **Notion** com cada post em uma **setinha contraída (Toggle)** contendo a data da análise, o link original e os bullet points diretos ao ponto.
5. Com o comando `/compilado [tema]`, a IA gera um **Guia Mestre** consolidado sob demanda.

---

## 🛠️ Arquitetura da Solução

```
                    [ 📱 Instagram ]
                           │
                (Compartilhar Link)
                           ▼
                 [ 🤖 Bot Telegram ]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [ 📸 Carrossel de Fotos ]   [ 🎙️ Áudio do Reels ]
             │                           │
   (Visão Computacional)          (Azure Speech AI)
             │                           │
             └─────────────┬─────────────┘
                           ▼
          [ 🧠 Azure OpenAI: GPT-4.1-nano ]
         (Extrai tópicos reais em bullet points)
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [ 💾 Backup Local ]         [ 📝 Notion Hub ]
    (data/dicas.json)       (Botões + Pastas com Toggles)
```

---

## 🚀 Como Executar

### 1. Pré-requisitos
* Python 3.10 ou superior
* Token de Bot no Telegram (criado via [@BotFather](https://t.me/BotFather))
* Chave de API do **Azure AI Foundry (GPT-4.1-nano)**
* Chave do **Azure Speech AI**
* Token de Integração do **Notion**

### 2. Configurar o `.env`
Preencha o arquivo `.env` na raiz do projeto:
```ini
TELEGRAM_BOT_TOKEN=seu_token_do_telegram

AZURE_OPENAI_API_KEY=sua_chave_azure_openai
AZURE_OPENAI_ENDPOINT=https://ai-foundry-kevin.services.ai.azure.com/openai/v1
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-nano
AZURE_OPENAI_API_VERSION=none

AZURE_SPEECH_KEY=sua_chave_azure_speech
AZURE_SPEECH_REGION=eastus2

NOTION_API_KEY=ntn_sua_chave_notion
NOTION_DATABASE_ID=id_da_sua_database_notion
```

### 3. Rodar Localmente
```bash
# Ativar o ambiente virtual
.\.venv\Scripts\activate

# Iniciar o bot
python bot.py
```

---

## ☁️ Deploy em Nuvem (Azure Container Apps)

Para deixar o bot rodando 24/7 sem depender do seu computador ligado, utilize o **Azure Cloud Shell**:

```bash
# 1. Clonar o repositório
git clone https://github.com/KevinShiroma/CompilaAI.git
cd CompilaAI

# 2. Criar Resource Group em East US 2 (região mais barata)
az group create --name rg-compila-ai --location eastus2

# 3. Compilar e subir o container
az containerapp up \
  --name compila-ai-bot \
  --resource-group rg-compila-ai \
  --location eastus2 \
  --source .

# 4. Configurar as variáveis de ambiente
az containerapp update \
  --name compila-ai-bot \
  --resource-group rg-compila-ai \
  --set-env-vars \
    TELEGRAM_BOT_TOKEN="..." \
    AZURE_OPENAI_API_KEY="..." \
    AZURE_OPENAI_ENDPOINT="https://ai-foundry-kevin.services.ai.azure.com/openai/v1" \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4.1-nano" \
    AZURE_SPEECH_KEY="..." \
    AZURE_SPEECH_REGION="eastus2" \
    NOTION_API_KEY="..." \
    NOTION_DATABASE_ID="..."
```

---

## 💬 Comandos no Telegram

| Comando | Descrição |
| :--- | :--- |
| `[Link do Instagram]` | Processa o post/reels, transcreve áudio/fotos e salva na pasta correspondente do Notion. |
| `/categorias` | Exibe a contagem de posts arquivados por categoria. |
| `/compilado` | A IA sintetiza todas as anotações em um dossiê geral. |
| `/compilado [tema]` | Gera o compilado específico (ex: `/compilado lugares` ou `/compilado reforma`). |
| `/start` | Mensagem de boas-vindas e orientações. |

---

## 📂 Estrutura de Pastas

```text
CompilaAI/
├── .venv/                   # Ambiente virtual Python
├── data/
│   └── dicas.json           # Backup offline de segurança (JSON)
├── utils/
│   ├── analyzer.py          # IA com visão computacional, filtro anti-engajamento e bullet points
│   ├── compiler.py          # Síntese e geração de manuais consolidados por tema
│   ├── helpers.py           # Logging e persistência atômica
│   ├── instagram.py         # Extrator de carrosséis e áudio via yt-dlp + Instaloader
│   ├── notion_sync.py       # Gerenciamento de pastas, botões e toggles no Notion
│   └── voice.py             # Pipeline de áudio PyAV + Azure Speech SDK
├── .dockerignore            # Exclusões para compilação Docker enxuta
├── Dockerfile               # Containerização Linux (Python 3.11 Slim + FFmpeg)
├── bot.py                   # Ponto de entrada do Telegram Bot
├── requirements.txt         # Dependências do projeto
└── README.md                # Documentação completa
```