import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURAZIONE ---
ITEMS = [
    "Dirind", "Gestita", "Credito al consumo", "Pac", "Avvera", 
    "Danni", "Vita", "Mutui", "MT", "BT", "Clienti", "Clienti affidati aziende"
]
GESTORI = ["Gup", "CCe", "Gsf", "Rdf"]
FILE_BUDGET = "budget_gestori.csv"
FILE_DATI = "registrazioni.csv"

st.set_page_config(page_title="Monitoraggio Budget & Gap", layout="wide")

# --- FUNZIONI DI CARICAMENTO ---
def carica_budget():
    if os.path.exists(FILE_BUDGET):
        return pd.read_csv(FILE_BUDGET)
    data = {"Item": ITEMS}
    for g in GESTORI: data[g] = 0.0
    return pd.DataFrame(data)

def carica_registrazioni():
    if os.path.exists(FILE_DATI):
        return pd.read_csv(FILE_DATI)
    return pd.DataFrame(columns=['Data', 'Gestore', 'Item', 'Valore'])

def aggiungi_registrazione(gestore, dati_dict):
    df_esistente = carica_registrazioni()
    nuovi_record = [{'Data': pd.Timestamp.now().strftime("%d/%m/%Y"), 'Gestore': gestore, 'Item': i, 'Valore': v} 
                    for i, v in dati_dict.items() if v > 0]
    if nuovi_record:
        pd.concat([df_esistente, pd.DataFrame(nuovi_record)], ignore_index=True).to_csv(FILE_DATI, index=False)
        return True
    return False

# --- LOGICA APP ---
st.title("📈 Dashboard Avanzamento con Analisi del GAP")
scelta = st.sidebar.selectbox("Menu", ["Dashboard Riepilogativa", "Inserimento Avanzamento", "Impostazione Budget"])

df_budget = carica_budget()
df_reg = carica_registrazioni()

# --- 1. IMPOSTAZIONE BUDGET ---
if scelta == "Impostazione Budget":
    st.header("⚙️ Definizione Budget Annuale per Gestore")
    st.info("Compila i budget annuali per ciascun gestore. Il totale verrà calcolato automaticamente.")
    df_budget_edit = st.data_editor(df_budget, use_container_width=True, hide_index=True)
    if st.button("Salva Budget"):
        df_budget_edit.to_csv(FILE_BUDGET, index=False)
        st.success("Configurazione Budget salvata!")
        st.rerun()

# --- 2. INSERIMENTO AVANZAMENTO ---
elif scelta == "Inserimento Avanzamento":
    st.header("✍️ Inserimento Avanzamento Giornaliero/Periodico")
    g_sel = st.selectbox("Seleziona Gestore", GESTORI)
    with st.form("form_v"):
        st.write(f"Stai registrando i dati per: **{g_sel}**")
        cols = st.columns(4)
        inputs = {item: cols[i%4].number_input(item, min_value=0.0) for i, item in enumerate(ITEMS)}
        if st.form_submit_button("Registra Dati"):
            if aggiungi_registrazione(g_sel, inputs): 
                st.success("Dati archiviati correttamente!")
                st.rerun()

# --- 3. DASHBOARD RIEPILOGATIVA ---
elif scelta == "Dashboard Riepilogativa":
    df_budget['Budget_Totale'] = df_budget[GESTORI].sum(axis=1)
    reale_matrix = df_reg.groupby(['Item', 'Gestore'])['Valore'].sum().unstack(fill_value=0)
    for g in GESTORI:
        if g not in reale_matrix.columns: reale_matrix[g] = 0.0
    
    st.subheader("📋 Riepilogo: Reale vs Passo Mensile (Gap)")
    st.markdown("_Il **Gap** indica la differenza tra il Reale attuale e l'obiettivo mensile (Budget/10)._")

    final_data = []
    for item in ITEMS:
        row = {"Item": item}
        # --- CALCOLO TOTALI ---
        b_tot = df_budget.loc[df_budget['Item'] == item, 'Budget_Totale'].values[0]
        r_tot = reale_matrix.loc[item].sum() if item in reale_matrix.index else 0
        p_tot = b_tot / 10 if b_tot > 0 else 0
        gap_tot = r_tot - p_tot
        
        row["Budget Annuo"] = b_tot
        row["Passo Mensile"] = round(p_tot, 1)
        row["Reale Tot."] = r_tot
        row["Gap Totale"] = round(gap_tot, 1)
        
        # --- CALCOLO PER SINGOLO GESTORE ---
        for g in GESTORI:
            b_g = df_budget.loc[df_budget['Item'] == item, g].values[0]
            r_g = reale_matrix.loc[item, g] if item in reale_matrix.index else 0
            p_g = b_g / 10 if b_g > 0 else 0
            # Aggiungiamo solo il Gap per non rendere la tabella enorme
            row[f"Reale {g}"] = r_g
            row[f"Gap {g}"] = round(r_g - p_g, 1)
            
        final_data.append(row)
    
    df_final = pd.DataFrame(final_data)
    
    # Funzione per colorare i Gap (Rosso se negativo, Verde se positivo)
    def color_gap(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    # Colonne da colorare
    cols_gap = ["Gap Totale"] + [f"Gap {g}" for g in GESTORI]

    st.dataframe(
        df_final.style.applymap(color_gap, subset=cols_gap)
        .format(precision=1), 
        use_container_width=True
    )

    st.markdown("---")

    # --- GRAFICO GAP ---
    st.subheader("📊 Analisi Visiva dello Scostamento (Gap)")
    
    # Prepariamo dati per il grafico dei Gap per gestore
    df_gap_chart = pd.melt(df_final, id_vars=['Item'], value_vars=[f"Gap {g}" for g in GESTORI],
                           var_name='Gestore', value_name='Scostamento')
    
    fig_gap = px.bar(df_gap_chart, x="Item", y="Scostamento", color="Gestore",
                     barmode="group", title="Sopra o Sotto il Passo Mensile per Gestore",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    
    # Aggiunge linea dello zero
    fig_gap.add_hline(y=0, line_dash="dash", line_color="black")
    st.plotly_chart(fig_gap, use_container_width=True)

    # --- DETTAGLIO STORICO ---
    with st.expander("Vedi registro completo inserimenti"):
        st.write(df_reg.sort_values(by="Data", ascending=False))