import streamlit as st
import pandas as pd
import altair as alt

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dashboard de Leituras",
    page_icon="📚",
    layout="wide"
)

# --- Carregamento de Dados (COM CACHE) ---
SHEET_ID = "1swGKETQFxDCXHyYeYSE1y3W1LGeSknO9Hsg-M20Lgbk"
SHEET_GID = "2090895525"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

@st.cache_data
def carregar_dados():
    """
    Função para carregar e limpar os dados do Google Sheets.
    Os dados são cacheados para melhor performance.
    """
    try:
        df = pd.read_csv(URL, on_bad_lines='skip')
        
        # --- LIMPEZA E PREPARAÇÃO DOS DADOS ---
        
        # 1. Converter data de término (Formato DD/MM/YYYY)
        df['Término da Leitura'] = pd.to_datetime(df['Término da Leitura'], format='%d/%m/%Y', errors='coerce')
        
        # 2. Converter Nota (Coluna 'Tipo') para número (float)
        if 'Tipo' in df.columns:
            df['Nota'] = df['Tipo'].astype(str).str.replace(',', '.').str.extract(r'(\d+\.?\d*)')
            df['Nota'] = pd.to_numeric(df['Nota'], errors='coerce')
        else:
            df['Nota'] = pd.Series(dtype='float')

        # 3. Converter Custos e Valores para número (Lidando com "R$", vírgula e espaços)
        custo_str = df['Custo'].astype(str).str.replace('R$', '', regex=False).str.strip().str.replace(',', '.')
        valor_str = df['Valor'].astype(str).str.replace('R$', '', regex=False).str.strip().str.replace(',', '.')
        
        df['Custo'] = pd.to_numeric(custo_str, errors='coerce').fillna(0)
        df['Valor'] = pd.to_numeric(valor_str, errors='coerce').fillna(0)
        
        # 4. Criar novas colunas úteis
        df['Economia'] = df['Valor'] - df['Custo']
        df['Ano Leitura'] = df['Término da Leitura'].dt.year
        
        # 5. Preencher valores nulos (NaN) em colunas de texto
        cols_categoricas = ['Gênero', 'Formato', 'Nacionalidade', 'Raça/Etnia', 'Obtido em', 'Idioma', 'Editora']
        for col in cols_categoricas:
            if col in df.columns:
                df[col] = df[col].fillna('Não Definido')

        # 6. Remover linhas onde a data de término é nula (livros não lidos)
        df_lidos = df[df['Término da Leitura'].notna()].copy()
        
        return df_lidos
    
    except Exception as e:
        st.error(f"Erro ao carregar ou processar dados: {e}")
        print(f"Erro detalhado: {e}")
        return pd.DataFrame()

# Carrega os dados
df = carregar_dados()

# --- Início do Layout do Streamlit ---

if df.empty:
    st.warning("Não foi possível carregar os dados ou não há livros lidos registrados.")
    st.info("Verifique se a planilha do Google Sheets está compartilhada com 'Qualquer pessoa com o link' pode ser 'Leitor'.")
