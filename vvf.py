import streamlit as st
import sqlite3
import pd
import time

st.set_page_config(page_title="LOG VVF", layout="wide")
st.title("🚒 Sala Operativa 115 - Log Interventi")

st.info("Questo monitor riceve automaticamente le schede dalla SOREU Alpina")

def carica_missioni():
    conn = sqlite3.connect('centrale_unica.db')
    # Carica solo le missioni dove i VVF sono stati allertati
    df = pd.read_sql_query("SELECT * FROM missioni WHERE stato_vvf != 'Non richiesti' ORDER BY id DESC", conn)
    conn.close()
    return df

# Ciclo di aggiornamento automatico
placeholder = st.empty()

while True:
    with placeholder.container():
        df = carica_missioni()
        if not df.empty:
            for index, row in df.iterrows():
                with st.container(border=True):
                    st.error(f"📟 SCHEDA VVF #{row['id']} - {row['scenario']}")
                    st.write(f"📍 LUOGO: {row['comune']} ({row['target']})")
                    st.info(f"📬 NOTA SANITÀ: {row['note_vvf']}")
                    
                    if st.button(f"SUL POSTO (Intervento {row['id']})"):
                        conn = sqlite3.connect('centrale_unica.db')
                        c = conn.cursor()
                        c.execute("UPDATE missioni SET stato_vvf = 'SUL POSTO' WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.rerun()
        else:
            st.write("Nessun intervento tecnico in attesa.")
        
        time.sleep(5) # Controlla nuovi dati ogni 5 secondi
