import openai
import requests
import time
from datetime import datetime
import pytz
import csv
import re
import os
import json
import traceback

# Nueva importación para conexión con MetaTrader5
import MetaTrader5 as mt5  # type: ignore

# --- DATOS DE CONFIGURACIÓN AQUÍ ---
OLLAMA_API_BASE = "http://localhost:11434/v1"
OLLAMA_MODEL = "deepseek-r1:14b"
TELEGRAM_TOKEN = "TU_TOKEN"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"
TWELVEDATA_API_KEY = "TU_TWELVEDATA_KEY"
SYMBOL = "BTC/USD"  # símbolo usado para las consultas a TwelveData

# Parámetros de conexión a MT5 (rellenar con datos reales)
MT5_LOGIN = 0
MT5_PASSWORD = "PASSWORD"
MT5_SERVER = "BROKER"
MT5_SYMBOL = "BTCUSD"  # símbolo en MT5; puede variar según el bróker

TIMEFRAMES = ["5min", "15min", "1h"]

openai.api_key = "none"
openai.api_base = OLLAMA_API_BASE

# -----------------------------------------------------------------------------------
# Conexión y utilidades de MT5
# -----------------------------------------------------------------------------------

def init_mt5():
    """Inicializa y realiza login en la terminal de MetaTrader 5."""
    try:
        if not mt5.initialize():
            raise RuntimeError(f"initialize() failed: {mt5.last_error()}")
        if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
            raise RuntimeError(f"login() failed: {mt5.last_error()}")
        info = mt5.account_info()
        print(f"[MT5] Conectado. Balance: {info.balance}")
    except Exception as e:
        print(f"[MT5] Error al iniciar: {e}")


def obtener_posiciones_mt5():
    """Obtiene todas las posiciones abiertas y las serializa para el prompt."""
    posiciones = []
    try:
        abiertas = mt5.positions_get()
        if abiertas:
            for p in abiertas:
                posiciones.append({
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "tipo": "COMPRA" if p.type == mt5.POSITION_TYPE_BUY else "VENTA",
                    "precio_entrada": p.price_open,
                    "sl": p.sl,
                    "tp": p.tp,
                    "volumen": p.volume,
                    "precio_actual": mt5.symbol_info_tick(p.symbol).bid if p.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(p.symbol).ask
                })
    except Exception as e:
        print(f"[MT5] Error al obtener posiciones: {e}")
    return posiciones


def obtener_balance_mt5():
    """Retorna el balance actual de la cuenta."""
    try:
        info = mt5.account_info()
        return info.balance if info else 0.0
    except Exception as e:
        print(f"[MT5] Error al obtener balance: {e}")
        return 0.0

# -----------------------------------------------------------------------------------
# Funciones originales de consulta de indicadores (sin cambios relevantes)
# -----------------------------------------------------------------------------------

