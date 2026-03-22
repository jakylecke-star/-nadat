import streamlit as st
import sqlite3
import pandas as pd
import os

# --- 1. ADATBÁZIS INICIALIZÁLÁSA ---
def init_db():
    conn = sqlite3.connect('terc_vegleges.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS normak 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, nev TEXT, egyseg TEXT, anyag REAL, norma REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projekt_tetelek 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, norma_id INTEGER, mennyiseg REAL)''')
    
    c.execute("SELECT count(*) FROM normak")
    if c.fetchone()[0] == 0:
        alap_normak = [
            ('21-001', 'Vázkerámia falazóblokk 30-as', 'm2', 5500, 1.2),
            ('11-002', 'Aljzatbeton készítése C16/20', 'm3', 32000, 2.5),
            ('33-005', 'Belső falfelület festése diszperziós festékkel', 'm2', 850, 0.4)
        ]
        c.executemany("INSERT INTO normak (kod, nev, egyseg, anyag, norma) VALUES (?,?,?,?,?)", alap_normak)
    conn.commit()
    conn.close()

init_db()

# --- 2. OLDAL BEÁLLÍTÁSAI ---
st.set_page_config(page_title="Digitális TERC Oktató", layout="wide", page_icon="🏗️")
st.title("🏗️ Digitális TERC - Költségvetés Készítő")

# --- 3. TÖMEGES FELTÖLTÉS ÉS ÚJ TÉTEL ---
col_menu1, col_menu2 = st.columns(2)

with col_menu1:
    with st.expander("📥 TÖMEGES FELTÖLTÉS (Excel/CSV fájlból)"):
        st.write("A fájl oszlopai: **kod, nev, egyseg, anyag, norma** (pontosvesszővel elválasztva)")
        feltoltott_fajl = st.file_uploader("Válassz ki egy CSV fájlt", type="csv")
        
        # Ez a rész lett javítva, hogy ne legyen NameError
        if feltoltott_fajl is not None:
            try:
                # Beolvassuk és rögtön szűrjük az oszlopokat
                df = pd.read_csv(feltoltott_fajl, sep=";")
                kell_oszlopok = ['kod', 'nev', 'egyseg', 'anyag', 'norma']
                
                # Ellenőrizzük, megvannak-e a szükséges oszlopok
                if all(col in df.columns for col in kell_oszlopok):
                    uj_adatok = df[kell_oszlopok].copy()
                    
                    if st.button("🚀 Importálás indítása"):
                        conn = sqlite3.connect('terc_vegleges.db')
                        uj_adatok.to_sql('normak', conn, if_exists='append', index=False)
                        conn.close()
                        st.success(f"Sikeresen hozzáadva {len(uj_adatok)} új tétel!")
                        st.rerun()
                else:
                    st.error("A CSV fájl oszlopnevei nem megfelelőek! Használd a kért fejlécet.")
            except Exception as e:
                st.error(f"Hiba a fájl feldolgozásakor: {e}")

with col_menu2:
    with st.expander("➕ EGYEDI TÉTEL HOZZÁADÁSA"):
        with st.form("uj_tetel_form"):
            u_kod = st.text_input("Kód")
            u_nev = st.text_input("Megnevezés")
            u_egys = st.selectbox("Egység", ["m2", "m3", "fm", "db", "kg"])
            u_ar = st.number_input("Anyagár", min_value=0)
            u_norm = st.number_input("Normaidő", min_value=0.0, step=0.1)
            if st.form_submit_button("Mentés"):
                conn = sqlite3.connect('terc_vegleges.db')
                conn.execute("INSERT INTO normak (kod, nev, egyseg, anyag, norma) VALUES (?,?,?,?,?)", (u_kod, u_nev, u_egys, u_ar, u_norm))
                conn.commit()
                conn.close()
                st.rerun()

# --- 4. KÖLTSÉGVETÉS ÖSSZEÁLLÍTÁSA ---
st.divider()
conn = sqlite3.connect('terc_vegleges.db')
normak_df = pd.read_sql_query("SELECT * FROM normak ORDER BY nev", conn)

if not normak_df.empty:
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        kiv_nev = st.selectbox("Tétel kiválasztása:", normak_df['nev'].tolist())
    with c2:
        menny = st.number_input("Mennyiség:", min_value=0.1, value=1.0)
    with c3:
        st.write("##")
        if st.button("📥 Hozzáadás"):
            t_id = normak_df[normak_df['nev'] == kiv_nev]['id'].values[0]
            c = conn.cursor()
            c.execute("INSERT INTO projekt_tetelek (norma_id, mennyiseg) VALUES (?,?)", (int(t_id), menny))
            conn.commit()
            st.rerun()

# --- 5. TÁBLÁZAT ÉS ÖSSZESÍTÉS ---
query = """
SELECT n.kod, n.nev, p.mennyiseg, n.egyseg, n.anyag, n.norma, 
       (p.mennyiseg * n.anyag) as ossz_anyag, 
       (p.mennyiseg * n.norma) as ossz_munkaora 
FROM projekt_tetelek p 
JOIN normak n ON p.norma_id = n.id
"""
projekt_df = pd.read_sql_query(query, conn)
conn.close()

if not projekt_df.empty:
    st.subheader("📊 Projekt tételei")
    st.dataframe(projekt_df, use_container_width=True)
    
    col_x, col_y = st.columns(2)
    col_x.metric("Összes anyagköltség", f"{projekt_df['ossz_anyag'].sum():,.0f} Ft".replace(",", " "))
    col_y.metric("Összes munkaóra", f"{projekt_df['ossz_munkaora'].sum():.2f} óra")
    
    if st.button("🗑️ Projekt ürítése"):
        conn = sqlite3.connect('terc_vegleges.db')
        conn.execute("DELETE FROM projekt_tetelek")
        conn.commit()
        conn.close()
        st.rerun()
else:
    st.info("Még nincsenek tételek a projektben.")
