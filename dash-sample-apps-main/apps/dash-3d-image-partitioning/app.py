import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State, ClientsideFunction
import plotly.graph_objects as go
from skimage import data, img_as_ubyte, segmentation, measure
from dash_canvas.utils import array_to_data_url
from plotly_common import plot_common
from plotly_common import image_utils
import numpy as np
from nilearn import image
import nibabel as nib
import plotly.express as px
from plotly_common import shape_utils
from sys import exit
import io
import base64
import skimage
import time
import os
from sqlalchemy.orm import Session
from database.config import get_db
from database.user_crud import create_user, get_user_by_email
from database.config import engine, Base
from dash.exceptions import PreventUpdate


Base.metadata.create_all(bind=engine)



DEBUG_MASK = False
DEFAULT_STROKE_COLOR = px.colors.qualitative.Light24[0]
DEFAULT_STROKE_WIDTH = 5
# the scales for the top and side images (they might be different)
# TODO: If the width and height scales are different, strange things happen? For
# example I have observed the masks getting scaled unevenly, maybe because the
# axes are actually scaled evenly (fixed to the x axis?) but then the mask gets
# scaled differently?
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


def PRINT(*vargs):
    if DEBUG:
        print(*vargs)


def make_seg_image(img):
    """ Segment the image, then find the boundaries, then return an array that
    is clear (alpha=0) where there are no boundaries. """
    segb = np.zeros_like(img).astype("uint8")
    seg = segmentation.slic(
        img, start_label=1, multichannel=False, compactness=0.1, n_segments=300
    )
    # Only keep superpixels with an average intensity greater than threshold
    # in order to remove superpixels of the background
    superpx_avg = (
        np.histogram(
            seg.astype(np.float), bins=np.arange(0, 310), weights=img.astype(np.float)
        )[0]
        / np.histogram(seg.astype(np.float), bins=np.arange(0, 310))[0]
        > 10
    )
    mask_brain = superpx_avg[seg]
    seg[np.logical_not(mask_brain)] = 0
    seg, _, _ = segmentation.relabel_sequential(seg)
    segb = segmentation.find_boundaries(seg).astype("uint8")
    segl = image_utils.label_to_colors(
        segb, colormap=["#000000", "#E48F72"], alpha=[0, 128], color_class_offset=0
    )
    return (segl, seg)


def make_default_figure(
    images=[],
    stroke_color=DEFAULT_STROKE_COLOR,
    stroke_width=DEFAULT_STROKE_WIDTH,
    img_args=dict(layer="above"),
    width_scale=1,
    height_scale=1,
):
    fig = plot_common.dummy_fig()
    plot_common.add_layout_images_to_fig(
        fig,
        images,
        img_args=img_args,
        width_scale=width_scale,
        height_scale=height_scale,
        update_figure_dims="height",
    )
    # add an empty image with the same size as the greatest of the already added
    # images so that we can add computed masks clientside later
    mwidth, mheight = [
        max([im[sz] for im in fig["layout"]["images"]]) for sz in ["sizex", "sizey"]
    ]
    fig.add_layout_image(
        dict(
            source="",
            xref="x",
            yref="y",
            x=0,
            y=0,
            sizex=mwidth,
            sizey=mheight,
            sizing="contain",
            layer="above",
        )
    )
    fig.update_layout(
        {
            "dragmode": "drawopenpath",
            "newshape.line.color": stroke_color,
            "newshape.line.width": stroke_width,
            "margin": dict(l=0, r=0, b=0, t=0, pad=4),
            "plot_bgcolor": DISPLAY_BG_COLOR,
        }
    )
    return fig


img = image.load_img("assets/BraTS19_2013_10_1_flair.nii")
img = img.get_fdata().transpose(2, 0, 1)[::-1].astype("float")

img = img_as_ubyte((img - img.min()) / (img.max() - img.min()))


