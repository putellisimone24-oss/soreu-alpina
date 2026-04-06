import streamlit as st
import pandas as pd
import random
import math
import time
from datetime import datetime

# =========================================================
# 1. CONFIGURAZIONE E SISTEMA ACCESSI (ID/PW)
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore Integrale", layout="wide")

# Database Utenti Persistente
if 'utenti_db' not in st.session_state:
    st.session_state.utenti_db = {
        "admin": {"pw": "admin", "cambio_obbligatorio": False, "ruolo": "Admin"},
        "mario.rossi": {"pw": "mario", "cambio_obbligatorio": True, "ruolo": "Operatore"}
    }

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

# Schermata Login / Cambio Password
if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login Sistema")
    
    if st.session_state.fase_cambio_pw:
        st.warning("⚠️ Primo accesso rilevato: devi cambiare la password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA NUOVA PASSWORD E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                u = st.session_state.temp_user
                st.session_state.utenti_db[u]["pw"] = n_p
                st.session_state.utenti_db[u]["cambio_obbligatorio"] = False
                st.session_state.utente_connesso = u
                st.rerun()
            else:
                st.error("Le password non coincidono o sono troppo corte (min 4 car).")
    else:
        u_in = st.text_input("ID Utente (es: admin o nome.cognome)").lower()
        p_in = st.text_input("Password", type="password")
        if st.button("ENTRA NEL SISTEMA", type="primary"):
            if u_in in st.session_state.utenti_db and st.session_state.utenti_db[u_in]["pw"] == p_in:
                if st.session_state.utenti_db[u_in]["cambio_obbligatorio"]:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else:
                st.error("Credenziali non corrette.")
    st.stop()

# =========================================================
# 2. LOGICA TECNICA E DATABASE MEZZI/OSPEDALI
# =========================================================

# Database Mezzi (Bergamo)
if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII"},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio"},
        "MSA 1 003": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5203, "lon": 9.7547, "tipo": "MSA", "sede": "Osp. Romano"},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo"},
        "CBBG_014.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6725, "lon": 9.6450, "tipo": "MSB", "sede": "Croce Bianca Bergamo"},
        "HORUS I-LMBD": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6710, "lon": 9.7020, "tipo": "ELI", "sede": "Base Elisoccorso BG"}
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4}
    }

if 'assistenze' not in st.session_state:
    st.session_state.assistenze = [
        {"Evento": "Maratona di Bergamo", "Mezzi": "2 MSB", "Data": "12/05/2026", "Stato": "Approvato"},
        {"Evento": "Concerto Stadio", "Mezzi": "1 MSA + 3 MSB", "Data": "20/06/2026", "Stato": "In attesa"}
    ]

# Variabili di Stato
for key in ['missioni', 'registro_radio', 'notifiche_centrale']:
    if key not in st.session_state: st.session_state[key] = [] if 'missione' not in key else {}

if 'auto_mode' not in st.session_state: st.session_state.auto_mode = False
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None

def aggiungi_log_radio(mittente, messaggio):
    ora = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{ora}] 📻 {mittente}: {messaggio}")

def riproduci_allarme():
    st.components.v1.html('<audio autoplay><source src="https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"></audio>', height=0)

# =========================================================
# 3. LOGICA SISTEMA AUTOMATICO EQUIPAGGI
# =========================================================
if st.session_state.auto_mode and st.session_state.missioni:
    now = time.time()
    rimuovere = []
    for m, dati in st.session_state.missioni.items():
        passato = now - dati["timestamp_creazione"]
        db = st.session_state.database_mezzi[m]
        
        if passato > 15 and db["stato"] == "1 - Partenza":
            db["stato"] = "2 - Sul Posto"
            aggiungi_log_radio(m, "STATO 2: Arrivati sul posto. Iniziamo triage.")
        elif passato > 45 and db["stato"] == "2 - Sul Posto":
            db["stato"] = "3 - Partenza Ospedale"
            aggiungi_log_radio(m, "STATO 3: Carico paziente, andiamo verso il PS.")
        elif passato > 90 and db["stato"] == "3 - Partenza Ospedale":
            db["stato"] = "Libero in Sede"; db["colore"] = "🟢"
            aggiungi_log_radio(m, "STATO 4: Paziente consegnato. Mezzo nuovamente LIBERO.")
            rimuovere.append(m)
    for r in rimuovere: del st.session_state.missioni[r]

# =========================================================
# 4. SIDEBAR E PANNELLO ADMIN (ID: admin)
# =========================================================
with st.sidebar:
    st.title(f"👤 {st.session_state.utente_connesso.upper()}")
    if st.button("🚪 ESCI DAL SISTEMA", type="secondary"):
        st.session_state.utente_connesso = None
        st.rerun()
    
    st.divider()
    # Switch Sistema Automatico
    st.session_state.auto_mode = st.toggle("🤖 Sistema Equipaggi Automatico", value=st.session_state.auto_mode)
    if st.session_state.auto_mode:
        st.caption("Gli equipaggi rispondono via radio e cambiano stato in autonomia.")

    # Gestione Utenze (Esclusiva Admin)
    if st.session_state.utente_connesso == "admin":
        st.subheader("🛠️ Gestione Utenze")
        with st.expander("Aggiungi / Rimuovi Operatori", expanded=False):
            n_u = st.text_input("ID Operatore (nome.cognome)")
            n_p = st.text_input("PW Provvisoria (es. nome)")
            if st.button("CREA UTENZA"):
                if n_u and n_p:
                    st.session_state.utenti_db[n_u] = {"pw": n_p, "cambio_obbligatorio": True, "ruolo": "Operatore"}
                    st.success(f"Utenza {n_u} creata!")
                    st.rerun()
            
            st.write("---")
            for usr in list(st.session_state.utenti_db.keys()):
                if usr != "admin":
                    col_u, col_x = st.columns([3, 1])
                    col_u.write(f"👤 {usr}")
                    if col_x.button("❌", key=f"del_{usr}"):
                        del st.session_state.utenti_db[usr]
                        st.rerun()

