import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px
import pandas as pd
import numpy as np
from dash.exceptions import PreventUpdate
import geopandas as gpd
import json
from io import BytesIO
import base64
import os

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server  # This is important for Render

# Generate some sample data with lat/lon coordinates and sample metrics
np.random.seed(42)
num_points = 1000
lat_center, lon_center = 37.7749, -122.4194  # San Francisco coordinates

# Generate random points around the center
lat = np.random.normal(lat_center, 0.5, num_points)
lon = np.random.normal(lon_center, 0.5, num_points)

# Generate some sample metrics
temperature = np.random.normal(15, 5, num_points)  # in Celsius
population = np.random.randint(1000, 10000, num_points)
rainfall = np.random.gamma(2, scale=10, size=num_points)  # in mm

# Create a dataframe
df = pd.DataFrame({
    'latitude': lat,
    'longitude': lon,
    'temperature': temperature,
    'population': population,
    'rainfall': rainfall
})

# App layout
app.layout = html.Div([
    html.H1("Interactive Map Dashboard", style={'textAlign': 'center'}),
    
    # File Upload Section
    html.Div([
        html.H3("Upload Shapefile"),
        dcc.Upload(
            id='upload-shapefile',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select Shapefile')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            multiple=False
        ),
    ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '20px'}),
    
    # Coordinate Input Section
    html.Div([
        html.H3("Input Coordinates"),
        html.Div([
            html.Label("Latitude:"),
            dcc.Input(id='lat-input', type='number', placeholder='Enter latitude'),
            html.Label("Longitude:"),
            dcc.Input(id='lon-input', type='number', placeholder='Enter longitude'),
            html.Button('Add Point', id='add-point-button', n_clicks=0),
        ], style={'margin': '10px'})
    ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '20px'}),
    
    # Main Map Section
    html.Div([
        html.Div([
            dcc.Graph(
                id='map-graph',
                figure=px.scatter_mapbox(
                    df,
                    lat='latitude',
                    lon='longitude',
                    color='temperature',
                    size='population',
                    color_continuous_scale=px.colors.cyclical.IceFire,
                    size_max=15,
                    zoom=9,
                    mapbox_style='open-street-map',
                    hover_data=['temperature', 'population', 'rainfall']
                ),
                style={'height': '70vh'}
            ),
            html.P("Use Box Select tool in the map's menu to select a region", style={'textAlign': 'center'}),
        ], style={'width': '70%', 'display': 'inline-block', 'vertical-align': 'top'}),
        
        html.Div([
            html.H3("Region Statistics", style={'textAlign': 'center'}),
            html.Div(id='stats-container', children=[
                html.P("Select a region on the map to see statistics"),
                html.Div(id='selection-coordinates'),
                html.Div(id='selection-stats')
            ], style={'padding': '20px', 'backgroundColor': '#f2f2f2', 'borderRadius': '10px'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding-left': '20px'})
    ]),
    
    # Store selection data
    dcc.Store(id='selected-data')
])

# Callback to store selection data
@app.callback(
    Output('selected-data', 'data'),
    Input('map-graph', 'selectedData')
)
def store_selection(selectedData):
    if selectedData is None:
        raise PreventUpdate
    return selectedData

# Callback to display selection coordinates
@app.callback(
    Output('selection-coordinates', 'children'),
    Input('selected-data', 'data')
)
def display_selected_coordinates(selectedData):
    if selectedData is None:
        return html.P("No region selected")
    
    # Extract the bounding box coordinates if available
    if 'range' in selectedData:
        lon_range = selectedData['range']['mapbox'][0]
        lat_range = selectedData['range']['mapbox'][1]
        return [
            html.P("Selected Bounding Box:"),
            html.P(f"Longitude: {lon_range[0]:.4f} to {lon_range[1]:.4f}"),
            html.P(f"Latitude: {lat_range[0]:.4f} to {lat_range[1]:.4f}")
        ]
    else:
        return html.P("Please use Box Select tool")

# Callback to calculate and display statistics
@app.callback(
    Output('selection-stats', 'children'),
    Input('selected-data', 'data')
)
def calculate_stats(selectedData):
    if selectedData is None or 'range' not in selectedData:
        return html.P("No statistics available")
    
    # Extract bounding box coordinates
    lon_range = selectedData['range']['mapbox'][0]
    lat_range = selectedData['range']['mapbox'][1]
    
    # Filter data within the bounding box
    filtered_df = df[
        (df['longitude'] >= lon_range[0]) & 
        (df['longitude'] <= lon_range[1]) & 
        (df['latitude'] >= lat_range[0]) & 
        (df['latitude'] <= lat_range[1])
    ]
    
    # Check if any points are in the selection
    if len(filtered_df) == 0:
        return html.P("No data points in selected region")
    
    # Calculate statistics
    stats = [
        html.H4(f"Data Points: {len(filtered_df)}"),
        html.H4("Temperature (°C):"),
        html.Ul([
            html.Li(f"Average: {filtered_df['temperature'].mean():.2f}"),
            html.Li(f"Min: {filtered_df['temperature'].min():.2f}"),
            html.Li(f"Max: {filtered_df['temperature'].max():.2f}")
        ]),
        html.H4("Population:"),
        html.Ul([
            html.Li(f"Total: {filtered_df['population'].sum():,}"),
            html.Li(f"Average: {filtered_df['population'].mean():.2f}"),
            html.Li(f"Min: {filtered_df['population'].min():,}"),
            html.Li(f"Max: {filtered_df['population'].max():,}")
        ]),
        html.H4("Rainfall (mm):"),
        html.Ul([
            html.Li(f"Average: {filtered_df['rainfall'].mean():.2f}"),
            html.Li(f"Min: {filtered_df['rainfall'].min():.2f}"),
            html.Li(f"Max: {filtered_df['rainfall'].max():.2f}")
        ])
    ]
    
    return stats

# Add shapefile processing callback
@app.callback(
    Output('map-graph', 'figure'),
    Input('upload-shapefile', 'contents'),
    State('upload-shapefile', 'filename')
)
def process_shapefile(contents, filename):
    if contents is None:
        raise PreventUpdate
    
    # Decode the uploaded file
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    # Read the shapefile using geopandas
    gdf = gpd.read_file(BytesIO(decoded))
    
    # Convert to WGS84 if not already
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    
    # Create a new figure with the shapefile
    fig = px.scatter_mapbox(
        df,
        lat='latitude',
        lon='longitude',
        color='temperature',
        size='population',
        color_continuous_scale=px.colors.cyclical.IceFire,
        size_max=15,
        zoom=9,
        mapbox_style='open-street-map',
        hover_data=['temperature', 'population', 'rainfall']
    )
    
    # Add the shapefile boundaries to the map
    for idx, row in gdf.iterrows():
        if row.geometry.geom_type == 'Polygon':
            coords = list(row.geometry.exterior.coords)
            fig.add_trace(px.line_mapbox(
                lat=[coord[1] for coord in coords],
                lon=[coord[0] for coord in coords],
                mapbox_style='open-street-map'
            ).data[0])
    
    return fig

# Add coordinate input callback
@app.callback(
    Output('map-graph', 'figure', allow_duplicate=True),
    Input('add-point-button', 'n_clicks'),
    State('lat-input', 'value'),
    State('lon-input', 'value'),
    prevent_initial_call=True
)
def add_custom_point(n_clicks, lat, lon):
    if lat is None or lon is None:
        raise PreventUpdate
    
    # Create a new point
    new_point = pd.DataFrame({
        'latitude': [lat],
        'longitude': [lon],
        'temperature': [df['temperature'].mean()],
        'population': [df['population'].mean()],
        'rainfall': [df['rainfall'].mean()]
    })
    
    # Update the dataframe
    global df
    df = pd.concat([df, new_point], ignore_index=True)
    
    # Update the figure
    fig = px.scatter_mapbox(
        df,
        lat='latitude',
        lon='longitude',
        color='temperature',
        size='population',
        color_continuous_scale=px.colors.cyclical.IceFire,
        size_max=15,
        zoom=9,
        mapbox_style='open-street-map',
        hover_data=['temperature', 'population', 'rainfall']
    )
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8051)))