def consulta_twelvedata(indicador, tf, params=None):
    if params is None:
        params = {}
    url = f"https://api.twelvedata.com/{indicador}"
    default_params = {
        "symbol": SYMBOL,
        "interval": tf,
        "apikey": TWELVEDATA_API_KEY
    }
    default_params.update(params)
    try:
        r = requests.get(url, params=default_params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "values" in data and data["values"]:
            return data["values"][0]
        else:
            print(f"[TWELVE DATA] Sin datos para {indicador} {tf}: {data}")
            return {}
    except Exception as e:
        print(f"[TWELVE DATA] Error al pedir {indicador} {tf}: {e}")
        return {}


def get_indicadores_tf(tf):
    return {
        "precio": consulta_twelvedata("price", tf),
        "vwap": consulta_twelvedata("vwap", tf),
        "rsi": consulta_twelvedata("rsi", tf, {"time_period": 14}),
        "macd": consulta_twelvedata("macd", tf),
        "bollinger": consulta_twelvedata("bbands", tf),
        "adx": consulta_twelvedata("adx", tf, {"time_period": 14}),
        "percent_b": consulta_twelvedata("percent_b", tf),
        "obv": consulta_twelvedata("obv", tf),
        "bop": consulta_twelvedata("bop", tf),
        "typical_price": consulta_twelvedata("typprice", tf),
        "rvol": consulta_twelvedata("rvol", tf),
        "stochastic": consulta_twelvedata("stoch", tf),
        "linearreg": consulta_twelvedata("linearreg", tf),
        "sma": consulta_twelvedata("sma", tf, {"time_period": 14}),
        "atr": consulta_twelvedata("atr", tf, {"time_period": 14}),
        "cci": consulta_twelvedata("cci", tf, {"time_period": 14}),
        "ichimoku": consulta_twelvedata("ichimoku", tf),
    }


def obtener_cierres(tf, cantidad=30):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": tf,
        "outputsize": cantidad,
        "apikey": TWELVEDATA_API_KEY
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        datos = r.json().get("values", [])
        cierres = [d.get("close", None) for d in datos if "close" in d]
        return cierres
    except Exception as e:
        print(f"[TWELVE DATA] Error al obtener cierres: {e}")
        return []


def limpiar(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                out[f"{k}_{sk}"] = sv
        else:
            out[k] = v
    if "datetime" in d:
        out["datetime"] = d["datetime"]
    return out

# -----------------------------------------------------------------------------------
# Prompt que incluye posiciones abiertas y balance de cuenta
# -----------------------------------------------------------------------------------

def generar_prompt(indicadores_multi, cierres_multi, posiciones, balance):
    PROMPT = (
        "Actúa como un trader institucional. Analiza BTC/USD con los indicadores proporcionados y las posiciones abiertas. "
        "Responde SOLO en formato JSON con las recomendaciones."
    )
    for tf, inds in indicadores_multi.items():
        if not inds:
            continue
        PROMPT += f"\n--- {tf} ---\n"
        for k, v in inds.items():
            PROMPT += f"{k}: {v}\n"
        if tf in cierres_multi:
            PROMPT += f"Cierres: {cierres_multi[tf]}\n"
    PROMPT += "\nPosiciones actuales en MT5:\n" + json.dumps(posiciones)
    PROMPT += f"\nBalance de la cuenta: {balance}\n"
    PROMPT += (
        "Formato de respuesta requerido: {\n"
        "  \"nuevas_operaciones\": [{\"accion\": \"COMPRA/VENTA\", \"volumen\": num, \"razon\": str}],\n"
        "  \"cierres\": [{\"ticket\": num, \"razon\": str}],\n"
        "  \"modificaciones\": [{\"ticket\": num, \"nuevo_stop_loss\": num, \"razon\": str}],\n"
        "  \"comentario\": str\n}"
    )
    return PROMPT

# -----------------------------------------------------------------------------------
# Comunicación con Ollama
# -----------------------------------------------------------------------------------

def analizar_con_ollama(prompt):
    try:
        respuesta = openai.ChatCompletion.create(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1500
        )
        return respuesta['choices'][0]['message']['content']
    except Exception as e:
        print(f"[OLLAMA] Error: {e}")
        return "ERROR_OLLAMA"

# -----------------------------------------------------------------------------------
# Envío de mensajes a Telegram
# -----------------------------------------------------------------------------------

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    max_len = 4096
    partes = [mensaje[i:i+max_len] for i in range(0, len(mensaje), max_len)]
    for idx, parte in enumerate(partes):
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": parte}
        try:
            r = requests.post(url, data=data, timeout=10)
            if r.status_code == 200:
                print(f"[TELEGRAM] Parte {idx+1} enviada")
            else:
                print(f"[TELEGRAM] Error: {r.text}")
        except Exception as e:
            print(f"[TELEGRAM] Excepción: {e}")

# -----------------------------------------------------------------------------------
# Logging de acciones
# -----------------------------------------------------------------------------------

def log_accion(hora, tipo, ticket, precio, sl, tp, volumen, razon, respuesta_ia):
    """Registra cualquier acción o error en CSV."""
    file = "historial_acciones.csv"
    if not os.path.isfile(file):
        with open(file, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["hora", "tipo", "ticket", "precio", "sl", "tp", "volumen", "razon", "respuesta_ia"])
    with open(file, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([hora, tipo, ticket, precio, sl, tp, volumen, razon, respuesta_ia.replace("\n", " ")])

# -----------------------------------------------------------------------------------
# Parsing y ejecución de acciones recomendadas por la IA
# -----------------------------------------------------------------------------------

def parsear_respuesta(respuesta):
    """Extrae y valida el JSON devuelto por la IA."""
    try:
        match = re.search(r"\{.*\}", respuesta, re.DOTALL)
        if not match:
            raise ValueError("No se encontró JSON")
        data = json.loads(match.group())
        # Aseguramos las claves esperadas
        for key in ["nuevas_operaciones", "cierres", "modificaciones", "comentario"]:
            data.setdefault(key, []) if key != "comentario" else data.setdefault(key, "")
        return data
    except Exception as e:
        print(f"[IA] Error al parsear JSON: {e}")
        log_accion(datetime.now().isoformat(), "error", None, None, None, None, None, f"JSON inválido: {e}", respuesta)
        return {"nuevas_operaciones": [], "cierres": [], "modificaciones": [], "comentario": ""}


def abrir_operacion(accion, volumen, razon, respuesta_ia):
    """Ejecuta una operación de compra o venta en MT5."""
    symbol_info = mt5.symbol_info(MT5_SYMBOL)
    if not symbol_info or not symbol_info.visible:
        mt5.symbol_select(MT5_SYMBOL, True)
    precio = mt5.symbol_info_tick(MT5_SYMBOL).ask if accion == "COMPRA" else mt5.symbol_info_tick(MT5_SYMBOL).bid
    tipo = mt5.ORDER_TYPE_BUY if accion == "COMPRA" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": MT5_SYMBOL,
        "volume": volumen,
        "type": tipo,
        "price": precio,
        "deviation": 20,
        "sl": 0,
        "tp": 0,
        "comment": "bot_ia"
    }
    result = mt5.order_send(request)
    hora = datetime.now().isoformat()
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        msg = f"[MT5] Operación {accion} ejecutada. Ticket {result.order}"
        enviar_telegram(msg + f"\nMotivo: {razon}")
        log_accion(hora, f"apertura_{accion.lower()}", result.order, precio, 0, 0, volumen, razon, respuesta_ia)
    else:
        err = f"Error apertura {accion}: {result.retcode}"
        enviar_telegram(err)
        log_accion(hora, "error_apertura", None, precio, 0, 0, volumen, err, respuesta_ia)


def cerrar_operacion(ticket, razon, respuesta_ia):
    pos = mt5.positions_get(ticket=ticket)
    hora = datetime.now().isoformat()
    if not pos:
        err = f"No se encontró posición {ticket}"
        enviar_telegram(err)
        log_accion(hora, "error_cierre", ticket, None, None, None, None, err, respuesta_ia)
        return
    p = pos[0]
    price = mt5.symbol_info_tick(p.symbol).bid if p.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(p.symbol).ask
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": p.symbol,
        "volume": p.volume,
        "type": mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 20,
        "comment": "bot_ia_close"
    }
    result = mt5.order_send(req)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        msg = f"[MT5] Posición {ticket} cerrada"
        enviar_telegram(msg + f"\nMotivo: {razon}")
        log_accion(hora, "cierre", ticket, price, p.sl, p.tp, p.volume, razon, respuesta_ia)
    else:
        err = f"Error cierre {ticket}: {result.retcode}"
        enviar_telegram(err)
        log_accion(hora, "error_cierre", ticket, price, p.sl, p.tp, p.volume, err, respuesta_ia)


def modificar_sl(ticket, nuevo_sl, razon, respuesta_ia):
    pos = mt5.positions_get(ticket=ticket)
    hora = datetime.now().isoformat()
    if not pos:
        err = f"No se encontró posición {ticket}"
        enviar_telegram(err)
        log_accion(hora, "error_mod_sl", ticket, None, None, None, None, err, respuesta_ia)
        return
    p = pos[0]
    req = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": p.symbol,
        "sl": nuevo_sl,
        "tp": p.tp,
        "comment": "bot_ia_sl"
    }
    result = mt5.order_send(req)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        msg = f"[MT5] StopLoss de {ticket} modificado a {nuevo_sl}"
        enviar_telegram(msg + f"\nMotivo: {razon}")
        log_accion(hora, "modificacion_sl", ticket, p.price_open, nuevo_sl, p.tp, p.volume, razon, respuesta_ia)
    else:
        err = f"Error modificar SL {ticket}: {result.retcode}"
        enviar_telegram(err)
        log_accion(hora, "error_mod_sl", ticket, p.price_open, nuevo_sl, p.tp, p.volume, err, respuesta_ia)