def make_empty_found_segments():
    """ fstc_slices is initialized to a bunch of images containing nothing (clear pixels) """
    found_segs_tensor = np.zeros_like(img)
    # convert to a colored image (but it will just be colored "clear")
    fst_colored = image_utils.label_to_colors(
        found_segs_tensor,
        colormap=["#000000", "#8A2BE2"],
        alpha=[0, 128],
        color_class_offset=0,
    )
    fstc_slices = [
        [
            array_to_data_url(np.moveaxis(fst_colored, 0, j)[i])
            for i in range(np.moveaxis(fst_colored, 0, j).shape[0])
        ]
        for j in range(NUM_DIMS_DISPLAYED)
    ]
    return fstc_slices


if len(LOAD_SUPERPIXEL) > 0:
    # load partitioned image (to save time)
    if LOAD_SUPERPIXEL.endswith(".gz"):
        import gzip

        with gzip.open(LOAD_SUPERPIXEL) as fd:
            dat = np.load(fd)
            segl = dat["segl"]
            seg = dat["seg"]
    else:
        dat = np.load(LOAD_SUPERPIXEL)
        segl = dat["segl"]
        seg = dat["seg"]
else:
    # partition image
    segl, seg = make_seg_image(img)

if len(SAVE_SUPERPIXEL) > 0:
    np.savez(SAVE_SUPERPIXEL, segl=segl, seg=seg)
    exit(0)

seg_img = img_as_ubyte(segl)
img_slices, seg_slices = [
    [
        # top
        [array_to_data_url(im[i, :, :]) for i in range(im.shape[0])],
        # side
        [array_to_data_url(im[:, i, :]) for i in range(im.shape[1])],
    ]
    for im in [img, seg_img]
]
# initially no slices have been found so we don't draw anything
found_seg_slices = make_empty_found_segments()
# store encoded blank slices for each view to save recomputing them for slices
# containing no colored pixels
blank_seg_slices = [found_seg_slices[0][0], found_seg_slices[1][0]]

app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

top_fig, side_fig = [
    make_default_figure(
        images=[img_slices[i][0], seg_slices[i][0]],
        width_scale=hwscales[i][1],
        height_scale=hwscales[i][0],
    )
    for i in range(NUM_DIMS_DISPLAYED)
]

default_3d_layout = dict(
    scene=dict(
        yaxis=dict(visible=False, showticklabels=False, showgrid=False, ticks=""),
        xaxis=dict(visible=True, title="Side View Slice Number"),
        zaxis=dict(visible=True, title="Top View Slice Number"),
        camera=dict(
            up=dict(x=0, y=0, z=1),
            center=dict(x=0, y=0, z=0),
            eye=dict(x=1.25, y=1.25, z=1.25),
        ),
    ),
    height=800,
)


def make_default_3d_fig():
    fig = go.Figure(data=[go.Mesh3d()])
    fig.update_layout(**default_3d_layout)
    return fig


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




