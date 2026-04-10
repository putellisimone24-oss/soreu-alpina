import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime

# =========================================================
# 1. INIZIALIZZAZIONE DATABASE VVF
# =========================================================
def init_db_vvf():
    conn = sqlite3.connect('centrale_vvf.db')
    c = conn.cursor()
    # Tabella Mezzi: ID, Nome, Tipo, Sede, Stato
    c.execute('''CREATE TABLE IF NOT EXISTS mezzi_vvf 
                 (id TEXT PRIMARY KEY, tipo TEXT, sede TEXT, stato TEXT)''')
    
    # Inserimento Mezzi Base se vuoto
    c.execute("SELECT COUNT(*) FROM mezzi_vvf")
    if c.fetchone()[0] == 0:
        mezzi = [
            ('APS 1', 'AutoPompa Serbatoio', 'Centrale', 'In Sede'),
            ('APS 2', 'AutoPompa Serbatoio', 'Distaccamento A', 'In Sede'),
            ('AS 1', 'AutoScala', 'Centrale', 'In Sede'),
            ('ABP 1', 'AutoBotte', 'Centrale', 'In Sede'),
            ('AG 1', 'AutoGru', 'Centrale', 'In Sede'),
            ('Vf 1', 'Vettura Comando', 'Centrale', 'In Sede')
        ]
        c.executemany("INSERT INTO mezzi_vvf VALUES (?,?,?,?)", mezzi)
    
    # Tabella Interventi
    c.execute('''CREATE TABLE IF NOT EXISTS interventi_vvf 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, tipologia TEXT, comune TEXT, indirizzo TEXT, stato TEXT, ora_inizio TEXT)''')
    
    conn.commit()
    conn.close()

init_db_vvf()

# =========================================================
# 2. SIDEBAR - STATO DISTACCAMENTI E ADMIN
# =========================================================
with st.sidebar:
    st.title("👨‍🚒 Comando VVF")
    st.subheader("🚒 Stato della Colonna Mobile")
    
    conn = sqlite3.connect('centrale_vvf.db')
    df_mezzi = pd.read_sql_query("SELECT * FROM mezzi_vvf", conn)
    conn.close()

    for _, mezzo in df_mezzi.iterrows():
        colore = "🟢" if mezzo['stato'] == "In Sede" else "🔴"
        st.write(f"{colore} **{mezzo['id']}** - {mezzo['tipo']} ({mezzo['sede']})")

    st.divider()
    # Qui andrebbe la tua gestione Account Admin che abbiamo fatto prima
    st.info("Loggato come: Capo Turno")

# =========================================================
# 3. AREA OPERATIVA - GESTIONE INTERVENTI
# =========================================================
st.title("📟 Sala Operativa 115")

col_sx, col_dx = st.columns([2, 1])

with col_sx:
    st.header("🚨 Interventi in Corso")
    conn = sqlite3.connect('centrale_vvf.db')
    interventi = pd.read_sql_query("SELECT * FROM interventi_vvf WHERE stato='APERTO'", conn)
    conn.close()

    if interventi.empty:
        st.write("Nessun intervento attivo al momento.")
    else:
        for _, intv in interventi.iterrows():
            with st.expander(f"🔥 {intv['tipologia']} - {intv['comune']}", expanded=True):
                st.write(f"**Indirizzo:** {intv['indirizzo']}")
                st.write(f"**Ora Chiamata:** {intv['ora_inizio']}")
                if st.button(f"Chiudi Intervento {intv['id']}", key=f"chiudi_{intv['id']}"):
                    # Logica per chiudere e liberare i mezzi
                    pass

with col_dx:
    st.header("📝 Nuova Scheda")
    with st.container(border=True):
        tipo_int = st.selectbox("Tipologia", [
            "Incendio Civile", 
            "Incendio Boschivo", 
            "Incidente Stradale", 
            "Soccorso Persona", 
            "Apertura Porta",
            "Allagamento"
        ])
        comune = st.text_input("Comune")
        via = st.text_input("Indirizzo")
        
        st.write("---")
        st.subheader("Seleziona Squadre")
        # Selezione multipla dei mezzi disponibili
        mezzi_disponibili = df_mezzi[df_mezzi['stato'] == 'In Sede']['id'].tolist()
        squadre_invio = st.multiselect("Mezzi da inviare", mezzi_disponibili)
        
        if st.button("🚀 INVIA SQUADRE", type="primary", use_container_width=True):
            if comune and via and squadre_invio:
                ora = datetime.now().strftime("%H:%M")
                conn = sqlite3.connect('centrale_vvf.db')
                # Crea intervento
                conn.execute("INSERT INTO interventi_vvf (tipologia, comune, indirizzo, stato, ora_inizio) VALUES (?,?,?,?,?)",
                             (tipo_int, comune, via, 'APERTO', ora))
                # Aggiorna stato mezzi
                for m in squadre_invio:
                    conn.execute("UPDATE mezzi_vvf SET stato='In Intervento' WHERE id=?", (m,))
                conn.commit()
                conn.close()
                st.success("Squadre in uscita!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Compilare tutti i campi e selezionare almeno un mezzo!")

# =========================================================
# 4. TABELLONE RIASSUNTIVO (Opzionale)
# =========================================================
st.divider()
st.subheader("📋 Registro di Servizio (Ultime 24h)")
# Qui potresti mettere la tabella degli interventi chiusi
