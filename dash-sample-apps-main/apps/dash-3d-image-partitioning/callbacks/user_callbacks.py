# callbacks/user_callback.py

from dash.dependencies import Input, Output, State
from sqlalchemy.orm import Session
from database.config import get_db
from database.user_crud import create_user, get_user_by_email
from dash.exceptions import PreventUpdate
import dash
import dash_html_components as html
from database.auth import User
from dash import callback_context


def register_callbacks(app):
    @app.callback(
            Output("register-message", "children"),
            [Input("register-button", "n_clicks")],
            [State("register-name", "value"), State("register-email", "value"), State("register-password", "value")]
    )
    def register_user(n_clicks, name, email, password):
        if n_clicks:
            if not name or not email or not password:
                return "All fields are required."

            db = next(get_db())
            if get_user_by_email(db, email):
                return "Email already registered. Try another."

            user = create_user(db, name=name, email=email, password=password)
            if user:
                return "User successfully registered!"
            else:
                return "Error registering the user. Please try again."
        return ""

        
        
    @app.callback(
            [Output("user-name", "children"), Output("user-email", "children"), Output("user-password", "children")],
            [Input("url", "pathname")],
            [State("user-email-store", "data")]
        )      
    
    def load_user_profile(pathname, email):
            if pathname == '/profile' and email:
                db = next(get_db())
                user = get_user_by_email(db, email)
                
                if user:
                    return f" {user.name}", f" {user.email}", f" {user.password}"
                else:
                    return "User not found.", "", ""
            return dash.no_update, dash.no_update, dash.no_update


    @app.callback(
        [
            Output("login-message", "children"),
            Output("url", "pathname"),
            Output("user-email-store", "data")
        ],
        [Input("login-button", "n_clicks")],
        [State("login-email", "value"), State("login-password", "value"), State("user-email-store", "data")]
    )
    def login_logout_user(login_n_clicks, email, password, stored_email):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Login 
        if button_id == "login-button":
            if not email or not password:
                return "All fields are required.", dash.no_update, dash.no_update

            db = next(get_db())
            user_db = get_user_by_email(db, email)
            
            if user_db and user_db.password == password:
                return "Login successful!", "/profile", email
            else:
                return "Incorrect email or password.", dash.no_update, dash.no_update

        # Logout 
        elif button_id == "logout-button" and "logout-button" in [c['prop_id'].split('.')[0] for c in ctx.triggered]:
            return "", "/", None
        
        #getitemsession limpar


        raise PreventUpdate
    

