import dash_html_components as html
import dash_core_components as dcc

from layout.header import header_layout

def profile_layout():
    return html.Div(
        style={
            "background-color": "#f3f3f3",
            "min-height": "100vh",
        },
        children=[
            header_layout(),
            html.Div(
                style={
                    "display": "flex",
                    "justify-content": "center",
                    "align-items": "center",
                    "padding": "30px",
                },
                children=[
                    html.Div(
                        style={
                            "width": "500px",
                            "padding": "30px",
                            "border-radius": "10px",
                            "box-shadow": "0px 4px 8px rgba(0, 0, 0, 0.1)",
                            "background-color": "white",
                            "text-align": "center",
                        },
                        children=[
                            html.H2("Profile", style={  
                                    "color": "#086D87",
                                    "fontSize": "28px",
                                    "fontWeight": "bold",
                                    "textAlign": "center",
                                    "width": "fit-content",
                                    "margin": "20px auto", }),
                            html.Table(
                                style={
                                    "width": "100%",
                                    "margin-top": "20px",
                                    "border-collapse": "collapse",
                                },
                                children=[
                                    
                                    html.Tr(
                                        children=[
                                            html.Td("Name", style={"padding": "10px", "color": "#333"}),
                                            html.Td(id="user-name", style={"padding": "10px", "color": "#555"}),
                                        ]
                                    ),
                                    html.Tr(
                                        children=[
                                            html.Td("Email", style={"padding": "10px", "color": "#333"}),
                                            html.Td(id="user-email", style={"padding": "10px", "color": "#555"}),
                                        ]
                                    ),
                                    html.Tr(
                                        children=[
                                            html.Td("Password", style={"padding": "10px", "color": "#333"}),
                                            html.Td(id="user-password", style={"padding": "10px", "color": "#555"}),
                                        ]
                                    )
                                ]
                            ),
                        ]
                    )
                ]
            )
        ]
    )
