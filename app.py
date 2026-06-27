import streamlit as st
import requests
import json

# Configuración de página con identidad agrícola
st.set_page_config(page_title="Predicción de Productividad", layout="wide", page_icon="🌾")

st.title("🌾 Calculadora de Productividad Agrícola")
st.markdown("Ingrese los parámetros del cultivo para obtener la **productividad** estimada.")

# --- Configuración de API desde Streamlit Secrets ---
try:
    DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
    DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
    DATAROBOT_HOST = st.secrets["DATAROBOT_HOST"].rstrip('/')
except KeyError as e:
    st.error(f"⚠️ Error: Falta configurar el secreto obligatorio {e} en los ajustes de Streamlit.")
    st.stop()

# URL exacta para predicciones en tiempo real
REALTIME_PREDICTIONS_URL = f"{DATAROBOT_HOST}/predApi/v1.0/deployments/{DATAROBOT_DEPLOYMENT_ID}/predictions"

# --- Formulario de Entrada de Datos ---
with st.form("cultivo_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Datos Geográficos y Temporales")
        cod_dane_dept = st.number_input("Código Dane departamento", min_value=0, value=105)
        departamento = st.text_input("Departamento", value="Antioquia")
        cod_dane_muni = st.number_input("Código Dane municipio", min_value=0, value=11005)
        municipio = st.text_input("Municipio", value="Medellín")
        anio = st.number_input("Año", min_value=2000, max_value=2030, value=2024)
        periodo = st.number_input("Periodo", min_value=1, value=2024)
        
    with col2:
        st.subheader("Datos del Cultivo")
        grupo = st.text_input("Grupo cultivo", value="Cereales")
        subgrupo = st.text_input("Subgrupo", value="Maíz")
        cultivo = st.text_input("Cultivo", value="Maíz Tecnificado")
        desagregacion = st.text_input("Desagregación cultivo", value="Maíz Tecnificado Solo")
        ciclo = st.text_input("Ciclo del cultivo", value="Transitorio")
        estado_fisico = st.text_input("Estado físico del cultivo", value="Grano")
        codigo_cultivo = st.number_input("Código del cultivo", min_value=0, value=2045801)
        nombre_cientifico = st.text_input("Nombre científico del cultivo", value="Zea mays")

    st.subheader("Variables Cuantitativas")
    col3, col4, col5, col6 = st.columns(4)
    with col3: area_sembrada = st.number_input("Área sembrada", format="%.2f", value=10.0)
    with col4: area_cosechada = st.number_input("Área cosechada", format="%.2f", value=9.5)
    with col5: produccion = st.number_input("Producción", format="%.2f", value=38.0)
    with col6: rendimiento = st.number_input("Rendimiento", format="%.2f", value=4.0)

    # El botón adoptará el color verde principal ('primaryColor') del archivo de configuración
    submit_button = st.form_submit_button(label="🚜 Calcular Productividad Agrícola")

# --- Lógica de Predicción en Tiempo Real ---
if submit_button:
    row_data = {
        "Código Dane departamento": cod_dane_dept,
        "Departamento": departamento,
        "Código Dane municipio": cod_dane_muni,
        "Municipio": municipio,
        "Grupo cultivo": grupo,
        "Subgrupo": subgrupo,
        "Cultivo": cultivo,
        "Desagregación cultivo": desagregacion,
        "Año": anio,
        "Periodo": periodo,
        "Área sembrada": area_sembrada,
        "Área cosechada": area_cosechada,
        "Producción": produccion,
        "Rendimiento": rendimiento,
        "Ciclo del cultivo": ciclo,
        "Estado físico del cultivo": estado_fisico,
        "Código del cultivo": codigo_cultivo,
        "Nombre científico del cultivo": nombre_cientifico
    }
    
    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    payload = [row_data]
    status_text = st.empty()
    
    try:
        status_text.info("Conectando con el modelo agrícola de DataRobot...")
        response = requests.post(REALTIME_PREDICTIONS_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            status_text.empty()
            response_data = response.json()
            predictions = response_data.get("data", [])
            
            if predictions:
                prediction_value = predictions[0].get("prediction")
                
                st.write("---")
                st.write("### 📈 Resultado de la Variable Objetivo:")
                st.metric(label="Productividad Estimada", value=f"{float(prediction_value):.4f}")
                st.success("✅ ¡Cálculo finalizado con éxito!")
            else:
                st.warning("Se procesó con éxito, pero la respuesta no contiene la estructura de datos esperada.")
                st.json(response_data)
        else:
            status_text.empty()
            st.error(f"Error en la predicción ({response.status_code})")
            st.text(response.text)
            
    except Exception as e:
        st.error(f"Ocurrió un error inesperado de conexión: {e}")
