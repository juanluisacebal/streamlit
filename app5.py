import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
import os

st.set_page_config(page_title="Netflix Visualization", layout="wide")

# Cargar datos
@st.cache_data
def cargar_datos():
    datos = pd.read_csv("/home/juanlu/streamlit/netflix_titles.csv")
    datos['date_added'] = pd.to_datetime(datos['date_added'], errors='coerce')
    datos['year_added'] = datos['date_added'].dt.year
    datos['release_year'] = pd.to_numeric(datos['release_year'], errors='coerce')
    return datos.dropna(subset=["release_year"])

datos = cargar_datos()

# Filtros en la barra lateral
st.sidebar.header("Filtros")
excluir_nulos = st.sidebar.checkbox("Excluir registros con nulos", value=False)
tipo_seleccionado = st.sidebar.multiselect("Tipo", datos['type'].unique(), default=list(datos['type'].unique()))
generos_seleccionados = st.sidebar.multiselect("Género", datos['listed_in'].explode().str.split(', ').explode().unique(), default=[])
rango_anio = st.sidebar.slider("Año de lanzamiento", int(datos['release_year'].min()), int(datos['release_year'].max()), (2010, 2020))

if excluir_nulos:
    datos = datos.dropna(subset=['country', 'duration'])

# Filtrar conjunto de datos
datos_filtrados = datos[datos['type'].isin(tipo_seleccionado)]
datos_filtrados = datos_filtrados[(datos_filtrados['release_year'] >= rango_anio[0]) & (datos_filtrados['release_year'] <= rango_anio[1])]
if generos_seleccionados:
    datos_filtrados = datos_filtrados[datos_filtrados['listed_in'].apply(lambda x: any(g in x for g in generos_seleccionados))]


st.title("📺 Análisis Visual de Contenido en Netflix")


# Estadísticas descriptivas mejoradas en la barra lateral con dos columnas
st.sidebar.markdown("### 📊 Estadísticas Descriptivas")
col1, col2 = st.sidebar.columns(2)

# Procesar duración numérica para métricas
duraciones_numericas = datos_filtrados['duration'].dropna().astype(str).str.extract(r'(\d+)')[0].astype(float)

with col1:
    st.metric("Total", datos_filtrados.shape[0])
    st.metric("Películas", datos_filtrados[datos_filtrados['type'] == 'Movie'].shape[0])
    st.metric("Países únicos", datos_filtrados['country'].dropna().str.split(', ').explode().nunique())
    st.metric("Duración promedio", f"{duraciones_numericas.mean():.1f}" if not duraciones_numericas.empty else "N/A")
    st.metric("Nulos país", datos_filtrados['country'].isna().sum())

with col2:
    st.metric("Series", datos_filtrados[datos_filtrados['type'] == 'TV Show'].shape[0])
    st.metric("Años únicos", datos_filtrados['release_year'].nunique())
    st.metric("Géneros únicos", datos_filtrados['listed_in'].str.split(', ').explode().nunique())
    st.metric("Duración mediana", f"{duraciones_numericas.median():.1f}" if not duraciones_numericas.empty else "N/A")
    st.metric("Nulos duración", datos_filtrados['duration'].isna().sum())

# Mostrar resumen de datos
st.markdown("### Evolución de títulos por año")
evolucion = datos_filtrados.groupby(['release_year', 'type']).size().reset_index(name='count')
grafico_evolucion = px.area(evolucion, x='release_year', y='count', color='type', markers=True,
                        labels={'release_year': 'Año', 'count': 'Cantidad de títulos', 'type': 'Tipo'})
st.plotly_chart(grafico_evolucion, use_container_width=True)

# Diferencia entre año añadido y año de lanzamiento
st.markdown("### Diferencia entre año de añadido y año de lanzamiento")
datos_filtrados = datos_filtrados.dropna(subset=["date_added", "release_year"])
datos_filtrados['year_added'] = datos_filtrados['date_added'].dt.year
datos_filtrados['diff_years'] = datos_filtrados['year_added'] - datos_filtrados['release_year']