def ejecutar_acciones(respuesta_json, respuesta_ia):
    for op in respuesta_json.get("nuevas_operaciones", []):
        try:
            abrir_operacion(op.get("accion", ""), op.get("volumen", 0), op.get("razon", ""), respuesta_ia)
        except Exception:
            enviar_telegram("Error abriendo operación")
            log_accion(datetime.now().isoformat(), "error_apertura", None, None, None, None, None, traceback.format_exc(), respuesta_ia)

    for c in respuesta_json.get("cierres", []):
        try:
            cerrar_operacion(c.get("ticket"), c.get("razon", ""), respuesta_ia)
        except Exception:
            enviar_telegram("Error cerrando posición")
            log_accion(datetime.now().isoformat(), "error_cierre", c.get("ticket"), None, None, None, None, traceback.format_exc(), respuesta_ia)

    for m in respuesta_json.get("modificaciones", []):
        try:
            modificar_sl(m.get("ticket"), m.get("nuevo_stop_loss"), m.get("razon", ""), respuesta_ia)
        except Exception:
            enviar_telegram("Error modificando SL")
            log_accion(datetime.now().isoformat(), "error_mod_sl", m.get("ticket"), None, m.get("nuevo_stop_loss"), None, None, traceback.format_exc(), respuesta_ia)