def register_layout():
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
                    html.H2(
                        "Cadastro",
                        style={"color": "#333", "margin-bottom": "20px"}
                    ),
                    dcc.Input(
                        id="register-name",
                        type="text",
                        placeholder="Nome de usuário",
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "margin-bottom": "10px",
                            "border-radius": "5px",
                            "border": "1px solid #ccc",
                        }
                    ),
                    dcc.Input(
                        id="register-email",
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
                        id="register-password",
                        type="password",
                        placeholder="Senha",
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "margin-bottom": "10px",
                            "border-radius": "5px",
                            "border": "1px solid #ccc",
                        }
                    ),
                    dcc.Input(
                        id="confirm-password",
                        type="password",
                        placeholder="Confirme a senha",
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "margin-bottom": "20px",
                            "border-radius": "5px",
                            "border": "1px solid #ccc",
                        }
                    ),
                    html.Button(
                        "Registrar",
                        id="register-button",
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
                    html.Div(id="register-message", style={"margin-top": "20px"}),
                    html.Br(),
                    html.A(
                        "Já tem uma conta? Faça login",
                        href="/login",
                        style={
                            "color": "#086D87",
                            "text-decoration": "none",
                            "font-size": "14px",
                        },
                        id="link-login",
                    )
                ]
            )
        ]
    )
    
    
    



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
                        placeholder="Senha",
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "margin-bottom": "20px",
                            "border-radius": "5px",
                            "border": "1px solid #ccc",
                        }
                    ),
                    html.Button(
                        "Entrar",
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
                        "Não tem uma conta? Cadastre-se",
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
@app.callback(
    Output("register-message", "children"),
    [Input("register-button", "n_clicks")],
    [State("register-name", "value"),
     State("register-email", "value"),
     State("register-password", "value")]
)
def register_user(n_clicks, name, email, password):
    if n_clicks:
        if not name or not email or not password:
            return "Todos os campos são obrigatórios."

        db = next(get_db())
        # Verifica se o email já está registrado
        if get_user_by_email(db, email):
            return "E-mail já cadastrado. Tente outro."

        # Cria um novo usuário
        user = create_user(db, name=name, email=email, password=password)
        if user:
            return "Usuário registrado com sucesso!"
        else:
            return "Erro ao registrar o usuário. Tente novamente."
    return ""



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






app.layout = html.Div([
    dcc.Store(id='login-state', storage_type='session'),  # Armazena o estado de login (sessão do usuário)
    dcc.Store(id='user-email-store', storage_type='session'),  # Armazena o email do usuário autenticado
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
])





def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if user and user.password == password:  
        return user
    return None


@app.callback(
    [Output("login-message", "children"), 
     Output("url", "pathname"), 
     Output("user-email-store", "data")],
    [Input("login-button", "n_clicks")], 
    [State("login-email", "value"), 
     State("login-password", "value")]  
)
def login_user(n_clicks, email, password):
    if n_clicks:
        # Verifica se os campos estão preenchidos
        if not email or not password:
            return "Todos os campos são obrigatórios.", dash.no_update, dash.no_update

        db = next(get_db())
        
        # Verifica as credenciais do usuário
        user = authenticate_user(db, email, password)
        if user:
            # Caso de sucesso: redireciona para o perfil do usuário
            return "Login bem-sucedido!", "/profile", email
        else:
            # Caso de falha: mensagem de erro
            return "E-mail ou senha incorretos.", dash.no_update, dash.no_update

    # Não há ação do botão, então não atualiza nada
    raise PreventUpdate





# Callback para alternar entre layouts com base na URL
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    [State('user-email-store', 'data')]
)
def display_page(pathname, user_email):
    # Verifica se o usuário está autenticado
    if pathname in ['/profile', '/main']:
        if not user_email:
            # Redireciona para a página de login se o usuário não estiver autenticado
            return login_layout()
    
    if pathname == '/login' or pathname == '/':
        return login_layout()
    elif pathname == '/register':
        return register_layout()
    elif pathname == '/profile':
        return profile_layout()
    elif pathname == '/main':
        return app_layout()
    else:
        return html.H1("404 - Página não encontrada")


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



app.clientside_callback(
    """
function (show_seg_n_clicks) {
    // update show segmentation button
    var show_seg_button = document.getElementById("show-seg-check");
    if (show_seg_button) {
        show_seg_button.textContent = show_seg_n_clicks % 2 ?
            "Show Segmentation" :
            "Hide Segmentation";
    }
    var ret = (show_seg_n_clicks % 2) ? "" : "show";
    return [ret,ret];
}
""",
    [Output("show-hide-seg-2d", "children"), Output("show-hide-seg-3d", "children")],
    [Input("show-seg-check", "n_clicks")],
)

