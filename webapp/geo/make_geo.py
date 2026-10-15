"""
make_geo.py — builds the simplified India boundary files used by the web maps.

Sources (WGS84 GeoJSON):
  states    github.com/datta07/INDIAN-SHAPEFILES (current boundaries)
  districts github.com/geohacker/india (GADM level 2; district names of the
            dataset's era, e.g. Gulbarga, Bijapur, so they match the crop record)
Boundaries are simplified (shapely) and coordinates rounded so the files stay small,
and state names are rewritten to match the crop dataset.

Run once:  python webapp/geo/make_geo.py
"""
import json
import urllib.request
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient

HERE = Path(__file__).resolve().parent
STATES_URL = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/INDIA/INDIA_STATES.geojson"
DISTRICTS_URL = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
STATE_FIX = {
    "Andaman & Nicobar": "Andaman and Nicobar Islands", "Dadra & Nagar Haveli": "Dadra and Nagar Haveli",
    "Daman & Diu": "Daman and Diu", "Jammu & Kashmir": "Jammu and Kashmir", "Ladakh": "Laddakh",
    "Andaman and Nicobar": "Andaman and Nicobar Islands", "Orissa": "Odisha", "Uttaranchal": "Uttarakhand",
    "Pondicherry": "Puducherry",
}


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def clockwise(g):
    """Plotly's map renderer (d3-geo) needs clockwise outer rings, otherwise it fills the rest of the globe."""
    if isinstance(g, Polygon):
        return orient(g, sign=-1.0)
    if isinstance(g, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in g.geoms])
    return g


def rounded(geom, nd=3):
    def rnd(c):
        return [rnd(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], nd), round(c[1], nd)]
    g = mapping(geom)
    return {"type": g["type"], "coordinates": rnd(g["coordinates"])}


def simplify(features, tol, props, keys=()):
    out = []
    for f in features:
        if not all(f["properties"].get(k) for k in keys):
            continue
        g = clockwise(shape(f["geometry"]).simplify(tol, preserve_topology=True))
        if not g.is_empty:
            out.append({"type": "Feature", "id": props(f["properties"])["name"], "properties": props(f["properties"]),
                        "geometry": rounded(g)})
    return {"type": "FeatureCollection", "features": out}


def state_name(raw):
    s = raw.title() if raw.isupper() else raw
    return STATE_FIX.get(s, s)


if __name__ == "__main__":
    states = simplify(fetch(STATES_URL)["features"], 0.02,
                      lambda p: {"name": state_name(p["STNAME_SH"])})
    districts = simplify(fetch(DISTRICTS_URL)["features"], 0.008,
                         lambda p: {"name": f"{p['NAME_2']}|{p['NAME_1']}", "district": p["NAME_2"],
                                    "state": state_name(p["NAME_1"])},
                         keys=("NAME_1", "NAME_2"))
    (HERE.parent / "static" / "india_states.json").write_text(json.dumps(states, separators=(",", ":")))
    (HERE / "india_districts.json").write_text(json.dumps(districts, separators=(",", ":")))
    print(len(states["features"]), "states,", len(districts["features"]), "districts")
