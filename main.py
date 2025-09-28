import streamlit as st
from sqlalchemy import create_engine

db = st.secrets["postgres"]
engine = create_engine(
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['dbname']}"
)


# Load Devanagari font
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600&display=swap" rel="stylesheet">',
    unsafe_allow_html=True
)

# CSS
st.markdown("""
<style>
/* Page background */
.stApp {
    background: linear-gradient(135deg, #e0f7fa, #ffe0b2, #e8f5e9);
    background-attachment: fixed;
}

/* Title */
.custom-title {
    font-family: 'Baloo 2', cursive;
    font-size: 50px;
    font-weight: 800;
    text-align: center;
    margin-bottom: 40px;
    background: linear-gradient(45deg, #ff6f00, #d500f9, #2979ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 2px 3px 8px rgba(0,0,0,0.15);
}

/* Menu container */
.menu-container {
    display: flex;
    justify-content: center;
    gap: 30px;
    flex-wrap: wrap;
    margin-top: 30px;
}

/* Menu box */
div[data-testid="stPageLink"] {
    background: #ffffffc0; /* semi-transparent white */
    border-radius: 10px;
    padding: 15px 15px;
    min-width: 300px;
    text-align: center;
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
    backdrop-filter: blur(8px);
}

/* Hover effect */
div[data-testid="stPageLink"]:hover {
    transform: scale(1.08);
    box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    background: #ffffffc0; /* keep background semi-transparent so text is visible */
}

/* Menu text */
div[data-testid="stPageLink"] a {
    font-family: 'Baloo 2', cursive;
    font-weight: 700;
    font-size: 30px;
    text-decoration: none;
    background: linear-gradient(45deg, #ff1744, #d500f9);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    transition: all 0.3s ease;
}

/* Hover text gradient */
div[data-testid="stPageLink"]:hover a {
    background: linear-gradient(45deg, #00e676, #2979ff);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

/* Second menu box different color */
div[data-testid="stPageLink"]:nth-of-type(2) {
    background: #ffffffc0;
}
div[data-testid="stPageLink"]:nth-of-type(2) a {
    background: linear-gradient(45deg, #1a237e, #64b5f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
div[data-testid="stPageLink"]:nth-of-type(2):hover a {
    background: linear-gradient(45deg, #ff4081, #ffeb3b);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="custom-title">शेळगांव प्राथमिक आरोग्य केंद्र</div>', unsafe_allow_html=True)

# Menu container
st.markdown('<div class="menu-container">', unsafe_allow_html=True)
st.page_link("pages/MNo_Record.py", label="📋 M1 Record")
st.page_link("pages/create_immunization_list.py", label="💉 लसीकरण यादी")
st.markdown('</div>', unsafe_allow_html=True)