app.clientside_callback(
    """
function(
    image_select_top_value,
    image_select_side_value,
    show_hide_seg_2d,
    found_segs_data,
    image_slices_data,
    image_display_top_figure,
    image_display_side_figure,
    seg_slices_data,
    drawn_shapes_data) {{
    let show_seg_check = show_hide_seg_2d;
    let image_display_figures_ = figure_display_update(
        [image_select_top_value,image_select_side_value],
        show_seg_check,
        found_segs_data,
        image_slices_data,
        [image_display_top_figure,image_display_side_figure],
        seg_slices_data,
        drawn_shapes_data),
        // slider order reversed because the image slice number is shown on the
        // other figure
        side_figure = image_display_figures_[1],
        top_figure = image_display_figures_[0],
        d=3,
        sizex, sizey;
    // append shapes that show what slice the other figure is in
    sizex = top_figure.layout.images[0].sizex,
    sizey = top_figure.layout.images[0].sizey;
    // tri_shape draws the triangular shape, see assets/app_clientside.js
    if (top_figure.layout.shapes) {{
        top_figure.layout.shapes=top_figure.layout.shapes.concat([
            tri_shape(d/2,sizey*image_select_side_value/found_segs_data[1].length,
                      d/2,d/2,'right'),
            tri_shape(sizex-d/2,sizey*image_select_side_value/found_segs_data[1].length,
                      d/2,d/2,'left'),
        ]);
    }}
    sizex = side_figure.layout.images[0].sizex,
    sizey = side_figure.layout.images[0].sizey;
    if (side_figure.layout.shapes) {{
        side_figure.layout.shapes=side_figure.layout.shapes.concat([
            tri_shape(d/2,sizey*image_select_top_value/found_segs_data[0].length,
                      d/2,d/2,'right'),
            tri_shape(sizex-d/2,sizey*image_select_top_value/found_segs_data[0].length,
                      d/2,d/2,'left'),
        ]);
    }}
    // return the outputs
    return image_display_figures_.concat([
    "Slice: " + (image_select_top_value+1) + " / {num_top_slices}",
    "Slice: " + (image_select_side_value+1) + " / {num_side_slices}",
    image_select_top_value,
    image_select_side_value
    ]);
}}
""".format(
        num_top_slices=len(img_slices[0]), num_side_slices=len(img_slices[1])
    ),
    [
        Output("image-display-graph-top", "figure"),
        Output("image-display-graph-side", "figure"),
        Output("image-select-top-display", "children"),
        Output("image-select-side-display", "children"),
        Output("slice-number-top", "data"),
        Output("slice-number-side", "data"),
    ],
    [
        Input("image-select-top", "value"),
        Input("image-select-side", "value"),
        Input("show-hide-seg-2d", "children"),
        Input("found-segs", "data"),
    ],
    [
        State("image-slices", "data"),
        State("image-display-graph-top", "figure"),
        State("image-display-graph-side", "figure"),
        State("seg-slices", "data"),
        State("drawn-shapes", "data"),
    ],
)

app.clientside_callback(
    """
function(top_relayout_data,
side_relayout_data,
undo_n_clicks,
redo_n_clicks,
top_slice_number,
side_slice_number,
drawn_shapes_data,
undo_data)
{
    // Ignore if "shapes" not in any of the relayout data
    let triggered = window.dash_clientside.callback_context.triggered.map(
        t => t['prop_id'])[0];
    if ((triggered === "image-display-graph-top.relayoutData" && !("shapes" in
        top_relayout_data)) || (triggered === "image-display-graph-side.relayoutData"
        && !("shapes" in side_relayout_data))) {
        return [window.dash_clientside.no_update,window.dash_clientside.no_update];
    }
    drawn_shapes_data = json_copy(drawn_shapes_data);
    let ret = undo_track_slice_figure_shapes (
    [top_relayout_data,side_relayout_data],
    ["image-display-graph-top.relayoutData",
     "image-display-graph-side.relayoutData"],
    undo_n_clicks,
    redo_n_clicks,
    undo_data,
    drawn_shapes_data,
    [top_slice_number,side_slice_number],
    // a function that takes a list of shapes and returns those that we want to
    // track (for example if some shapes are to show some attribute but should not
    // be tracked by undo/redo)
    function (shapes) { return shapes.filter(function (s) {
            let ret = true;
            try { ret &= (s.fillcolor == "%s"); } catch(err) { ret &= false; }
            try { ret &= (s.line.color == "%s"); } catch(err) { ret &= false; }
            // return !ret because we don't want to keep the indicators
            return !ret;
        });
    });
    undo_data=ret[0];
    drawn_shapes_data=ret[1];
    return [drawn_shapes_data,undo_data];
}
"""
    % ((INDICATOR_COLOR,) * 2),
    [Output("drawn-shapes", "data"), Output("undo-data", "data")],
    [
        Input("image-display-graph-top", "relayoutData"),
        Input("image-display-graph-side", "relayoutData"),
        Input("undo-button", "n_clicks"),
        Input("redo-button", "n_clicks"),
    ],
    [
        State("slice-number-top", "data"),
        State("slice-number-side", "data"),
        State("drawn-shapes", "data"),
        State("undo-data", "data"),
    ],
)