else:
    # --- TÍTULO DO DASHBOARD ---
    st.title("Dashboard Pessoal de Leituras")

    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("Filtros")

    # Filtro de Ano
    anos_disponiveis = df['Ano Leitura'].dropna().unique().astype(int)
    anos_disponiveis.sort()
    
    min_ano = min(anos_disponiveis)
    max_ano = max(anos_disponiveis)

    if min_ano == max_ano:
        st.sidebar.info(f"Ano de leitura disponível: {min_ano}")
        ano_selecionado = (min_ano, min_ano) 
    else:
        ano_selecionado = st.sidebar.slider(
            "Selecione o Ano de Leitura",
            min_value=min_ano,
            max_value=max_ano,
            value=(min_ano, max_ano) 
        )

    # Filtro de Nota
    nota_selecionada = st.sidebar.slider(
        "Filtrar por Nota",
        min_value=0.0,
        max_value=5.0,
        value=(0.0, 5.0), 
        step=0.5
    )

    # Filtros Categóricos
    formatos_selecionados = st.sidebar.multiselect(
        "Formato",
        options=df['Formato'].unique(),
        default=df['Formato'].unique()
    )

    nacionalidade_selecionada = st.sidebar.multiselect(
        "Nacionalidade do Autor",
        options=df['Nacionalidade'].unique(),
        default=df['Nacionalidade'].unique()
    )

    idioma_selecionado = st.sidebar.multiselect(
        "Idioma",
        options=df['Idioma'].unique(),
        default=df['Idioma'].unique()
    )
    
    aquisicao_selecionada = st.sidebar.multiselect(
        "Forma de Aquisição",
        options=df['Obtido em'].unique(),
        default=df['Obtido em'].unique()
    )

    # --- APLICAÇÃO DOS FILTROS ---
    df_filtrado = df[
        (df['Ano Leitura'] >= ano_selecionado[0]) &
        (df['Ano Leitura'] <= ano_selecionado[1]) &
        (df['Nota'] >= nota_selecionada[0]) &
        (df['Nota'] <= nota_selecionada[1]) &
        (df['Formato'].isin(formatos_selecionados)) &
        (df['Nacionalidade'].isin(nacionalidade_selecionada)) &
        (df['Idioma'].isin(idioma_selecionado)) &
        (df['Obtido em'].isin(aquisicao_selecionada))
    ]

    # --- LAYOUT PRINCIPAL (MÉTRICAS E GRÁFICOS) ---

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        # Seção de Métricas Chave (KPIs)
        if ano_selecionado[0] == ano_selecionado[1]:
            st.header(f"Métricas ({ano_selecionado[0]})")
        else:
            st.header(f"Métricas ({ano_selecionado[0]} - {ano_selecionado[1]})")
            
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Livros Lidos", f"{df_filtrado.shape[0]} livros")
        col2.metric("Total Gasto", f"R$ {df_filtrado['Custo'].sum():,.2f}")
        col3.metric("Total Economizado", f"R$ {df_filtrado['Economia'].sum():,.2f}")
        col4.metric("Nota Média", f"{df_filtrado['Nota'].mean():.1f} Estrelas")

        st.markdown("---") 

        # Seção de Análise Temporal
        st.header("Análise Temporal")
        
        leituras_por_mes = df_filtrado.groupby(df_filtrado['Término da Leitura'].dt.to_period('M')).size()
        leituras_por_mes.index = leituras_por_mes.index.to_timestamp()
        leituras_por_mes = leituras_por_mes.reset_index()
        leituras_por_mes.columns = ['Mês', 'Quantidade de Livros']

        st.subheader("Livros Lidos por Mês")
        st.line_chart(leituras_por_mes.set_index('Mês'), use_container_width=True)
        
        st.markdown("---")

        # Seção de Aquisição e Custos
        st.header("Análise de Aquisição e Custos")
        col_aq, col_custo = st.columns(2)

        with col_aq:
            st.subheader("Formas de Aquisição")
            chart_aq = alt.Chart(df_filtrado['Obtido em'].value_counts().reset_index()).mark_bar().encode(
                x=alt.X('count:Q', title='Quantidade de Livros'),
                y=alt.Y('Obtido em:N', sort='-x', title='Fonte'),
                tooltip=['Obtido em', 'count']
            ).interactive()
            st.altair_chart(chart_aq, use_container_width=True)

        with col_custo:
            st.subheader("Gasto vs. Economia por Aquisição")
            df_custos = df_filtrado.groupby('Obtido em')[['Custo', 'Economia']].sum().reset_index()
            df_custos_melted = df_custos.melt('Obtido em', var_name='Tipo de Valor', value_name='Valor (R$)')
            
            chart_custos = alt.Chart(df_custos_melted).mark_bar().encode(
                x=alt.X('Obtido em:N', axis=None), 
                y=alt.Y('Valor (R$):Q'),
                color=alt.Color('Tipo de Valor:N', title='Tipo'),
                column=alt.Column('Obtido em:N', header=alt.Header(titleOrient="bottom", labelOrient="bottom"), title='Fonte'),
                tooltip=['Obtido em', 'Tipo de Valor', 'Valor (R$)']
            ).interactive()
            st.altair_chart(chart_custos, use_container_width=True)

        st.markdown("---")

        # Seção de Análise de Diversidade
        st.header("Análise de Diversidade dos Autores")
        col_genero, col_etnia = st.columns(2) 

        with col_genero:
            st.subheader("Identidade de Gênero")
            chart_genero = alt.Chart(df_filtrado['Gênero'].value_counts().reset_index()).mark_bar().encode(
                x=alt.X('count:Q', title='Quantidade de Livros'),
                y=alt.Y('Gênero:N', sort='-x'),
                tooltip=['Gênero', 'count']
            ).interactive()
            st.altair_chart(chart_genero, use_container_width=True)

        with col_etnia:
            st.subheader("Raça/Etnia")
            chart_etnia = alt.Chart(df_filtrado['Raça/Etnia'].value_counts().reset_index()).mark_bar().encode(
                x=alt.X('count:Q', title='Quantidade de Livros'),
                y=alt.Y('Raça/Etnia:N', sort='-x'),
                tooltip=['Raça/Etnia', 'count']
            ).interactive()
            st.altair_chart(chart_etnia, use_container_width=True)
            
        st.markdown("---")

        # Seção de Avaliações e Categorias
        st.header("Análise de Avaliações e Formatos")
        col_nota, col_formato = st.columns(2)

        with col_nota:
            st.subheader("Distribuição das Notas")
            
            # --- CORREÇÃO AQUI ---
            # Trocado 'df_trado' por 'df_filtrado'
            chart_nota = alt.Chart(df_filtrado['Nota'].value_counts().reset_index().sort_values(by='Nota', ascending=False)).mark_bar().encode(
                x=alt.X('Nota:N', title='Nota', sort=None), 
                y=alt.Y('count:Q', title='Quantidade de Livros'),
                tooltip=['Nota', 'count']
            ).interactive()
            st.altair_chart(chart_nota, use_container_width=True)

        with col_formato:
            st.subheader("Formatos de Leitura")
            chart_formato = alt.Chart(df_filtrado['Formato'].value_counts().reset_index()).mark_bar().encode(
                x=alt.X('count:Q', title='Quantidade de Livros'),
                y=alt.Y('Formato:N', sort='-x'),
                tooltip=['Formato', 'count']
            ).interactive()
            st.altair_chart(chart_formato, use_container_width=True)

        # Seção de Dados Brutos
        st.header("Biblioteca Detalhada (Filtrada)")
        st.dataframe(df_filtrado, use_container_width=True)