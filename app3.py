import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os

st.set_page_config(layout="wide")

nodos = pd.read_csv("/tmp/musicbrainz_data/nodos.csv")
aristas = pd.read_csv("/tmp/musicbrainz_data/aristas.csv")

G = nx.Graph()

for _, linea in nodos.iterrows():
    tooltip =''
    for col in nodos.columns:
        if col not in ["mbid","data_extracted_at","end_date"] and pd.notnull(linea[col]):
            if col == "country":
                etiqueta = "País"
            elif col == "gender":
                etiqueta = "Sexo"
            elif col == "name":
                etiqueta = "Nombre"
            elif col == "begin_date":
                etiqueta = "Comienzo_carrera"
            else:
                etiqueta = col

            tooltip += f"{etiqueta}: {linea[col]} "
    G.add_node(linea["mbid"], label=linea["name"], title=tooltip)#, color="#1f3b4d")
 
  
for _, linea in aristas.iterrows():
    tooltip =''
    for col in aristas.columns:
        if col not in ["source", "target","recording_id"] and pd.notnull(linea[col]):
            if col == "type":
                etiqueta = "Tipo"
            elif col == "relation_begin":
                etiqueta = "Inicio_relacion"
            elif col == "target_name":
                etiqueta = "Nombre_objetivo"
            else:
                etiqueta = col
                
            tooltip += f"{etiqueta}: {linea[col]} "
    G.add_edge(linea["source"], linea["target"], label="", title=tooltip)


nodos_validos = set(nodos["mbid"])
for node_id in G.nodes:
    if node_id not in nodos_validos:
        G.nodes[node_id]["label"] = " "
        G.nodes[node_id]["color"] = "#1f3b4d" #"#97c2fc"

# Visualización con PyVis
net = Network(height="600px", width="100%", bgcolor="#222122", font_color="white")
net.from_nx(G)
net.force_atlas_2based()
a=("""
{
  "physics": {
    "stabilization": {
      "enabled": true,
      "iterations": 1000,
      "updateInterval": 25
    }
  }
}
""")
#net.set_options
#net.set_options(a)
original_cwd = os.getcwd()
os.chdir("/tmp")
net.save_graph("network.html")
os.chdir(original_cwd)


st.title("Visualización de datos, una visualización de Red - MusicBrainz")
HtmlFile = open("/tmp/network.html", "r", encoding="utf-8")
html_content = HtmlFile.read().replace(
    "<body>",
    '<body style="margin:0;background:#222222;">'
)
components.html(html_content, height=700, scrolling=True, width=1300)