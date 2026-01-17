import os
import json
import requests
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime

# --- CONFIGURAÇÃO ---
# Você vai pegar essas chaves no site do Supabase e no Google AI Studio
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Inicializa clientes
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# --- FUNÇÃO 1: O "OLHEIRO" (Busca o texto bruto) ---
def fetch_edital_content(url):
    """
    Na vida real, aqui você usaria bibliotecas como 'BeautifulSoup' ou 'Playwright'
    para extrair o texto de um PDF ou HTML.
    Para este exemplo, vamos simular que já extraímos o texto de uma página de notícias.
    """
    print(f"🔍 Acessando {url}...")
    
    # Exemplo prático: Vamos supor que acessamos um site e pegamos este texto:
    # (Num caso real, use requests.get(url).text e limpe o HTML)
    texto_bruto = """
    URGENTE: Saiu o edital do ENARE 2026!
    O Exame Nacional de Residência Médica publicou hoje as normas.
    São 45 vagas para Radiologia em diversas cidades.
    Inscrições começam dia 20/10/2026 e vão até 10/11/2026.
    A prova será dia 10/12/2026.
    A taxa subiu para R$ 350,00.
    Banca: FGV.
    """
    return texto_bruto

# --- FUNÇÃO 2: O CÉREBRO (Gemini estrutura os dados) ---
def extract_data_with_ai(text):
    print("🧠 Processando com Gemini...")
    
    model = genai.GenerativeModel('gemini-1.5-flash') # Ou flash-exp
    
    prompt = f"""
    Analise o texto de edital de residência médica abaixo e extraia os dados em JSON.
    Campos obrigatórios: instituicao, estado (sigla), cidade, especialidade, vagas (int), 
    inicioInscricao (AAAA-MM-DD), fimInscricao (AAAA-MM-DD), dataProva (AAAA-MM-DD), 
    taxa (float), link (string ou null), previsto (boolean).
    
    Se faltar info, deixe null. Se for previsão, marque previsto: true.
    
    Texto: {text}
    """
    
    # Configurando para retornar JSON puro
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"Erro ao parsear JSON: {e}")
        return None

# --- FUNÇÃO 3: O ARQUIVISTA (Salva no Supabase) ---
def save_to_db(data):
    if not data:
        return

    print("💾 Salvando no Banco de Dados...")
    
    # Verifica se já existe (para não duplicar)
    # Supondo que usamos 'instituicao' e 'especialidade' como chave única lógica
    existing = supabase.table("editais").select("*").eq("instituicao", data['instituicao']).eq("especialidade", data['especialidade']).execute()
    
    if len(existing.data) > 0:
        print("⚠️ Edital já existe. Atualizando...")
        supabase.table("editais").update(data).eq("id", existing.data[0]['id']).execute()
    else:
        supabase.table("editais").insert(data).execute()
        print("✅ Novo edital cadastrado!")

# --- ORQUESTRAÇÃO ---
def main():
    # Lista de URLs que você quer monitorar
    urls_to_check = [
        "https://site-exemplo.com/noticia-enare",
        # Adicione mais aqui...
    ]

    for url in urls_to_check:
        text = fetch_edital_content(url)
        structured_data = extract_data_with_ai(text)
        
        # Adiciona um link padrão se a IA não achou
        if structured_data and not structured_data.get('link'):
            structured_data['link'] = url
            
        save_to_db(structured_data)

if __name__ == "__main__":
    main()
