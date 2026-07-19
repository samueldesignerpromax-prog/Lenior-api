import subprocess
import tempfile
import os
import sys
import time

class CodeExecutor:
    @staticmethod
    def executar_codigo(codigo: str, timeout: int = 5) -> dict:
        bloqueados = ['os.system', 'subprocess', 'eval', 'exec', '__import__']
        for palavra in bloqueados:
            if palavra in codigo:
                return {"sucesso": False, "saida": "", "erro": f"Código contém palavra bloqueada: {palavra}"}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(codigo)
            caminho = f.name

        try:
            processo = subprocess.run(
                [sys.executable, caminho],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            saida = processo.stdout
            erro = processo.stderr
            sucesso = (processo.returncode == 0)
            return {"sucesso": sucesso, "saida": saida, "erro": erro}
        except subprocess.TimeoutExpired:
            return {"sucesso": False, "saida": "", "erro": "Tempo limite excedido"}
        finally:
            os.unlink(caminho)
