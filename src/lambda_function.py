import asyncio
import os
import json
import logging
from telegram import Bot, Update
from custom_langchain import LangChainProcessor
from botocore.exceptions import BotoCoreError, ClientError
from telegram.request import HTTPXRequest

# Token para conexão do bot do Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "COLOQUE SEU TOKEM AQUI")
if not TELEGRAM_TOKEN:
    raise ValueError("O token do Telegram não está configurado.")

# Configurar o pool de conexões
request = HTTPXRequest(connection_pool_size=20)
bot = Bot(token=TELEGRAM_TOKEN, request=request)

# Configuração do Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

langchain_class = LangChainProcessor(bucket_name="sprint7-8", region_name="us-east-1")

# Função para responder às mensagens
async def respond(update: Update):
    """
    Processa uma mensagem recebida e responde ao usuário.
    """
    try:
        question = update.message.text
        chat_id = update.message.chat.id  # Corrige o acesso ao ID do chat
        logger.info(f"Pergunta recebida: {question}")

        # Ignorar mensagens geradas pelo próprio bot
        if update.message.from_user.is_bot:
            logger.info("Mensagem ignorada: gerada pelo próprio bot.")
            return

        # Consulta ao LangChainProcessor
        response = langchain_class.query(question)
        logger.info(f"Resposta gerada: {response}")

        # Envia a resposta ao usuário
        await bot.send_message(chat_id=chat_id, text=response)
        logger.info(f"Resposta enviada: {response}")
        return response
    except Exception as e:
        logger.error(f"Erro ao processar resposta: {e}")
        await bot.send_message(chat_id=chat_id, text="Desculpe, ocorreu um erro ao processar sua solicitação.")

# Função assíncrona para processar o evento do Lambda
async def handle_event(event):
    """
    Processa eventos recebidos do Lambda.
    """
    try:
        logger.info(f"Evento recebido: {event}")

        # Validação do contexto do evento
        if "body" not in event:
            raise ValueError("Evento inválido: 'body' não encontrado.")

        body = json.loads(event["body"])  # Corpo do evento recebido

        # Criação do objeto Update a partir do JSON recebido
        update = Update.de_json(body, bot)

        # Processa a mensagem recebida
        await backoff_retry(respond, max_attempts=5, base_delay=2, update=update)

        return {"statusCode": 200, "body": json.dumps({"message": "Processed"})}
    except Exception as e:
        logger.error(f"Erro no handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

# Coordenador do processamento de resposta
async def backoff_retry(func, max_attempts=5, base_delay=1, **kwargs):
    """
    Função genérica de backoff para tentar novamente em caso de falha (exponencial).
    """
    attempts = 0
    while attempts < max_attempts:
        try:
            return await func(**kwargs)  # Executa a função alvo
        except (BotoCoreError, ClientError, Exception) as e:
            attempts += 1
            delay = base_delay * (2 ** (attempts - 1))  # Delay exponencial
            logger.warning(f"Erro encontrado: {e}. Tentando novamente em {delay} segundos.")
            await asyncio.sleep(delay)
    raise Exception(f"Máximo de tentativas alcançado para {func.__name__}")

def handler(event, context):
    """
    Função Lambda principal.
    """
    logger.info('Inicio do logger.')
    try:
        logger.info(f"Evento recebido: {event}")
        loop = asyncio.get_event_loop()

        # Verifica se o loop está ativo ou fechado
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Executa a função assíncrona no loop de eventos
        logger.info("Fim do handler.")
        return loop.run_until_complete(handle_event(event))
    except Exception as e:
        logger.error(f"Erro no handler principal: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
