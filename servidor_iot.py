from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="TermoSensorial API", version="1.0")

# Estrutura dos dados que o Arduino vai enviar
class DadosTermicos(BaseModel):
    dispositivo_id: str
    temperatura: float
    humidade: float

# Lista temporária para guardar as leituras recebidas na memória
historico_leituras = []

@app.post("/api/enviar")
def receber_dados_sensor(dados: DadosTermicos):
    registo = {
        "dispositivo_id": dados.dispositivo_id,
        "temperatura": dados.temperatura,
        "humidade": dados.humidade,
        "registado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Adicionar o registo ao nosso histórico
    historico_leituras.append(registo)
    
    print(f"[{registo['registado_em']}] Recebido -> Temp: {dados.temperatura}°C | Hum: {dados.humidade}%")
    
    return {"status": "sucesso", "mensagem": "Dados guardados com sucesso!", "dados": registo}

@app.get("/api/historico")
def consultar_historico():
    return {"total": len(historico_leituras), "leituras": historico_leituras}