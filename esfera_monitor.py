import os
import uuid
import datetime
import requests

# -------------------------------------------------------------
# CONFIGURAÇÕES DO ALERTA (TELEGRAM)
# Substitua com os valores obtidos no BotFather e userinfobot:
# -------------------------------------------------------------
TELEGRAM_BOT_TOKEN = "9085044834:AAHb0D4nJ_l8W9awvc2rETlfrKsg5_58wE8"
TELEGRAM_CHAT_ID = "9107792039"

# -------------------------------------------------------------
# ROTAS E DATAS
# -------------------------------------------------------------
ORIGEM = "GRU"
DESTINO = "MCO"

# Data Primária (Alvo Principal)
DATA_IDA_ALVO = "2028-05-08"
DATA_VOLTA_ALVO = "2028-05-22"

# Data de Fallback (Caso a primária ainda não esteja disponível)
DATA_IDA_FALLBACK = "2027-10-04"
DATA_VOLTA_FALLBACK = "2027-10-18"

PASSAGEIROS_IDADES = [30, 30, 30]  # 3 passageiros
TETO_PONTOS_TOTAL = 550000
ARQUIVO_HISTORICO = "menor_preco.txt"

# -------------------------------------------------------------
# ENDPOINTS E TOKENS CAPTURADOS
# -------------------------------------------------------------
ENDPOINT = "https://travel.esfera.com.vc/esfera-travels/v2/flights/v1/avail"
PARTNER_TOKEN = "98JZNSfp5j/AjdKcqSi3aG3CfoTHZdQAks3BxtvmRnpIK7u/NAb5K6VScTX9hKrE"
USER_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJjcmVkZW50aWFsIjp7ImJyYW5jaElkIjoxMDM1LCJhZ2VudFNpZ24iOiJFU0YifSwiZXhwIjoxNjc2MDU4MjAwLCJpYXQiOjE2NzYwNDAyMDB9.pB5hADNQOBZE8b1DOlMyjps80tzk3MKI3MN_No4d5YU"

def gerar_transaction_id() -> str:
    ts = datetime.datetime.now().strftime("%d_%m_%Y-%H_%M_%S")
    rand_prefix = uuid.uuid4().hex[:6]
    return f"{rand_prefix}-bot-{ts}"