def shapes_to_segs(
    drawn_shapes_data, image_display_top_figure, image_display_side_figure,
):
    masks = np.zeros_like(img)
    for j, (graph_figure, (hscale, wscale)) in enumerate(
        zip([image_display_top_figure, image_display_side_figure], hwscales)
    ):
        fig = go.Figure(**graph_figure)
        # we use the width and the height of the first layout image (this will be
        # one of the images of the brain) to get the bounding box of the SVG that we
        # want to rasterize
        width, height = [fig.layout.images[0][sz] for sz in ["sizex", "sizey"]]
        for i in range(seg_img.shape[j]):
            shape_args = [
                dict(width=width, height=height, shape=s)
                for s in drawn_shapes_data[j][i]
            ]
            if len(shape_args) > 0:
                mask = shape_utils.shapes_to_mask(
                    shape_args,
                    # we only have one label class, so the mask is given value 1
                    1,
                )
                # TODO: Maybe there's a more elegant way to downsample the mask?
                np.moveaxis(masks, 0, j)[i, :, :] = mask[::hscale, ::wscale]
    found_segs_tensor = np.zeros_like(img)
    if DEBUG_MASK:
        found_segs_tensor[masks == 1] = 1
    else:
        # find labels beneath the mask
        labels = set(seg[1 == masks])
        # for each label found, select all of the segment with that label
        for l in labels:
            found_segs_tensor[seg == l] = 1
    return found_segs_tensor


@app.callback(
    [Output("found-segs", "data"), Output("current-render-id", "data")],
    [Input("drawn-shapes", "data")],
    [
        State("image-display-graph-top", "figure"),
        State("image-display-graph-side", "figure"),
        State("current-render-id", "data"),
    ],
)
def draw_shapes_react(
    drawn_shapes_data,
    image_display_top_figure,
    image_display_side_figure,
    current_render_id,
):
    if any(
        [
            e is None
            for e in [
                drawn_shapes_data,
                image_display_top_figure,
                image_display_side_figure,
            ]
        ]
    ):
        return dash.no_update
    t1 = time.time()
    found_segs_tensor = shapes_to_segs(
        drawn_shapes_data, image_display_top_figure, image_display_side_figure,
    )
    t2 = time.time()
    PRINT("Time to convert shapes to segments:", t2 - t1)
    # convert to a colored image
    fst_colored = image_utils.label_to_colors(
        found_segs_tensor,
        colormap=["#8A2BE2"],
        alpha=[128],
        # we map label 0 to the color #000000 using no_map_zero, so we start at
        # color_class 1
        color_class_offset=1,
        labels_contiguous=True,
        no_map_zero=True,
    )
    t3 = time.time()
    PRINT("Time to convert from labels to colored image:", t3 - t2)
    fstc_slices = [
        [
            array_to_data_url(s) if np.any(s != 0) else blank_seg_slices[j]
            for s in np.moveaxis(fst_colored, 0, j)
        ]
        for j in range(NUM_DIMS_DISPLAYED)
    ]
    t4 = time.time()
    PRINT("Time to convert to data URLs:", t4 - t3)
    PRINT("Total time to compute 2D annotations:", t4 - t1)
    return fstc_slices, current_render_id + 1


def _decode_b64_slice(s):
    return base64.b64decode(s.encode())


