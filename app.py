import streamlit as st
import requests
import pandas as pd
import io
import time

st.set_page_config(page_title="Predicción de Productividad", layout="wide")

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f3fff4 0%, #e8f5e9 45%, #ffffff 100%);
        font-family: 'Segoe UI', sans-serif;
    }

    .main-title {
        text-align: center;
        font-size: 42px;
        font-weight: 800;
        color: #1b5e20;
        margin-bottom: 5px;
    }

    .subtitle {
        text-align: center;
        font-size: 19px;
        color: #4f6f52;
        margin-bottom: 35px;
    }

    .section-card {
        background-color: white;
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0px 8px 24px rgba(0,0,0,0.08);
        border-left: 7px solid #43a047;
        margin-bottom: 20px;
    }

    h3 {
        color: #2e7d32 !important;
        font-weight: 700 !important;
    }

    label {
        font-weight: 600 !important;
        color: #2f3e2f !important;
    }

    .stButton > button {
        background: linear-gradient(90deg, #2e7d32, #66bb6a);
        color: white;
        font-size: 18px;
        font-weight: 700;
        border-radius: 14px;
        padding: 12px 30px;
        border: none;
        width: 100%;
        transition: 0.3s;
    }

    .stButton > button:hover {
        background: linear-gradient(90deg, #1b5e20, #43a047);
        transform: scale(1.01);
    }

    [data-testid="stMetricValue"] {
        color: #1b5e20;
        font-size: 36px;
        font-weight: 800;
    }

    .result-box {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 30px;
        box-shadow: 0px 8px 25px rgba(0,0,0,0.10);
        border-top: 8px solid #43a047;
        margin-top: 25px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌾 Calculadora de Productividad Agrícola</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Predicción de productividad para cultivos de Banano y Plátano mediante DataRobot.</div>',
    unsafe_allow_html=True
)

try:
    DATAROBOT_API_KEY = st.secrets["DATAROBOT_API_KEY"]
    DATAROBOT_DEPLOYMENT_ID = st.secrets["DATAROBOT_DEPLOYMENT_ID"]
    DATAROBOT_HOST = st.secrets["DATAROBOT_HOST"].rstrip('/')
except KeyError as e:
    st.error(f"⚠️ Error: Falta configurar el secreto obligatorio {e} en los ajustes de Streamlit.")
    st.stop()

BATCH_PREDICTIONS_URL = f"{DATAROBOT_HOST}/api/v2/batchPredictions/"

with st.form("cultivo_form"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("📍 Datos Geográficos y Temporales")

        departamento = st.text_input("Departamento", value="Antioquia")
        municipio = st.text_input("Municipio", value="Medellín")
        anio = st.number_input("Año", min_value=2000, max_value=2030, value=2024)
        periodo = st.number_input("Periodo", min_value=1, value=2024)

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("🌱 Datos del Cultivo")

        grupo = st.text_input("Grupo cultivo", value="Frutales")

        subgrupo = st.selectbox(
            "Subgrupo",
            ["Banano", "Plátano"]
        )

        cultivo = subgrupo
        desagregacion = subgrupo

        ciclo = st.text_input("Ciclo del cultivo", value="Permanente")
        estado_fisico = st.text_input("Estado físico del cultivo", value="Fresco")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("📊 Variables Cuantitativas")

    col3, col4, col5, col6 = st.columns(4)

    with col3:
        area_sembrada = st.number_input("Área sembrada", format="%.2f", value=10.0)
    with col4:
        area_cosechada = st.number_input("Área cosechada", format="%.2f", value=9.5)
    with col5:
        produccion = st.number_input("Producción", format="%.2f", value=38.0)
    with col6:
        rendimiento = st.number_input("Rendimiento", format="%.2f", value=4.0)

    st.markdown('</div>', unsafe_allow_html=True)

    submit_button = st.form_submit_button(label="🌾 Calcular Productividad")

if submit_button:
    row_data = {
        "Departamento": [departamento],
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
        "Estado físico del cultivo": [estado_fisico]
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

        status_text.info("Subiendo datos ingresados...")
        upload_url = links["csvUpload"]
        upload_headers = {
            "Authorization": f"Token {DATAROBOT_API_KEY}",
            "Content-Type": "text/csv; encoding=utf-8"
        }

        upload_response = requests.put(upload_url, data=csv_buffer, headers=upload_headers)

        if upload_response.status_code not in [200, 201, 202, 204]:
            st.error(f"Error al subir los datos ({upload_response.status_code})")
            st.text(upload_response.text)
            st.stop()

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
                status_text.success("Procesamiento de DataRobot completado.")
                download_url = check_response["links"]["download"]
                break
            elif status in ["FAILED", "ABORTED"]:
                st.error(f"La tarea de DataRobot falló con estado: {status}")
                st.text(check_response.get("statusDetails", "Sin detalles adicionales."))
                st.stop()

            time.sleep(2)

        if download_url:
            download_response = requests.get(download_url, headers=headers)
            result_df = pd.read_csv(io.StringIO(download_response.text))

            pred_column = [col for col in result_df.columns if 'prediction' in col.lower()]

            if pred_column:
                prediction_value = result_df[pred_column[0]].iloc[0]

                st.markdown('<div class="result-box">', unsafe_allow_html=True)
                st.write("### 📈 Resultado de la Variable Objetivo")
                st.metric(
                    label="Productividad Estimada",
                    value=f"{float(prediction_value):.4f}"
                )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Se procesó con éxito, pero no se encontró la columna de predicción en el archivo devuelto.")
                st.dataframe(result_df)
        else:
            st.error("No se pudo obtener el enlace de descarga de los resultados.")

    except Exception as e:
        st.error(f"Ocurrió un error inesperado de conexión: {e}")
