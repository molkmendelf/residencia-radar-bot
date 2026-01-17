import os
import json
import requests
from google import genai
from google.genai import types
from supabase import create_client, Client
from datetime import datetime

# --- 1. CONFIGURAÇÃO E SEGURANÇA ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRO CRÍTICO: Chaves do Supabase não encontradas.")
    exit(1)

if not GEMINI_API_KEY:
    print("❌ ERRO CRÍTICO: Chave do Gemini não encontrada.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FUNÇÃO: O "OLHEIRO" ---
def fetch_edital_content(url):
    print(f"🔍 Acessando {url}...")
    texto_simulado = """
    URGENTE: Saiu o edital do ENARE 2026!
    O Exame Nacional de Residência Médica publicou hoje as normas.
    São 45 vagas para Radiologia em diversas cidades.
    Inscrições começam dia 20/10/2026 e vão até 10/11/2026.
    A prova será dia 10/12/2026.
    A taxa subiu para R$ 350,00.
    Banca: FGV.
    """
    return texto_simulado

# --- 3. FUNÇÃO: O CÉREBRO ---
def extract_data_with_ai(text):
    print("🧠 Processando com Gemini 1.5 Flash...")
    prompt = f"""
    Analise o texto e extraia JSON.
    Campos: instituicao, estado (sigla), cidade, especialidade, vagas (int), 
    inicioInscricao (AAAA-MM-DD), fimInscricao (AAAA-MM-DD), dataProva (AAAA-MM-DD), 
    taxa (float), link (string), previsto (boolean).
    
    Texto: {text}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        dados = json.loads(response.text)
        print("✅ JSON Gerado com sucesso.")
        return dados
    except Exception as e:
        print(f"❌ ERRO NA IA: {e}")
        # Mostra o que a IA tentou responder antes de dar erro
        if 'response' in locals():
            print(f"Resposta bruta da IA: {response.text}")
        exit(1) # Força erro no GitHub

# --- 4. FUNÇÃO: O ARQUIVISTA ---
def save_to_db(data):
    print(f"💾 Tentando salvar {data.get('instituicao')}...")
    
    try:
        # Tenta inserir. Se falhar por permissão, vai cair no except.
        existing = supabase.table("editais").select("*").eq("instituicao", data['instituicao']).eq("especialidade", data['especialidade']).execute()
        
        if len(existing.data) > 0:
            print(f"🔄 Atualizando ID: {existing.data[0]['id']}...")
            supabase.table("editais").update(data).eq("id", existing.data[0]['id']).execute()
        else:
            print("✨ Inserindo novo registro...")
            result = supabase.table("editais").insert(data).execute()
            print(f"✅ Resultado do Insert: {result}")
            
    except Exception as e:
        print(f"❌ ERRO NO SUPABASE: {e}")
        print("💡 DICA: Verifique se você desativou o RLS ou criou as Policies no Supabase.")
        exit(1) # Força erro no GitHub

# --- 5. PRINCIPAL ---
def main():
    urls = ["https://site-ficticio.com/noticia-enare-2026"]
    for url in urls:
        texto = fetch_edital_content(url)
        data = extract_data_with_ai(texto)
        if not data.get('link'): data['link'] = url
        save_to_db(data)

if __name__ == "__main__":
    main()
