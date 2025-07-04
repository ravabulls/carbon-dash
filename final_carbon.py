#Create a Virtual Environment (Optional but Recommended)
#python -m venv venv
#Activate it:venv\Scripts\activate.bat
#Install All Required Dependencies: pip install pandas plotly dash dash-bootstrap-components openpyxl
#In the same terminal:python final_carbon.py

import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State, dash_table, callback_context, no_update
import dash_bootstrap_components as dbc
import json

# Initialize the Dash app with Bootstrap for better styling
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server
# Load and Prepare the Data
df = pd.read_excel("carbontracedata31.xlsx")
df = df[df["Year"] != 2025]  # Filter out the year 2025

# If both a raw "Emissions" and an "Emissions in billions" column exist, drop the raw "Emissions"
if 'Emissions' in df.columns and 'Emissions in billions' in df.columns:
    df.drop('Emissions', axis=1, inplace=True)

# Clean and rename columns
if 'sector' in df.columns:
    df.drop(['sector', 'subsector'], axis=1, inplace=True)

df.rename(columns={
    "Sector (Capital)": "Sector",
    "Subsector(Capital)": "Subsector",
    "Emissions in billions": "Emissions"
}, inplace=True)

if 'co2e_100yr_emissions_quantity' in df.columns:
    df.drop('co2e_100yr_emissions_quantity', axis=1, inplace=True)

# Extract unique values for dropdown options
countries = sorted(df["Country"].unique())
years = sorted(df["Year"].unique())
sectors = sorted(df["Sector"].unique())
subsectors = sorted(df["Subsector"].unique())

country_options = [{"label": c, "value": c} for c in countries]
year_options = [{"label": str(y), "value": y} for y in years]
sector_options = [{"label": s, "value": s} for s in sectors]
subsector_options = [{"label": ss, "value": ss} for ss in subsectors]

# Define light color scheme
COLOR_SCHEME = {
    'map': 'Sunsetdark',   # teal, 
    'treemap': 'viridis',
    'bar': px.colors.qualitative.Bold,
    'line': '#2c7bb6',
    'background': '#f8f9fa',
    'card': '#ffffff'
}


# Dashboard Layout
app.layout = html.Div([
    # Header with title and reset button
    dbc.Row([
        dbc.Col(html.H1("Carbon Emissions Dashboard", className="text-left my-4"), width=8),
        dbc.Col([
            html.Button("Reset All Filters", id="reset-button", n_clicks=0, className="btn btn-secondary mt-4")
        ], width=4, className="text-end"),
    ], className="mb-4"),

    # Filter cards
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Country Filter"),
            dbc.CardBody(dcc.Dropdown(
                id="country-dropdown",
                options=country_options,
                placeholder="Select Country",
                multi=True
            ))
        ], className="shadow-sm"), width=3),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Year Filter"),
            dbc.CardBody(dcc.Dropdown(
                id="year-dropdown",
                options=year_options,
                placeholder="Select Year",
                multi=True
            ))
        ], className="shadow-sm"), width=3),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Sector Filter"),
            dbc.CardBody(dcc.Dropdown(
                id="sector-dropdown",
                options=sector_options,
                placeholder="Select Sector",
                multi=True
            ))
        ], className="shadow-sm"), width=3),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Subsector Filter"),
            dbc.CardBody(dcc.Dropdown(
                id="subsector-dropdown",
                options=subsector_options,
                placeholder="Select Subsector",
                multi=True
            ))
        ], className="shadow-sm"), width=3),
    ], className="mb-4"),

    # Summary cards
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Total Emissions (CO₂e)"),
            dbc.CardBody(html.H4(id="total-emissions", className="card-title"))
        ], className="shadow-sm"), width=4),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Number of Countries"),
            dbc.CardBody(html.H4(id="num-countries", className="card-title"))
        ], className="shadow-sm"), width=4),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Average Emissions per Country"),
            dbc.CardBody(html.H4(id="avg-emissions", className="card-title"))
        ], className="shadow-sm"), width=4),
    ], className="mb-4"),

    # Plots
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Global Emissions Distribution (Click countries to filter)"),
            dbc.CardBody(dcc.Graph(id="map-fig"))
        ], className="shadow-sm mb-4"), width=6),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Emissions by Sector and Subsector (Click to filter)"),
            dbc.CardBody(dcc.Graph(id="treemap-fig"))
        ], className="shadow-sm mb-4"), width=6),
    ]),

    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Top Emitting Countries (Click bars to filter)"),
            dbc.CardBody(dcc.Graph(id="bar-fig"))
        ], className="shadow-sm mb-4"), width=6),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Emissions Trend Over Time"),
            dbc.CardBody(dcc.Graph(id="line-fig"))
        ], className="shadow-sm mb-4"), width=6),
    ]),

    # Detailed data table
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Detailed Emissions Data"),
            dbc.CardBody(dash_table.DataTable(
                id="emissions-table",
                columns=[],
                data=[],
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "5px",
                    "whiteSpace": "normal",
                    "height": "auto",
                },
            ))
        ], className="shadow-sm"), width=12),
    ]),
], style={"backgroundColor": COLOR_SCHEME['background'], "padding": "20px"})

