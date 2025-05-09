import pytest
from dash.testing.application_runners import import_app
from dash.testing.browser import Browser
import pandas as pd
import numpy as np
import json
import base64
from io import BytesIO
import geopandas as gpd
from shapely.geometry import Polygon

# Import the app
app = import_app('map_dashboard')

def test_app_layout():
    """Test if the app layout is properly structured"""
    assert app.layout is not None
    assert len(app.layout.children) > 0

def test_data_generation():
    """Test if the sample data is generated correctly"""
    # Generate test data
    np.random.seed(42)
    num_points = 1000
    lat_center, lon_center = 37.7749, -122.4194
    
    lat = np.random.normal(lat_center, 0.5, num_points)
    lon = np.random.normal(lon_center, 0.5, num_points)
    temperature = np.random.normal(15, 5, num_points)
    population = np.random.randint(1000, 10000, num_points)
    rainfall = np.random.gamma(2, scale=10, size=num_points)
    
    df = pd.DataFrame({
        'latitude': lat,
        'longitude': lon,
        'temperature': temperature,
        'population': population,
        'rainfall': rainfall
    })
    
    # Test data properties
    assert len(df) == num_points
    assert all(col in df.columns for col in ['latitude', 'longitude', 'temperature', 'population', 'rainfall'])
    assert df['latitude'].mean() == pytest.approx(lat_center, abs=0.5)
    assert df['longitude'].mean() == pytest.approx(lon_center, abs=0.5)

def test_selection_callback():
    """Test the selection callback functionality"""
    # Create sample selection data
    selected_data = {
        'range': {
            'mapbox': [
                [-122.5, -122.4],  # longitude range
                [37.7, 37.8]       # latitude range
            ]
        }
    }
    
    # Test the callback
    from map_dashboard import store_selection
    result = store_selection(selected_data)
    assert result == selected_data

def test_stats_calculation():
    """Test the statistics calculation functionality"""
    # Create sample data
    df = pd.DataFrame({
        'latitude': [37.75, 37.76, 37.77],
        'longitude': [-122.45, -122.44, -122.43],
        'temperature': [15, 16, 17],
        'population': [1000, 2000, 3000],
        'rainfall': [10, 20, 30]
    })
    
    # Create sample selection
    selected_data = {
        'range': {
            'mapbox': [
                [-122.46, -122.42],  # longitude range
                [37.74, 37.78]       # latitude range
            ]
        }
    }
    
    # Test the callback
    from map_dashboard import calculate_stats
    result = calculate_stats(selected_data)
    assert result is not None
    assert len(result) > 0

def test_shapefile_processing():
    """Test the shapefile processing functionality"""
    # Create a sample shapefile
    polygon = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    gdf = gpd.GeoDataFrame(geometry=[polygon], crs='EPSG:4326')
    
    # Save to bytes
    buffer = BytesIO()
    gdf.to_file(buffer, driver='ESRI Shapefile')
    buffer.seek(0)
    
    # Create base64 encoded content
    content = base64.b64encode(buffer.getvalue()).decode()
    contents = f'data:application/x-shapefile;base64,{content}'
    
    # Test the callback
    from map_dashboard import process_shapefile
    result = process_shapefile(contents, 'test.shp')
    assert result is not None

def test_coordinate_input():
    """Test the coordinate input functionality"""
    # Test the callback with valid coordinates
    from map_dashboard import add_custom_point
    result = add_custom_point(1, 37.7749, -122.4194)
    assert result is not None
    
    # Test with invalid coordinates
    with pytest.raises(Exception):
        add_custom_point(1, None, None)

@pytest.mark.parametrize("test_input,expected", [
    ({"range": {"mapbox": [[-122.5, -122.4], [37.7, 37.8]]}}, True),
    (None, False),
    ({}, False)
])
def test_selection_validation(test_input, expected):
    """Test selection data validation"""
    from map_dashboard import store_selection
    if expected:
        result = store_selection(test_input)
        assert result == test_input
    else:
        with pytest.raises(Exception):
            store_selection(test_input)

if __name__ == '__main__':
    pytest.main(['-v', 'test_map_dashboard.py']) 