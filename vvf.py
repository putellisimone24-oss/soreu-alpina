import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="Monitor VVF", layout="wide")
st.title("🚒 Comando Vigili del Fuoco")

def leggi_missioni():
    conn = sqlite3.connect('centrale.db')
    df = pd.read_sql_query("SELECT * FROM missioni_vvf ORDER BY id DESC", conn)
    conn.close()
    return df

st.write("Interventi tecnici attivi:")
df = leggi_missioni()
st.table(df) # Questo ti fa vedere la lista degli interventi