def slice_image_list_to_ndarray(fstc_slices):
    # convert encoded slices to array
    # TODO eventually make it format agnostic, right now we just assume png and
    # strip off length equal to uri_header from the uri string
    uri_header = "data:image/png;base64,"
    # preallocating the final tensor by reading the first image makes converting
    # much faster (because all the images have the same dimensions)
    n_slices = len(fstc_slices)
    first_img = plot_common.str_to_img_ndarrary(
        _decode_b64_slice(fstc_slices[0][len(uri_header) :])
    )
    fstc_ndarray = np.zeros((n_slices,) + first_img.shape, dtype=first_img.dtype)
    PRINT("first_img.dtype", first_img.dtype)
    fstc_ndarray[0] = first_img
    for n, img_slice in enumerate(fstc_slices[1:]):
        img = plot_common.str_to_img_ndarrary(
            _decode_b64_slice(img_slice[len(uri_header) :])
        )
        fstc_ndarray[n] = img
    PRINT("fstc_ndarray.shape", fstc_ndarray.shape)
    # transpose back to original
    if len(fstc_ndarray.shape) == 3:
        # Brain data is lacking the 4th channel dimension
        # Here we allow for this function to also return an array for the 3D brain data
        return fstc_ndarray.transpose((1, 2, 0))
    return fstc_ndarray.transpose((1, 2, 0, 3))


# Converts found slices to nii file and encodes in b64 so it can be downloaded
def save_found_slices(fstc_slices):
    # we just save the first view (it makes no difference in the end)
    fstc_slices = fstc_slices[0]
    fstc_ndarray = slice_image_list_to_ndarray(fstc_slices)
    # if the tensor is all zero (no partitions found) return None
    if np.all(fstc_ndarray == 0):
        return None
    # TODO add affine
    # technique for writing nii to bytes from here:
    # https://gist.github.com/arokem/423d915e157b659d37f4aded2747d2b3
    fstc_nii = nib.Nifti1Image(skimage.img_as_ubyte(fstc_ndarray), affine=None)
    fstcbytes = io.BytesIO()
    file_map = fstc_nii.make_file_map({"image": fstcbytes, "header": fstcbytes})
    fstc_nii.to_file_map(file_map)
    fstcb64 = base64.b64encode(fstcbytes.getvalue()).decode()
    return fstcb64


@app.callback(
    Output("found-image-tensor-data", "data"),
    [Input("download-button", "n_clicks"), Input("download-brain-button", "n_clicks")],
    [State("found-segs", "data"), State("image-slices", "data")],
)
def download_button_react(
    download_button_n_clicks,
    download_brain_button_n_clicks,
    found_segs_data,
    brain_data,
):
    ctx = dash.callback_context
    # Find out which download button was triggered
    if not ctx.triggered:
        # Nothing has happened yet
        return ""
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger_id == "download-button":
        ret = save_found_slices(found_segs_data)
    elif trigger_id == "download-brain-button":
        ret = save_found_slices(brain_data)
    else:
        return ""

    if ret is None:
        return ""
    return ret


app.clientside_callback(
    """
function (found_image_tensor_data) {
    if (found_image_tensor_data.length <= 0) {
        return "";
    }
    // for some reason you can't use the conversion to ascii from base64 directly
    // with blob, you have to use the ascii encoded as numbers
    const byte_chars = window.atob(found_image_tensor_data);
    const byte_numbers = Array.from(byte_chars,(b,i)=>byte_chars.charCodeAt(i));
    const byte_array = new Uint8Array(byte_numbers);
    let b = new Blob([byte_array],{type: 'application/octet-stream'});
    let url = URL.createObjectURL(b);
    return url;
}
""",
    Output("download-link", "href"),
    [Input("found-image-tensor-data", "data")],
)

app.clientside_callback(
    """
function (href) {
    if (href != "") {
        let download_a=document.getElementById("download-link");
        download_a.click();
    }
    return '';
}
""",
    Output("dummy", "children"),
    [Input("download-link", "href")],
)

