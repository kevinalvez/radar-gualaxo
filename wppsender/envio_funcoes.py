import os
import subprocess
from time import sleep

import pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==============================
# ABRIR CONVERSA
# ==============================

def abrir_conversa(driver, delay, numero):
    url = f"https://web.whatsapp.com/send?phone={numero}"
    driver.get(url)

    WebDriverWait(driver, delay).until(
        EC.presence_of_element_located((By.XPATH, "//footer"))
    )

    sleep(3)

    WebDriverWait(driver, delay).until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@contenteditable="true"]')
        )
    )


# ==============================
# ENVIAR ITEM
# ==============================

def enviar_item(driver, delay, item):

    tipo = item.get("tipo")

    # ==========================
    # TEXTO
    # ==========================
    if tipo == "texto":

        conteudo = item.get("conteudo", "")

        campo = WebDriverWait(driver, delay).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            )
        )
        print("ANTES COPY")
        pyperclip.copy(conteudo)
        campo.click()
        sleep(5)
        campo.send_keys(Keys.CONTROL, "v")
        print("DEPOIS COPY")
        sleep(5)
        campo.send_keys(Keys.ENTER)

    # ==========================
    # IMAGEM / VÍDEO / ÁUDIO
    # ==========================
    # ==========================
# IMAGEM / VÍDEO / ÁUDIO
# ==========================
    elif tipo in ["imagem", "video", "audio", "arquivo"]:

        caminho = os.path.abspath(item.get("arquivo", ""))

        if not os.path.exists(caminho):
            print(f"❌ Arquivo não encontrado: {caminho}")
            return

        # copiar pro clipboard (Windows)
        cmd = f'Set-Clipboard -Path "{caminho}"'
        subprocess.run(['powershell', '-command', cmd], check=True)

        # focar campo
        campo = WebDriverWait(driver, delay).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="main"]/footer/div/div/span/div/div/div/div[3]/div')
            )
        )
        campo.click()
        sleep(5)

        # colar arquivo
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()

        print(f"Upload de {tipo}...")

        sleep(15)

        # legenda (só faz sentido pra imagem/vídeo)
        legenda = item.get("legenda")

        if tipo in ["imagem", "video"]:
            legenda_box = WebDriverWait(driver, delay).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//div[@role="textbox"][@contenteditable="true"]')
                )
            )

            if legenda:
                pyperclip.copy(legenda)
                legenda_box.click()
                sleep(1)
                legenda_box.send_keys(Keys.CONTROL, "v")
                sleep(2)

            legenda_box.send_keys(Keys.ENTER)

        else:
            # áudio geralmente envia direto (sem legenda)
            actions.send_keys(Keys.ENTER).perform()


# ==============================
# PRINT
# ==============================

def salvar_print(pyautogui, numero, pasta_base):
    import os
    from datetime import datetime

    largura, altura = pyautogui.size()

    # 👉 porcentagens de corte (ajuste aqui)
    corte_esquerda = 0.35   # 35% da largura
    corte_topo = 0.10       # 10% da altura

    x = int(largura * corte_esquerda)
    y = int(altura * corte_topo)

    w = largura - x
    h = altura - y

    pasta = os.path.join(pasta_base, numero)
    os.makedirs(pasta, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(pasta, f"print_{numero}_{timestamp}.png")

    screenshot = pyautogui.screenshot(region=(x, y, w, h))
    screenshot.save(caminho)

    print(f"📸 Print salvo em: {caminho}")