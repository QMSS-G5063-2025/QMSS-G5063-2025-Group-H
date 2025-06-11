def run_bookbans():
    import streamlit as st
    import pandas as pd
    import folium
    from streamlit_folium import st_folium
    import altair as alt
    import re

    # Fix: @st.cache_data needs to decorate a function
    @st.cache_data
    def load_data():
        DATA_URL = 'combined_bans.csv'
        data = pd.read_csv(DATA_URL)
        lowercase = lambda x: str(x).lower()
        data.rename(lowercase, axis='columns', inplace=True)
        return data
    
    st.markdown("""
    <style>
    .st-bo {
        background-color: rgb(0, 0, 0); important! 
    }
                
    .plain-text {
        font-size: 15px;   
        font-family: 'Courier New', Courier, monospace;
        text-align: center;
        animation: fadeIn 0.5s ease-in forwards;
        animation-delay: 0s;
        opacity: 0;
        position: relative;
    }      
                
     
    .stSelectbox div[data-baseweb="select"] > div {
        color: white !important;
    }
                
    iframe[title="streamlit_folium.st_folium"] {
        height: 500px !important;
        max-height: 500px !important;
    }
                                
    </style>
    """, unsafe_allow_html=True)



    def plot_bans_by_year(df, year):
        df = df.copy()
        df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year
        filtered = df[df['year'] == year]

        #  number of bans per state
        state_counts = filtered.groupby('state').size().reset_index(name='bans')

        # most banned titles per state
        top_titles = (filtered.groupby(['state', 'title'])
                            .size()
                            .reset_index(name='count')
                            .sort_values(['state', 'count'], ascending=[True, False]))

        # top 3 per state
        top_titles = top_titles.groupby('state').head(3)
        top_titles_agg = (top_titles.groupby('state')['title']
                                .apply(lambda x: ', '.join(x))
                                .reset_index(name='top_titles'))

        # merge lat/lon and titles
        state_coords_df = df[['state', 'lat', 'lon']].drop_duplicates()
        merged = state_counts.merge(state_coords_df, on='state', how='left')
        merged = merged.merge(top_titles_agg, on='state', how='left')

        #  map
        m = folium.Map(location=[39.5, -98.35], zoom_start=4)
        for _, row in merged.dropna(subset=['lat', 'lon']).iterrows():
            popup_html = f"""
            <strong>{row['state']}</strong><br>
            📚 <b>{row['bans']} bans</b> in {year}<br>
            🔥 Top titles: {row['top_titles']}
            """
            folium.CircleMarker(
                location=(row['lat'], row['lon']),
                radius=row['bans']**0.5 + 3,
                popup=folium.Popup(popup_html, max_width=250),
                color='crimson',
                fill=True,
                fill_opacity=0.6
            ).add_to(m)

        return m
    

    def simplify_ban_status(status):
            status = str(status).lower()
            status = re.sub(r'\b(from|in)\b', '', status)  # remove noise words
            status = re.sub(r'\s+', ' ', status).strip()   # collapse extra spaces
            return "banned pending investigation" if status == "banned pending investigation" else "banned"

    def plot_bans_by_month_and_status(df):
            # Parse and clean date
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])

            # Simplify ban status into 2 categories
            df['ban status'] = df['ban status'].fillna("unknown").apply(simplify_ban_status)

            # Year-month grouping
            df['year_month'] = df['date'].dt.to_period('M').dt.to_timestamp()

            # Grouped counts
            grouped = df.groupby(['year_month', 'ban status']).size().reset_index(name='count')

            # Plot
            chart = alt.Chart(grouped).mark_area(opacity=0.7).encode(
                x=alt.X('year_month:T', title='Month', axis=alt.Axis(format='%b %Y', labelAngle=-45)),
                y=alt.Y('count:Q', title='Number of Bans', stack='zero'),
                color=alt.Color('ban status:N', title='Ban Status',
                    scale=alt.Scale(domain=["banned", "banned pending investigation"]),
                    legend=alt.Legend(labelLimit=200)
                ),
                tooltip=[
                    alt.Tooltip('year_month:T', title='Month'),
                    alt.Tooltip('ban status:N', title='Ban Status'),
                    alt.Tooltip('count:Q', title='Number of Bans')
                ]
            ).properties(
                title='Book Bans Over Time',
                width=700,
                height=400
            )

            return chart
                                    
    # Start of Streamlit app
    st.markdown('<div class="plain-text">Book bans are a form of censorship that can have significant implications for free speech, intellectual freedom, and access to information. In the United States, book bans have been a contentious issue, with various states and school districts implementing restrictions on certain books in libraries and classrooms.</div>', unsafe_allow_html=True)
    st.subheader("Book Bans from 2021-2024")

    # Load data
    data = load_data()

    # Dropdown
    year_options = sorted(data['year'].dropna().astype(int).unique())
    year_to_filter = st.selectbox('Select Year', year_options, index=len(year_options)-1)

    # Plot folium map
    st.write(f"**Book Bans in {year_to_filter}**")
    folium_map = plot_bans_by_year(data, year_to_filter)
    col1, col2, col3 = st.columns([1, 6, 1])

    with col2:
        st_folium(folium_map, width=700, height=700)

    st.subheader("Bans Over Time")
    st.altair_chart(plot_bans_by_month_and_status(data), use_container_width=True)

# To run
# run_bookbans()


