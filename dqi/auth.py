"""
Module Name : auth.py

Purpose:
--------
Secure multi-user login for House Visit DQI using Streamlit Secrets.

Version:
--------
3.1.4

Important:
----------
- Supports multiple users.
- No region-based restriction is applied.
- north_admin and south_admin can both access the full dashboard.
- Passwords must stay in Streamlit Secrets only.
"""

import streamlit as st

from .config import APP_NAME


def get_login_credentials() -> dict:
    """
    Read authorized users from Streamlit Secrets.

    Expected Streamlit Secrets format:

    [auth.users.north_admin]
    username = "north_admin"
    password = "YOUR_PASSWORD"

    [auth.users.south_admin]
    username = "south_admin"
    password = "YOUR_PASSWORD"

    The username field inside each block is optional.
    If omitted, the block name itself is used as the username.
    """

    users = {}

    try:
        auth_config = st.secrets.get("auth", {})

        if not auth_config:
            return users

        # --------------------------------------------------------
        # Preferred multi-user configuration
        # --------------------------------------------------------
        if "users" in auth_config:
            users_config = auth_config["users"]

            for user_key, user_config in users_config.items():

                # Use explicit username if supplied.
                # Otherwise use the TOML block name.
                username = str(
                    user_config.get(
                        "username",
                        user_key,
                    )
                ).strip()

                password = str(
                    user_config.get(
                        "password",
                        "",
                    )
                )

                if username and password:
                    users[username] = {
                        "password": password,
                    }

        # --------------------------------------------------------
        # Backward compatibility with old single-user structure
        # --------------------------------------------------------
        elif (
            "username" in auth_config
            and "password" in auth_config
        ):
            username = str(
                auth_config.get(
                    "username",
                    "",
                )
            ).strip()

            password = str(
                auth_config.get(
                    "password",
                    "",
                )
            )

            if username and password:
                users[username] = {
                    "password": password,
                }

    except Exception as exc:
        # Do not expose secret values.
        st.error(
            "Unable to read login configuration from Streamlit Secrets."
        )

        st.caption(
            f"Configuration error: {type(exc).__name__}"
        )

    return users


def render_login_page():
    """
    Render login page and stop application execution
    until the user successfully authenticates.
    """

    st.markdown(
        """
        <style>

        .login-page-title {
            text-align: center;
            font-size: 34px;
            font-weight: 850;
            color: #1f2937;
            margin-top: 48px;
            margin-bottom: 4px;
        }

        .login-page-subtitle {
            text-align: center;
            font-size: 15px;
            color: #6b7280;
            margin-bottom: 30px;
        }

        .login-warning {
            background: #fff7e6;
            border-left: 6px solid #f59e0b;
            border-radius: 12px;
            padding: 14px 16px;
            margin-top: 15px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="login-page-title">
            {APP_NAME}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="login-page-subtitle">
            Secure access for internal data quality review
        </div>
        """,
        unsafe_allow_html=True,
    )

    authorized_users = get_login_credentials()

    # ------------------------------------------------------------
    # Secrets missing / invalid
    # ------------------------------------------------------------
    if not authorized_users:

        st.markdown(
            """
            <div class="login-warning">

            <b>Login secrets are not configured.</b><br><br>

            Add authorized users in:

            <code>.streamlit/secrets.toml</code>

            locally, or in:

            <b>Streamlit Cloud → Manage app → Settings → Secrets</b>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.stop()

    # ------------------------------------------------------------
    # Login form
    # ------------------------------------------------------------
    col_left, col_mid, col_right = st.columns(
        [1, 1.15, 1]
    )

    with col_mid:

        with st.form(
            "login_form"
        ):

            username = st.text_input(
                "Username",
                placeholder="Enter username",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password",
            )

            submitted = st.form_submit_button(
                "Login",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                entered_username = (
                    username.strip()
                )

                user_record = (
                    authorized_users.get(
                        entered_username
                    )
                )

                if (
                    user_record
                    and password
                    == user_record["password"]
                ):

                    st.session_state[
                        "authenticated"
                    ] = True

                    st.session_state[
                        "authenticated_user"
                    ] = entered_username

                    st.rerun()

                else:

                    st.error(
                        "Invalid username or password."
                    )


def require_login():
    """
    Require authentication before allowing access
    to the main application.
    """

    if (
        "authenticated"
        not in st.session_state
    ):
        st.session_state[
            "authenticated"
        ] = False

    if (
        "authenticated_user"
        not in st.session_state
    ):
        st.session_state[
            "authenticated_user"
        ] = None

    if not st.session_state[
        "authenticated"
    ]:

        render_login_page()

        st.stop()


def render_logout_button():
    """
    Display signed-in username and Logout button.
    """

    user_col, logout_col = st.columns(
        [7, 1]
    )

    with user_col:

        username = (
            st.session_state.get(
                "authenticated_user"
            )
        )

        if username:

            st.caption(
                f"Signed in as **{username}**"
            )

    with logout_col:

        if st.button(
            "Logout",
            use_container_width=True,
        ):

            st.session_state[
                "authenticated"
            ] = False

            st.session_state[
                "authenticated_user"
            ] = None

            # Also clear uploaded / analysed data
            # when the user logs out.
            st.session_state.pop(
                "dqi_result",
                None,
            )

            st.session_state.pop(
                "dqi_file_key",
                None,
            )

            st.session_state.pop(
                "dqi_download_package",
                None,
            )

            st.rerun()