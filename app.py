import streamlit as st
import pandas as pd
import numpy as np
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE)
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    c.execute("SELECT COUNT(*) FROM utenti")
    if c.fetchone()[0] == 0:
        utenti_iniziali = [
            ('admin', 'admin', 0, 'Admin'),
            ('simone.putelli', 'simone', 1, 'Operatore'),
            ('simone.marinoni', 'simone', 1, 'Operatore')
        ]
        c.executemany("INSERT INTO utenti VALUES (?,?,?,?)", utenti_iniziali)
    conn.commit()
    conn.close()

def get_utente_db(username):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("SELECT username, password, cambio_obbligatorio, ruolo FROM utenti WHERE username=?", (username,))
    res = c.fetchone()
    conn.close()
    return res

def aggiorna_password_db(username, nuova_pw):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("UPDATE utenti SET password=?, cambio_obbligatorio=0 WHERE username=?", (nuova_pw, username))
    conn.commit()
    conn.close()

init_db()

# =========================================================
# 2. FUNZIONI TECNICHE (ECG, AUDIO, DISTANZE)
# =========================================================
def genera_tracciato_ecg():
    x = np.linspace(0, 10, 500)
    y = np.sin(x * 1.2 * 2 * np.pi) + 0.5 * np.sin(x * 2.4 * 2 * np.pi) + np.random.normal(0, 0.05, 500)
    return pd.DataFrame({"Tempo": x, "mV": y})

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    st.components.v1.html(f'<audio autoplay style="display:none;"><source src="{audio_url}"></audio>', height=0)

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo = round((distanza / velocita) * 60)
    return round(distanza, 1), max(1, tempo)

# =========================================================
# 3. CONFIGURAZIONE E SESSION STATE
# =========================================================
st.set_page_config(page_title="SOREU Alpina - PRO System", layout="wide")

# Login State
if 'utente_connesso' not in st.session_state: st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state: st.session_state.fase_cambio_pw = False
if 'temp_user' not in st.session_state: st.session_state.temp_user = None
if 'ecg_repository' not in st.session_state: st.session_state.ecg_repository = {}

# Database Mezzi (Tua Logica Originale)
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso Bergamo"}
    }

# Database Ospedali
if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True, "lat": 45.6869, "lon": 9.6272},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False, "lat": 45.5220, "lon": 9.5990},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False, "lat": 45.6900, "lon": 9.6800}
    }

# Inventario Nuova Funzione
if 'inventario_mezzi' not in st.session_state:
    st.session_state.inventario_mezzi = {m: {"O2": 100, "Elettrodi": 20} for m in st.session_state.database_mezzi.keys()}

# Variabili Operative
for var in ['missioni', 'notifiche_centrale', 'registro_radio', 'scrivania_selezionata', 'ruolo', 'mezzo_selezionato', 'evento_corrente', 'last_mission_time', 'turno_iniziato', 'auto_mode', 'log_chiamate']:
    if var not in st.session_state:
        st.session_state[var] = [] if any(x in var for x in ['notifiche', 'registro', 'log']) else ({} if var == 'missioni' else (False if 'mode' in var or 'turno' in var else None))

def aggiungi_log_radio(mittente, messaggio):
    st.session_state.registro_radio.insert(0, f"[{datetime.now().strftime('%H:%M:%S')}] 📻 {mittente}: {messaggio}")

