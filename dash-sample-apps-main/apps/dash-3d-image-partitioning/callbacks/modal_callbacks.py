from dash.dependencies import Input, Output

def register_callbacks(app):
    @app.callback(
        Output("markdown", "style"),
        [Input("learn-more-button", "n_clicks"), Input("markdown_close", "n_clicks")]
    )
    
    def update_click_output(button_click, close_click):
        if button_click > close_click:
            return {"display": "block"}
        else:
            return {"display": "none"}