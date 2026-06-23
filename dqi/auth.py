"""
Module Name : auth.py

Purpose:
--------
Secure login layer for House Visit DQI using Streamlit secrets and session state.

Owner:
------
Magic Bus Data Team

Version:
--------
1.0.0
"""

import streamlit as st
from .config import APP_NAME


def get_login_credentials():
    """Read login credentials from Streamlit secrets."""
    try:
        return st.secrets["auth"]["username"], st.secrets["auth"]["password"]
    except Exception:
        return None, None


def render_login_page():
    """Render the login page and stop the app until authenticated."""
    st.markdown(
        """
        <style>
            .login-page-title {text-align:center;font-size:34px;font-weight:850;color:#1f2937;margin-top:48px;margin-bottom:4px;}
            .login-page-subtitle {text-align:center;font-size:15px;color:#6b7280;margin-bottom:30px;}
            .login-warning {background:#fff7e6;border-left:6px solid #f59e0b;border-radius:12px;padding:14px 16px;margin-top:15px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="login-page-title">{APP_NAME}</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-page-subtitle">Secure access for internal data quality review</div>', unsafe_allow_html=True)

    expected_username, expected_password = get_login_credentials()
    if not expected_username or not expected_password:
        st.markdown(
            """
            <div class="login-warning">
                <b>Login secrets are not configured.</b><br>
                Add credentials in <code>.streamlit/secrets.toml</code> locally or in Streamlit Cloud secrets online.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    col_left, col_mid, col_right = st.columns([1, 1.15, 1])
    with col_mid:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            if submitted:
                if username == expected_username and password == expected_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Invalid username or password")


def require_login():
    """Gate the app behind login."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        render_login_page()
        st.stop()


def render_logout_button():
    """Render logout button in the header."""
    _, logout_col = st.columns([8, 1])
    with logout_col:
        if st.button("Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.rerun()
