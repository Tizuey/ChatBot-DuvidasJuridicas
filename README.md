# 🚀 Chat Bot - PDF´s Jurídicos 
## 🗒️ Descrição do Projeto:
Trata-se de um chatbot para consultas de documentos jurídicos no Telegram.
O sistema foi desenvolvido utilizando tecnologias como AWS Bedrock, LangChain, Chroma e com suporte a logs via CloudWatch.


## Objetivo:
Criar um chatbot que permite a consulta de documentos jurídicos utilizando Retrieval-Augmented Generation(RAG).

O sistema deve incluir:
 - Carregamento de documentos para um bucket S3;
 - Geração de embeddings com AWS Bedrock;
 - Indexação e consulta com Chroma;
 - Interface via Telegram;
 - Monitoramento de logs com AWS CloudWatch.



## 🛠️ Tecnologias Utilizadas:
- Python
- AWS CloudWatch 
- AWS Bedrock 
- LangChain
- ChromaDB
- Telegram Bot API
- Docker


## Como utilizar o sistema:
 Antes de rodar o projeto, configure o ambiente da seguinte forma:

### 1. Crie um bot no Telegram:

- **Acesse o BotFather no Telegram e gere um token para seu bot.** 

### 2. Configure suas credenciais da AWS: 

- Certifique-se de configurar suas chaves de acesso à AWS:
     ```bash
     export AWS_ACCESS_KEY_ID=<sua_chave>
     export AWS_SECRET_ACCESS_KEY=<sua_chave_secreta>

### 3. Clone o repositório:

    ```bash 
    https://github.com/Compass-pb-aws-2024-SETEMBRO/sprints-7-8-pb-aws-setembro/tree/grupo-6 
    ```
### 4. Crie e Execute a Imagem Docker:

-  Monte e suba sua imagem no Amazon ECR:

   ```bash
    docker build -t chatbot-juridico .
    docker tag chatbot-juridico:latest <seu-repositorio-ecr>:latest
    docker push <seu-repositorio-ecr>:latest
    ```

### 5. Inicie o Bot no Telegram:

- No Telegram, encontre o bot pelo nome que você configurou no BotFather e envie sua pergunta.

### 6. Crie uma função Lambda:

- No Lambda, escolha a função com um container image e escolha a imagem do projeto que você colocou no ECR.

### 7. Crie uma API Gateway:

- Na API Gateway, escolha a opção de API Rest.

- **New API** .

- Crie um recurso e dê o nome de webhook.

- Crie um metodo **POST**.

- Click em **Deploy API** e escolha **New Stage**.

- Copie o **Invoke URL** .

### 8. Faça o Webhook do Telegram com a API Gateway:

- Abra o **CMD** do seu computador.

- Utilize esse comando no CMD do seu computador 

    ```bash
    curl -X POST "https://api.telegram.org/bot<token_telegram>/setWebhook" -d "url=<invoke_url>"
    ```
## Dificuldades Encontradas:
- AWS Bedrock
- Implementar lógica do código no ECR
- Configuração do ChromaDB
- Conexão entre o Telegram e a AWS Cloud.


## 👨‍💻 Grupo-6: Componentes:

- <a href="https://github.com/Tizuey">Julia Tizuey</a>
- <a href="https://github.com/mayararoseno1">Mayara Roseno </a>
- <a href="https://github.com/DerickSabino" >Derick Sabino</a>
- <a href="https://github.com/Eduardo-Bomfim" >Eduardo Bomfim</a>