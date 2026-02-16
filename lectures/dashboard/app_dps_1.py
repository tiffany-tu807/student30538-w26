import os
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import streamlit as st

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(SCRIPT_DIR, "dps_data")
RAIL_GEOJSON = f"{INPUT_DIR}/CTA_-_'L'_(Rail)_Lines_20250924.geojson"
BUS_GEOJSON = f"{INPUT_DIR}/CTA_-_Bus_Routes_20250924.geojson"

COLOR_ROUTES = ["Brown", "Orange", "Purple", "Pink", "Yellow", "Green", "Red", "Blue"]


def load_routes() -> gpd.GeoDataFrame:
    rail_raw = gpd.read_file(RAIL_GEOJSON)
    bus = gpd.read_file(BUS_GEOJSON)

    rail_raw["lines"] = rail_raw["lines"].astype(str)
    rail_raw["route_list"] = rail_raw["lines"].apply(
        lambda s: [c for c in COLOR_ROUTES if c.lower() in s.lower()]
    )

    rail_long = rail_raw[rail_raw["route_list"].map(len) > 0].explode("route_list")
    rail_long["route"] = rail_long["route_list"].astype(str)
    rail = (
        rail_long[["route", "geometry"]]
        .dissolve(by="route")
        .reset_index()
        .pipe(lambda df: gpd.GeoDataFrame(df, geometry="geometry", crs=rail_raw.crs))
    )

    rail["mode"] = "L"
    bus["mode"] = "Bus"
    lines = pd.concat([rail, bus], ignore_index=True)
    lines["route"] = lines["route"].astype(str)
    return lines


def render_map(gdf: gpd.GeoDataFrame) -> None:
    view_state = pdk.ViewState(latitude=41.8781, longitude=-87.6298, zoom=10)  
    layer = pdk.Layer(
        "GeoJsonLayer",
        data=gdf,
        pickable=True,
        auto_highlight=True,
        get_line_color=[0, 100, 200, 180],
        get_line_width=3,
        line_width_units="pixels",
        line_cap_rounded=True,
        line_joint_rounded=True,
    )

    tooltip = {
        "html": "<b>Route:</b> {route}<br/><b>Mode:</b> {mode}",
        "style": {"backgroundColor": "white", "color": "black"},
    }
    st.pydeck_chart(
        pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip),
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="CTA Routes Map", layout="wide")
    st.title("CTA Routes Map")

    gdf = load_routes()

    mode_options = ["Bus", "L"]

    st.sidebar.header("Select mode")
    st.sidebar.write("Put a slider here with options for Bus, L, or Both to show on the map")

    #comment the line below out and replace it with a multiselect widget to allow users to choose whether to show Bus, L, or Both modes
    selected_modes = mode_options

    if selected_modes:
        gdf = gdf[gdf["mode"].isin(selected_modes)].copy()
    else:
        gdf = gdf.iloc[0:0].copy()
        
    render_map(gdf)


if __name__ == "__main__":
    main()