# =========================================================
# 4. GESTIONE LOGIN
# =========================================================
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        st.warning(f"Primo accesso per {st.session_state.temp_user}. Imposta una nuova password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Le password non coincidono o sono troppo corte.")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI", type="primary"):
            res = get_utente_db(u_in)
            if res and res[1] == p_in:
                if res[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("Credenziali Errate")
    st.stop()

# =========================================================
# 5. DASHBOARD SELEZIONE RUOLO
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.header(f"Benvenuto Operatore: {st.session_state.utente_connesso}")
    c1, c2 = st.columns(2)
    if c1.button("🖥️ CENTRALE OPERATIVA (SALA)", use_container_width=True):
        st.session_state.scrivania_selezionata = "SALA"; st.session_state.ruolo = "centrale"; st.rerun()
    if c2.button("🚑 TABLET BORDO MEZZO (ESTERNO)", use_container_width=True):
        st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

# =========================================================
# 6. LOGICA CENTRALE (LOGICA TARGET ORIGINALE)
# =========================================================
elif st.session_state.ruolo == "centrale":
    st.sidebar.button("🔙 Menu", on_click=lambda: st.session_state.update({"scrivania_selezionata": None}))
    tab1, tab2, tab3, tab4 = st.tabs(["📟 Missioni", "🗺️ Mappa", "🏥 Ospedali", "📊 Tele-ECG"])
    
    with tab1:
        st.subheader("Gestione Eventi")
        # Pulsante per simulare la tua logica originale di generazione target
        if st.button("🚨 GENERA NUOVO TARGET (TEST)"):
            nuovo_id = f"T{random.randint(100, 999)}"
            st.session_state.missioni[nuovo_id] = {
                "target": f"Via Roma {random.randint(1,50)}", 
                "codice": "ROSSO",
                "timestamp_creazione": time.time()
            }
            riproduci_suono_allarme()
            st.rerun()
        
        if st.session_state.missioni:
            for m_id, dati in st.session_state.missioni.items():
                st.write(f"📌 **{m_id}**: {dati['target']} - Codice: {dati['codice']}")

    with tab2:
        df_mezzi = pd.DataFrame([{"lat": d["lat"], "lon": d["lon"], "Mezzo": k} for k, d in st.session_state.database_mezzi.items()])
        st.map(df_mezzi)
        
    with tab3:
        for osp, dati in st.session_state.database_ospedali.items():
            st.write(f"**{osp}**: {dati['pazienti']}/{dati['max']} pazienti")
            st.progress(dati['pazienti']/dati['max'])

    with tab4:
        st.subheader("📡 ECG dal Campo")
        if not st.session_state.ecg_repository:
            st.info("Nessun tracciato ricevuto.")
        for m, ecg in st.session_state.ecg_repository.items():
            with st.expander(f"🚑 Tracciato da {m}", expanded=True):
                st.line_chart(ecg, x="Tempo", y="mV")
                if st.button(f"Valida referto {m}"): st.success("ECG Validato dal Medico di Centrale.")

# =========================================================
# 7. LOGICA MEZZO (SCHEDA PAZIENTE + INVENTARIO + ECG)
# =========================================================
elif st.session_state.ruolo == "mezzo":
    if st.session_state.mezzo_selezionato is None:
        st.session_state.mezzo_selezionato = st.selectbox("Seleziona Mezzo in Servizio", list(st.session_state.database_mezzi.keys()))
        if st.button("CONNETTI TERMINALE"): st.rerun()
    else:
        mio_mezzo = st.session_state.mezzo_selezionato
        inv = st.session_state.inventario_mezzi[mio_mezzo]
        st.title(f"🚑 Tablet: {mio_mezzo}")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("📦 Inventario")
            st.metric("O2 Residuo", f"{inv['O2']}%")
            st.metric("Elettrodi", inv['Elettrodi'])
            if st.button("🔄 Rifornimento in Sede"):
                st.session_state.inventario_mezzi[mio_mezzo] = {"O2": 100, "Elettrodi": 20}
                st.rerun()
        
        with c2:
            st.subheader("🩺 Monitor & Parametri")
            pa = st.slider("PA Sistolica", 40, 220, 120)
            fc = st.slider("FC", 30, 200, 80)
            
            # Funzione ECG Integrata
            if st.button("📉 TRASMETTI ECG A SOREU", type="primary", use_container_width=True):
                if inv['Elettrodi'] >= 4:
                    st.session_state.inventario_mezzi[mio_mezzo]['Elettrodi'] -= 4
                    st.session_state.ecg_repository[mio_mezzo] = genera_tracciato_ecg()
                    st.toast("ECG Trasmesso!", icon="📉")
                    st.rerun()
                else:
                    st.error("Elettrodi insufficienti per ECG!")
            
            if mio_mezzo in st.session_state.ecg_repository:
                st.line_chart(st.session_state.ecg_repository[mio_mezzo], x="Tempo", y="mV")

            st.divider()
            # Chiusura Intervento con Logica Consumo
            if st.button("🏁 CHIUDI INTERVENTO (STATO 4)"):
                st.session_state.inventario_mezzi[mio_mezzo]["O2"] -= random.randint(5, 15)
                st.session_state.database_mezzi[mio_mezzo]["stato"] = "Libero in Sede"
                st.session_state.database_mezzi[mio_mezzo]["colore"] = "🟢"
                if mio_mezzo in st.session_state.ecg_repository: del st.session_state.ecg_repository[mio_mezzo]
                aggiungi_log_radio(mio_mezzo, "Intervento concluso. Mezzo libero.")
                st.rerun()
