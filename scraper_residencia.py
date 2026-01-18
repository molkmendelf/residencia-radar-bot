import os
import json
import time
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRO: Chaves do Supabase não encontradas.")
    exit(1)
if not GEMINI_API_KEY:
    print("❌ ERRO: Chave do Gemini não encontrada.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. OLHEIRO ---
def fetch_edital_content(url):
    print(f"🔍 Acessando {url}...")
    return """
    URGENTE: Saiu o edital do ENARE 2026!
    O Exame Nacional de Residência Médica publicou hoje as normas.
    São 45 vagas para Radiologia em diversas cidades.
    Inscrições começam dia 20/10/2026 e vão até 10/11/2026.
    A prova será dia 10/12/2026.
    A taxa subiu para R$ 350,00.
    Banca: FGV.
    """

# --- 3. CÉREBRO (Estratégia Força Bruta) ---
def extract_data_with_ai(text):
    prompt = f"""
    Analise o texto e extraia JSON.
    Campos: instituicao, estado (sigla), cidade, especialidade, vagas (int), 
    inicioInscricao (AAAA-MM-DD), fimInscricao (AAAA-MM-DD), dataProva (AAAA-MM-DD), 
    taxa (float), link (string), previsto (boolean).
    Texto: {text}
    """
    
    # LISTA DE MODELOS (Do mais moderno ao mais antigo/estável)
    # Se o 2.0 estiver cheio, ele tenta os 1.5 específicos, e por fim o 1.0 Pro que é super estável.
    modelos_para_tentar = [
        'gemini-2.0-flash',       # Experimental (Rápido)
        'gemini-1.5-flash',       # Padrão Atual
        'gemini-1.5-flash-001',   # Versão Específica 1
        'gemini-1.5-flash-002',   # Versão Específica 2
        'gemini-1.5-pro',         # Mais robusto
        'gemini-1.0-pro'          # O Clássico (Velho de Guerra)
    ]
    
    for modelo in modelos_para_tentar:
        print(f"🧠 Tentando processar com {modelo}...")
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json')
            )
            print(f"✅ SUCESSO com o modelo {modelo}!")
            return json.loads(response.text)
            
        except Exception as e:
            msg = str(e)
            if "429" in msg or "Quota" in msg:
                print(f"⚠️ Cota cheia no {modelo}. Esperando 5s para tentar o próximo...")
                time.sleep(5) 
            elif "404" in msg:
                print(f"⚠️ Modelo {modelo} não encontrado nesta API Key. Pulando...")
            else:
                print(f"❌ Erro genérico no {modelo}: {msg}")
    
    print("❌ Falha total: Nenhum dos 6 modelos funcionou. Verifique sua API Key ou Conta Google.")
    exit(1)

# --- 4. ARQUIVISTA ---
def save_to_db(data):
    print(f"💾 Salvando {data.get('instituicao')}...")
    try:
        existing = supabase.table("editais").select("*").eq("instituicao", data['instituicao']).eq("especialidade", data['especialidade']).execute()
        if len(existing.data) > 0:
            supabase.table("editais").update(data).eq("id", existing.data[0]['id']).execute()
        else:
            supabase.table("editais").insert(data).execute()
        print("✅ Dados salvos no Supabase!")
    except Exception as e:
        print(f"❌ Erro Supabase: {e}")
        # Não damos exit(1) aqui para não falhar o workflow se for só um erro de banco
        # Mas avisamos no log

# --- 5. EXECUÇÃO ---
if __name__ == "__main__":
    urls = ["https://site-ficticio.com/noticia-enare-2026"]
    for url in urls:
        texto = fetch_edital_content(url)
        data = extract_data_with_ai(texto)
        if data:
            if not data.get('link'): data['link'] = url
            save_to_db(data)
