# app.py

import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from database.config import engine, Base
from callbacks import user_callbacks, app_callbacks, modal_callbacks, image_callbacks
from flask import Flask, redirect
from flask_login import current_user, LoginManager
from layout.main import app_layout
from layout.login import login_layout
from database.auth import auth_bp, login_manager
import os
import plotly.express as px


# Configuração e criação do banco de dados
Base.metadata.create_all(bind=engine)

# Inicializa o app Flask
server = Flask(__name__)
server.secret_key = os.urandom(24)

# Configuração do LoginManager
login_manager.init_app(server)

# Registra o Blueprint de autenticação
server.register_blueprint(auth_bp)

# Inicializa o app Dash e associa ao Flask
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)

# Layout principal do Dash
app.layout = html.Div([
    dcc.Store(id='login-state', storage_type='session'), 
    dcc.Store(id='user-email-store', storage_type='session'),  
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
])

# Registra os callbacks
app_callbacks.register_callbacks(app)
user_callbacks.register_callbacks(app)
modal_callbacks.register_callbacks(app)
image_callbacks.register_callbacks(app)


if __name__ == "__main__":
    app.run_server(debug=True)
