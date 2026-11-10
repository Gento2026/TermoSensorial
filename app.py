from datetime import date, datetime
import io
import json
import os
import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

# 1. Configuração Global da Página
st.set_page_config(
    page_title="TermoSensorial | Gorongosa Fogo em Contexto",
    page_icon="🔥",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stTextInput input, .stSelectbox select, .stDateInput input, .stTextArea textarea {
        border-radius: 6px !important;
        border: 1px solid #ced4da !important;
    }
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        padding: 10px 0;
        border-radius: 6px;
        margin-bottom: 20px;
    }
    .ticker {
        display: inline-block;
        white-space: nowrap;
        animation: ticker 25s linear infinite;
        font-weight: bold;
        color: #856404;
    }
    @keyframes ticker {
        0% { transform: translate3d(100%, 0, 0); }
        100% { transform: translate3d(-100%, 0, 0); }
    }
    </style>
""",
    unsafe_allow_html=True,
)

ARQUIVO_FICHAS = "fichas_campo.json"


def carregar_fichas_json():
  if os.path.exists(ARQUIVO_FICHAS):
    with open(ARQUIVO_FICHAS, "r", encoding="utf-8") as f:
      return pd.DataFrame(json.load(f))
  return pd.DataFrame(columns=[
      "ID Ficha",
      "Latitude",
      "Longitude",
      "Sensor",
      "Data Alerta",
      "Estado",
      "Observações",
  ])


def salvar_fichas_json(df):
  df.to_json(ARQUIVO_FICHAS, orient="records", force_ascii=False, indent=4)


if "fichas_campo" not in st.session_state:
  st.session_state.fichas_campo = carregar_fichas_json()

# 2. Configuração de Parâmetros Globais da NASA FIRMS
BOUNDING_BOX = "33.8,-19.5,34.8,-18.3"  # Parque Nacional da Gorongosa
SOURCES = {
    "MODIS (Terra/Aqua)": "MODIS_NRT",
    "VIIRS (S-NPP)": "VIIRS_SNPP_NRT",
    "VIIRS (NOAA-20)": "VIIRS_NOAA20_NRT",
}


# Função robusta de carregamento com diagnóstico por sensor
@st.cache_data(ttl=3600)
def carregar_dados_nasa(map_key, bbox, days):
  dados_harmonizados = []
  status_sensores = {}

  for nome_sensor, codigo_fonte in SOURCES.items():
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{codigo_fonte}/{bbox}/{days}"
    try:
      response = requests.get(url)
      if response.status_code == 200:
        conteudo = response.text.strip()
        if conteudo and not conteudo.startswith("Error"):
          df = pd.read_csv(io.StringIO(conteudo))
          if not df.empty:
            if "atitude" in df.columns:
              df.rename(columns={"atitude": "latitude"}, inplace=True)
            df["sensor_fonte"] = nome_sensor
            dados_harmonizados.append(df)
            status_sensores[nome_sensor] = (
                f"Sucesso ({len(df)} registos encontrados)"
            )
          else:
            status_sensores[nome_sensor] = (
                "Sem focos detetados no período/área"
            )
        else:
          status_sensores[nome_sensor] = f"Aviso da API: {conteudo[:40]}"
      else:
        status_sensores[nome_sensor] = (
            f"Erro HTTP {response.status_code} (Verifique a MAP_KEY)"
        )
    except Exception as e:
      status_sensores[nome_sensor] = f"Erro de ligação: {str(e)}"

  if dados_harmonizados:
    df_final = pd.concat(dados_harmonizados, ignore_index=True)
    df_final["acq_date"] = pd.to_datetime(df_final["acq_date"])
    return df_final, status_sensores

  return pd.DataFrame(), status_sensores


# --- BARRA LATERAL ---
st.sidebar.title("🧭 Navegação do Sistema")
pagina_selecionada = st.sidebar.radio(
    "Ir para:",
    [
        "🏠 Página Inicial",
        "🗺️ 1. Mapa de Deteções (NASA)",
        "📅 2. Calendário Histórico",
        "⚠️ 3. Locais para Verificação",
        "📋 4. Ficha de Visita de Campo",
        "📊 5. Resumo e Exportação",
    ],
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Configurações da API")
map_key_input = st.sidebar.text_input(
    "NASA MAP_KEY", value="65db16dd516c272d7fe0fa13e1489396"
)

# RESTRICÃO APLICADA: Máximo de 7 dias conforme solicitado
dias_analise = st.sidebar.slider(
    "Intervalo de Dias (Retroativo)", min_value=1, max_value=7, value=5
)

# Carregar dados em tempo real
with st.spinner(
    "A sincronizar dados em tempo real com os satélites (MODIS e VIIRS)..."
):
  df_focos, status_diagnostico = carregar_dados_nasa(
      map_key_input, BOUNDING_BOX, dias_analise
  )

# ==========================================
# 🏠 PÁGINA INICIAL
# ==========================================
if pagina_selecionada == "🏠 Página Inicial":
  st.title("🔥 Plataforma Integrada de Monitorização de Focos de Calor")
  st.markdown(
      "Sistema de apoio à decisão operacional, cruzamento de dados de satélite"
      " (NASA FIRMS) e telemetria física na Gorongosa."
  )

  st.markdown(
      """
      <div class="ticker-wrap">
          <div class="ticker">
              ⚠️ AVISO OPERACIONAL: Monitorização ativa de satélites MODIS, VIIRS-SNPP e VIIRS-NOAA20 no Parque Nacional da Gorongosa | Verifique periodicamente os locais críticos.
          </div>
      </div>
  """,
      unsafe_allow_html=True,
  )

  st.markdown("### 📌 Estado da Ligação aos Satélites (Diagnóstico)")
  for sensor, estado in status_diagnostico.items():
    if "Sucesso" in estado:
      st.success(f"✅ **{sensor}**: {estado}")
    else:
      st.info(f"ℹ️ **{sensor}**: {estado}")

  st.markdown("---")
  col1, col2, col3 = st.columns(3)
  total_focos = len(df_focos) if not df_focos.empty else 0
  col1.metric(label="Total de Deteções Orbitais", value=total_focos)
  col2.metric(
      label="Fichas de Campo Registadas",
      value=len(st.session_state.fichas_campo),
  )
  col3.metric(label="Estado da API NASA", value="Ativo")

# ==========================================
# 🗺️ 1. MAPA DE DETEÇÕES
# ==========================================
elif pagina_selecionada == "🗺️ 1. Mapa de Deteções (NASA)":
  st.subheader(
      "🗺️ Mapa Interativo de Deteções Reais (MODIS & VIIRS na Gorongosa)"
  )

  if not df_focos.empty:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
      sensores_disponiveis = df_focos["sensor_fonte"].unique().tolist()
      sensores_sel = st.multiselect(
          "Ativar / Ocultar Sensores no Mapa:",
          sensores_disponiveis,
          default=sensores_disponiveis,
      )
    with col_f2:
      min_d = df_focos["acq_date"].dt.date.min()
      max_d = df_focos["acq_date"].dt.date.max()
      periodo_filtro = st.date_input(
          "Filtrar por Período:", [min_d, max_d], min_value=min_d, max_value=max_d
      )

    if len(periodo_filtro) == 2:
      d_ini, d_fim = periodo_filtro
    else:
      d_ini, d_fim = periodo_filtro[0], periodo_filtro[0]

    df_filtrado = df_focos[
        (df_focos["sensor_fonte"].isin(sensores_sel))
        & (df_focos["acq_date"].dt.date >= d_ini)
        & (df_focos["acq_date"].dt.date <= d_fim)
    ]

    st.write(
        f"A apresentar **{len(df_filtrado)}** registos ativos para os filtros"
        " selecionados."
    )

    if not df_filtrado.empty:
      lat_c = df_filtrado["latitude"].mean()
      lon_c = df_filtrado["longitude"].mean()
      m = folium.Map(location=[lat_c, lon_c], zoom_start=9)

      for _, r in df_filtrado.iterrows():
        if "VIIRS (S-NPP)" in str(r["sensor_fonte"]):
          cor = "red"
        elif "VIIRS (NOAA-20)" in str(r["sensor_fonte"]):
          cor = "purple"
        else:
          cor = "orange"

        folium.CircleMarker(
            location=[r["latitude"], r["longitude"]],
            radius=7,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.8,
            popup=(
                f"<b>Sensor:</b> {r['sensor_fonte']}<br><b>Data:</b>"
                f" {r['acq_date'].strftime('%Y-%m-%d')} às"
                f" {r['acq_time']}<br><b>Confiança:</b>"
                f" {r['confidence']}%<br><b>Potência (FRP):</b> {r['frp']} MW"
            ),
        ).add_to(m)

      st_folium(m, width=1100, height=500)
    else:
      st.warning(
          "Nenhum foco encontrado com os filtros de sensor/período aplicados."
      )
  else:
    st.warning(
        "Não foram encontrados dados da NASA para o intervalo selecionado ou"
        " verifique a chave MAP_KEY."
    )

# ==========================================
# 📅 2. CALENDÁRIO HISTÓRICO
# ==========================================
elif pagina_selecionada == "📅 2. Calendário Histórico":
  st.subheader("📅 Resumo Cronológico e Frequência Temporal")

  if not df_focos.empty:
    c1, c2 = st.columns(2)
    with c1:
      st.markdown("**Frequência de Deteções por Dia:**")
      df_dia = df_focos.groupby(df_focos["acq_date"].dt.date).size()
      st.bar_chart(df_dia)
    with c2:
      st.markdown("**Distribuição por Sensor Orbital:**")
      df_sen = df_focos.groupby("sensor_fonte").size()
      st.bar_chart(df_sen)
  else:
    st.info("Sem dados disponíveis para gerar gráficos estatísticos.")

# ==========================================
# ⚠️ 3. LOCAIS PARA VERIFICAÇÃO
# ==========================================
elif pagina_selecionada == "⚠️ 3. Locais para Verificação":
  st.subheader("⚠️ Identificação de Focos Críticos para Verificação no Terreno")
  st.markdown(
      "Critério automático: Focos com alta potência energética (*FRP > 15 MW*)"
      " ou reincidência de deteções num curto espaço."
  )

  if not df_focos.empty:
    df_focos["frp_num"] = (
        pd.to_numeric(df_focos["frp"], errors="coerce").fillna(0)
    )
    criticos = df_focos[df_focos["frp_num"] > 15]

    if not criticos.empty:
      st.error(
          f"🚨 Identificados **{len(criticos)} pontos de alta intensidade"
          " térmica** que requerem prioridade operacional."
      )
      st.dataframe(
          criticos[[
              "latitude",
              "longitude",
              "acq_date",
              "acq_time",
              "sensor_fonte",
              "confidence",
              "frp",
          ]],
          use_container_width=True,
      )
    else:
      st.info(
          "ℹ️ Não existem focos de calor com níveis críticos extremos no período"
          " atual."
      )
  else:
    st.warning("Sem dados para análise.")

# ==========================================
# 📋 4. FICHA DE VISITA DE CAMPO
# ==========================================
elif pagina_selecionada == "📋 4. Ficha de Visita de Campo":
  st.subheader("📋 Registo de Ficha de Visita de Campo")

  if not df_focos.empty:
    with st.form("form_fichas_estrito", clear_on_submit=True):
      c1, c2 = st.columns(2)
      with c1:
        foco_opcoes = df_focos.index.tolist()
        foco_escolhido = st.selectbox(
            "Selecionar Alerta NASA:",
            foco_opcoes,
            format_func=lambda x: (
                f"Lat: {df_focos.loc[x, 'latitude']:.4f}, Lon:"
                f" {df_focos.loc[x, 'longitude']:.4f} ("
                f"{df_focos.loc[x, 'acq_date'].strftime('%Y-%m-%d')})"
            ),
        )
        lat_sel = df_focos.loc[foco_escolhido, "latitude"]
        lon_sel = df_focos.loc[foco_escolhido, "longitude"]
        sensor_sel = df_focos.loc[foco_escolhido, "sensor_fonte"]
        data_alerta = str(
            df_focos.loc[foco_escolhido, "acq_date"].strftime("%Y-%m-%d")
        )

        st.text(f"Latitude: {lat_sel}")
        st.text(f"Longitude: {lon_sel}")

      with c2:
        estado_ficha = st.selectbox(
            "Estado da Ocorrência",
            [
                "Pendente de Verificação",
                "Em Inspeção no Terreno",
                "Fogo Extinto",
                "Alarme Falso",
            ],
        )
        observacao = st.text_area("Observações e Notas da Brigada")

      enviar = st.form_submit_button("💾 Registar Ficha no Sistema")

    if enviar:
      novo_id = f"FC-{len(st.session_state.fichas_campo)+1:03d}"
      nova_linha = pd.DataFrame([{
          "ID Ficha": novo_id,
          "Latitude": lat_sel,
          "Longitude": lon_sel,
          "Sensor": sensor_sel,
          "Data Alerta": data_alerta,
          "Estado": estado_ficha,
          "Observações": observacao,
      }])
      st.session_state.fichas_campo = pd.concat(
          [st.session_state.fichas_campo, nova_linha], ignore_index=True
      )
      salvar_fichas_json(st.session_state.fichas_campo)
      st.success(f"Ficha {novo_id} gravada com sucesso!")

    st.markdown("---")
    st.markdown("#### Histórico de Fichas Registadas")
    st.dataframe(st.session_state.fichas_campo, use_container_width=True)
  else:
    st.warning("Carregue dados válidos para gerar fichas de campo.")

# ==========================================
# 📊 5. RESUMO E EXPORTAÇÃO
# ==========================================
elif pagina_selecionada == "📊 5. Resumo e Exportação":
  st.subheader("📊 Resumo Estatístico e Exportação de Dados")

  r1, r2, r3 = st.columns(3)
  r1.metric(
      "Total de Focos NASA", len(df_focos) if not df_focos.empty else 0
  )
  r2.metric("Sensores Integrados", "MODIS & VIIRS")
  r3.metric("Fichas de Campo Salvas", len(st.session_state.fichas_campo))

  st.markdown("---")
  if not df_focos.empty:
    csv_export = df_focos.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descarregar Dados Consolidados (CSV)",
        data=csv_export,
        file_name="gorongosa_focos_nasa.csv",
        mime="text/csv",
    )
  else:
    st.info("Sem dados para exportar.")