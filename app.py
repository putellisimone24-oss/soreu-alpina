import streamlit as st
import pandas as pd
import random
import math
import time
import sqlite3
from datetime import datetime

# =========================================================
# 1. GESTIONE DATABASE PERSISTENTE (SQLITE) - POTENZIATO
# =========================================================
def init_db():
    conn = sqlite3.connect('centrale.db', check_same_thread=False)
    c = conn.cursor()
    # Tabella Utenti (Esistente)
    c.execute('''CREATE TABLE IF NOT EXISTS utenti 
                 (username TEXT PRIMARY KEY, password TEXT, cambio_obbligatorio INTEGER, ruolo TEXT)''')
    
    # Tabella Missioni Condivise (Per Multi-User Reale)
    c.execute('''CREATE TABLE IF NOT EXISTS missioni_condivise 
                 (mezzo TEXT PRIMARY KEY, target TEXT, lat REAL, lon REAL, codice TEXT, 
                  ospedale_assegnato TEXT, patologia TEXT, timestamp_creazione REAL, 
                  clinica_ok INTEGER DEFAULT 0, ossigeno_ok INTEGER DEFAULT 1)''')
    
    # Tabella Statistiche Fine Turno
    c.execute('''CREATE TABLE IF NOT EXISTS statistiche_missioni 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, mezzo TEXT, codice TEXT, ospedale TEXT, data TEXT)''')
    
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

