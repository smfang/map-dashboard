import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import numpy as np
from dash.exceptions import PreventUpdate
import geopandas as gpd
import json
from io import BytesIO
import base64
import os
from netcdf_handler import NetCDFProcessor

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# App layout
app.layout = html.Div([
    html.H1("Spatial Analysis Dashboard", style={'textAlign': 'center'}),
    
    # Configuration Section
    html.Div([
        html.H3("Configuration"),
        html.Div(id='config-variable-selector'),
        html.Div(id='dataset-stats', style={'marginTop': '20px', 'backgroundColor': '#e6f7ff', 'padding': '10px', 'borderRadius': '8px'}),
        html.Div(id='data-table-preview', style={'marginTop': '20px'})
    ], style={'width': '100%', 'padding': '10px', 'marginBottom': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '10px'}),

    # File Upload Section
    html.Div([
        html.H3("Upload NetCDF File"),
        dcc.Upload(
            id='upload-netcdf',
            children=html.Div([
                'Drag and Drop or ',
                html.A('Select NetCDF File')
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
        html.Div(id='variable-selector'),
    ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top', 'padding': '20px'}),
    
    # Main Map Section
    html.Div([
        html.Div([
            dcc.Graph(
                id='map-graph',
                figure=px.scatter_mapbox(
                    lat=[0],
                    lon=[0],
                    mapbox_style='open-street-map',
                    zoom=1
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
    
    # Store selection data and NetCDF processor
    dcc.Store(id='selected-data'),
    dcc.Store(id='netcdf-processor')
])

# Callback to handle NetCDF file upload and update config variable selector
@app.callback(
    [Output('variable-selector', 'children'),
     Output('netcdf-processor', 'data'),
     Output('config-variable-selector', 'children'),
     Output('dataset-stats', 'children')],
    Input('upload-netcdf', 'contents'),
    State('upload-netcdf', 'filename')
)
def process_netcdf(contents, filename):
    print("process_netcdf callback triggered")
    if contents is None:
        print("No contents received in upload.")
        raise PreventUpdate
    try:
        print(f"Received file: {filename}")
        # Decode the uploaded file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        # Save the file temporarily
        temp_path = f"temp_{filename}"
        with open(temp_path, 'wb') as f:
            f.write(decoded)
        print(f"File saved to {temp_path}")
        # Initialize NetCDF processor
        processor = NetCDFProcessor(temp_path)
        variables = processor.get_variable_info()
        print(f"Extracted variables: {variables}")
        # Create variable selector dropdown (for both config and main)
        variable_selector = html.Div([
            html.Label("Select Variable:"),
            dcc.Dropdown(
                id='variable-dropdown',
                options=[{'label': f"{v['long_name']} ({v['units']})", 'value': k} 
                        for k, v in variables.items()],
                value=list(variables.keys())[0] if variables else None
            )
        ])
        # For config section (same dropdown, but with a different id for demonstration)
        config_variable_selector = html.Div([
            html.Label("Select Variable for Display:"),
            dcc.Dropdown(
                id='config-variable-dropdown',
                options=[{'label': f"{v['long_name']} ({v['units']})", 'value': k} 
                        for k, v in variables.items()],
                value=list(variables.keys())[0] if variables else None
            )
        ])
        # Compute dataset-wide stats for the first variable (default)
        dataset_stats = None
        if variables:
            first_var = list(variables.keys())[0]
            data = processor.dataset.variables[first_var][:]
            dataset_stats = html.Div([
                html.H4(f"Dataset Statistics for {variables[first_var]['long_name']} ({variables[first_var]['units']})"),
                html.Ul([
                    html.Li(f"Average: {np.nanmean(data):.2f}"),
                    html.Li(f"Min: {np.nanmin(data):.2f}"),
                    html.Li(f"Max: {np.nanmax(data):.2f}"),
                    html.Li(f"Std Dev: {np.nanstd(data):.2f}"),
                    html.Li(f"Count: {data.size}")
                ])
            ])
        processor.close()
        # Store processor info
        processor_info = {
            'path': temp_path,
            'variables': variables
        }
        print("Returning from process_netcdf callback.")
        return variable_selector, processor_info, config_variable_selector, dataset_stats
    except Exception as e:
        print(f"Exception in process_netcdf: {e}")
        return html.P(f"Error: {e}"), None, None, None

# Callback to update dataset statistics when variable is changed in config section
@app.callback(
    Output('dataset-stats', 'children'),
    [Input('config-variable-dropdown', 'value')],
    State('netcdf-processor', 'data')
)
def update_dataset_stats(variable_name, processor_info):
    if variable_name is None or processor_info is None:
        return html.P("No statistics available")
    processor = NetCDFProcessor(processor_info['path'])
    variables = processor.get_variable_info()
    if variable_name not in variables:
        processor.close()
        return html.P("Variable not found in file")
    data = processor.dataset.variables[variable_name][:]
    stats = html.Div([
        html.H4(f"Dataset Statistics for {variables[variable_name]['long_name']} ({variables[variable_name]['units']})"),
        html.Ul([
            html.Li(f"Average: {np.nanmean(data):.2f}"),
            html.Li(f"Min: {np.nanmin(data):.2f}"),
            html.Li(f"Max: {np.nanmax(data):.2f}"),
            html.Li(f"Std Dev: {np.nanstd(data):.2f}"),
            html.Li(f"Count: {data.size}")
        ])
    ])
    processor.close()
    return stats

# Callback to update map based on selected region
@app.callback(
    Output('map-graph', 'figure'),
    [Input('selected-data', 'data'),
     Input('variable-dropdown', 'value')],
    State('netcdf-processor', 'data')
)
def update_map(selected_data, variable_name, processor_info):
    if selected_data is None or variable_name is None or processor_info is None:
        raise PreventUpdate
    
    # Extract bounding box coordinates
    lon_range = selected_data['range']['mapbox'][0]
    lat_range = selected_data['range']['mapbox'][1]
    
    # Get data subset
    processor = NetCDFProcessor(processor_info['path'])
    subset = processor.get_spatial_subset(
        variable_name,
        lat_range[0], lat_range[1],
        lon_range[0], lon_range[1]
    )
    
    # Create figure
    fig = px.scatter_mapbox(
        lat=subset['lats'].flatten(),
        lon=subset['lons'].flatten(),
        color=subset['data'].flatten(),
        color_continuous_scale=px.colors.cyclical.IceFire,
        mapbox_style='open-street-map',
        zoom=9,
        title=f"{subset['variable_name']} ({subset['units']})"
    )
    
    processor.close()
    return fig

# Callback to display selection coordinates
@app.callback(
    Output('selection-coordinates', 'children'),
    Input('selected-data', 'data')
)
def display_selected_coordinates(selectedData):
    if selectedData is None:
        return html.P("No region selected")
    
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
    [Input('selected-data', 'data'),
     Input('variable-dropdown', 'value')],
    State('netcdf-processor', 'data')
)
def calculate_stats(selectedData, variable_name, processor_info):
    if selectedData is None or variable_name is None or processor_info is None:
        return html.P("No statistics available")
    
    if 'range' not in selectedData:
        return html.P("Please use Box Select tool")
    
    # Extract bounding box coordinates
    lon_range = selectedData['range']['mapbox'][0]
    lat_range = selectedData['range']['mapbox'][1]
    
    # Get data subset
    processor = NetCDFProcessor(processor_info['path'])
    subset = processor.get_spatial_subset(
        variable_name,
        lat_range[0], lat_range[1],
        lon_range[0], lon_range[1]
    )
    
    data = subset['data']
    stats = [
        html.H4(f"Data Points: {data.size}"),
        html.H4(f"{subset['variable_name']} ({subset['units']}):"),
        html.Ul([
            html.Li(f"Average: {np.nanmean(data):.2f}"),
            html.Li(f"Min: {np.nanmin(data):.2f}"),
            html.Li(f"Max: {np.nanmax(data):.2f}"),
            html.Li(f"Std Dev: {np.nanstd(data):.2f}")
        ])
    ]
    
    processor.close()
    return stats

# Callback to update data table preview when variable or file changes
@app.callback(
    Output('data-table-preview', 'children'),
    [Input('config-variable-dropdown', 'value')],
    State('netcdf-processor', 'data')
)
def update_data_table_preview(variable_name, processor_info):
    if variable_name is None or processor_info is None:
        return html.P("No data preview available")
    processor = NetCDFProcessor(processor_info['path'])
    variables = processor.get_variable_info()
    if variable_name not in variables:
        processor.close()
        return html.P("Variable not found in file")
    data = processor.dataset.variables[variable_name][:]
    # Only show up to 10x10 for preview
    preview = data[:10, :10] if data.ndim == 2 else data[:10]
    processor.close()
    # Convert to DataFrame for display
    if preview.ndim == 2:
        df = pd.DataFrame(preview)
    else:
        df = pd.DataFrame(preview, columns=[variables[variable_name]['long_name']])
    return dash_table.DataTable(
        data=df.round(2).to_dict('records'),
        columns=[{"name": str(i), "id": str(i)} for i in df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center', 'minWidth': '60px', 'maxWidth': '100px'},
        page_size=10
    )

# Run the app
if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8051)))