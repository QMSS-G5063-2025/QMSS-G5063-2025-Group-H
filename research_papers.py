import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
from itertools import combinations
import networkx as nx
from pyvis.network import Network
import research_papers
import matplotlib.pyplot as plt
import re
import plotly.express as px
from wordcloud import WordCloud


def run():
    # ACTUAL STREAMLIT APP
    @st.cache_data
    def load_data():
        df = pd.read_csv('abstracts.csv')
        return df

    df = load_data()

    #styling for the python code 
    st.markdown("""
    <style>
    .st-bo {
        background-color: rgb(0, 0, 0); important! 
    }
                
    .plain-text {
        font-size: 15px;   
        font-family: 'Courier New', Courier, monospace;
        text-align: center;
        opacity: 0;
        animation: fadeIn 0.5s ease-in forwards;
        animation-delay: 0s;
        position: relative;
    }                             
    </style>
    """, unsafe_allow_html=True)

    # algorithm for banned words
    banned_words = pd.read_csv('banned_words.txt', header=None).values.flatten().tolist()
    banned_words = [word.lower() for word in banned_words]
    df['abstract_lower'] = df['abstract'].str.lower()

    # check if any banned word appears in the abstract
    def contains_banned(abstract):
        return any(re.search(rf'\b{re.escape(word)}\b', str(abstract), re.IGNORECASE) for word in banned_words)

    # apply function
    df['contains_banned'] = df['abstract_lower'].apply(contains_banned)

    from collections import Counter

    # Only keep titles that contain banned words
    banned_titles = df[df['contains_banned']]['abstract_lower']

    # Count banned words
    word_counter = Counter()

    for title in banned_titles:
        for word in banned_words:
            if word in title:
                word_counter[word] += 1

    # store data
    word_counts = pd.DataFrame.from_dict(word_counter, orient='index', columns=['count']).sort_values('count', ascending=False)

    # store the titles for potential interactivity
    banned_word_titles = {
        word: df[df['abstract_lower'].str.contains(rf'\b{re.escape(word)}\b', na=False, regex=True)]['title'].tolist()
        for word in word_counts.index
    }

    # update the data frame including the titles for each banned word
    word_counts['titles'] = word_counts.index.map(lambda word: "<br>".join(banned_word_titles[word][:10]))  # show first 10 titles

    #VISUAL
    # caption
    st.markdown('<div class="plain-text">Recently, restrictions on scientific research and scholarship in the U.S. have been imposed through multiple executive orders. Billions of dollars allocated for research have been frozen, and topics such as climate change and gender continue to be targeted and censored. </div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    st.markdown('<div class="plain-text"> <a href="https://www.pbs.org/newshour/health/what-happens-to-health-research-when-women-and-diversity-are-banned-words" target="_blank" style="color:inherit;">Reports</a> suggest that research grants with certain words are not considered for funding. We look at what could happen if research papers dealing with \"flagged\" topics were removed. </div>', unsafe_allow_html=True)
    percent_banned = df['contains_banned'].mean() * 1000 / 488 * 100; #there are 488 available abstracts
    percent_text = f"""{percent_banned:.2f}% contained recent \"flagged words\" as listed by the <a href="https://www.nytimes.com/interactive/2025/03/07/us/trump-federal-agencies-websites-words-dei.html" target="_blank" style="color: inherit; text-decoration: underline;">New York Times</a>."""
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    st.markdown('<div class="plain-text">Out of 488 randomly selected abstracts from the <a href="https://aclanthology.org/2020.acl-main.447" target="_blank" style="color: inherit; text-decoration: underline;">Semantic Scholar Open Research Corpus</a></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="plain-text">{percent_text}</div>', unsafe_allow_html=True)
    st.markdown('')
    st.markdown('')
    
    # WORD CLOUD
    def red_color_func(*args, **kwargs):
        return "hsl(0, 100%%, %d%%)" % random.randint(30, 70)

    col1, col2 = st.columns(2)

    with col1:
        wordcloud = WordCloud(
            width=600,
            height=400,
            background_color='white',
            color_func=red_color_func
        ).generate_from_frequencies(word_counter)

        fig_wc, ax_wc = plt.subplots(figsize=(8, 6))
        ax_wc.imshow(wordcloud, interpolation='bilinear')
        ax_wc.axis("off")
        ax_wc.set_title(
            "Flagged Words Word Cloud",
            fontsize=18,
            color='black',
            fontname='Courier New', 
            fontweight='bold'
        )
        st.markdown("<div style='height:5px;'></div>", unsafe_allow_html=True)
        st.pyplot(fig_wc)
        

    # Horizontal Bar Chart
    with col2:
            word_counts_sorted = word_counts.reset_index().sort_values(by='count', ascending=False)
        
            fig = px.bar(
                word_counts_sorted,
                x='count',
                y='index',
                labels={'index': 'Flagged Word', 'count': 'Count'},
                color_discrete_sequence=['red'],
                orientation='h',
                custom_data=['titles']
            )

            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>Count: %{y}<br><br><b>Abstract Titles:</b><br>%{customdata[0]}<extra></extra>'
            )

            fig.update_layout(
                title={
                    'text': 'Flagged Words Frequency in Research Abstracts',
                    'y':1,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {
                        'family': 'Courier New, monospace',
                        'size': 17,
                        'color': 'black',
                    }
                },
                xaxis_tickangle=-45,
                bargap=0.2
            )
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="plain-text">The above visuals suggests that topics related to gender, identity, and marginalized populations are disproportionately marked with “flagged” keywords (trans, women, expression, identity, etc.). This may reflect political sensitivity around these areas — and signals that scholarly work on these themes could be at higher risk of scrutiny or suppression. </div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="plain-text">The "flagged" keywords can be studied in numerous contexts, however. We take a look at how different areas of research could potentially be targets for suppression and defunding.</div>', unsafe_allow_html=True)

    #MORE VISUALIZATIONS
    # remove 'Unknown' themes and create a flagged column
    df_sunburst = df[df['theme'] != 'Unknown'].copy()
    df_sunburst['flagged'] = df_sunburst['contains_banned'].map({True: 'Flagged', False: 'Not Flagged'})

    sunburst_fig = px.sunburst(
        df_sunburst,
        path=['theme', 'flagged'],
        title="Research Themes and Flagged Status",
        color='flagged',
        color_discrete_map={'Flagged': 'red', 'Not Flagged': 'lightgray'}
    )

    sunburst_fig.update_layout(
        height=800,  # Increase figure height
        margin=dict(t=80, l=0, r=0, b=0),
        uniformtext=dict(minsize=10, mode='hide')  # prevents text overlap
    )

    st.plotly_chart(sunburst_fig, use_container_width=True)
# run()