# Agrupar por año añadido
agregados_vs_edad = datos_filtrados.groupby(['year_added', 'diff_years']).size().reset_index(name='count')
grafico_diff = px.bar(agregados_vs_edad, x='year_added', y='count', color='diff_years',
                  labels={'year_added': 'Año añadido', 'count': 'Número de títulos', 'diff_years': 'Diferencia de años'},
                  title="Distribución de títulos por diferencia entre año añadido y año de lanzamiento")
st.plotly_chart(grafico_diff, use_container_width=True)

# Distribución por país dividida por tipo
st.markdown("### Distribución por país")
paises_tipo = datos_filtrados.dropna(subset=['country']).copy()
paises_tipo = paises_tipo.assign(paises=paises_tipo['country'].str.split(', ')).explode('paises')
paises_tipo = paises_tipo.groupby(['paises', 'type']).size().reset_index(name='count')
top_paises = paises_tipo.groupby('paises')['count'].sum().nlargest(10).index
paises_tipo = paises_tipo[paises_tipo['paises'].isin(top_paises)]

grafico_pais = px.bar(paises_tipo, x='paises', y='count', color='type',
                      labels={'paises': 'País', 'count': 'Número de títulos', 'type': 'Tipo'},
                      title="Distribución por país dividida por tipo")
st.plotly_chart(grafico_pais, use_container_width=True)


# Top 10 Directores
st.markdown("### Top 10 Directores")
directores_top = datos_filtrados['director'].dropna().str.split(', ').explode().value_counts().nlargest(10)
grafico_directores = px.bar(directores_top, x=directores_top.index, y=directores_top.values,
                       labels={'x': 'Director', 'y': 'Número de títulos'},
                       title="Top 10 Directores")
st.plotly_chart(grafico_directores, use_container_width=True)

# Top 20 Actores y Actrices
st.markdown("### Top 20 Actores y Actrices")
elenco_top = datos_filtrados['cast'].dropna().str.split(', ').explode().value_counts().nlargest(20)
grafico_cast = px.bar(elenco_top, x=elenco_top.index, y=elenco_top.values,
                  labels={'x': 'Actor/Actriz', 'y': 'Número de títulos'},
                  title="Top 20 Reparto (Cast)")
st.plotly_chart(grafico_cast, use_container_width=True)

# Frecuencia de géneros
st.markdown("### Géneros más comunes")
todos_generos = datos_filtrados['listed_in'].str.split(', ').explode()
generos_top = todos_generos.value_counts().nlargest(10)
grafico_generos = px.pie(values=generos_top.values, names=generos_top.index, title="Top 10 Géneros")
st.plotly_chart(grafico_generos, use_container_width=True)


# Precio de la acción de Netflix
st.markdown("### 📈 Evolución del Precio de la Acción de Netflix")
def cargar_datos_accion(fecha_inicio, fecha_fin):
    nombre_archivo = f"netflix_stock_{fecha_inicio.year}_{fecha_fin.year}.csv"
    ruta_archivo = os.path.join("/home/juanlu/streamlit", nombre_archivo)
    if not os.path.exists(ruta_archivo):
        datos = yf.download("NFLX", start=fecha_inicio.strftime("%Y-%m-%d"), end=fecha_fin.strftime("%Y-%m-%d"))
        datos.reset_index().to_csv(ruta_archivo, index=False)
    else:
        try:
            return pd.read_csv(ruta_archivo, parse_dates=['Date'])
        except (ValueError, pd.errors.ParserError):
            datos = yf.download("NFLX", start=fecha_inicio.strftime("%Y-%m-%d"), end=fecha_fin.strftime("%Y-%m-%d"))
            datos.reset_index().to_csv(ruta_archivo, index=False)
    return pd.read_csv(ruta_archivo, parse_dates=['Date'])

fecha_inicio = pd.Timestamp(rango_anio[0], 1, 1)
fecha_fin = pd.Timestamp(rango_anio[1], 12, 31)
datos_accion = cargar_datos_accion(fecha_inicio, fecha_fin)
grafico_accion = px.line(datos_accion, x='Date', y='Close',
                    labels={'Date': 'Fecha', 'Close': 'Precio de Cierre'},
                    title="Precio histórico de la acción de Netflix (NFLX)")
st.plotly_chart(grafico_accion, use_container_width=True)