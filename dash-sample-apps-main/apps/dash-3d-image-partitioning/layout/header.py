# layout/header.py

import dash_html_components as html
import dash_core_components as dcc

def header_layout():
    return html.Div(
        style={
            "display": "flex",
            "justify-content": "space-between",
            "align-items": "center",
            "background-color": "#086D87",
            "padding": "10px",
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
                        href="/main",
                    ),
                ],
                style={"display": "flex", "align-items": "center"}
            ),
            html.Div(
                children=[
                    html.A(
                        html.Img(
                            src="/assets/custom-icon.svg", 
                            style={
                                "height": "30px",  
                                "cursor": "pointer",
                                "padding": "10px",
                            },
                        ),
                        href="/profile",
                        style={
                            "text-decoration": "none",
                            "display": "flex",
                            "align-items": "center",
                            "justify-content": "center",
                            "background-color": "#086D87",
                            "border-radius": "50%",
                            "width": "24px",
                            "height": "24px",
                            "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",
                            "margin-right": "10px"
                        }
                    ),
                    dcc.Link(
                        html.Img(
                            src="/assets/logout-icon.svg",  
                            style={
                               "height": "30px",  
                                "cursor": "pointer",
                                "color": "red",
                            }
                        ),
                        href="/logout",
                        style={
                            "text-decoration": "none",
                            "display": "flex",
                            "align-items": "center",
                            "justify-content": "center",
                            "cursor": "pointer",
                            "transition": "0.3s ease",
                        }
                    ),
                ],
                style={"display": "flex", "align-items": "center"}
            )

        ]
    )