# =========================================================
# 5. DASHBOARD OPERATIVA
# =========================================================
if st.session_state.scrivania_selezionata is None:
    st.header("Seleziona il tuo ruolo di turno")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🖥️ CENTRALE OPERATIVA (SOREU)", use_container_width=True): 
            st.session_state.scrivania_selezionata = "SOREU"; st.rerun()
    with c2:
        if st.button("🚑 EQUIPAGGIO MEZZO (Triage)", use_container_width=True): 
            st.session_state.scrivania_selezionata = "MEZZO"; st.rerun()

else:
    # --- INTERFACCIA CENTRALE (SOREU) ---
    if st.session_state.scrivania_selezionata == "SOREU":
        st.subheader("📟 Centrale Operativa SOREU Alpina")
        tab_invio, tab_risorse, tab_manifestazioni = st.tabs(["📝 Missioni Attive", "🗺️ Mappa & Risorse", "📩 Manifestazioni"])
        
        with tab_invio:
            col_l, col_r = st.columns([2, 1])
            with col_l:
                if st.button("🔔 SIMULA NUOVA CHIAMATA 112", type="primary"):
                    st.session_state.evento_corrente = {"via": "Piazza Vecchia, Bergamo", "sintomi": "Arresto Cardiaco", "codice": "ROSSO"}
                    riproduci_allarme()
                
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    st.error(f"📍 EMERGENZA: {ev['via']} - 🩺 {ev['sintomi']}")
                    mezzi_liberi = [m for m, v in st.session_state.database_mezzi.items() if v["stato"] == "Libero in Sede"]
                    scelti = st.multiselect("Assegna Risorse:", mezzi_liberi)
                    if st.button("🚀 INVIA MEZZI"):
                        for s in scelti:
                            st.session_state.missioni[s] = {"timestamp_creazione": time.time()}
                            st.session_state.database_mezzi[s]["stato"] = "1 - Partenza"
                            st.session_state.database_mezzi[s]["colore"] = "🟡"
                            aggiungi_log_radio(s, f"Ricevuto, in partenza per {ev['via']}.")
                        st.session_state.evento_corrente = None; st.rerun()
            
            with col_r:
                st.subheader("📻 Registro Radio")
                st.code("\n".join(st.session_state.registro_radio), language="text")

        with tab_risorse:
            st.map(pd.DataFrame([{"lat": v["lat"], "lon": v["lon"]} for v in st.session_state.database_mezzi.values()]))
            st.table(pd.DataFrame.from_dict(st.session_state.database_mezzi, orient='index'))

        with tab_manifestazioni:
            st.header("Assistenze a Manifestazioni")
            st.dataframe(st.session_state.assistenze, use_container_width=True)
            if st.button("Aggiungi Evento Sportivo"):
                st.info("Pannello inserimento nuova assistenza (Simulazione).")

    # --- INTERFACCIA MEZZO (EQUIPAGGIO) ---
    else:
        st.subheader("🚑 Terminale Bordo Mezzo")
        mio = st.selectbox("Seleziona il tuo Mezzo:", list(st.session_state.database_mezzi.keys()))
        d = st.session_state.database_mezzi[mio]
        
        st.info(f"Stato Attuale: **{d['stato']}**")
        
        c1, c2, c3 = st.columns(3)
        if c1.button("🚨 PARTENZA (1)"): 
            d["stato"] = "1 - Partenza"; d["colore"] = "🟡"; aggiungi_log_radio(mio, "Partiti per il target."); st.rerun()
        if c2.button("📍 SUL POSTO (2)"): 
            d["stato"] = "2 - Sul Posto"; aggiungi_log_radio(mio, "Siamo sul posto."); st.rerun()
        if c3.button("🏁 LIBERO (4)"): 
            d["stato"] = "Libero in Sede"; d["colore"] = "🟢"
            if mio in st.session_state.missioni: del st.session_state.missioni[mio]
            aggiungi_log_radio(mio, "Intervento concluso. Mezzo libero."); st.rerun()
        
        st.divider()
        st.subheader("🩺 Triage & Clinica")
        pa = st.slider("Pressione Sistolica", 40, 220, 120)
        fc = st.slider("Frequenza Cardiaca", 30, 200, 80)
        if st.button("📑 INVIA REPORT CLINICO"):
            st.session_state.notifiche_centrale.append(f"Report {mio}: PA {pa}, FC {fc}")
            aggiungi_log_radio(mio, f"Paziente stabilizzato. PA {pa}, FC {fc}. Richiediamo destinazione.")
            st.success("Parametri inviati in centrale!")

    if st.button("⬅️ Torna alla selezione Ruolo"):
        st.session_state.scrivania_selezionata = None; st.rerun()
