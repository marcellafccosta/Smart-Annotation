# layout/main.py

import dash_html_components as html
import dash_core_components as dcc
import dash
from layout.header import header_layout
from layout.modals import make_modal
from callbacks.image_callbacks import *



app = dash.Dash(__name__, suppress_callback_exceptions=True)

DEBUG_MASK = False
DEFAULT_STROKE_COLOR = px.colors.qualitative.Light24[0]
DEFAULT_STROKE_WIDTH = 5
hwscales = [(2, 2), (2, 2)]
# the number of dimensions displayed
NUM_DIMS_DISPLAYED = 2  # top and side
# the color of the triangles displaying the slice number
INDICATOR_COLOR = "DarkOrange"
DISPLAY_BG_COLOR = "white"


# A string, if length non-zero, saves superpixels to this file and then exits
SAVE_SUPERPIXEL = os.environ.get("SAVE_SUPERPIXEL", default="")
# A string, if length non-zero, loads superpixels from this file
LOAD_SUPERPIXEL = os.environ.get("LOAD_SUPERPIXEL", default="")
# If not "0", debugging mode is on.
DEBUG = os.environ.get("DEBUG", default="0") != "0"

# img_slices = make_seg_image(img, seg_img)


def app_layout():
    return html.Div([
        html.Div(
            id="main",
            children=[
                html.Div(
                    id="banner",
                    children=[
                        html.Div(
                            children=[
                                html.Img(
                                    id="logo",
                                    src=app.get_asset_url("imlogo.jpeg"),
                                    style={
                                        "height": "50px",
                                        "marginRight": "15px"
                                    },
                                ),
                            ],
                        ),
                        html.Div(
                            children=[
                                html.Button(
                                    "Learn more",
                                    id="learn-more-button",
                                    n_clicks=0,
                                    style={
                                        "width": "auto",
                                        "borderRadius": "5px",
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                            ],
                        ),
                        
                        html.Div(
                            children=[
                                html.A(
                                    html.Img(
                                        src=app.get_asset_url("custom-icon.svg"), 
                                        style={
                                            "height": "30px",  
                                            "cursor": "pointer",
                                            "padding": "10px",
                                        },
                                    ),
                                    href="/profile",
                                    style={"textDecoration": "none"}
                                ),
                            ],
                            style={"display": "flex", "alignItems": "center"}
                        ),
                        make_modal(),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "backgroundColor": "#086D87",
                        "padding": "10px",
                    },
                ),
            ],
            style={"backgroundColor": "#F0F4F8"}
        ),

        dcc.Store(id="image-slices", data=img_slices),
        dcc.Store(id="seg-slices", data=seg_slices),
        dcc.Store(
            id="drawn-shapes",
            data=[
                [[] for _ in range(seg_img.shape[i])] for i in range(NUM_DIMS_DISPLAYED)
            ],
        ),
        dcc.Store(id="slice-number-top", data=0),
        dcc.Store(id="slice-number-side", data=0),
        dcc.Store(
            id="undo-data",
            data=dict(
                undo_n_clicks=0,
                redo_n_clicks=0,
                undo_shapes=[],
                redo_shapes=[],
                empty_shapes=[
                    [[] for _ in range(seg_img.shape[i])]
                    for i in range(NUM_DIMS_DISPLAYED)
                ],
            ),
        ),

        html.Div(
            id="loader-wrapper",
            children=[
                html.Div(id="dummy", style={"display": "none"}),
                html.Div(id="dummy2", style={"display": "none"}, children=",0"),
                html.Div(
                    id="show-hide-seg-2d", children="show", style={"display": "none"}
                ),
                html.Div(
                    id="show-hide-seg-3d", children="show", style={"display": "none"}
                ),
                dcc.Loading(
                    id="graph-loading",
                    type="circle",
                    children=[
                        html.A(id="download-link", download="found_image.nii"),
                        dcc.Store(id="found-image-tensor-data", data=""),
                        html.Div(
                            children=[
                                html.Button(
                                    "3D View",
                                    id="view-select-button",
                                    n_clicks=0,
                                    style={
                                        "width": "25%",                                    
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                                html.Button(
                                    "Hide Segmentation",
                                    id="show-seg-check",
                                    n_clicks=0,
                                    style={
                                        "width": "25%",                                    
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                                html.Button(
                                    "Download Brain Volume",
                                    id="download-brain-button",
                                    style={
                                        "width": "auto",                                    
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                                html.Button(
                                    "Download Selected Partitions",
                                    id="download-button",
                                    style={
                                        "width": "auto",                                    
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                                html.Button(
                                    "Undo",
                                    id="undo-button",
                                    n_clicks=0,
                                    style={
                                        "width": "12.5%",                                    
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                                html.Button(
                                    "Redo",
                                    id="redo-button",
                                    n_clicks=0,
                                    style={
                                        "width": "12.5%",                                    
                                        "backgroundColor": "#005F73",
                                        "color": "white",
                                        "border": "none",
                                        "cursor": "pointer",
                                    },
                                ),
                            ],
                            style={"display": "flex",},
                        ),
                        html.Div(
    id="2D-graphs",
    style={
        "display": "grid",
        "gridTemplateColumns": "repeat(2, 1fr)",
        "gridAutoRows": "auto",
        "gridGap": "10px",  
        "padding": "20px", 
        "backgroundColor": "#f9f9f9",  
        "borderRadius": "8px",  
        "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.1)",  
    },
    children=[
        html.Div(
            [
                html.H6(
                    "Top View", style={
                        "textAlign": "center",
                        "color": "#086D87",
                        "fontWeight": "bold",
                        "marginBottom": "10px"
                    }
                )
            ],
            style={
                "gridColumn": "1",
                "gridRow": "1",
                "backgroundColor": "#fff",
                "padding": "10px",
                "borderRadius": "5px",
                "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)"
            },
        ),
        html.Div(
            [
                dcc.Graph(
                    id="image-display-graph-top",
                    figure=top_fig,
                )
            ],
            style={
                "gridColumn": "1",
                "gridRow": "2",
                "backgroundColor": "#fff",
                "padding": "10px",
                "borderRadius": "5px",
                "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)"
            },
        ),
        html.Div(
            [
                html.Div(
                    id="image-select-top-display",
                    style={"width": "125px", "padding": "5px"},
                ),
                html.Div(
                   dcc.Slider(
                        id="image-select-top",
                        min=0,
                        max=len(img_slices[0]) - 1,
                        step=1,
                        updatemode="drag",
                        value=len(img_slices[0]) // 2,
                        tooltip={"always_visible": True, "placement": "top"}  # Exibe o valor quando o usuário interage com o slider
                    ),

                    style={"flexGrow": "1", "padding": "0 10px"},
                ),
            ],
            style={
                "gridColumn": "1",
                "gridRow": "3",
                "display": "flex",
                "alignItems": "center",
                "background": "#ececec",
                "borderRadius": "5px",
                "padding": "10px",
                "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)"
            },
        ),
        html.Div(
            [
                html.H6(
                    "Side View", style={
                        "textAlign": "center",
                        "color": "#086D87",
                        "fontWeight": "bold",
                        "marginBottom": "10px"
                    }
                )
            ],
            style={
                "gridColumn": "2",
                "gridRow": "1",
                "backgroundColor": "#fff",
                "padding": "10px",
                "borderRadius": "5px",
                "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)"
            },
        ),
        html.Div(
            [
                dcc.Graph(
                    id="image-display-graph-side",
                    figure=side_fig,
                )
            ],
            style={
                "gridColumn": "2",
                "gridRow": "2",
                "backgroundColor": "#fff",
                "padding": "10px",
                "borderRadius": "5px",
                "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)"
            },
        ),
        html.Div(
            [
                html.Div(
                    id="image-select-side-display",
                    style={"width": "125px", "padding": "5px"},
                ),
                html.Div(
                    [
                        dcc.Slider(
                            id="image-select-side",
                            min=0,
                            max=len(img_slices[1]) - 1,
                            step=1,
                            updatemode="drag",
                            value=len(img_slices[1]) // 2,
                            tooltip={"always_visible": True, "placement": "top"}
                        )
                    ],
                    style={"flexGrow": "1", "padding": "0 10px"},
                ),
            ],
            style={
                "gridColumn": "2",
                "gridRow": "3",
                "display": "flex",
                "alignItems": "center",
                "background": "#ececec",
                "borderRadius": "5px",
                "padding": "10px",
                "boxShadow": "0px 2px 4px rgba(0, 0, 0, 0.1)"
            },
        ),
        dcc.Store(id="found-segs", data=found_seg_slices),
    ],
),
        html.Div(
            id="3D-graphs",
            children=[
                dcc.Graph(
                    id="image-display-graph-3d",
                    figure=make_default_3d_fig(),
                    config=dict(displayModeBar=False),
                )
            ],
            style={
                "display": "none",
                "padding": "20px",
                "backgroundColor": "#f9f9f9",
                "borderRadius": "8px",
                "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.1)"
            },
        ),

                    ],
                ),
            ],
        ),
        dcc.Store(id="fig-3d-scene", data=default_3d_layout),
        dcc.Store(id="current-render-id", data=0),
        dcc.Store(id="last-render-id", data=0),
    ])