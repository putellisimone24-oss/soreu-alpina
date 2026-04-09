import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Monitor VVF", layout="wide")
st.title("🚒 Comando Vigili del Fuoco")

def leggi_missioni():
    conn = sqlite3.connect('centrale.db')
    # --- QUESTA RIGA CREA LA TABELLA SE MANCA ---
    conn.execute('''CREATE TABLE IF NOT EXISTS missioni_vvf 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  scenario TEXT, comune TEXT, indirizzo TEXT, 
                  stato_vvf TEXT, ora TEXT, note TEXT)''')
    # --------------------------------------------
    df = pd.read_sql_query("SELECT * FROM missioni_vvf ORDER BY id DESC", conn)
    conn.close()
    return df

st.write("### 🚨 Interventi Tecnici in tempo reale")

try:
    df = leggi_missioni()
    if not df.empty:
        st.table(df)
    else:
        st.info("In attesa di nuove missioni dalla centrale SOREU...")
except Exception as e:
    st.error(f"Errore nel caricamento dati: {e}")

# Bottone per aggiornare manualmente
if st.button("🔄 Aggiorna Lista"):
    st.rerun()
