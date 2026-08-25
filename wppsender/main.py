import json
import os
import random
import csv
from time import sleep
from datetime import datetime
import sys
from gerar_relatorio_docx import gerar_relatorio_docx
from arquivo_contatos import carregar_numeros_txt

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from postgres_service import (
    buscar_destinatarios,
    registrar_auditoria,
    registrar_mob_envio
)
from envio_funcoes import (
    abrir_conversa,
    enviar_item
)

def iniciar_envios():
    # ==============================
    # CONFIG
    # ==============================

    delay = 40
    batch_size = 40
    hora_limite = 18

    # ==============================
    # DADOS DA MOBILIZAÇÃO
    # ==============================

    with open("mobilizacao.json", "r", encoding="utf8") as f:
        mobilizacao = json.load(f)

    telefone_inicial = (
        mobilizacao
        .get("telefone_inicial", "")
        .strip()
    )
    resultado_envio = {
        "envio_id": mobilizacao["envio_id"],
        "tema": mobilizacao["tema"],
        "comunidade": mobilizacao["comunidade"],
        "operador": mobilizacao["operador"],
        "inicio": datetime.now().isoformat(),
        "envios": [],
        "telefone_inicial": telefone_inicial
    }

    comunidade = mobilizacao["comunidade"]


    # ==============================
    # CHROME
    # ==============================

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--user-data-dir=/var/tmp/chrome_user_data")

    driver = webdriver.Chrome(options=options)

    # ==============================
    # CARREGAR NÚMEROS
    # ==============================

    #destinatarios = buscar_destinatarios(comunidade)
    MAPA_TXT = {
        "Bento Rodrigues": "bento_rodrigues.txt",
        "Camargos": "camargos.txt",
        "Bicas": "bicas.txt",
        "Borba": "borba.txt",
        "Pedras": "pedras.txt",
        "Paracatu de Baixo": "paracatu_baixo.txt",
        "Paracatu de Cima": "paracatu_cima.txt",
        "Ponte do Gama": "ponte_do_gama.txt",
        "Campinas": "campinas.txt"
    }
    arquivo_contatos = MAPA_TXT.get(comunidade)

    if not arquivo_contatos:
        raise Exception(
            f"Comunidade sem arquivo TXT: {comunidade}"
        )

    destinatarios = carregar_numeros_txt(
        arquivo_contatos
    )

    # destinatarios = [
    #     {
    #         "identificador": "NFDI-1",
    #         "telefone": "5531993990073"  # seu número
    #     },
    #     {
    #         "identificador": "NFMOB-1",
    #         "telefone": "5531992180129"  # Marlon
    #     },
    #     {
    #         "identificador": "NFMOB-2",
    #         "telefone": "5531997691899"  # Diogo
    #     },
    #     {
    #         "identificador": "NFMOB-3",
    #         "telefone": "553182056195"  # Brenda
    #     },
    #     {
    #         "identificador": "NFMOB-4",
    #         "telefone": "5531999228797"  # Rosa
    #     },
    #     {
    #         "identificador": "NFMOB-5",
    #         "telefone": "5531995632649"  # Wandersson
    #     },
    #     {
    #         "identificador": "NFMOB-6",
    #         "telefone": "5531982023511"  # Danielle
    #     }
    # ]

    if telefone_inicial:

        encontrou = False
        destinatarios_filtrados = []

        for d in destinatarios:

            if encontrou:
                destinatarios_filtrados.append(d)

            elif d["telefone"] == telefone_inicial:
                encontrou = True

        destinatarios = destinatarios_filtrados

        if telefone_inicial and not destinatarios:
            print(
                f"telefone não encontrado: "
                f"{telefone_inicial}"
            )

            driver.quit()
            return
    

    total_number = len(destinatarios)

    print(f"\nTotal de destinatários: {total_number}\n")

    print(f"\nTotal de números: {total_number}\n")

    arquivo_envio = "envios.json"

    if len(sys.argv) > 1 and sys.argv[1] == "temp":
        arquivo_envio = "envios_temp.json"

    with open(arquivo_envio, "r", encoding="utf8") as f:
        envios = json.load(f)
    # ==============================
    # CARREGAR ENVIOS
    # ==============================

    print(f"{len(envios)} itens de envio carregados\n")

    # ==============================
    # LOG CSV
    # ==============================
    # cria pasta de logs (se não existir)

    log_file = "envios_log.csv"

    # cria o arquivo com cabeçalho se ainda não existir
    if not os.path.exists(log_file):
        with open(log_file, "w", newline="", encoding="utf8") as f:
            writer = csv.writer(f)

            writer.writerow([
                "data",
                "identificador",
                "telefone",
                "status",
                "erro"
            ])

    # ==============================
    # ABRIR WHATSAPP
    # ==============================

    driver.get("https://web.whatsapp.com")

    sleep(10)

    # ==============================
    # LOOP PRINCIPAL
    # ==============================

    for idx, destinatario in enumerate(destinatarios):
        
        identificador = destinatario["identificador"]
        telefone = destinatario["telefone"]
        agora = datetime.now()
        
        if agora.hour >= hora_limite:
            print(f"\n horário limite atingido ({hora_limite}:00)")
            print("Encerrando envios...\n")
            break

        if not telefone:
            continue

        print(
            f"{idx+1}/{total_number} "
            f"=> {identificador} "
            f"({telefone})"
        )

        status = "enviado"
        erro_msg = ""

        try:
            sleep(random.randint(5, 10))

            # abre conversa
            abrir_conversa(driver, delay, telefone)

            # envia todos os itens
            for item in envios:
                enviar_item(driver, delay, item)
            
            sleep(3)  # estabilidade entre envios
            
            registrar_auditoria(
                identificador=identificador,
                status="ENVIADO"
            )

            registrar_mob_envio(
                envio_id=resultado_envio["envio_id"],
                tema=resultado_envio["tema"],
                comunidade=resultado_envio["comunidade"],
                operador=resultado_envio["operador"],
                identificador=identificador,
                status="ENVIADO"
            )

            print("✔ Enviado com sucesso\n")

            resultado_envio["envios"].append({
                "identificador": identificador,
                "telefone": telefone,
                "status": "ENVIADO",
                "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "erro": None
            })

            # delay entre contatos
            wait_time = random.randint(25, 60)
            print(f"Aguardando {wait_time}s...\n")
            sleep(wait_time)

            # pausa por lote
            if (idx + 1) % batch_size == 0:
                pausa = random.randint(600, 1200)
                print(f"\nLote concluído. Pausando {pausa/60:.1f} minutos\n")
                sleep(pausa)

        except Exception as e:
            status = "erro"
            erro_msg = str(e)
            print(
                f"❌ Erro com {identificador} "
                f"({telefone}): {erro_msg}"
            )
            resultado_envio["envios"].append({
                "identificador": identificador,
                "telefone": telefone,
                "status": "FALHA",
                "data_envio": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "erro": erro_msg
            })
            registrar_auditoria(
                identificador=identificador,
                status="FALHA",
                erro=erro_msg
            )
            registrar_mob_envio(
                envio_id=resultado_envio["envio_id"],
                tema=resultado_envio["tema"],
                comunidade=resultado_envio["comunidade"],
                operador=resultado_envio["operador"],
                identificador=identificador,
                status="FALHA"
            )

        # ==============================
        # LOG
        # ==============================

        with open(log_file, "a", newline="", encoding="utf8") as f:
            writer = csv.writer(f)

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                identificador,
                telefone,
                status,
                erro_msg
            ])

    # ==============================
    # FINALIZAR
    # ==============================
    sucessos = len([
        x for x in resultado_envio["envios"]
        if x["status"] == "ENVIADO"
    ])

    falhas = len([
        x for x in resultado_envio["envios"]
        if x["status"] == "FALHA"
    ])

    resultado_envio["fim"] = datetime.now().isoformat()
    resultado_envio["total"] = len(resultado_envio["envios"])
    resultado_envio["sucessos"] = sucessos
    resultado_envio["falhas"] = falhas
    with open(
        "resultado_envio.json",
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            resultado_envio,
            f,
            indent=2,
            ensure_ascii=False
        )
    print("\nGerando Relatorio")    
    try:
        gerar_relatorio_docx()
        print("Relatorio gerado com sucesso")

    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")

    driver.quit()

    print("\nEnvio finalizado\n")
    
if __name__ == "__main__":
    iniciar_envios()