# Callback for map click to update country dropdown
@app.callback(
    Output("country-dropdown", "value"),
    [Input("map-fig", "clickData")],
    [State("country-dropdown", "value")],
    prevent_initial_call=True
)
def update_country_from_map(click_data, current_countries):
    if not click_data or not click_data.get('points'):
        return no_update
    
    try:
        clicked_country = click_data['points'][0]['location']
        if not clicked_country:
            return no_update
        
        # Initialize current_countries if None
        if current_countries is None:
            current_countries = []
        else:
            current_countries = list(current_countries)  # Make a copy
        
        # Toggle country selection
        if clicked_country in current_countries:
            current_countries.remove(clicked_country)
        else:
            current_countries.append(clicked_country)
        
        return current_countries
    except Exception as e:
        print(f"Error in map click: {e}")
        return no_update

# Callback for bar chart click to update country dropdown
@app.callback(
    Output("country-dropdown", "value", allow_duplicate=True),
    [Input("bar-fig", "clickData")],
    [State("country-dropdown", "value")],
    prevent_initial_call=True
)
def update_country_from_bar(click_data, current_countries):
    if not click_data or not click_data.get('points'):
        return no_update
    
    try:
        clicked_country = click_data['points'][0]['x']
        if not clicked_country:
            return no_update
        
        # Initialize current_countries if None
        if current_countries is None:
            current_countries = []
        else:
            current_countries = list(current_countries)  # Make a copy
        
        # Toggle country selection
        if clicked_country in current_countries:
            current_countries.remove(clicked_country)
        else:
            current_countries.append(clicked_country)
        
        return current_countries
    except Exception as e:
        print(f"Error in bar click: {e}")
        return no_update

# Callback for treemap click to update sector dropdown
@app.callback(
    Output("sector-dropdown", "value"),
    [Input("treemap-fig", "clickData")],
    [State("sector-dropdown", "value")],
    prevent_initial_call=True
)
def update_sector_from_treemap(click_data, current_sectors):
    if not click_data or not click_data.get('points'):
        return no_update
    
    try:
        clicked_point = click_data['points'][0]
        
        # Try to extract sector information from different possible fields
        sector = None
        
        # Method 1: Try to get from 'id' field (hierarchical treemap)
        if 'id' in clicked_point and clicked_point['id']:
            path_parts = str(clicked_point['id']).split('/')
            if path_parts:
                sector = path_parts[0]
        
        # Method 2: Try to get from 'label' field
        elif 'label' in clicked_point and clicked_point['label']:
            sector = clicked_point['label']
        
        # Method 3: Try to get from 'text' field
        elif 'text' in clicked_point and clicked_point['text']:
            sector = clicked_point['text']
        
        if not sector:
            return no_update
        
        # Initialize current_sectors if None
        if current_sectors is None:
            current_sectors = []
        else:
            current_sectors = list(current_sectors)  # Make a copy
        
        # Toggle sector selection
        if sector in current_sectors:
            current_sectors.remove(sector)
        else:
            current_sectors.append(sector)
        
        return current_sectors
    except Exception as e:
        print(f"Error in treemap click: {e}")
        return no_update