# --- Funzioni DB per Sincronizzazione Real-Time ---
def db_salva_missione(mezzo, target, lat, lon, codice, ospedale, patologia):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO missioni_condivise 
                 (mezzo, target, lat, lon, codice, ospedale_assegnato, patologia, timestamp_creazione) 
                 VALUES (?,?,?,?,?,?,?,?)""", 
              (mezzo, target, lat, lon, codice, ospedale, patologia, time.time()))
    conn.commit()
    conn.close()

def db_get_missioni():
    conn = sqlite3.connect('centrale.db')
    df = pd.read_sql_query("SELECT * FROM missioni_condivise", conn)
    conn.close()
    return df

def db_aggiorna_clinica(mezzo, stato):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("UPDATE missioni_condivise SET clinica_ok=? WHERE mezzo=?", (1 if stato else 0, mezzo))
    conn.commit()
    conn.close()

def db_chiudi_missione(mezzo, codice, ospedale):
    conn = sqlite3.connect('centrale.db')
    c = conn.cursor()
    c.execute("DELETE FROM missioni_condivise WHERE mezzo=?", (mezzo,))
    c.execute("INSERT INTO statistiche_missioni (mezzo, codice, ospedale, data) VALUES (?,?,?,?)",
              (mezzo, codice, ospedale, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

init_db()

# =========================================================
# 2. SCHERMATA LOGIN (INVARIATA)
# =========================================================
st.set_page_config(page_title="SOREU Alpina - Simulatore 118", layout="wide")

if 'utente_connesso' not in st.session_state:
    st.session_state.utente_connesso = None
if 'fase_cambio_pw' not in st.session_state:
    st.session_state.fase_cambio_pw = False

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

if st.session_state.utente_connesso is None:
    st.title("🔐 SOREU Alpina - Login")
    if st.session_state.fase_cambio_pw:
        st.warning(f"⚠️ Primo accesso per {st.session_state.temp_user}: Imposta una nuova password.")
        n_p = st.text_input("Nuova Password", type="password")
        c_p = st.text_input("Conferma Password", type="password")
        if st.button("SALVA E ACCEDI"):
            if n_p == c_p and len(n_p) >= 4:
                aggiorna_password_db(st.session_state.temp_user, n_p)
                st.session_state.utente_connesso = st.session_state.temp_user
                st.rerun()
            else: st.error("Errore nelle password (minimo 4 caratteri).")
    else:
        u_in = st.text_input("Username").lower().strip()
        p_in = st.text_input("Password", type="password")
        if st.button("ACCEDI", type="primary"):
            user_data = get_utente_db(u_in)
            if user_data and user_data[1] == p_in:
                if user_data[2] == 1:
                    st.session_state.fase_cambio_pw = True
                    st.session_state.temp_user = u_in
                    st.rerun()
                else:
                    st.session_state.utente_connesso = u_in
                    st.rerun()
            else: st.error("ID o Password errati.")
    st.stop()

# =========================================================
# 3. LOGICA ORIGINALE INTEGRALE + NUOVI MODULI
# =========================================================

def riproduci_suono_allarme():
    audio_url = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

def riproduci_suono_notifica():
    audio_url = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"
    sound_html = f'<audio autoplay style="display:none;"><source src="{audio_url}" type="audio/ogg"></audio>'
    st.components.v1.html(sound_html, height=0, width=0)

if 'database_mezzi' not in st.session_state:
    st.session_state.database_mezzi = {
        "MSA 02 001": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6869, "lon": 9.6272, "tipo": "MSA", "sede": "Osp. Papa Giovanni XXIII", "ossigeno": 100},
        "MSA 2 004": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.5220, "lon": 9.5990, "tipo": "MSA", "sede": "Osp. Treviglio", "ossigeno": 100},
        "CRI_BG_161.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6928, "lon": 9.6428, "tipo": "MSB", "sede": "CRI Bergamo", "ossigeno": 100},
        "CBBG_014.C": {"stato": "Libero in Sede", "colore": "🟢", "lat": 45.6725, "lon": 9.6450, "tipo": "MSB", "sede": "Croce Bianca Bergamo", "ossigeno": 100},
    }

if 'database_ospedali' not in st.session_state:
    st.session_state.database_ospedali = {
        "Osp. Papa Giovanni XXIII (BG)": {"pazienti": 0, "max": 12, "hub": True},
        "Osp. Treviglio-Caravaggio": {"pazienti": 0, "max": 6, "hub": False},
        "Osp. Romano di Lombardia": {"pazienti": 0, "max": 4, "hub": False},
        "Cliniche Gavazzeni (BG)": {"pazienti": 0, "max": 5, "hub": False}
    }

# --- Variabili di Stato ---
if 'notifiche_centrale' not in st.session_state: st.session_state.notifiche_centrale = []
if 'registro_radio' not in st.session_state: st.session_state.registro_radio = []
if 'scrivania_selezionata' not in st.session_state: st.session_state.scrivania_selezionata = None
if 'ruolo' not in st.session_state: st.session_state.ruolo = None; st.session_state.mezzo_selezionato = None
if 'turno_iniziato' not in st.session_state: st.session_state.turno_iniziato = False
if 'evento_corrente' not in st.session_state: st.session_state.evento_corrente = None
if 'last_mission_time' not in st.session_state: st.session_state.last_mission_time = time.time()
if 'time_mult' not in st.session_state: st.session_state.time_mult = 1.0

def calcola_distanza_e_tempo(lat1, lon1, lat2, lon2, is_eli=False):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distanza = R * c
    velocita = 220.0 if is_eli else 45.0
    tempo_minuti = round((distanza / velocita) * 60)
    return round(distanza, 1), tempo_minuti

def aggiungi_log_radio(mittente, messaggio):
    orario = datetime.now().strftime("%H:%M:%S")
    st.session_state.registro_radio.insert(0, f"[{orario}] 📻 {mittente}: {messaggio}")

# --- Generazione Eventi ---
database_indirizzi = [
    {"comune": "Bergamo", "via": "Via della Croce Rossa 2", "lat": 45.6928, "lon": 9.6428},
    {"comune": "Treviglio", "via": "Via Roma 12", "lat": 45.5268, "lon": 9.5925},
]
scenari_clinici = [
    {"sintomi": "Uomo 60 anni, dolore forte retrosternale.", "codice_reale": "ROSSO", "patologia": "IMA"},
    {"sintomi": "Ragazzo caduto da moto, trauma arto.", "codice_reale": "GIALLO", "patologia": "Trauma"},
]

# ==================== INTERFACCIA PRINCIPALE ====================

if st.session_state.scrivania_selezionata is None:
    st.subheader("🖥️ Selezione Postazione di Lavoro")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🖥️ Accedi come CENTRALE"): 
            st.session_state.scrivania_selezionata = "SOREU"; st.session_state.ruolo = "centrale"; st.rerun()
    with c2:
        if st.button("🚑 Accedi come EQUIPAGGIO"): 
            st.session_state.scrivania_selezionata = "MEZZO"; st.session_state.ruolo = "mezzo"; st.rerun()

else:
    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 📍 {st.session_state.scrivania_selezionata}")
    if st.sidebar.button("⬅️ LOGOUT"):
        st.session_state.scrivania_selezionata = None; st.rerun()

    # --- CENTRALE ---
    if st.session_state.ruolo == "centrale":
        tab_op, tab_ris, tab_stats = st.tabs(["📝 Operazioni", "🚑 Mezzi", "📊 Statistiche"])
        
        with tab_op:
            col_invio, col_mappa = st.columns([1, 1])
            with col_invio:
                if st.button("🔔 Ricevi Nuova Chiamata"):
                    ev = random.choice(database_indirizzi)
                    clin = random.choice(scenari_clinici)
                    st.session_state.evento_corrente = {**ev, **clin}
                    riproduci_suono_allarme()
                
                if st.session_state.evento_corrente:
                    ev = st.session_state.evento_corrente
                    st.error(f"EVENTO: {ev['via']} - {ev['sintomi']}")
                    codice = st.selectbox("Codice", ["ROSSO", "GIALLO", "VERDE"])
                    mezzo = st.selectbox("Assegna Mezzo", [m for m, d in st.session_state.database_mezzi.items() if d['stato'] == "Libero in Sede"])
                    osp = st.selectbox("Ospedale", list(st.session_state.database_ospedali.keys()))
                    
                    if st.button("🚀 INVIA"):
                        db_salva_missione(mezzo, ev['via'], ev['lat'], ev['lon'], codice, osp, ev['patologia'])
                        st.session_state.database_mezzi[mezzo]['stato'] = "1 - Inviato"
                        st.session_state.evento_corrente = None
                        st.rerun()
            
            with col_mappa:
                st.map(pd.DataFrame([{"lat": 45.69, "lon": 9.66}])) # Semplificata per brevità
                st.subheader("📻 Registro Radio")
                st.text_area("Log", "\n".join(st.session_state.registro_radio[:10]), height=150)

        with tab_stats:
            st.header("📈 Rendimento Turno")
            conn = sqlite3.connect('centrale.db')
            df_s = pd.read_sql_query("SELECT * FROM statistiche_missioni", conn)
            conn.close()
            if not df_s.empty:
                st.write(f"Missioni totali completate: {len(df_s)}")
                st.bar_chart(df_s['codice'].value_counts())
                st.dataframe(df_s, use_container_width=True)

    # --- MEZZO ---
    elif st.session_state.ruolo == "mezzo":
        if st.session_state.mezzo_selezionato is None:
            st.session_state.mezzo_selezionato = st.selectbox("Seleziona il tuo Mezzo", list(st.session_state.database_mezzi.items()))
            if st.button("Collega Terminale"): st.rerun()
        else:
            mio_mezzo = st.session_state.mezzo_selezionato[0]
            dati_m = st.session_state.database_mezzi[mio_mezzo]
            
            # Controllo Consumabili (Ossigeno)
            if dati_m['ossigeno'] < 20:
                st.error("⚠️ OSSIGENO IN ESAURIMENTO! Torna in sede.")
                if st.button("🔄 Rifornimento Presidi"):
                    dati_m['ossigeno'] = 100; st.rerun()
            
            # Recupero missione dal DB Condiviso
            df_m = db_get_missioni()
            miss = df_m[df_m['mezzo'] == mio_mezzo]
            
            if not miss.empty:
                m_data = miss.iloc[0]
                st.header(f"📟 Terminale {mio_mezzo}")
                st.warning(f"🎯 TARGET: {m_data['target']} | CODICE: {m_data['codice']}")
                
                # Check-list Realismo
                st.subheader("📋 Check-list Clinica (Obbligatoria per STATO 3)")
                c1 = st.checkbox("Paziente Immobilizzato", value=m_data['clinica_ok'])
                c2 = st.checkbox("ECG Eseguito", value=m_data['clinica_ok'])
                c3 = st.checkbox("Parametri Trasmessi", value=m_data['clinica_ok'])
                
                if (c1 and c2 and c3) != m_data['clinica_ok']:
                    db_aggiorna_clinica(mio_mezzo, (c1 and c2 and c3))
                    st.rerun()

                col_stati = st.columns(4)
                if col_stati[0].button("🚨 STATO 1"): aggiungi_log_radio(mio_mezzo, "In partenza")
                if col_stati[1].button("📍 STATO 2"): aggiungi_log_radio(mio_mezzo, "Arrivati sul posto")
                
                # Blocco Stato 3 se check-list non completa
                if col_stati[2].button("🏥 STATO 3", disabled=not m_data['clinica_ok']):
                    aggiungi_log_radio(mio_mezzo, f"Direzione {m_data['ospedale_assegnato']}")
                
                if col_stati[3].button("🏁 STATO 4", type="primary"):
                    db_chiudi_missione(mio_mezzo, m_data['codice'], m_data['ospedale_assegnato'])
                    st.session_state.database_mezzi[mio_mezzo]['stato'] = "Libero in Sede"
                    st.session_state.database_mezzi[mio_mezzo]['ossigeno'] -= 30 # Consumo
                    st.success("Missione chiusa!")
                    st.rerun()
            else:
                st.info("☘️ Nessuna missione assegnata. In attesa...")
