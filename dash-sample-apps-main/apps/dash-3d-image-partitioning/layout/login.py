import dash_html_components as html
import dash_core_components as dcc

def login_layout():
    return html.Div(
        style={
            "display": "flex",
            "justify-content": "center",
            "align-items": "center",
            "height": "100vh",
            "background-color": "#f3f3f3",
        },
        children=[
            html.Div(
                style={
                    "width": "350px",
                    "padding": "30px",
                    "border-radius": "10px",
                    "box-shadow": "0px 4px 8px rgba(0, 0, 0, 0.1)",
                    "background-color": "white",
                    "text-align": "center",
                },
                children=[
                    html.Div(
                        children=[
                            html.A(
                                html.Img(
                                    src="/assets/imlogo.jpeg",
                                    style={
                                        "height": "50px",
                                        "margin-right": "15px"
                                    },
                                ),
                                
                            ),
                        ],
                        style={"display": "flex", "align-items": "center", "justify-content": "center"}
                    ),
                    html.H2(
                        "Login",
                        style={"color": "#333", "margin-bottom": "20px"}
                    ),
                    dcc.Input(
                        id="login-email",
                        type="email",
                        placeholder="E-mail",
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "margin-bottom": "10px",
                            "border-radius": "5px",
                            "border": "1px solid #ccc",
                        }
                    ),
                    dcc.Input(
                        id="login-password",
                        type="password",
                        placeholder="Password",
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "margin-bottom": "20px",
                            "border-radius": "5px",
                            "border": "1px solid #ccc",
                        }
                    ),
                    html.Button(
                        "Login",
                        id="login-button",
                        style={
                            "width": "100%",
                            "border-radius": "5px",
                            "border": "none",
                            "background-color": "#086D87",
                            "color": "white",
                            "font-size": "16px",
                            "cursor": "pointer",
                            "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                        }
                    ),
                    html.Div(id="login-message", style={"margin-top": "20px"}),
                    html.Br(),
                    html.A(
                        "Don't have an account? Sign up",
                        href="/register",
                        style={
                            "color": "#086D87",
                            "text-decoration": "none",
                            "font-size": "14px",
                        },
                        id="link-register",
                    )
                ]
            )
        ]
    )
