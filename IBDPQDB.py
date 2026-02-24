import streamlit as st
import sqlite3
import pandas as pd

# 1. Configuración de alto rendimiento
st.set_page_config(page_title="IBDPQB", layout="wide")

# 2. CSS y MathJax (Carga optimizada)
st.markdown("""
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .question-card { 
        border: 1px solid #eee; padding: 20px; border-radius: 10px; 
        background: white; margin-bottom: 25px; color: black;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; }
    .syllabus-old { background-color: #ff4b4b; color: white; }
    .syllabus-2025 { background-color: #28a745; color: white; }
    .syllabus-math { background-color: #6c757d; color: white; }
    .info-label { color: #666; font-size: 13px; margin-right: 15px; }
    
    @media print {
        .no-print, header, [data-testid="stSidebar"], .stTabs, .stButton, .stExpander { display: none !important; }
        .question-card { border: none !important; margin-bottom: 30px; page-break-inside: avoid; }
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Funciones de Datos con Cache (Optimizado)
@st.cache_data
def run_query(query, params=()):
    try:
        with sqlite3.connect('database.db', check_same_thread=False) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception as e:
        st.error(f"Error en BD: {e}")
        return pd.DataFrame()

@st.cache_data
def get_unique_values(column):
    df = run_query(f"SELECT DISTINCT {column} FROM questionsC")
    return df[column].tolist() if not df.empty else []

def format_topic(topic_text):
    if not topic_text: return "N/A"
    return topic_text.split("–")[0].strip() if "–" in topic_text else topic_text[:70]

def render_question(row):
    is_math = "math" in str(row['subject']).lower()
    is_old = str(row['version']).upper() in ['V4', 'V5']
    
    # Lógica de badges corregida para mostrarse siempre correctamente
    if is_math:
        badge = '<span class="badge syllabus-math">MATHEMATICS</span>'
    else:
        s_class = "syllabus-old" if is_old else "syllabus-2025"
        badge = f'<span class="badge {s_class}">{"OLD" if is_old else "2025"} SYLLABUS</span>'

    st.markdown(f"""
    <div class="question-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h4 style="margin:0; color:black;">{row['subject']} - Q{row['question_num']}</h4>
            {badge}
        </div>
        <div style="margin: 8px 0; border-bottom: 1px solid #eee; padding-bottom: 8px;">
            <span class="info-label"><b>Session:</b> {row['session']}</span>
            <span class="info-label"><b>Paper:</b> {row['paper']}</span>
            <span class="info-label"><b>Level:</b> {row['level']}</span>
            <span class="info-label"><b>Code:</b> {row['unique_code']}</span>
            <span class="info-label"><b>Topic:</b> {format_topic(row['topic'])}</span>
        </div>
        <div class="math-content" style="color:black; line-height:1.5;">
            {row['content_html']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("👁️ Ver Markscheme"):
        st.markdown(f"<div style='color:black;'>{row['markscheme_html']}</div>", unsafe_allow_html=True)

# --- APP ---
tab1, tab2 = st.tabs(["🔍 Buscador General", "📝 Generador de Exámenes"])

# --- TAB 1: BUSCADOR ---
with tab1:
    st.title("IBDPQB Search")
    subjects = get_unique_values("subject")
    
    c1, c2 = st.columns([1,3])
    f_sub = c1.selectbox("Asignatura", ["Todas"] + subjects, key="search_sub")
    search_term = c2.text_input("Buscar por texto, código o markscheme...", key="search_text")

    with st.expander("🔍 Filtros Avanzados"):
        fa1, fa2, fa3, fa4 = st.columns(4)
        f_sess = fa1.text_input("Session (e.g. M23)")
        f_pap = fa2.text_input("Paper (1, 2, 3)")
        f_lev = fa3.text_input("Level (HL, SL...)")
        f_top = fa4.text_input("Topic Keyword")

    if search_term or f_sub != "Todas" or f_sess or f_pap or f_lev or f_top:
        q = "SELECT * FROM questionsC WHERE 1=1"
        p = []
        if f_sub != "Todas": q += " AND subject = ?"; p.append(f_sub)
        if search_term: q += " AND (content_html LIKE ? OR unique_code LIKE ? OR markscheme_html LIKE ?)"; p.extend([f"%{search_term}%"]*3)
        if f_sess: q += " AND session LIKE ?"; p.append(f"%{f_sess}%")
        if f_pap: q += " AND paper = ?"; p.append(f_pap)
        if f_lev: q += " AND level = ?"; p.append(f_lev)
        if f_top: q += " AND topic LIKE ?"; p.append(f"%{f_top}%")
        
        results = run_query(q, tuple(p))
        st.write(f"Resultados encontrados: {len(results)}")
        for _, r in results.iterrows(): render_question(r)

# --- TAB 2: GENERADOR ---
with tab2:
    st.title("Exam Generator")
    all_subs = get_unique_values("subject")
    
    st.subheader("1. Selección de Asignaturas")
    sel_criteria = []
    cols = st.columns(3)
    for i, s in enumerate(all_subs):
        sl = s.lower()
        if "physics" in sl or "chemistry" in sl:
            name = "Physics" if "physics" in sl else "Chemistry"
            if cols[i%3].checkbox(f"{name} (2025)", key=f"n_{s}"): sel_criteria.append((s, False))
            if cols[i%3].checkbox(f"{name} (Old)", key=f"o_{s}"): sel_criteria.append((s, True))
        else:
            if cols[i%3].checkbox(s, key=f"g_{s}"): sel_criteria.append((s, None))

    if sel_criteria:
        parts = [f"(subject='{s}'" + (f" AND version {'IN' if old else 'NOT IN'} ('V4','V5')" if old is not None else "") + ")" for s, old in sel_criteria]
        where_gen = " OR ".join(parts)
        
        # Optimización: Cache de temas específicos según selección
        topics = run_query(f"SELECT DISTINCT topic FROM questionsC WHERE {where_gen} ORDER BY topic ASC")['topic'].tolist()
        
        st.subheader("2. Ajustes")
        col_t, col_n = st.columns([3, 1])
        
        if col_t.button("Elegir todos los temas"):
            st.session_state.sel_topics = topics
            
        sel_topics = col_t.multiselect("Temas", topics, key="sel_topics")
        num_q = col_n.number_input("Nº Preguntas", 1, 100, 10)
        
        col_p, col_l = st.columns(2)
        sel_p = col_p.multiselect("Paper", ["1A","1B", "2", "3"])
        sel_l = col_l.multiselect("Level", ["HL", "SL", "AHL", "ASL"])

        if st.button("🚀 GENERAR EXAMEN"):
            gen_query = f"SELECT * FROM questionsC WHERE ({where_gen})"
            if sel_topics: 
                topic_list = "','".join(sel_topics)
                gen_query += f" AND topic IN ('{topic_list}')"
            if sel_p: 
                paper_list = "','".join(sel_p)
                gen_query += f" AND paper IN ('{paper_list}')"
            if sel_l: 
                level_list = "','".join(sel_l)
                gen_query += f" AND level IN ('{level_list}')"
            
            res_exam = run_query(gen_query)
            if not res_exam.empty:
                exam = res_exam.sample(n=min(len(res_exam), num_q))
                st.markdown(f"### Examen Generado ({len(exam)} preguntas)")
                st.markdown('<button onclick="window.print()" style="width:100%; background:#28a745; color:white; border:none; padding:12px; border-radius:5px; cursor:pointer; font-weight:bold;">🖨️ IMPRIMIR / GUARDAR PDF</button>', unsafe_allow_html=True)
                for _, r in exam.iterrows(): render_question(r)
            else:

                st.warning("No hay preguntas que coincidan.")
