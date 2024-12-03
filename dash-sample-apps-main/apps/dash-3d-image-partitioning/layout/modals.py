import dash_html_components as html
import dash_core_components as dcc

def make_modal():
    with open("assets/howto.md", "r") as f:
        readme_md = f.read()

    return html.Div(
        id="markdown",
        className="modal",
        style={"display": "none"},
        children=[
            html.Div(
                id="markdown-container",
                className="markdown-container",
                # style={
                #     "color": text_color["light"],
                #     "backgroundColor": card_color["light"],
                # },
                children=[
                    html.Div(
                        className="close-container",
                        children=html.Button(
                            "Close",
                            id="markdown_close",
                            n_clicks=0,
                            className="closeButton",
                            style={"color": "DarkBlue"},
                        ),
                    ),
                    html.Div(
                        className="markdown-text", children=dcc.Markdown(readme_md)
                    ),
                ],
            )
        ],
    )