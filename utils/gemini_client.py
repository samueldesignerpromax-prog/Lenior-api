import os
import google.generativeai as genai
from typing import List, Dict, Any

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.chat = None
        self.historico = []
        self.system_prompt = (
            "Você é Lenior, um assistente pessoal inteligente criado para Samuel. "
            "Você é especialista em programação e pode gerar e executar código Python. "
            "Responda sempre em português do Brasil, com tom amigável e prestativo. "
            "Lembre-se que seu dono é o Samuel e você está aqui para ajudá-lo."
        )

    def iniciar_conversa(self):
        self.historico = [
            {"role": "user", "parts": [self.system_prompt]},
            {"role": "model", "parts": ["Entendido! Sou Lenior, assistente de Samuel. Como posso ajudar?"]}
        ]
        self.chat = self.model.start_chat(history=self.historico)
        return self.historico

    def enviar_mensagem(self, mensagem: str) -> str:
        if self.chat is None:
            self.iniciar_conversa()
        resposta = self.chat.send_message(mensagem)
        texto = resposta.text
        self.historico.append({"role": "user", "parts": [mensagem]})
        self.historico.append({"role": "model", "parts": [texto]})
        return texto

    def enviar_com_audio(self, audio_file_path: str, prompt_texto: str = "Transcreva e responda") -> str:
        arquivo = genai.upload_file(audio_file_path)
        modelo_stt = genai.GenerativeModel("gemini-1.5-flash")
        resposta = modelo_stt.generate_content([prompt_texto, arquivo])
        transcricao = resposta.text
        return self.enviar_mensagem(transcricao)
