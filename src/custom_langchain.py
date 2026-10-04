import logging
from io import BytesIO
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_aws.llms.bedrock import BedrockLLM
import boto3

class LangChainProcessor:
    def __init__(self, bucket_name, region_name):
        """
        Inicializa a classe com as configurações do S3, Bedrock e CloudWatch.
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.client_bedrock = boto3.client('bedrock-runtime', region_name=region_name)
        self.s3_client = boto3.client('s3', region_name=region_name)
        self.vector_store = None
        self.qa_chain = None
        self.CHROMA_DIR = "/tmp/chroma"
        self.MODEL_ID = "mistral.mistral-large-2402-v1:0"
        # Configuração do self.logger
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger()

        self.init_resources()

    def loadDocumentS3(self):
        """
        Carrega documentos PDF do bucket S3 e extrai o texto.
        """
        self.logger.info("Carregando documentos do S3...")
        documents = []
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            for obj in response.get('Contents', []):
                file_key = obj['Key']
                if file_key.endswith('.pdf'):
                    self.logger.info(f"Baixando e processando arquivo: {file_key}")
                    file_object = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
                    content = file_object['Body'].read()
                    
                    # Lê o conteúdo do PDF
                    pdf_reader = PdfReader(BytesIO(content))
                    text = "".join(page.extract_text() for page in pdf_reader.pages)
                    
                    documents.append(Document(page_content=text, metadata={"filename": file_key}))
            self.logger.info("Documentos carregados com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao carregar documentos do S3: {e}")
        return documents

    def createVector(self, documents):
        """
        Cria um banco vetorial usando embeddings do Amazon Bedrock.
        """
        self.logger.info("Criando banco vetorial...")
        try:
            bedrock_embeddings = BedrockEmbeddings(client=self.client_bedrock, model_id="amazon.titan-embed-text-v2:0")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            
            chunks = []
            for doc in documents:
                split_chunks = text_splitter.split_text(doc.page_content)
                chunks.extend(
                    Document(page_content=chunk, metadata={"filename": doc.metadata["filename"]})
                    for chunk in split_chunks
                )
            
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=bedrock_embeddings,
                persist_directory=self.CHROMA_DIR
            )
            self.vector_store.persist()
            self.logger.info("Banco vetorial criado e persistido com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao criar banco vetorial: {e}")

    def createRetrievalQA(self):
        """
        Cria a Retrieval QA Chain para responder perguntas com base no banco vetorial.
        """
        self.logger.info("Criando QA Chain...")
        try:
            llm = BedrockLLM(model_id=self.MODEL_ID, client=self.client_bedrock)
            prompt_template = PromptTemplate.from_template("""
            Você é um assistente virtual do grupo-6, especializado em fornecer informações sobre documentos jurídicos que estão armazenados no bucket, com ênfase em acórdãos-embargos. 
            Diretrizes para respostas: Saudações: Se a mensagem for uma saudação como “Olá”, “Oi”, “Bom dia”, “Boa tarde”, “Boa noite”, “Alô”, “E aí”, “Como vai”, “Tudo bem”, “Salve”, “Oi, tudo bem?”, “Oi, como está?”, “Olá, como você está?”, “Oi, tudo certo?”, “Bom dia, como vai?”, “Boa tarde, tudo bem?”, “Boa noite, como foi o dia?”, responda de forma educada e amigável, demonstrando interesse no contato. Exemplo: “Olá! Como posso ajudar você hoje?” Agradecimentos: Se a mensagem for um agradecimento como “Obrigado”, “Obrigada”, “Valeu”, “Muito obrigado”, “Muito obrigada”, “Agradeço”, “Grato”, “Grata”, “Thanks”, “Muito obrigado pela ajuda”, “Muito obrigada pela informação”, “Agradeço pela resposta”, “Valeu pela dica”, “Agradeço muito”, “Muito grato”, “Muito grata”, “Obrigado mesmo”, “Obrigada mesmo”, “Agradecido”, “Agradecida”, responda gentilmente, agradeça e coloque-se à disposição para auxiliar com outras dúvidas. 
            Exemplo: “Agradeço seu retorno! Estou à disposição para esclarecer outras dúvidas que você possa ter.” Fora do contexto: Se a pergunta não puder ser respondida dentro do contexto fornecido, responda: “Peço desculpas, mas não consegui localizar a resposta em nossos arquivos. Estou à disposição para esclarecer dúvidas relacionadas a acórdãos e embargos. Como posso ajudar?” Frases sem sentido: Se a mensagem contiver palavras soltas, letras isoladas ou frases sem sentido, responda: “Desculpe, não consegui compreender sua mensagem. Caso tenha dúvidas sobre acórdãos e embargos, estarei aqui para ajudar. Poderia reformular sua pergunta?” Respostas completas: Se a pergunta puder ser respondida com base no contexto fornecido, elabore uma resposta clara e objetiva: “Consegui esclarecer sua dúvida? Caso precise de mais informações, estou à disposição!” 
            Instruções importantes: 
                                                           
            1. Jamais forneça informações fora do contexto. 
            2. Não invente respostas ou dados inexistentes com as informacoes do documento. 
            3. Mande apenas uma das alternativas do exemplo, de acordo com a ocasião e não repita a mensagem para o usuário.
            4. Siga rigorosamente as diretrizes acima.                                           
            
            Documento:
            {context}

            Pergunta:
            {question}

            Resposta:
        """)
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=self.vector_store.as_retriever(search_kwargs={'k': 2}),
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt_template}
            )
            self.logger.info("QA Chain criada com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao criar QA Chain: {e}")

    def init_resources(self):
        """
        Inicializa recursos como o banco vetorial e a chain de QA.
        """
        print("Inicializando recursos...")
        documents = self.loadDocumentS3()
        if documents:
            self.createVector(documents)
            self.createRetrievalQA()
        else:
            self.logger.error("Nenhum documento encontrado no bucket S3.")

    def query(self, question):
        """
        Realiza uma consulta no banco vetorial usando a QA Chain.
        """
        if self.qa_chain is None:
            self.logger.info("QA Chain não inicializada. Recriando os recursos necessários...")
            self.init_resources()
        
        try:
            # Logando a pergunta recebida
            self.logger.info(f"Pergunta recebida: {question}")
            print(f'Pergunta recebida: {question}')
            # Realizando a consulta
            response = self.qa_chain.invoke({"query": question})
            self.logger.info(f"Resposta: {response}")
            print(f'Resposta: {response}')
            # Validando e processando a resposta
            if "result" in response:
                self.logger.info(f"Resposta gerada com sucesso: {response['result']}")
                return response["result"]
            else:
                self.logger.error("Resposta não contém o campo 'result'. Verifique a configuração da QA Chain.")
                return "Desculpe, não consegui encontrar uma resposta adequada para sua pergunta."

        except KeyError as ke:
            # Tratamento de erro para chaves ausentes
            self.logger.error(f"Erro ao obter o resultado da consulta: {ke}")
            return "Erro ao processar sua consulta. Parece que a resposta está incompleta."
        
        except Exception as e:
            # Tratamento de erros gerais
            self.logger.error(f"Erro inesperado ao realizar a consulta: {e}", exc_info=True)
            return "Ocorreu um erro inesperado ao processar sua consulta. Por favor, tente novamente mais tarde."

