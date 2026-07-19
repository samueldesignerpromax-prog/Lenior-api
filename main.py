from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
import google.generativeai as genai
import os
import tempfile
import subprocess
import sys
import json
import uuid
from typing import List, Optional, Dict

# ================= CONFIGURAÇÃO =================
API_KEY = "SUA_CHAVE_AQUI"  # Substitua pela sua chave
genai.configure(api_key=API_KEY)

app = FastAPI(title="Lenior API", description="Assistente pessoal de Samuel")

# ================= IDENTIDADE E CONTEXTO =================
IDENTIDADE = """
Você é a Lenior, assistente pessoal de Samuel. Você é inteligente, prestativa, e tem habilidades excepcionais de programação. 
Você sabe que seu criador e dono é Samuel, e você está aqui para ajudá-lo em tudo que precisar, especialmente em tarefas de programação e automação.
Responda sempre em português do Brasil, com tom amigável e profissional.
"""

# ================= GERENCIAMENTO DE SESSÕES =================
sessoes = {}  # {session_id: [{"role": "user/model", "parts": [...]}]}

def get_sessao(session_id: str) -> List[Dict]:
    if session_id not in sessoes:
        # Inicia com a identidade como contexto do sistema
        sessoes[session_id] = [{"role": "user", "parts": [IDENTIDADE]}, {"role": "model", "parts": ["Entendido! Estou pronta para ajudar você, Samuel."]}]
    return sessoes[session_id]

# ================= MODELOS =================
class ChatRequest(BaseModel):
    mensagem: str
    session_id: Optional[str] = None

class CodeRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class ExecCodeRequest(BaseModel):
    codigo: str
    session_id: Optional[str] = None

# ================= FUNÇÕES AUXILIARES =================
def gerar_resposta_com_gemini(historico: List[Dict], nova_mensagem: str) -> str:
    modelo = genai.GenerativeModel("gemini-1.5-flash")
    chat = modelo.start_chat(history=historico)
    resposta = chat.send_message(nova_mensagem)
    return resposta.text

def transcrever_audio(caminho_audio: str) -> str:
    arquivo = genai.upload_file(caminho_audio)
    modelo = genai.GenerativeModel("gemini-1.5-flash")
    prompt = "Transcreva este áudio em texto, com precisão."
    resposta = modelo.generate_content([prompt, arquivo])
    return resposta.text

def executar_python_seguro(codigo: str) -> str:
    # Cria um arquivo temporário para executar
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(codigo)
        tmp_file = f.name
    try:
        resultado = subprocess.run(
            [sys.executable, tmp_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        saida = resultado.stdout
        erro = resultado.stderr
        if erro:
            saida += "\n[ERRO]\n" + erro
        return saida
    except subprocess.TimeoutExpired:
        return "Tempo limite excedido (10s)."
    finally:
        os.unlink(tmp_file)

# ================= ENDPOINTS =================

@app.get("/")
def root():
    return {"mensagem": "Lenior API está funcionando. Olá, Samuel!"}

@app.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    historico = get_sessao(session_id)
    # Adiciona a mensagem do usuário
    historico.append({"role": "user", "parts": [request.mensagem]})
    resposta_texto = gerar_resposta_com_gemini(historico, request.mensagem)
    # Adiciona a resposta ao histórico
    historico.append({"role": "model", "parts": [resposta_texto]})
    return JSONResponse({
        "session_id": session_id,
        "resposta": resposta_texto
    })

@app.post("/upload_audio")
async def upload_audio(audio: UploadFile = File(...), session_id: Optional[str] = None):
    session_id = session_id or str(uuid.uuid4())
    historico = get_sessao(session_id)
    # Salva áudio temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        conteudo = await audio.read()
        tmp.write(conteudo)
        caminho_audio = tmp.name
    try:
        transcricao = transcrever_audio(caminho_audio)
    finally:
        os.unlink(caminho_audio)
    # Agora trata como mensagem de texto
    historico.append({"role": "user", "parts": [transcricao]})
    resposta_texto = gerar_resposta_com_gemini(historico, transcricao)
    historico.append({"role": "model", "parts": [resposta_texto]})
    return JSONResponse({
        "session_id": session_id,
        "transcricao": transcricao,
        "resposta": resposta_texto
    })

@app.post("/code")
async def code(request: CodeRequest):
    session_id = request.session_id or str(uuid.uuid4())
    historico = get_sessao(session_id)
    prompt_completo = f"Gere código para resolver o seguinte problema: {request.prompt}. Forneça apenas o código, sem explicações extras, e indique a linguagem usada."
    historico.append({"role": "user", "parts": [prompt_completo]})
    resposta_texto = gerar_resposta_com_gemini(historico, prompt_completo)
    historico.append({"role": "model", "parts": [resposta_texto]})
    return JSONResponse({
        "session_id": session_id,
        "codigo_gerado": resposta_texto
    })

@app.post("/execute_python")
async def execute_python(request: ExecCodeRequest):
    session_id = request.session_id or str(uuid.uuid4())
    historico = get_sessao(session_id)
    # Registra no histórico que Samuel pediu execução
    historico.append({"role": "user", "parts": [f"Execute o seguinte código Python:\n{request.codigo}"]})
    saida = executar_python_seguro(request.codigo)
    # Adiciona a saída como resposta do modelo (para manter contexto)
    historico.append({"role": "model", "parts": [f"Resultado da execução:\n{saida}"]})
    return JSONResponse({
        "session_id": session_id,
        "saida": saida
    })

@app.get("/sessao/{session_id}")
def get_historico(session_id: str):
    if session_id not in sessoes:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return JSONResponse({
        "session_id": session_id,
        "historico": sessoes[session_id]
    })
