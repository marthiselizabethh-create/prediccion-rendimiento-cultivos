import streamlit as st
import requests
import pandas as pd
import io
import time

# Configuración de página
st.set_page_config(page_title="Predicción de Productividad", layout="wide")

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

# URL exacta para la creación de tareas por lotes
BATCH_PREDICTIONS_URL = f"{DATAROBOT_HOST}/api/v2/batchPredictions/"

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

    submit_button = st.form_submit_button(label="Calcular Productividad")

# --- Lógica de Predicción por Lotes en Tiempo Real ---
if submit_button:
    row_data = {
        "Código Dane departamento": [cod_dane_dept],
        "Departamento": [departamento],
        "Código Dane municipio": [cod_dane_muni],
        "Municipio": [municipio],
        "Grupo cultivo": [grupo],
        "Subgrupo": [subgrupo],
        "Cultivo": [cultivo],
        "Desagregación cultivo": [desagregacion],
        "Año": [anio],
        "Periodo": [periodo],
        "Área sembrada": [area_sembrada],
        "Área cosechada": [area_cosechada],
        "Producción": [produccion],
        "Rendimiento": [rendimiento],
        "Ciclo del cultivo": [ciclo],
        "Estado físico del cultivo": [estado_fisico],
        "Código del cultivo": [codigo_cultivo],
        "Nombre científico del cultivo": [nombre_cientifico]
    }
    
    df = pd.DataFrame(row_data)
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_buffer.seek(0)
    
    headers = {
        "Authorization": f"Token {DATAROBOT_API_KEY}"
    }
    
    payload = {
        "deploymentId": DATAROBOT_DEPLOYMENT_ID,
        "passthroughColumnsSet": "all"
    }
    
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    try:
        status_text.info("Iniciando tarea de predicción en DataRobot...")
        job_response = requests.post(BATCH_PREDICTIONS_URL, json=payload, headers=headers)
        
        if job_response.status_code not in [200, 201, 202]:
            st.error(f"Error al inicializar el Job ({job_response.status_code})")
            st.text(job_response.text)
            st.stop()
            
        job_data = job_response.json()
        links = job_data["links"]
        
        # Subir nuestro dataset temporal (PUT)
        status_text.info("Subiendo datos ingresados...")
        upload_url = links["csvUpload"]
        upload_headers = {
            "Authorization": f"Token {DATAROBOT_API_KEY}",
            "Content-Type": "text/csv; encoding=utf-8"
        }
        requests.put(upload_url, data=csv_buffer, headers=upload_headers)
        
        # Monitorear el progreso en bucle
        job_url = links["self"]
        download_url = None
        
        while True:
            check_response = requests.get(job_url, headers=headers).json()
            status = check_response["status"]
            
            if status == "INITIALIZING":
                status_text.info("DataRobot está preparando la cola de ejecución...")
            elif status == "RUNNING":
                percentage = int(check_response.get("percentageCompleted", 0))
                progress_bar.progress(percentage)
                status_text.info(f"Procesando predicción... {percentage}%")
            elif status == "COMPLETED":
                progress_bar.progress(100)
                status_text.success("¡Procesamiento de DataRobot completado!")
                download_url = check_response["links"]["download"]
                break
            elif status in ["FAILED", "ABORTED"]:
                st.error(f"La tarea de DataRobot falló con estado: {status}")
                st.text(check_response.get("statusDetails", "Sin detalles adicionales."))
                st.stop()
                
            time.sleep(2)
            
        # Descargar los resultados finales (GET)
        if download_url:
            download_response = requests.get(download_url, headers=headers)
            result_df = pd.read_csv(io.StringIO(download_response.text))
            
            # Buscamos la columna dinámica generada por DataRobot
            pred_column = [col for col in result_df.columns if 'prediction' in col.lower()]
            
            if pred_column:
                prediction_value = result_df[pred_column[0]].iloc[0]
                st.write("---")
                st.write("### 📈 Resultado de la Variable Objetivo:")
                st.metric(label="Productividad Estimada", value=f"{float(prediction_value):.4f}")
            else:
                st.warning("Se procesó con éxito, pero no se encontró la columna de predicción en el archivo devuelto.")
                st.dataframe(result_df)
        else:
            st.error("No se pudo obtener el enlace de descarga de los resultados.")
            
    except Exception as e:
        st.error(f"Ocurrió un error inesperado de conexión: {e}")