def enviar_telegram(mensagem: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or TELEGRAM_BOT_TOKEN == "SEU_TOKEN_DO_BOTFATHER_AQUI":
        print("[!] Token ou Chat ID do Telegram não configurados.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("[✓] Notificação enviada para o Telegram com sucesso!")
        else:
            print(f"[!] Erro ao enviar para o Telegram: HTTP {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[!] Erro na comunicação com o Telegram: {e}")

def obter_ultimo_preco_salvo() -> float:
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r") as f:
                return float(f.read().strip())
        except ValueError:
            return float("inf")
    return float("inf")

def salvar_novo_menor_preco(preco: float):
    with open(ARQUIVO_HISTORICO, "w") as f:
        f.write(str(preco))

def consultar_voos(data_ida: str, data_volta: str):
    routes_param = f"{ORIGEM},{DESTINO},{data_ida}+{DESTINO},{ORIGEM},{data_volta}"
    ages_param = ",".join(str(age) for age in PASSAGEIROS_IDADES)

    params = {
        "routes": routes_param,
        "packageGroup": "STANDALONE",
        "itemsPerPage": "10",
        "ages": ages_param,
        "businessClass": "NO",
        "sortBy": "price",
        "sortOrder": "ascending",
        "withBaggage": "false",
        "withoutBaggage": "false",
        "withHandLuggage": "false",
        "withOutHandLuggage": "false",
        "pageNumber": "1"
    }

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "gtw-partner-token": PARTNER_TOKEN,
        "gtw-sec-user-token": USER_TOKEN,
        "gtw-transaction-id": gerar_transaction_id(),
        "origin": "https://travel.esfera.com.vc",
        "referer": f"https://travel.esfera.com.vc/passagens-aereas/search?IataOri={ORIGEM}&IataDes={DESTINO}&routes={routes_param}",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    print(f"[*] Consultando Esfera: {ORIGEM} ➔ {DESTINO} ({data_ida} a {data_volta})")
    
    session = requests.Session()
    try:
        response = session.get(ENDPOINT, params=params, headers=headers, timeout=25)
        if response.status_code == 200:
            dados = response.json()
            voos = dados.get("flights", [])
            if voos:
                return voos
            print("[-] Retorno vazio: data ainda sem voos carregados.")
            return None
        elif response.status_code in [400, 422]:
            print(f"[-] Data indisponível no calendário (HTTP {response.status_code}).")
            return None
        else:
            print(f"[!] Resposta da API: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[!] Falha na conexão de rede: {e}")
        return None

def processar_resultados(voos: list, data_ida: str, data_volta: str, eh_fallback: bool = False):
    tipo_busca = "Plano Alternativo (Outubro/2027)" if eh_fallback else "Data Alvo Principal (Maio/2028)"
    print(f"\n[✓] Sucesso! {len(voos)} voos encontrados para {tipo_busca}.")
    print("=" * 65)

    melhor = voos[0]
    cia_nome = melhor.get("validatingBy", {}).get("name", "N/A")
    fare_group = melhor.get("fareGroup", {})
    pontos_total = fare_group.get("priceWithTax", 0)

    fares = fare_group.get("fares", [])
    pontos_por_pessoa = 0
    taxas_brl_por_pessoa = 0.0

    if fares:
        primeiro_fare = fares[0]
        pontos_por_pessoa = primeiro_fare.get("priceWithTax", 0)
        for taxa in primeiro_fare.get("taxes", []):
            for val in taxa.get("values", []):
                if val.get("currency") == "BRL":
                    taxas_brl_por_pessoa += val.get("amount", 0.0)

    taxas_brl_total = taxas_brl_por_pessoa * len(PASSAGEIROS_IDADES)

    # Exibe as 5 menores opções no terminal
    for idx, voo in enumerate(voos[:5], start=1):
        c_nome = voo.get("validatingBy", {}).get("name", "N/A")
        pts = voo.get("fareGroup", {}).get("priceWithTax", 0)
        print(f"Opção {idx:02d} | Cia: {c_nome} | Total: {pts:,.0f} pts")

    print("-" * 65)

    ultimo_menor = obter_ultimo_preco_salvo()

    # Dispara alerta caso o preço seja menor que o histórico anterior ou na primeira execução
    if pontos_total < ultimo_menor or not eh_fallback:
        salvar_novo_menor_preco(pontos_total)
        
        if eh_fallback:
            titulo = "✈️ *PASSAGEM DISNEY - ESFERA*\n⚠️ _(Maio/2028 ainda fechado - Cotando período 04 a 18/10/27)_"
        else:
            titulo = "🚨 *MALHA ABERTA: MAIO/2028 LIBERADO NO ESFERA!*"

        msg = (
            f"{titulo}\n\n"
            f"• *Cia Aérea:* {cia_nome}\n"
            f"• *Rota:* {ORIGEM} ➔ {DESTINO}\n"
            f"• *Datas:* {data_ida} a {data_volta}\n"
            f"• *Pontos Grupo:* {pontos_total:,} pts\n"
            f"• *Pontos/Pessoa:* {pontos_por_pessoa:,} pts\n"
            f"• *Taxas Totais:* R$ {taxas_brl_total:,.2f}\n\n"
            f"[Acessar Esfera Viagens](https://travel.esfera.com.vc)"
        )
        enviar_telegram(msg)
    else:
        print(f"[-] Preço atual ({pontos_total:,} pts) não é inferior ao histórico gravado ({ultimo_menor:,} pts). Notificação silenciada.")

def executar_monitoramento():
    print("--- INICIANDO MONITORAMENTO ESFERA ---")
    
    # 1. Tentativa primária: Maio/2028
    voos = consultar_voos(DATA_IDA_ALVO, DATA_VOLTA_ALVO)
    
    if voos:
        processar_resultados(voos, DATA_IDA_ALVO, DATA_VOLTA_ALVO, eh_fallback=False)
    else:
        # 2. Fallback automático: Outubro/2027
        print("\n[i] Data primária (Maio/2028) indisponível. Acionando fallback para 04 a 18/10/2027...")
        voos_fallback = consultar_voos(DATA_IDA_FALLBACK, DATA_VOLTA_FALLBACK)
        
        if voos_fallback:
            processar_resultados(voos_fallback, DATA_IDA_FALLBACK, DATA_VOLTA_FALLBACK, eh_fallback=True)
        else:
            print("[!] Nenhuma das opções retornou voos no momento.")

if __name__ == "__main__":
    executar_monitoramento()
