# callbacks/app_callbacks.py


from dash.dependencies import Input, Output, State
import dash_html_components as html
from layout import login_layout, register_layout, profile_layout, app_layout
from flask_login import current_user

def register_callbacks(app):
    @app.callback(
        Output('page-content', 'children'),
        [Input('url', 'pathname')],
        [State('user-email-store', 'data')]
    )
    
    def display_page(pathname, user_email):
        print(f"Pathname recebido: {pathname}") 
        
        if pathname == '/login' or pathname == '/':
            return login_layout()
        elif pathname == '/register':
            return register_layout()
        elif pathname == '/profile' and user_email: 
            return profile_layout() 
        elif pathname == '/main' and user_email: 
            return app_layout()
        else:
            return login_layout()