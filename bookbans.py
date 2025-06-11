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
            Most Banned Titles: {row['top_titles']}
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
    def get_top_banned_books(df, n=10):
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df[df['date'].dt.year.between(2021, 2023)]
        top = df['title'].value_counts().nlargest(n).reset_index()
        top.columns = ['title', 'ban_count']
        return top
    
    def show_top_books_grid(top_df, image_map, ban_reason_map):
            cols = st.columns(5)

            top_df['rank'] = top_df['ban_count'].rank(method='min', ascending=False).astype(int)

            for idx, row in top_df.iterrows():
                col = cols[idx % 5]
                title = row['title']
                count = row['ban_count']
                rank = row['rank']
                img_url = image_map.get(title)
                hover_text = ban_reason_map.get(title, "No reason available.")

                if img_url:
                    with col:
                        unique_id = f"book-{idx}"  # unique per image

                        st.markdown(f"""
                            <style>
                            #{unique_id} {{
                                position: relative;
                                width: 100%;
                            }}
                            #{unique_id} img {{
                                width: 100%;
                                border-radius: 6px;
                            }}
                            #{unique_id} .overlay {{
                                position: absolute;
                                top: 0;
                                left: 0;
                                width: 100%;
                                height: 100%;
                                background-color: rgba(0, 0, 0, 0.6);
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                opacity: 0;
                                border-radius: 6px;
                                transition: opacity 0.3s ease;
                                padding: 10px;
                                text-align: center;
                            }}
                            #{unique_id} .overlay-text {{
                                background-color: rgba(0, 0, 0, 0.4);
                                color: white;
                                font-size: 0.8em;
                                font-weight: bold;
                                padding: 10px;
                                border-radius: 6px;
                                max-width: 90%;
                            }}
                            #{unique_id}:hover .overlay {{
                                opacity: 1;
                            }}
                            </style>

                            <div id="{unique_id}">
                                <img src="{img_url}">
                                <div class="overlay">
                                    <div class="overlay-text">{hover_text}</div>
                                </div>
                            </div>
                            <div style='text-align: center; font-size: 0.85em; margin-top: 4px;'>
                                <strong>{rank}. {title}</strong><br>Banned {count} time{'s' if count > 1 else ''}
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    with col:
                        st.write("(No image)")
                        st.markdown(f"<div style='text-align: center; font-size: 0.85em;'>"
                                    f"<strong>{title}</strong><br>Banned {count} time{'s' if count > 1 else ''}"
                                    f"</div>", unsafe_allow_html=True)
                        
                                    
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
            "The Kite Runner":"https://m.media-amazon.com/images/I/61GMQ+GG--L.jpg",
            "Me and Earl and the Dying Girl": "https://images.squarespace-cdn.com/content/v1/54b1d240e4b07e1baddc8c47/1429279129732-KW0LZC6JT3ZDWJ1SU68Y/image-asset.jpeg",
        }

    ban_reason_map = {
            "Gender Queer: A Memoir": "This book has been banned in more states than any other book. Gender Queer covers topics relevant to the transgender experience. <a href='https://www.nytimes.com/2022/05/01/books/maia-kobabe-gender-queer-book-ban.html' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "The Bluest Eye": "The Bluest Eye has been banned for its themes of sexual abuse, racism, and slavery. <a href='https://www.nypl.org/events/exhibitions/galleries/literature-and-film/item/17353' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "The Perks of Being a Wallflower": "This book has been banned for containing things such as LGBTQ themes, explicit sexual references, and drug use. <a href='https://www.marshall.edu/library/bannedbooks/the-perks-of-being-a-wallflower/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "All Boys Aren't Blue": "All Boys Aren't Blue, a book about being Black and queer, has been banned due to its LGBTQ content. <a href='https://www.npr.org/2022/10/25/1130433140/banned-books-all-boys-arent-blue-george-johnson-lgbtq-ya' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "Sold":"This book has been banned for its sexually explicit content and mentions of sexual violence. <a href='https://www.marshall.edu/library/bannedbooks/sold/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "Looking for Alaska":"This book has been banned for its depiction of LGBTQ teenagers and sexual content. <a href='https://www.marshall.edu/library/bannedbooks/looking-for-alaska/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "Nineteen Minutes":"While it details a violent school shooting, this book has been banned for sexual content. <a href='https://pen.org/press-release/nearly-200-percent-surge-in-school-book-bans-during-2023-2024-school-year/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "Thirteen Reasons Why":"This book has been banned for its themes of teen suicide and its mentions of drugs, alcohol, and sex. <a href='https://www.marshall.edu/library/bannedbooks/thirteen-reasons-why/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "Tricks":"Tricks has been banned for being sexually explicit and having LGBTQIA+ content. <a href='https://www.marshall.edu/library/bannedbooks/tricks/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "The Kite Runner":"The Kite runner has been banned for its discussion of sexual violence. <a href='https://www.marshall.edu/library/bannedbooks/kite-runner/' target='_blank' style='color:#add8e6;'>Read more</a>.",
            "Me and Earl and the Dying Girl": "This book has been banned for its sexual content and language. <a href='https://www.marshall.edu/library/bannedbooks/me-and-earl-and-the-dying-girl/' target='_blank' style='color:#add8e6;'>Read more</a>.",
        }

    st.write("**Top Ten Banned Books from 2021 - 2024**")
    top10 = get_top_banned_books(data, n=11) #11 because of a tie
    show_top_books_grid(top10, image_map, ban_reason_map)

