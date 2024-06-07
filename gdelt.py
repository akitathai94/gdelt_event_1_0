import datetime as dt
import csv
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
import requests
import zipfile
import os

import folium
from streamlit_folium import folium_static

GDELT_DATA_EVENT_1_0_URL = "http://data.gdeltproject.org/events/"
FILENAME = ".export.CSV.zip"

# Title of the app
st.set_page_config(layout="wide")
st.title('GDELT Event 1.0 Query')

# Columns format
# col1, col2 = st.columns([0.3, 0.7])

# Start from 20130401 until today - 1 if it passes 6AM EST, otherwise today - 2
start = dt.datetime.strptime("20130401", "%Y%m%d")
yesterday = dt.datetime.now() - dt.timedelta(days=1)

yesterday_formatted_now = yesterday.strftime("%Y%m%d")
end = dt.datetime.strptime(yesterday_formatted_now, "%Y%m%d")

date_generated = [
    start + dt.timedelta(days=x) for x in range((end-start).days, 0, -1)]


def read_csv_into_df(file_name, csv_header_filename, url):

    # check if you have the file already so not download again
    # Get the current working directory
    current_directory = os.getcwd()
    zip_file_path = os.path.join(current_directory, file_name)
    if not os.path.exists(zip_file_path):
        # Send an HTTP GET request to the URL
        with st.status("Processing data...", expanded=True) as status:

            st.write("Downloading data...")
            try:
                response = requests.get(url, stream=True, timeout=5.0)
            except requests.Timeout:
                st.write('Dataset not available !!!')
            with open(file_name, "wb") as f:
                for chunk in response.iter_content(chunk_size=512):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

            st.write("Unzip data...")
            # Open the ZIP file
            with zipfile.ZipFile(file_name, 'r') as zip_ref:
                # Extract all the contents to the specified directory
                print(f"Filename in zipfile: {file_name}")
                zip_ref.extractall(current_directory)

            status.update(label="Process complete!",
                          state="complete", expanded=False)
    # read csv header
    header_names = []
    with open(csv_header_filename, newline='', encoding='utf-8') as csvfile:
        header_obj = csv.reader(csvfile, delimiter='\t')
        for col in header_obj:
            header_names.append(col)
    # print(header_names[0])

    # read dataframe
    df = pd.read_csv(file_name[:-4], sep="\t",
                     names=header_names[0], low_memory=False)

    # load data to sessions
    if 'df' not in st.session_state:
        st.session_state.df = df
        # st.session_state.filtered_df = df

    # Configure the grid options
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(
        paginationAutoPageSize=True)  # Enable pagination
    gb.configure_side_bar()  # Add a sidebar
    gb.configure_selection('single')  # Enable single row selection
    gb.configure_default_column(editable=True)  # Make columns editable

    # Build grid options
    gridOptions = gb.build()

    AgGrid(st.session_state.df, gridOptions=gridOptions)
    display_geo_data(df)


def display_geo_data(locations):
    # Drop row that has empty data in lat and long
    cleared_locations = locations.dropna(
        subset=["ActionGeo_Lat", "ActionGeo_Long"])

    m = folium.Map(location=[cleared_locations["ActionGeo_Lat"][0],
                   cleared_locations["ActionGeo_Long"][0]], zoom_start=4)

    for _, row in cleared_locations.head(100).iterrows():
        source_url = row["SOURCEURL"]
        popup_html = f"""
        <strong>{row['ActionGeo_FullName']}</strong><br>
        <a href="{source_url}" target="_blank">Source Link</a>
        """
        folium.Marker(
            location=[row["ActionGeo_Lat"], row["ActionGeo_Long"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row["ActionGeo_FullName"]
        ).add_to(m)

    # Display the map in Streamlit
    folium_static(m, width=700, height=500)


with st.sidebar:
    # all unique countries events
    filtered_countries = []
    if 'df' in st.session_state:
        filtered_countries = st.session_state.df["ActionGeo_FullName"].unique(
        )
    options = st.multiselect(
        "Filter out Events by Countries",
        filtered_countries)

    st.write("You selected:", options)

# col2 rendering
# with col2:
# List of options
options = [date.strftime("%Y%m%d") for date in date_generated]

# Dropdown menu
selected_option = st.selectbox('Select date to load event data:', options)

# Download csv file selected from dropdown
selected_filename_url = GDELT_DATA_EVENT_1_0_URL + selected_option + FILENAME

# Display the selected option
# st.write(f'You selected: {selected_filename_url}')
if st.button("Populate Data") or options:
    read_csv_into_df(selected_option + FILENAME,
                     "CSV.header.dailyupdates.txt", selected_filename_url)

# col1 rendering
# with col1:
#     pass
