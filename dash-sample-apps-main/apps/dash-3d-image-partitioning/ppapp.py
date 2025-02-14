# # app.py

# import dash
# import dash_html_components as html
# import dash_core_components as dcc
# from dash.dependencies import Input, Output, State
# from dash.exceptions import PreventUpdate
# from database.config import engine, Base
# from callbacks import user_callbacks, app_callbacks, modal_callbacks, image_callbacks
# from flask import Flask, redirect
# from flask_login import current_user, LoginManager
# from layout.main import app_layout
# from layout.login import login_layout
# from database.auth import auth_bp, login_manager
# import os
# import plotly.express as px


# Base.metadata.create_all(bind=engine)

# server = Flask(__name__)
# server.secret_key = os.urandom(24)

# login_manager.init_app(server)

# server.register_blueprint(auth_bp)

# app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)

# app.layout = html.Div([
#     dcc.Store(id='login-state', storage_type='session'), 
#     dcc.Store(id='user-email-store', storage_type='session'),  
#     dcc.Location(id='url', refresh=False),
#     html.Div(id='page-content'),
# ])


# app_callbacks.register_callbacks(app)
# user_callbacks.register_callbacks(app)
# modal_callbacks.register_callbacks(app)
# image_callbacks.register_callbacks(app)


# if __name__ == "__main__":
#     app.run_server(debug=True)
