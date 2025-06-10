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

    iframe[title="streamlit_folium.st_folium"] {
        height: 500px !important;
        max-height: 500px !important;
    }
                                
    </style>
    """, unsafe_allow_html=True)

    # Function to plot bans by year
    def plot_bans_by_year(df, year):
        df = df.copy()
        df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year  # Isolate year
        filtered = df[df['year'] == year]
        state_counts = filtered.groupby('state').size().reset_index(name='bans')
        
        # Get lat/lon info
        state_coords_df = df[['state', 'lat', 'lon']].drop_duplicates()
        state_counts = state_counts.merge(state_coords_df, on='state', how='left')

        m = folium.Map(location=[39.5, -98.35], zoom_start=4)
        for _, row in state_counts.dropna(subset=['lat', 'lon']).iterrows():
            folium.CircleMarker(
                location=(row['lat'], row['lon']),
                radius=row['bans']**0.5 / 2,
                popup=f"{row['state']}: {row['bans']} bans in {year}",
                color='crimson',
                fill=True,
                fill_opacity=0.6
            ).add_to(m)

        return m
    
    def plot_bans_by_month(df):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])

        df['year_month'] = df['date'].dt.to_period('M').dt.to_timestamp()

        monthly_counts = df.groupby('year_month').size().reset_index(name='count')

        # Create the chart
        chart = alt.Chart(monthly_counts).mark_line(point=True).encode(
            x=alt.X('year_month:T', title='Month',
                    axis=alt.Axis(format='%b %Y', labelAngle=-45)),  # e.g., Nov 2021
            y=alt.Y('count:Q', title='Number of Bans'),
            tooltip=[alt.Tooltip('year_month:T', title='Month'), 'count']
        ).properties(
            title='Book Bans Over Time (by Month)',
            width=700,
            height=400
        )

        return chart
    
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
    
    def get_top_banned_books(df, n=10):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df[df['date'].dt.year.between(2021, 2023)]
        top = df['title'].value_counts().nlargest(n).reset_index()
        top.columns = ['title', 'ban_count']
        return top
    
    def show_top_books_grid(top_df, image_map):
        st.markdown("### Top 10 Banned Books (2021–2023)")
        cols = st.columns(5)  # two rows of up to 5
        
        for idx, row in top_df.iterrows():
            col = cols[idx % 5]
            title = row['title']
            count = row['ban_count']
            img = image_map.get(title)

            with col:
                if img:
                    st.image(img, use_column_width=True)
                else:
                    st.write("(No image)")
                st.markdown(f"<div style='text-align: center; font-size: 0.85em;'>"
                            f"<strong>{title}</strong><br>Banned {count} time{'s' if count > 1 else ''}"
                            f"</div>", unsafe_allow_html=True)                
    # Start of Streamlit app
    st.markdown('<div class="plain-text">Book bans are a form of censorship that can have significant implications for free speech, intellectual freedom, and access to information. In the United States, book bans have been a contentious issue, with various states and school districts implementing restrictions on certain books in libraries and classrooms.</div>', unsafe_allow_html=True)

    # Load data
    data = load_data()

    # Slider for year
    year_to_filter = st.slider('Select Year', 2021, 2023, 2023)

    # Plot folium map
    st.subheader(f"Book Bans in {year_to_filter}")
    folium_map = plot_bans_by_year(data, year_to_filter)
    st_folium(folium_map, width=700, height=500)

    st.subheader("Bans Over Time")
    st.altair_chart(plot_bans_by_month_and_status(data), use_container_width=True)

    image_map = {
        "Gender Queer: A Memoir": "https://d28hgpri8am2if.cloudfront.net/book_images/onix/cvr9781549304002/gender-queer-a-memoir-9781549304002_hr.jpg",
        "The Bluest Eye": "https://m.media-amazon.com/images/I/81Qq9n7OtDL._AC_UF1000,1000_QL80_.jpg",
        "The Perks of Being a Wallflower": "https://m.media-amazon.com/images/I/61KSi8OvgVL.jpg",
        "All Boys Aren't Blue": "https://img.buzzfeed.com/buzzfeed-static/static/2022-06/27/15/asset/36241d3041bb/sub-buzz-826-1656343765-7.jpg?crop=2225:3176;48,16&downsize=900:*&output-format=auto&output-quality=auto",
        "Sold":"https://m.media-amazon.com/images/I/61NiFw4L1YL._AC_UF1000,1000_QL80_.jpg",
        "Looking for Alaska":"https://m.media-amazon.com/images/I/7127ZROAw5L.jpg",
        "Nineteen Minutes":"https://m.media-amazon.com/images/I/818it868QJL.jpg",
        "Thirteen Reasons Why":"https://m.media-amazon.com/images/I/51jViCo2wiL._AC_UF1000,1000_QL80_.jpg",
        "Tricks":"https://www.marshall.edu/library/files/2023/08/tricks.jpg",
        "Me and Earl and the Dying Girl":"https://images.squarespace-cdn.com/content/v1/54b1d240e4b07e1baddc8c47/1429228428333-SMZ9WXTA8BFS9HQXFSY7/image-asset.jpeg",
    }

    top10 = get_top_banned_books(data, n=10)
    show_top_books_grid(top10, image_map)

# To run
# run_bookbans()


