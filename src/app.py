import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table
from datetime import date, timedelta
import numpy as np

# --- Initialize the App ---
app = Dash(__name__, external_stylesheets=[dbc.themes.SOLAR])
server = app.server

# --- App Layout ---
app.layout = dbc.Container(
    [
        # 1. Header
        dbc.Row(
            dbc.Col(
                html.H1("Stock Finance Dashboard", className="text-center text-primary mb-4"),
                width=12,
            )
        ),
        # 2. Control Panel
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Select Stock", className="card-title"),
                                dbc.Input(
                                    id="ticker-input",
                                    value="AAPL",
                                    type="text",
                                    placeholder="Enter stock ticker (e.g., AAPL)",
                                    className="mb-2",
                                ),
                                dcc.DatePickerRange(
                                    id="date-picker",
                                    min_date_allowed=date(2010, 1, 1),
                                    max_date_allowed=date.today(),
                                    start_date=date.today() - timedelta(days=365),
                                    end_date=date.today(),
                                    className="mb-2",
                                ),
                                dbc.Button(
                                    "Fetch Data",
                                    id="submit-button",
                                    color="primary",
                                    n_clicks=0,
                                ),
                            ]
                        )
                    ),
                    width=12,
                )
            ],
            className="mb-4",
        ),
        # 3. Key Metrics
        dbc.Row(
            [
                dbc.Col(dbc.Card(id="latest-close-card", color="success", inverse=True)),
                dbc.Col(dbc.Card(id="52-week-high-card", color="warning", inverse=True)),
                dbc.Col(dbc.Card(id="52-week-low-card", color="danger", inverse=True)),
            ],
            className="mb-4",
        ),
        # 4. Graphs
        dbc.Row(
            [
                dbc.Col(
                    dcc.Loading(dcc.Graph(id="candlestick-chart"), type="graph"),
                    width=6,
                ),
                dbc.Col(
                    dcc.Loading(dcc.Graph(id="price-chart"), type="graph"),
                    width=6,
                ),
            ],
            className="mb-4",
        ),
        # 5. Data Table
        dbc.Row(
            dbc.Col(
                dcc.Loading(
                    dash_table.DataTable(
                        id="data-table",
                        sort_action="native",
                        page_size=10,
                        style_table={"overflowX": "auto"},
                        style_header={"backgroundColor": "rgb(30, 30, 30)", "color": "white"},
                        style_data={"backgroundColor": "rgb(50, 50, 50)", "color": "white"},
                        style_cell={"textAlign": "left", "padding": "5px"},
                    ),
                    type="default",
                ),
                width=12,
            )
        ),
    ],
    fluid=True,
)

# --- Callback ---
@app.callback(
    Output("candlestick-chart", "figure"),
    Output("price-chart", "figure"),
    Output("latest-close-card", "children"),
    Output("52-week-high-card", "children"),
    Output("52-week-low-card", "children"),
    Output("data-table", "data"),
    Output("data-table", "columns"),
    Input("submit-button", "n_clicks"),
    State("ticker-input", "value"),
    State("date-picker", "start_date"),
    State("date-picker", "end_date"),
    prevent_initial_call=True,
)
def update_dashboard(n_clicks, ticker, start_date, end_date):
    # 1. --- Handle Errors and Fetch Data ---
    if not ticker:
        empty_fig = go.Figure().update_layout(
            title_text="No Ticker Selected",
            template="plotly_dark",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )
        empty_card = dbc.CardBody([html.H5("N/A"), html.P("Enter a ticker")])
        return empty_fig, empty_fig, empty_card, empty_card, empty_card, [], []

    try:
        df_chart = yf.download(ticker, start=start_date, end=end_date)
        today = date.today()
        year_ago = today - timedelta(days=365)
        df_metrics = yf.download(ticker, start=year_ago, end=today)

        # Flatten MultiIndex columns if needed
        if isinstance(df_chart.columns, pd.MultiIndex):
            df_chart.columns = df_chart.columns.get_level_values(0)
        if isinstance(df_metrics.columns, pd.MultiIndex):
            df_metrics.columns = df_metrics.columns.get_level_values(0)

        if df_chart.empty or df_metrics.empty:
            raise ValueError(f"No data found for ticker '{ticker}'")

    except Exception as e:
        error_fig = go.Figure().update_layout(
            title_text=f"Error: {e}", template="plotly_dark"
        )
        error_card = dbc.CardBody([html.H5("Error"), html.P(str(e))])
        return error_fig, error_fig, error_card, error_card, error_card, [], []

    # 2. --- Create Figures ---
    # Ensure data is serializable
    df_chart = df_chart.reset_index()
    df_chart["Date"] = pd.to_datetime(df_chart["Date"]).dt.strftime("%Y-%m-%d")

    candlestick_fig = go.Figure(
        data=[
            go.Candlestick(
                x=df_chart["Date"].tolist(),
                open=df_chart["Open"].astype(float).tolist(),
                high=df_chart["High"].astype(float).tolist(),
                low=df_chart["Low"].astype(float).tolist(),
                close=df_chart["Close"].astype(float).tolist(),
                name="Candlestick",
            )
        ]
    )
    candlestick_fig.update_layout(
        title=f"{ticker.upper()} Candlestick Chart",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
    )

    price_fig = go.Figure()
    price_fig.add_trace(
        go.Scatter(
            x=df_chart["Date"].tolist(),
            y=df_chart["Close"].astype(float).tolist(),
            mode="lines",
            name="Close",
        )
    )
    price_fig.add_trace(
        go.Bar(
            x=df_chart["Date"].tolist(),
            y=df_chart["Volume"].astype(float).tolist(),
            name="Volume",
            yaxis="y2",
        )
    )
    price_fig.update_layout(
        title=f"{ticker.upper()} Close Price & Volume",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        yaxis2=dict(title="Volume", overlaying="y", side="right"),
        template="plotly_dark",
    )

    # 3. --- Metrics ---
    latest_close = float(df_metrics["Close"].dropna().iloc[-1])
    week_52_high = float(df_metrics["High"].max())
    week_52_low = float(df_metrics["Low"].min())

    close_card = dbc.CardBody(
        [
            html.H5("Latest Close", className="card-title"),
            html.P(f"${latest_close:,.2f}", className="card-text fs-3"),
        ]
    )
    high_card = dbc.CardBody(
        [
            html.H5("52-Week High", className="card-title"),
            html.P(f"${week_52_high:,.2f}", className="card-text fs-3"),
        ]
    )
    low_card = dbc.CardBody(
        [
            html.H5("52-Week Low", className="card-title"),
            html.P(f"${week_52_low:,.2f}", className="card-text fs-3"),
        ]
    )

    # 4. --- Data Table ---
    df_table = df_chart.copy()
    numeric_cols = ["Open", "High", "Low", "Close"]
    for col in numeric_cols:
        df_table[col] = df_table[col].round(2)

    table_data = df_table.to_dict("records")
    table_cols = [{"name": i, "id": i} for i in df_table.columns]

    # 5. --- Return Outputs ---
    return (
        candlestick_fig,
        price_fig,
        close_card,
        high_card,
        low_card,
        table_data,
        table_cols,
    )


# --- Run the App ---
if __name__ == "__main__":
    app.run(debug=True)