app.clientside_callback(
    """
function (view_select_button_nclicks,current_render_id) {
    console.log("view_select_button_nclicks");
    console.log(view_select_button_nclicks);
    var graphs_2d = document.getElementById("2D-graphs"),
        graphs_3d = document.getElementById("3D-graphs"),
        ret = "";
    // update view select button
    var view_select_button = document.getElementById("view-select-button");
    if (view_select_button) {
        view_select_button.textContent = view_select_button_nclicks % 2 ?
            "2D View" :
            "3D View";
    }
    if (graphs_2d && graphs_3d) {
        if (view_select_button_nclicks % 2) {
            graphs_2d.style.display = "none";
            graphs_3d.style.display = "";
            ret = "3d shown";
        } else {
            graphs_2d.style.display = "grid";
            graphs_3d.style.display = "none";
            ret = "2d shown";
        }
    }
    ret += ","+current_render_id;
    return ret;
}
""",
    Output("dummy2", "children"),
    [Input("view-select-button", "n_clicks")],
    [State("current-render-id", "data")],
)


@app.callback(
    Output("fig-3d-scene", "data"),
    [Input("image-display-graph-3d", "relayoutData")],
    [State("fig-3d-scene", "data")],
)
def store_scene_data(graph_3d_relayoutData, last_3d_scene):
    PRINT("graph_3d_relayoutData", graph_3d_relayoutData)
    if graph_3d_relayoutData is not None:
        for k in graph_3d_relayoutData.keys():
            last_3d_scene[k] = graph_3d_relayoutData[k]
        return last_3d_scene
    return dash.no_update


@app.callback(
    [Output("image-display-graph-3d", "figure"), Output("last-render-id", "data")],
    [Input("dummy2", "children"), Input("show-hide-seg-3d", "children")],
    [
        State("drawn-shapes", "data"),
        State("fig-3d-scene", "data"),
        State("last-render-id", "data"),
        State("image-display-graph-top", "figure"),
        State("image-display-graph-side", "figure"),
    ],
)
def populate_3d_graph(
    dummy2_children,
    show_hide_seg_3d,
    drawn_shapes_data,
    last_3d_scene,
    last_render_id,
    image_display_top_figure,
    image_display_side_figure,
):
    # extract which graph shown and the current render id
    graph_shown, current_render_id = dummy2_children.split(",")
    current_render_id = int(current_render_id)
    start_time = time.time()
    cbcontext = [p["prop_id"] for p in dash.callback_context.triggered][0]
    # check that we're not toggling the display of the 3D annotation
    if cbcontext != "show-hide-seg-3d.children":
        PRINT(
            "might render 3D, current_id: %d, last_id: %d"
            % (current_render_id, last_render_id)
        )
        if graph_shown != "3d shown" or current_render_id == last_render_id:
            if current_render_id == last_render_id:
                PRINT("not rendering 3D because it is up to date")
            return dash.no_update
    PRINT("rendering 3D")
    segs_ndarray = shapes_to_segs(
        drawn_shapes_data, image_display_top_figure, image_display_side_figure,
    ).transpose((1, 2, 0))
    # image, color
    images = [
        (img.transpose((1, 2, 0))[:, :, ::-1], "grey"),
    ]
    if show_hide_seg_3d == "show":
        images.append((segs_ndarray[:, :, ::-1], "purple"))
    data = []
    for im, color in images:
        im = image_utils.combine_last_dim(im)
        try:
            verts, faces, normals, values = measure.marching_cubes(im, 0, step_size=3)
            x, y, z = verts.T
            i, j, k = faces.T
            data.append(
                go.Mesh3d(x=x, y=y, z=z, color=color, opacity=0.5, i=i, j=j, k=k)
            )
        except RuntimeError:
            continue
    fig = go.Figure(data=data)
    fig.update_layout(**last_3d_scene)
    end_time = time.time()
    PRINT("serverside 3D generation took: %f seconds" % (end_time - start_time,))
    return (fig, current_render_id)


if __name__ == "__main__":
    app.run_server(debug=True)
