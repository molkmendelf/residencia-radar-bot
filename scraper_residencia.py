import os
import json
import requests
from google import genai
from google.genai import types
from supabase import create_client, Client
from datetime import datetime

# --- 1. CONFIGURAÇÃO E SEGURANÇA ---
# Pega as chaves que você configurou no GitHub Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Inicializa o Banco de Dados (Supabase)
# Se der erro aqui, verifique se as secrets SUPABASE_URL e KEY estão certas no GitHub
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRO CRÍTICO: Chaves do Supabase não encontradas.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Inicializa a Inteligência Artificial (Google Gemini - Nova Biblioteca)
if not GEMINI_API_KEY:
    print("❌ ERRO CRÍTICO: Chave do Gemini não encontrada.")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FUNÇÃO: O "OLHEIRO" (Busca o texto) ---
def fetch_edital_content(url):
    print(f"🔍 Acessando {url}...")
    
    # SIMULAÇÃO: Como não temos um link real agora, fingimos que baixamos este texto.
    # Na vida real, você usaria: response = requests.get(url); return response.text
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

# --- 3. FUNÇÃO: O CÉREBRO (Processa com IA) ---
def extract_data_with_ai(text):
    print("🧠 Processando com Gemini 1.5 Flash...")
    
    prompt = f"""
    Analise o texto de edital de residência médica abaixo e extraia os dados em JSON.
    Campos obrigatórios: instituicao, estado (sigla), cidade, especialidade, vagas (int), 
    inicioInscricao (AAAA-MM-DD), fimInscricao (AAAA-MM-DD), dataProva (AAAA-MM-DD), 
    taxa (float), link (string ou null), previsto (boolean).
    
    Regras:
    1. Se faltar info, deixe null. 
    2. Se o texto parecer um rumor ou previsão, marque 'previsto': true.
    3. Retorne APENAS o JSON.
    
    Texto: {text}
    """
    
    try:
        # Usa a nova sintaxe da biblioteca google-genai (SDK v1)
        # Atenção: 'gemini-1.5-flash' é o modelo estável gratuito
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        
        # O Gemini já retorna o JSON limpo graças ao response_mime_type
        dados = json.loads(response.text)
        print("✅ Dados extraídos com sucesso!")
        return dados
        
    except Exception as e:
        print(f"❌ Erro ao processar com a IA: {e}")
        return None

# --- 4. FUNÇÃO: O ARQUIVISTA (Salva no Banco) ---
def save_to_db(data):
    if not data:
        print("⚠️ Sem dados para salvar.")
        return

    print(f"💾 Salvando {data.get('instituicao')} no Supabase...")
    
    try:
        # Verifica se já existe esse edital (para não duplicar)
        # A lógica aqui busca por Instituição + Especialidade
        existing = supabase.table("editais")\
            .select("*")\
            .eq("instituicao", data['instituicao'])\
            .eq("especialidade", data['especialidade'])\
            .execute()
        
        if len(existing.data) > 0:
            print(f"🔄 Edital já existia (ID: {existing.data[0]['id']}). Atualizando...")
            supabase.table("editais").update(data).eq("id", existing.data[0]['id']).execute()
        else:
            print("✨ Novo edital encontrado! Inserindo...")
            supabase.table("editais").insert(data).execute()
            
        print("✅ Sucesso no Banco de Dados!")
        
    except Exception as e:
        print(f"❌ Erro ao conectar no Supabase: {e}")

# --- 5. ORQUESTRAÇÃO PRINCIPAL ---
def main():
    # Lista de sites para vigiar (aqui usamos um fake só para testar a lógica)
    urls_to_check = [
        "https://site-ficticio.com/noticia-enare-2026"
    ]

    for url in urls_to_check:
        # 1. Baixa
        texto = fetch_edital_content(url)
        # 2. Pensa
        dados_estruturados = extract_data_with_ai(texto)
        
        # 3. Salva
        if dados_estruturados:
            # Garante que tem um link, mesmo que seja o da notícia
            if not dados_estruturados.get('link'):
                dados_estruturados['link'] = url
                
            save_to_db(dados_estruturados)

if __name__ == "__main__":
    main()
