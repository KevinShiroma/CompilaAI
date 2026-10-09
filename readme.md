# 🏡 InstaBot - Curador Inteligente de Reforma & Apartamento

O **InstaBot** é um assistente pessoal no Telegram que processa posts e Reels do Instagram sobre obras, reformas, arquitetura e vistoria de imóveis. Ele transcreve vídeos via **Azure Speech AI**, analisa as boas práticas e erros comuns usando **Azure OpenAI (GPT-4o-mini)** e cataloga tudo de forma estruturada no seu **Notion** e em banco local, gerando dossiês e manuais sob demanda.

---

## 🎯 Por que este projeto existe?
Durante a fase de compra e reforma de um apartamento, somos bombardeados diariamente por dicas no Instagram (elétrica, hidráulica, marcenaria, caimento de ralos, vistoria de chaves). No entanto, quando realmente precisamos da informação na obra ou na reunião com empreiteiros, esses posts estão perdidos no histórico de "salvos".

O **InstaBot** resolve isso:
1. **Compartilhe o link no Telegram** diretamente do app do Instagram.
2. O bot **transcreve o áudio** do Reels e lê a legenda.
3. A IA extrai: **Categoria/Cômodo**, **Checklist Prático para a Obra**, **Erros a Evitar** e **Grau de Criticidade**.
4. Cria automaticamente um card com checkboxes no seu **Notion** e salva backup offline.
5. Com o comando `/compilado [cômodo]`, a IA sintetiza todas as dicas salvas em um **Manual Prático da Obra**.

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
    [ 📜 Legenda do Post ]      [ 🎙️ Áudio do Reels ]
             │                           │
             │                    (PyAV + Azure Speech)
             │                           │
             └─────────────┬─────────────┘
                           ▼
          [ 🧠 Azure OpenAI: GPT-4o-mini ]
       (Classifica, extrai checklist e alertas)
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [ 💾 Backup Local ]         [ 📝 Notion Database ]
    (data/dicas.json)         (Cards visuais e interativos)
```

---

## 🚀 Como Executar

### 1. Pré-requisitos
* Python 3.10 ou superior
* Conta no Telegram para criar o bot com o [@BotFather](https://t.me/BotFather)
* Chave de API do **Azure AI Foundry / Azure OpenAI**
* Chave do **Azure Speech** (mesma do seu projeto anterior)

### 2. Configurar o `.env`
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```
Preencha as variáveis:
```ini
TELEGRAM_BOT_TOKEN=seu_token_do_telegram
AZURE_OPENAI_API_KEY=sua_chave_azure_openai
AZURE_OPENAI_ENDPOINT=https://seu-recurso.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-08-01-preview

AZURE_SPEECH_KEY=sua_chave_azure_speech
AZURE_SPEECH_REGION=eastus2

# Opcional (se quiser sincronizar no Notion):
NOTION_API_KEY=sua_secret_integracao_notion
NOTION_DATABASE_ID=id_do_seu_banco_notion
```

### 3. Instalar Dependências e Iniciar
```bash
# Ativar o ambiente virtual (Windows)
.\.venv\Scripts\activate

# Iniciar o Bot
python bot.py
```

---

## 💬 Comandos no Telegram

| Comando | Descrição |
| :--- | :--- |
| `[Link do Instagram]` | Processa o post/reels, transcreve áudio, extrai dicas e salva. |
| `/categorias` | Exibe quantidade de dicas salvas por cômodo/área (ex: Elétrica, Banheiro, Cozinha). |
| `/compilado` | A IA sintetiza **todas** as dicas salvas em um Guia Geral da Obra. |
| `/compilado [categoria]` | Gera o dossiê focado (ex: `/compilado banheiro` ou `/compilado eletrica`). |
| `/start` | Mensagem de boas-vindas e instruções. |

---

## 📂 Estrutura de Pastas

```text
instabot/
├── .venv/                   # Ambiente virtual Python
├── data/
│   └── dicas.json           # Banco de dados local (backup offline de custo zero)
├── utils/
│   ├── analyzer.py          # Raciocínio da IA (Azure OpenAI) e extração de checklist
│   ├── compiler.py          # Síntese e geração de manuais consolidado por área
│   ├── helpers.py           # Utilitários de logging e persistência JSON
│   ├── instagram.py         # Extrator de legendas e mídia de links via yt-dlp
│   ├── notion_sync.py       # Sincronização de cards interativos no Notion
│   └── voice.py             # Pipeline de Voice AI (conversão PCM + Azure Speech)
├── .env.example             # Modelo das variáveis de ambiente
├── .gitignore               # Ignora arquivos de mídia, log e chaves
├── bot.py                   # Ponto de entrada do Telegram Bot
├── requirements.txt         # Dependências do projeto
└── README.md                # Documentação do projeto
```