# -----------------------------------------------------------------------------------
# Utilidades varias
# -----------------------------------------------------------------------------------

def debe_consultar(tf, dt):
    minute = dt.minute
    if tf == "5min":
        return minute % 5 == 0
    elif tf == "15min":
        return minute % 15 == 0
    elif tf == "30min":
        return minute % 30 == 0
    elif tf == "1h":
        return True
    return False

# -----------------------------------------------------------------------------------
# Programa principal
# -----------------------------------------------------------------------------------

if __name__ == "__main__":
    init_mt5()
    sydney = pytz.timezone("Australia/Sydney")
    datos_guardados = {tf: {} for tf in TIMEFRAMES}
    cierres_guardados = {tf: [] for tf in TIMEFRAMES}
    datetime_guardados = {tf: None for tf in TIMEFRAMES}

    while True:
        now_sydney = datetime.now(sydney)
        print(f"⏳ {now_sydney.strftime('%Y-%m-%d %H:%M:%S')} - Analizando...")
        for tf in TIMEFRAMES:
            datos_vacios = datos_guardados[tf] is None or datos_guardados[tf] == {}
            nuevos_datos = limpiar(get_indicadores_tf(tf))
            nuevo_datetime = nuevos_datos.get('precio_datetime') or nuevos_datos.get('datetime')
            guardado_datetime = datetime_guardados[tf]
            if tf == "1h":
                if datos_vacios or (nuevo_datetime and nuevo_datetime != guardado_datetime):
                    if nuevos_datos and nuevo_datetime:
                        datos_guardados[tf] = nuevos_datos
                        cierres_guardados[tf] = obtener_cierres(tf, cantidad=30)
                        datetime_guardados[tf] = nuevo_datetime
                        print(f"✅ 1h actualizado ({nuevo_datetime})")
                    else:
                        print(f"⚠️ Datos inválidos en {tf}")
                        datos_guardados[tf] = {}
                else:
                    print(f"Usando vela 1h guardada ({guardado_datetime})")
            else:
                if datos_vacios or debe_consultar(tf, now_sydney):
                    if nuevos_datos:
                        datos_guardados[tf] = nuevos_datos
                        cierres_guardados[tf] = obtener_cierres(tf, cantidad=30)
                        datetime_guardados[tf] = nuevo_datetime
                        print(f"✅ {tf} actualizado ({nuevo_datetime})")
                    else:
                        print(f"⚠️ Datos inválidos en {tf}")
                        datos_guardados[tf] = {}
                else:
                    print(f"Usando datos guardados en {tf} ({guardado_datetime})")

        posiciones = obtener_posiciones_mt5()
        balance = obtener_balance_mt5()
        prompt = generar_prompt(datos_guardados, cierres_guardados, posiciones, balance)
        respuesta_ia = analizar_con_ollama(prompt)
        print("Respuesta IA:\n", respuesta_ia)
        acciones = parsear_respuesta(respuesta_ia)
        ejecutar_acciones(acciones, respuesta_ia)
        if acciones.get("comentario"):
            enviar_telegram("Comentario IA: " + acciones["comentario"])
        print("Ciclo terminado. Esperando 60 segundos...\n" + "-"*40)
        time.sleep(60)
