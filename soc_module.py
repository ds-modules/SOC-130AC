import pandas as pd
import os
import folium
import geojson
import random
import numpy as np
from sklearn import preprocessing
import re
from geopy.geocoders import Nominatim
import time

import certifi
import ssl
import geopy.geocoders
# ctx = ssl.create_default_context(cafile=certifi.where())
# geopy.geocoders.options.default_ssl_context = ctx

def html_popup(title, comment, imgpath, data):
    """Format the image data into html.

    :params title, comment, imgpath, data: strings"""
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
    """Clean up census tract names.

    :param t: Series of string tract names
    :returns: Series of cleaned tract names
    """
    if type(t) == str:
        return t
    return str(t).rstrip("0").rstrip(".")

def get_coords(data, alameda, user_agent):
    """Get the geographical coordinates (latitude and longitude) of a
    list of street addresses.

    :param data: DataFrame with student responses from Google form
    :param alameda: GeoJSON data for Alameda county
    :user_agent: string user agent for OpenStreetMap
    :returns: "data" dataframe with appended column of coordinates
    """
    tracts = folium.features.GeoJson(alameda)
    tract_centroids = get_centroids(alameda)

    data['Census Tract'] = data['Census Tract'].apply(fix_tract)

    for j in np.arange(1, 6):
        image_coords = []
        for i, row in data.iterrows():
            tract = row['Census Tract']

            if not pd.isnull(row['Full Address of Block Face in Image #' + str(j) + ' (Street Number, Street Name, City, State, Zip Code). E.g.: 2128 Oxford Street, Berkeley, CA, 94704.']):
                address = row['Full Address of Block Face in Image #' + str(j) + ' (Street Number, Street Name, City, State, Zip Code). E.g.: 2128 Oxford Street, Berkeley, CA, 94704.']


                geocoder = Nominatim(user_agent=user_agent, timeout=3)
                loc = geocoder.geocode(address)

                if loc is None :
                    if len(tract) == 3:
                        tract += "0"
                    coords = tract_centroids[tract]
                else:
                    coords = [loc.latitude, loc.longitude]

                image_coords.append(coords)
            elif not pd.isnull(row['Image #' + str(j)]):
                image_coords.append(tract_centroids[tract])
            else:
                image_coords.append('NaN')
            time.sleep(0.5)
        data['Image #' + str(j)+ ' coordinates'] = image_coords
    return data


def get_centroids(geojson):
    """Get census tract centroids.

    :param geojson: a GeoJSON file with census tract location data
    :returns: a dictionary with tract names mapped to coordinate tuples"""
    tract_centroids = {}

    for t in geojson['features']:
        lat = t['properties']['intptlat10']
        lon = t['properties']['intptlon10']
        name = t['properties']['name10']
        tract_centroids[name] = (float(lat), float(lon))

    return tract_centroids

def map_data(myMap, alameda, obs_data):
    """Map student observations.

    :param myMap: Folium Map object
    :param alameda: GeoJSON of alameda county census tracts
    :param obs_data: DataFrame image addresses and coordinates
    :returns: Folium Map object with markers for student data
    """
    # add tract outlines
    tracts = folium.features.GeoJson(alameda)
    tract_centroids = get_centroids(alameda)
    myMap.add_child(tracts)
    
    # transfer Table to pandas
    obs_data = obs_data.to_df()

    for t in list(set(set(obs_data['Census Tract']))):
        subset = obs_data[obs_data['Census Tract'] == t]
        markers = []
        popups = []

        for i, row in subset.iterrows():
            for j in np.arange(1, 6):
                if not pd.isnull(row['Image #' + str(j)]):
                    try:
                        image_url = row['Image #' + str(j)].replace(
                            "open?", "uc?export=download&")
                    except:
                        image_url = "NA"

                    coords = [float(coords) for coords in re.findall('-?[0-9]+.[0-9]+', row['Image #' + str(j) + ' coordinates'])]
                    
                    # if there aren't coords of format [lat, lon] the loop skips this iteration
                    if len(coords) != 2:
                        continue
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
                    
                    popup = folium.Popup(
                        folium.IFrame(
                            html=html,
                            width=200,
                            height=300),
                        max_width=2650
                    )
                    
                    markers += [coords]
                    popups += [popup]
                    
        marker_cluster = folium.plugins.MarkerCluster(locations=markers, popups=popups).add_to(myMap)
    
    return myMap

def minmax_scale(x):
    """Scales values in array to range (0, 1)
    
    :param x: array of values to scale
    """
    if min(x) == max(x):
        return x * 0
    return (x - min(x)) / (max(x) - min(x))

def scale_values(tbl, columns):
    """Scale values in a dataframe using MinMax scaling.

    :param tbl: Table
    :param columns: iterable with names of columns to be scaled
    :returns: Table with scaled columns
    """
    new_tbl = tbl.copy()
    for col in columns:
        name = new_tbl.labels[col]
        x_scaled = minmax_scale(new_tbl[name])
        new_tbl[name] = x_scaled
        
    return new_tbl

# NO LONGER USED as of Fall 2018
def choropleth_overlay(mapa, column_name, joined, alameda):
    """Add a choropleth overlay to a map.

    :param mapa: Folium Map object
    :param column_name:  string column name with data to overlay
    :param joined:
    :param alameda: GeoJSON Alameda county census tract data
    :returns: mapa with a chloropleth overlay
    """
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
