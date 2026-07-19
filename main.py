from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import tempfile
import uuid
import base64
import re
from dotenv import load_dotenv
from utils.gemini_client import GeminiClient
from utils.code_executor import CodeExecutor
from utils.audio_utils import AudioUtils

load_dotenv()

app = FastAPI(title="Lenior API - Assistente de Samuel", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY não definida no .env")

sessoes = {}

class Mensagem(BaseModel):
    texto: str
    sessao_id: Optional[str] = None

@app.get("/")
def root():
    return {"mensagem": "Lenior está online! Sou assistente de Samuel."}

@app.post("/chat/texto")
async def chat_texto(mensagem: Mensagem):
    sessao_id = mensagem.sessao_id or str(uuid.uuid4())
    if sessao_id not in sessoes:
        sessoes[sessao_id] = GeminiClient(API_KEY)
        sessoes[sessao_id].iniciar_conversa()

    cliente = sessoes[sessao_id]
    resposta_texto = cliente.enviar_mensagem(mensagem.texto)

    codigo_extraido = extrair_codigo(resposta_texto)
    resultado_execucao = None
    if codigo_extraido:
        resultado_execucao = CodeExecutor.executar_codigo(codigo_extraido)
        if resultado_execucao["sucesso"]:
            resposta_texto += f"\n\n**Saída do código:**\n{resultado_execucao['saida']}"
        else:
            resposta_texto += f"\n\n**Erro ao executar:**\n{resultado_execucao['erro']}"

    try:
        audio_bytes = AudioUtils.texto_para_audio_gemini(resposta_texto)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        audio_base64 = None

    return JSONResponse({
        "sessao_id": sessao_id,
        "texto": resposta_texto,
        "audio": audio_base64,
        "executou_codigo": resultado_execucao
    })

@app.post("/chat/audio")
async def chat_audio(audio: UploadFile = File(...), sessao_id: Optional[str] = Form(None)):
    sessao_id = sessao_id or str(uuid.uuid4())
    if sessao_id not in sessoes:
        sessoes[sessao_id] = GeminiClient(API_KEY)
        sessoes[sessao_id].iniciar_conversa()

    cliente = sessoes[sessao_id]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        conteudo = await audio.read()
        tmp.write(conteudo)
        caminho_audio = tmp.name

    try:
        resposta_texto = cliente.enviar_com_audio(caminho_audio)
    finally:
        os.unlink(caminho_audio)

    codigo_extraido = extrair_codigo(resposta_texto)
    resultado_execucao = None
    if codigo_extraido:
        resultado_execucao = CodeExecutor.executar_codigo(codigo_extraido)
        if resultado_execucao["sucesso"]:
            resposta_texto += f"\n\n**Saída do código:**\n{resultado_execucao['saida']}"
        else:
            resposta_texto += f"\n\n**Erro ao executar:**\n{resultado_execucao['erro']}"

    try:
        audio_bytes = AudioUtils.texto_para_audio_gemini(resposta_texto)
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        audio_base64 = None

    return JSONResponse({
        "sessao_id": sessao_id,
        "texto": resposta_texto,
        "audio": audio_base64,
        "executou_codigo": resultado_execucao
    })

def extrair_codigo(texto: str) -> str:
    padrao = r"```python\n(.*?)```"
    matches = re.findall(padrao, texto, re.DOTALL)
    if matches:
        return "\n\n".join(matches)
    return None
