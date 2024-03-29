#!/usr/bin/env python3
# Copyright (c) 2023-2024 Berlin zaehlt Mobilitaet
# SPDX-License-Identifier: MIT

# @file    map.py
# @author  Michael Behrisch
# @date    2023-12-11

from dash import Dash, html, dcc, Output, Input
from dash_extensions.javascript import assign
import dash_leaflet as dl

from api import json_api
from common import GEO_JSON_NAME


# css for grayscale is loaded from separate file,
# see https://stackoverflow.com/questions/50844844/python-dash-custom-css
# and https://stackoverflow.com/questions/32684470/openstreetmap-grayscale-tiles

# geojson is loaded from file for performance reasons, could be transfered to pbf someday
# see https://www.dash-leaflet.com/components/vector_layers/geojson
deployed = __name__ != '__main__'
app = Dash(__name__, requests_pathname_prefix="/cgi-bin/map.cgi/" if deployed else None)
sep = '&nbsp;|&nbsp;'
attribution=(sep.join(['&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                       '<a href="https://telraam.net">Telraam</a>',
                       '<a href="https://www.berlin.de/sen/uvk/mobilitaet-und-verkehr/verkehrsplanung/radverkehr/weitere-radinfrastruktur/zaehlstellen-und-fahrradbarometer/">SenUMVK Berlin</a>',
                       '<a href="https://berlin-zaehlt.de">Berlin z&auml;hlt Mobilit&auml;t</a>']) + '<br/>' +
             sep.join(['<a href="https://dashboard.berlin-zaehlt.de">Dashboard</a>',
                       '<a href="https://github.com/DLR-TS/we-count">GitHub</a>',
                       '<a href="/csv">CSV data</a> under <a href="https://creativecommons.org/licenses/by/4.0/">CC-BY 4.0</a> and <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>']))

# Create drop down options.
dd_options = [{"value": c, "label": c} for c in ["active", "non-active"]]
dd_defaults = [o["value"] for o in dd_options]
# Create javascript function that filters on activity.
geojson_filter = assign("""
    function(feature, context) {
        if (feature.properties.cameras.length == 0) return false;
        const active = feature.properties.uptime === 0;
        return (active && context.hideout.includes('active')) || (!active && context.hideout.includes('non-active'));
    }""")
popup_telraam = assign("""
    function onEachFeature(feature, layer) {
        let popupContent = `<a href="https://telraam.net/home/location/${feature.properties.segment_id}">Telraam sensor on segment ${feature.properties.segment_id}</a>`;
        if (feature.properties.last_data_package) {
            popupContent += `<br/><a href="/csv/segments/bzm_telraam_${feature.properties.segment_id}.csv">CSV data for segment ${feature.properties.segment_id}</a>`;
        }
        layer.bindPopup(popupContent);
    }""")
popup_ecocounter = assign("""
    function onEachFeature(feature, layer) {
        let popupContent = `<a href="https://data.eco-counter.com/public2/?id=${feature.properties.segment_id}">Eco-counter on segment ${feature.properties.segment_id}</a>` +
                           `<br/><a href="/csv/segments/bzm_ecocounter_${feature.properties.segment_id}.csv">CSV data for segment ${feature.properties.segment_id}</a>`;
        layer.bindPopup(popupContent);
    }""")

app.layout = html.Div([
    dl.Map(children=[
        dl.TileLayer(className='bw', attribution=attribution),
        dl.GeoJSON(url=('/csv/' if deployed else 'assets/') + GEO_JSON_NAME,
                   filter=geojson_filter, hideout=dd_defaults, id="telraam",
                   onEachFeature=popup_telraam),
        dl.GeoJSON(url=('/csv/' if deployed else 'assets/') + 'bzm_ecocounter_segments.geojson',
                   id="ecocounter",
                   onEachFeature=popup_ecocounter)
    ], style={'height': '80vh'}, center=(52.5, 13.55), zoom=11),
    dcc.Dropdown(id="dd", value=dd_defaults, options=dd_options, clearable=False, multi=True)
])
# Link drop down to geojson hideout prop (could be done with a normal callback, but clientside is more performant).
app.clientside_callback("function(x){return x;}", Output("telraam", "hideout"), Input("dd", "value"))

app.server.register_blueprint(json_api)

if __name__ == '__main__':
    app.run_server(debug=True)