# Main callback for updating dashboard
@app.callback(
    [
        Output("total-emissions", "children"),
        Output("num-countries", "children"),
        Output("avg-emissions", "children"),
        Output("map-fig", "figure"),
        Output("treemap-fig", "figure"),
        Output("bar-fig", "figure"),
        Output("line-fig", "figure"),
        Output("emissions-table", "columns"),
        Output("emissions-table", "data"),
        Output("country-dropdown", "value", allow_duplicate=True),
        Output("year-dropdown", "value"),
        Output("sector-dropdown", "value", allow_duplicate=True),
        Output("subsector-dropdown", "value"),
    ],
    [
        Input("country-dropdown", "value"),
        Input("year-dropdown", "value"),
        Input("sector-dropdown", "value"),
        Input("subsector-dropdown", "value"),
        Input("reset-button", "n_clicks")
    ],
    prevent_initial_call='initial_duplicate'
)
def update_dashboard(selected_countries, selected_years, selected_sectors, selected_subsectors, reset_clicks):
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # If "Reset Filters" button clicked, clear all selections
    if triggered_id == "reset-button":
        selected_countries = []
        selected_years = []
        selected_sectors = []
        selected_subsectors = []

    dff = df.copy()

    # Apply filters if they exist
    if selected_countries:
        dff = dff[dff["Country"].isin(selected_countries)]
    if selected_years:
        dff = dff[dff["Year"].isin(selected_years)]
    if selected_sectors:
        dff = dff[dff["Sector"].isin(selected_sectors)]
    if selected_subsectors:
        dff = dff[dff["Subsector"].isin(selected_subsectors)]

    # Summary metrics
    total_emissions = dff["Emissions"].sum().round(3)
    num_countries = dff["Country"].nunique()
    avg_emissions = (total_emissions / num_countries).round(3) if num_countries > 0 else 0
    map_df = dff.groupby("Country")[["Emissions"]].sum().reset_index()
    # 1) Choropleth Map
    fig_map = px.choropleth(
        map_df,
        locations="Country",
        locationmode="country names",
        color="Emissions",
        hover_name="Country",
        hover_data={"Emissions": ":.3f"},
        color_continuous_scale=COLOR_SCHEME['map'],
        title="Click on countries to filter the dashboard"
    )
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    fig_map.update_traces(hovertemplate="<b>%{hovertext}</b><br>Emissions: %{z:.2f} Billion", hoverinfo="text")
    
    
    # 2) Treemap
    if not dff.empty:
        fig_treemap = px.treemap(
            dff,
            path=["Sector", "Subsector"],
            values="Emissions",
            color="Emissions",
            hover_data=["Country"],
            color_continuous_scale=COLOR_SCHEME['treemap'],
            title="Click on sectors to filter the dashboard"
        )
    else:
        # Empty treemap when no data
        fig_treemap = px.treemap(
            pd.DataFrame({'Sector': ['No Data'], 'Subsector': ['No Data'], 'Emissions': [0]}),
            path=["Sector", "Subsector"],
            values="Emissions",
            title="No data to display"
        )
    fig_treemap.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    fig_treemap.update_traces(hovertemplate="<b>%{label}</b><br>Emissions: %{value:.2f} Billion",hoverinfo="text")
    

 # 3) Bar Chart
    top_countries = map_df.nlargest(10, "Emissions")
    if not top_countries.empty:
        fig_bar = px.bar(
            top_countries,
            x="Country",
            y="Emissions",
            title="Click on bars to filter the dashboard",
            color="Emissions",
            color_continuous_scale=COLOR_SCHEME['bar'],)   
    
    # Highlight selected countries
        if selected_countries:
            colors = []
            for country in top_countries["Country"]:
                if country in selected_countries:
                    colors.append('red')
                else:
                    colors.append('lightblue')
            fig_bar.update_traces(marker_color=colors)
    
    # Custom hover template
        fig_bar.update_traces(
            hovertemplate="<b>%{x}</b><br>Emissions: %{y:.3f} Billion",
            hoverinfo="text"
        )
    
        fig_bar.update_layout(
            yaxis_title="Emissions (billion tons CO₂e)", 
            margin={"r":0,"t":40,"l":0,"b":0},
            xaxis_tickangle=-45
        )
    else:
    # Empty bar chart
        fig_bar = px.bar(title="No data to display")
        fig_bar.update_layout(margin={"r":0,"t":40,"l":0,"b":0})

# 4) Line Chart
    if selected_countries and len(selected_countries) == 1:
        country_name = selected_countries[0]
        trend_df = dff[dff["Country"] == country_name].groupby("Year")[["Emissions"]].sum().reset_index()
        fig_line = px.line(
            trend_df,
            x="Year",
            y="Emissions",
            title=f"Emissions Trend: {country_name}",
            markers=True
        )
    elif selected_countries and len(selected_countries) > 1:
        trend_df = dff[dff["Country"].isin(selected_countries)].groupby(["Year", "Country"])[["Emissions"]].sum().reset_index()
        fig_line = px.line(
            trend_df,
            x="Year",
            y="Emissions",
            color="Country",
            title="Emissions Trend: Selected Countries",
            markers=True
        )
    else:
        trend_df = dff.groupby("Year")[["Emissions"]].sum().reset_index()
        fig_line = px.line(
            trend_df,
            x="Year",
            y="Emissions",
            title="Global Emissions Trend",
            markers=True
        )
    
    fig_line.update_layout(
        yaxis_title="Emissions (billion tons CO₂e)", 
        xaxis=dict(tickmode='linear'), 
        margin={"r":0,"t":40,"l":0,"b":0}
    )

    # 5) Data Table
    table_columns = [
        {"name": "Country", "id": "Country"},
        {"name": "Year", "id": "Year"},
        {"name": "Sector", "id": "Sector"},
        {"name": "Subsector", "id": "Subsector"},
        {"name": "Emissions (billion tons CO₂e)", "id": "Emissions", "type": "numeric", "format": {"specifier": ".3f"}}
    ]
    
    # Sort table data by emissions in descending order
    if not dff.empty:
        table_data = dff[["Country", "Year", "Sector", "Subsector", "Emissions"]].sort_values("Emissions", ascending=False)
        table_data["Emissions"] = table_data["Emissions"].round(3)
        table_records = table_data.to_dict("records")
    else:
        table_records = []

    return (
        f"{total_emissions} billion tons CO₂e",
        num_countries,
        f"{avg_emissions} billion tons CO₂e",
        fig_map,
        fig_treemap,
        fig_bar,
        fig_line,
        table_columns,
        table_records,
        selected_countries,
        selected_years,
        selected_sectors,
        selected_subsectors
    )

# Run the app
if __name__ == "__main__":
    app.run(debug=True, port=8053)