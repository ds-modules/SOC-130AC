import pandas as pd
import os
import folium
import geojson
import random
import numpy as np
from sklearn import preprocessing
import re

def html_popup(title, comment, imgpath, data):
    html = """
    <h3>TITLE</h3>
    <img
       src = IMGPATH
       style="width:180px;height:128px;"
       >
    <p>
       "COMMENT"
    </p>
    <p>
       DATA
    </p>
    """

    html = html.replace(
        "TITLE",
        title).replace(
        "COMMENT",
        comment).replace(
            "IMGPATH",
            imgpath).replace(
                "DATA",
        data)

    return html


def fix_tract(t):
    return str(t).rstrip("0").rstrip(".")

def get_coords(data, alameda):
    tracts = folium.features.GeoJson(alameda)
    tract_centroids = get_centroids(alameda)
    
    for j in np.arange(1, 6):
        image_coords = []
        for i, row in data.iterrows():
            tract = str(row['Census Tract'])

            if not pd.isnull(row['Full Address of Block Face in Image #' + str(j) + ' (Street Number, Street Name, City, State, Zip Code). E.g.: 2128 Oxford Street, Berkeley, CA, 94704.']):
                address = row['Full Address of Block Face in Image #' + str(j) + ' (Street Number, Street Name, City, State, Zip Code). E.g.: 2128 Oxford Street, Berkeley, CA, 94704.']
                

                loc = geolocator.geocode(address)

                if loc is None :
                    coords = tract_centroids[tract]
                else:
                    coords = [loc.latitude, loc.longitude]
                
                image_coords.append(coords)
            elif not pd.isnull(row['Image #' + str(j)]):
                image_coords.append(tract_centroids[tract])
            else:
                image_coords.append('NaN')
        data['Image #' + str(j)+ ' coordinates'] = image_coords
    return data
        

def get_centroids(geojson):
    tract_centroids = {}

    for t in geojson['features']:
        lat = t['properties']['intptlat10']
        lon = t['properties']['intptlon10']
        name = t['properties']['name10']
        tract_centroids[name] = (float(lat), float(lon))

    return tract_centroids

def map_data(myMap, alameda, obs_data):
    # add tract outlines
    tracts = folium.features.GeoJson(alameda)
    tract_centroids = get_centroids(alameda)
    myMap.add_child(tracts)

    
    for t in list(set(set(obs_data['Census Tract']))):
        marker_cluster = folium.plugins.MarkerCluster().add_to(myMap)
        subset = obs_data[obs_data['Census Tract'] == t]
        
        for i, row in subset.iterrows():
            for j in np.arange(1, 6):
                if not pd.isnull(row['Image #' + str(j)]):
                    try:
                        image_url = row['Image #' + str(j)].replace(
                            "open?", "uc?export=download&")
                    except:
                        image_url = "NA"

                    coords = [float(coords) for coords in re.findall('-?[0-9]+.[0-9]+', row['Image #' + str(j) + ' coordinates'])] 
                    tract = str(row['Census Tract'])

                    comment = row["Other thoughts or comments for Image #" + str(j)]
                    if not isinstance(comment, str):
                        comment = "NA"
                    data = np.mean([row[i] for i in range(5, 14)
                                    if type(row[i]) in [int, float]])
                    html = html_popup(
                        title="Tract: " + tract,
                        comment=comment,
                        imgpath=image_url,
                        data="")
                    folium.Marker(
                        coords,
                        popup=folium.Popup(
                            folium.IFrame(
                                html=html,
                                width=200,
                                height=300),
                            max_width=2650)).add_to(marker_cluster)
    return myMap


def choropleth_overlay(mapa, column_name, joined, alameda):
    # add tract outlines
    tracts = folium.features.GeoJson(alameda)
    tract_centroids = get_centroids(alameda)
    mapa.add_child(tracts)

    threshold_scale = np.linspace(
        joined[column_name].min(),
        joined[column_name].max(),
        6,
        dtype=float).tolist()

    mapa = folium.Map(location=(37.8044, -122.2711), zoom_start=11)

    mapa.choropleth(geo_data=alameda,
                    data=joined,
                    columns=['Census Tract', column_name],
                    fill_color='YlOrRd',
                    key_on='feature.properties.name10',
                    threshold_scale=threshold_scale)

    return mapa


def scale_values(df, columns):
    for c in columns:
        name = df.columns[c]
        x = df.iloc[:, [c]].values  # returns a numpy array
        min_max_scaler = preprocessing.MinMaxScaler()
        x_scaled = min_max_scaler.fit_transform(x)
        df[name] = x_scaled
    return df