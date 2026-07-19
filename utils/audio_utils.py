import os
import base64
import tempfile
from gtts import gTTS
import google.generativeai as genai

class AudioUtils:
    @staticmethod
    def texto_para_audio_gemini(texto: str) -> bytes:
        try:
            modelo_tts = genai.GenerativeModel("gemini-2.5-flash-tts-preview")
            config = {"speech_config": {"voice": "Kore"}}
            resposta = modelo_tts.generate_content(
                texto,
                generation_config=config,
                response_format={"type": "audio/wav"}
            )
            audio_data = resposta.result
            if isinstance(audio_data, str):
                audio_bytes = base64.b64decode(audio_data)
            else:
                audio_bytes = audio_data
            return audio_bytes
        except Exception as e:
            print(f"Falha no TTS do Gemini, usando gTTS: {e}")
            return AudioUtils.texto_para_audio_gtts(texto)

    @staticmethod
    def texto_para_audio_gtts(texto: str) -> bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tts = gTTS(texto, lang='pt-br')
            tts.save(tmp.name)
            with open(tmp.name, 'rb') as f:
                audio_bytes = f.read()
            os.unlink(tmp.name)
            return audio_bytes
