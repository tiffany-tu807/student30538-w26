import streamlit as st
import geopandas as gpd
import pydeck as pdk
import pandas as pd
from urllib.error import URLError


st.set_page_config(page_title="World Map", layout="wide")
st.title("World Map")
st.caption("World boundaries from Natural Earth via GeoPandas.")


st.write(
    """
    This demo shows how to select a year of data, print it to a table, and plot it on a map.
"""
)

@st.cache_data
def get_UN_data():
    AWS_BUCKET_URL = "http://streamlit-demo-data.s3-us-west-2.amazonaws.com"
    df = pd.read_csv(AWS_BUCKET_URL + "/agri.csv.gz")
    return df.set_index("Region")

try:
    df = get_UN_data()
    selected_year = st.slider(
        "Select year",
        min_value=1961,
        max_value=2007,
        value=2007,
    )
    data = df
    data /= 1000000.0
    data = data.sort_values(by=str(selected_year), ascending=False)
    annual = (
        data[str(selected_year)]
        .rename(f"{selected_year} production ($B)")
        .to_frame()
    )

    st.write("### Gross Agricultural Production ($B)", annual)

    world = gpd.read_file(
        "ne_110m_admin_0_countries/ne_110m_admin_0_countries.shp"
    ).to_crs(epsg=4326)

    name_candidates = ["NAME_LONG", "NAME", "ADMIN", "name"]
    name_column = next((col for col in name_candidates if col in world.columns), None)

    if name_column is None:
        st.error("Could not find a country name column in the shapefile.")
    else:
        year_series = (df[str(selected_year)] / 1_000_000.0)
        world_with_data = world.merge(
            year_series.rename("production"),
            left_on=name_column,
            right_index=True,
            how="left",
        )
        world_with_data["display_name"] = world_with_data[name_column]
        world_with_data["production_text"] = world_with_data["production"].map(
            lambda x: f"{x:.2f} B" if pd.notna(x) else "No data"
        )

        centroids = world_with_data.copy()
        centroids["lon"] = centroids.geometry.centroid.x
        centroids["lat"] = centroids.geometry.centroid.y

        min_prod = year_series.min()
        max_prod = year_series.max()
        range_span = (
            max_prod - min_prod if pd.notna(min_prod) and pd.notna(max_prod) else None
        )

        def production_to_color(value):
            if pd.isna(value) or range_span in (None, 0):
                return [200, 200, 200, 80]
            norm = (value - min_prod) / range_span
            norm = max(0.0, min(1.0, norm))
            base = 30
            blue = int(136 + 100 * norm)
            green = int(100 + 100 * norm)
            return [base, min(green, 255), min(blue, 255), 200]

        world_with_data["color"] = world_with_data["production"].apply(
            production_to_color
        )

        layers = [
            pdk.Layer(
                "GeoJsonLayer",
                data=world_with_data,
                get_fill_color="color",
                stroked=True,
                get_line_color=[255, 255, 255],
                line_width_min_pixels=1,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=centroids.dropna(subset=["lon", "lat"]),
                get_position="[lon, lat]",
                get_text="display_name",
                get_size=12,
                get_color=[255, 255, 255],
                get_angle=0,
                get_alignment_baseline="'bottom'",
            ),
        ]

        tooltip = {
            "html": "<b>{display_name}</b><br/>Production: {production_text}",
            "style": {"backgroundColor": "#1f2d3d", "color": "white"},
        }

        view_state = pdk.ViewState(
            latitude=0, longitude=0, zoom=1, max_zoom=5, pitch=0, bearing=0
        )

        deck = pdk.Deck(
            map_style=None,
            initial_view_state=view_state,
            layers=layers,
            tooltip=tooltip,
        )

        st.pydeck_chart(deck)

except URLError as e:
    st.error(
        """
        **This demo requires internet access.**

        Connection error: %s
    """
        % e.reason
    )
