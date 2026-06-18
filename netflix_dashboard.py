import pandas as pd
from bokeh.plotting import figure
from bokeh.io import output_file, save, curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import Div, ColumnDataSource, HoverTool, Select, BoxAnnotation, LabelSet, Label
from bokeh.models import CustomJS
import numpy as np

# ==================================
# LOAD & PREPROCESSING DATA
# ==================================

df = pd.read_csv("netflix_titles.csv")

df['date_added'] = pd.to_datetime(df['date_added'], errors='coerce')
df['year_added'] = df['date_added'].dt.year

df['country'] = df['country'].fillna(df['country'].mode()[0])

df['cast'].replace(np.nan, 'No Data', inplace=True)
df['director'].replace(np.nan, 'No Data', inplace=True)

df["date_added"] = pd.to_datetime(df['date_added'])

df['month_added'] = df['date_added'].dt.month
df['month_name_added'] = df['date_added'].dt.month_name()
df['year_added'] = df['date_added'].dt.year

# Drop Duplicates
df.drop_duplicates(inplace=True)

# Explode country
df = df.dropna(subset=['country'])
df = df.assign(country=df['country'].str.split(', ')).explode('country')

# ==================================
# KPI CALCULATIONS
# ==================================

total_titles = len(df)
movies = len(df[df['type'] == 'Movie'])
tvshows = len(df[df['type'] == 'TV Show'])
countries = df['country'].nunique()

# ==================================
# FILTER PANEL (STREAMLINED MINIMALIST)
# ==================================

content_filter = Select(
    title="Content Type",
    value="All",
    options=["All", "Movie", "TV Show"],
    width=200,
    height=45
)

filter_panel = row(
    Div(text="""
    <div style="display:flex; align-items:center; gap:12px; height:100%;">
        <div style="
            width:32px; height:32px; border-radius:50%; 
            background:#FFF1F1; color:#E50914; 
            display:flex; align-items:center; justify-content:center; 
            font-size:16px; flex-shrink:0;">
            🔻
        </div>
        <div>
            <span style="font-size:15px; font-weight:700; color:#E50914; margin-right:8px;">
                Dashboard Filters:
            </span>
            <span style="color:#666; font-size:13px;">
                <p>Select content type to instantly update all data visualizations.</p>
            </span>
        </div>
    </div>
    """, width=500),

    content_filter,

    styles={
        "border": "1px solid #E5E5E5",
        "border-radius": "12px",
        "padding": "10px 25px",
        "background": "white",
        "box-shadow": "0 2px 6px rgba(0,0,0,0.03)",
        "align-items": "center"
    },
    sizing_mode="stretch_width",
    height=65
)

# ==================================
# GROWTH OVER TIME CHART
# ==================================

trend = df.groupby('year_added').size().reset_index(name='count')
movie_trend = df[df['type'] == 'Movie'].groupby('year_added').size().reset_index(name='count')
tv_trend = df[df['type'] == 'TV Show'].groupby('year_added').size().reset_index(name='count')

growth_df = pd.merge(movie_trend, tv_trend, on='year_added', how='outer', suffixes=('_movie', '_tv')).fillna(0)
growth_df.columns = ['year_added', 'movie_count', 'tv_count']

source = ColumnDataSource(growth_df)
all_source = ColumnDataSource(growth_df)

movie_only = growth_df.copy()
movie_only['tv_count'] = 0

tv_only = growth_df.copy()
tv_only['movie_count'] = 0

movie_source = ColumnDataSource(movie_only)
tv_source = ColumnDataSource(tv_only)

growth_chart = figure(
    title="Growth of Netflix Content Over Time",
    height=320,
    tools="pan,wheel_zoom,box_zoom,reset,save"
)

growth_chart.varea_stack(
    ['movie_count', 'tv_count'],
    x='year_added',
    source=source,
    color=['#E50914', '#221F1F'],
    alpha=0.9,
    legend_label=['Movie', 'TV Show']
)

growth_chart.legend.location = "top_left"
growth_chart.legend.orientation = "horizontal"
growth_chart.add_tools(HoverTool(tooltips=[("Year", "@year_added"), ("Movie", "@movie_count"), ("TV Show", "@tv_count")]))


# Tambahkan Label Insight ke Growth Chart
growth_insight_text = (
    "GROWTH ANALYSIS:\n"
    "• 2015: Rapid increase starts.\n"
    "• 2019: Historic peak of 2,401 titles.\n"
    "• 2020: Slowdown due to pandemic.\n"
    "• Focus on Movie > TV Show volume."
)

growth_label = Label(
    x=2008, y=150, # Sesuaikan koordinat x,y agar pas di area kosong
    text=growth_insight_text,
    text_font_size="9pt",
    background_fill_color="#FCEAEA",
    background_fill_alpha=0.8,
    border_line_color=None,
    padding=10
)
growth_chart.add_layout(growth_label)

# ==================================
# TOP COUNTRIES BUBBLE CHART
# ==================================

country_count = df['country'].value_counts().reset_index()
country_count.columns = ['country', 'count']
country_count = country_count.head(5)

country_coords = {
    'United States': (-98, 39), 'India': (78, 22), 'United Kingdom': (-2, 54),
    'Canada': (-106, 56), 'France': (2, 46), 'Japan': (138, 36),
    'Spain': (-4, 40), 'South Korea': (128, 36), 'Germany': (10, 51), 'Mexico': (-102, 23)
}

country_count['lon'] = country_count['country'].map(lambda x: country_coords[x][0])
country_count['lat'] = country_count['country'].map(lambda x: country_coords[x][1])

max_count = country_count['count'].max()
country_count['size'] = 30 + np.sqrt(country_count['count'] / max_count) * 100
country_count['count_label'] = country_count['count'].apply(lambda x: f"{x:,}")

country_all_source = ColumnDataSource(country_count)
country_movie_source = ColumnDataSource(country_count.copy())
country_tv_source = ColumnDataSource(country_count.copy())
country_source = ColumnDataSource(country_count)

country_map = figure(
    title="Where Netflix Content Comes From",
    height=320,
    x_range=(-140, 110),
    y_range=(0, 80),
    tools="pan,wheel_zoom,box_zoom,reset,save"
)

pink_overlay = BoxAnnotation(fill_color="#FCEAEA", fill_alpha=0.35)
country_map.add_layout(pink_overlay)

country_map.circle(
    x='lon', y='lat', size='size', source=country_source,
    fill_color="#E50914", fill_alpha=0.65, line_color="white", line_width=3
)

country_labels = LabelSet(
    x='lon', y='lat', text='country', source=country_source,
    y_offset=15, text_font_size="9pt", text_font_style="bold"
)

bubble_labels = LabelSet(
    x='lon', y='lat', text='count_label', source=country_source,
    text_color='white', text_font_style='bold', text_align='center'
)

country_map.add_layout(bubble_labels)
country_map.add_layout(country_labels)
country_map.add_tools(HoverTool(tooltips=[("Country", "@country"), ("Titles", "@count")]))

country_map.background_fill_color = "#F8F3F3"
country_map.border_fill_color = "#F8F3F3"
country_map.xaxis.visible = False
country_map.yaxis.visible = False

# ==================================
# TOP 10 GENRES CHART
# ==================================

genre_all = df['listed_in'].str.split(', ').explode().value_counts().head(10)
genre_movie = df[df['type'] == 'Movie']['listed_in'].str.split(', ').explode().value_counts().head(10)
genre_tv = df[df['type'] == 'TV Show']['listed_in'].str.split(', ').explode().value_counts().head(10)

genre_all_df = genre_all.reset_index(); genre_all_df.columns = ['genre', 'count']
genre_movie_df = genre_movie.reset_index(); genre_movie_df.columns = ['genre', 'count']
genre_tv_df = genre_tv.reset_index(); genre_tv_df.columns = ['genre', 'count']

def assign_genre_colors(dataframe):
    highest_counts = dataframe['count'].nlargest(3).values
    colors = []
    for val in dataframe['count']:
        if val in highest_counts:
            colors.append("#B20710")
        else:
            colors.append("#D3D3D3")
    return colors

genre_all_df['color'] = assign_genre_colors(genre_all_df)
genre_movie_df['color'] = assign_genre_colors(genre_movie_df)
genre_tv_df['color'] = assign_genre_colors(genre_tv_df)

genre_source = ColumnDataSource(genre_all_df.copy())
genre_all_source = ColumnDataSource(genre_all_df)
genre_movie_source = ColumnDataSource(genre_movie_df)
genre_tv_source = ColumnDataSource(genre_tv_df)

genre_chart = figure(
    y_range=list(reversed(genre_all_df['genre'])),
    title="Top 10 Genres",
    height=320,
    tools="pan,wheel_zoom,reset,save"
)

genre_chart.hbar(y='genre', right='count', height=0.6, source=genre_source, fill_color='color', line_color='color')
genre_chart.add_tools(HoverTool(tooltips=[("Genre", "@genre"), ("Titles", "@count")]))

# ==================================
# AUDIENCE RATING PROFILE CHART
# ==================================

rating_all = df['rating'].value_counts().head(10)
rating_movie = df[df['type'] == 'Movie']['rating'].value_counts().head(10)
rating_tv = df[df['type'] == 'TV Show']['rating'].value_counts().head(10)

rating_all_df = rating_all.reset_index(); rating_all_df.columns = ['rating', 'count']
rating_movie_df = rating_movie.reset_index(); rating_movie_df.columns = ['rating', 'count']
rating_tv_df = rating_tv.reset_index(); rating_tv_df.columns = ['rating', 'count']

rating_order = ['R', 'TV-MA', 'TV-14', 'TV-PG', 'PG-13', 'PG', 'TV-G', 'NR', 'TV-Y7', 'TV-Y']

def get_color(rating):
    if rating in ['TV-MA', 'R']: return '#E50914'
    elif rating in ['TV-14', 'PG-13', 'TV-PG']: return '#B20710'
    else: return '#666666'

for data in [rating_all_df, rating_movie_df, rating_tv_df]:
    data['color'] = data['rating'].apply(get_color)
    data['count_label'] = data['count'].apply(lambda x: f"{x:,}")
    data['rating'] = pd.Categorical(data['rating'], categories=rating_order, ordered=True)
    data.sort_values('rating', inplace=True)

rating_all_source = ColumnDataSource(rating_all_df)
rating_movie_source = ColumnDataSource(rating_movie_df)
rating_tv_source = ColumnDataSource(rating_tv_df)
rating_source = ColumnDataSource(rating_all_df)

rating_chart = figure(
    y_range=rating_order[::-1],
    title="Audience Rating Profile",
    height=320,
    toolbar_location=None
)

rating_chart.hbar(y='rating', right='count', source=rating_source, height=0.65, color='color')
rating_chart.add_layout(LabelSet(x='count', y='rating', text='count_label', source=rating_source, x_offset=8, text_font_size="10pt"))
rating_chart.add_tools(HoverTool(tooltips=[("Rating", "@rating"), ("Titles", "@count")]))

rating_chart.grid.grid_line_alpha = 0.0
rating_chart.outline_line_color = None
rating_chart.ygrid.grid_line_color = None
rating_chart.xgrid.grid_line_color = None

rating_chart.add_layout(Label(x=2000, y=2.5, text="■ Mature (TV-MA, R)", text_color="#E50914", text_font_size="10pt"))
rating_chart.add_layout(Label(x=2000, y=2.0, text="■ Mild (TV-14, PG-13, TV-PG)", text_color="#B20710", text_font_size="10pt"))
rating_chart.add_layout(Label(x=2000, y=1.5, text="■ Kids / Family", text_color="#666666", text_font_size="10pt"))
rating_chart.x_range.end = 5200

# ==================================
# DURATION DISTRIBUTION CHART
# ==================================

movie_df = df[df['type'] == 'Movie'].copy().dropna(subset=['duration'])
movie_df['duration_num'] = movie_df['duration'].str.extract(r'(\d+)').astype(int)

bins = [0, 60, 90, 120, 150, 180, 999]
labels = ['<60', '60-90', '90-120', '120-150', '150-180', '>180']
movie_df['duration_group'] = pd.cut(movie_df['duration_num'], bins=bins, labels=labels)

tv_df = df[df['type'] == 'TV Show'].copy()
tv_df['season_num'] = pd.to_numeric(tv_df['duration'].str.extract(r'(\d+)')[0], errors='coerce').fillna(0).astype(int)
tv_df['season_group'] = tv_df['season_num'].apply(lambda x: '5+ Seasons' if x >= 5 else f'{x} Season')

duration_movie = movie_df['duration_group'].value_counts().sort_index()
duration_tv = tv_df['season_group'].value_counts().reindex(['1 Season', '2 Season', '3 Season', '4 Season', '5+ Seasons']).fillna(0)

duration_all_df = duration_movie.reset_index(); duration_all_df.columns = ['bucket', 'count']
duration_movie_df = duration_movie.reset_index(); duration_movie_df.columns = ['bucket', 'count']
duration_tv_df = duration_tv.reset_index(); duration_tv_df.columns = ['bucket', 'count']

duration_source = ColumnDataSource(duration_all_df)
duration_all_source = ColumnDataSource(duration_all_df)
duration_movie_source = ColumnDataSource(duration_movie_df)
duration_tv_source = ColumnDataSource(duration_tv_df)

duration_chart = figure(
    title="Duration Distribution",
    height=320,
    x_range=list(duration_all_df['bucket']),
    tools="pan,wheel_zoom,reset,save"
)

duration_chart.vbar(x='bucket', top='count', width=0.7, source=duration_source, color="#E50914")
duration_chart.add_tools(HoverTool(tooltips=[("Duration", "@bucket"), ("Titles", "@count")]))

duration_chart.xaxis.major_label_text_font_size = "9pt"
duration_chart.yaxis.major_label_text_font_size = "9pt"

# ==================================
# INTEGRATED HEADER & KPI BANNER
# ==================================

header_banner = Div(text=f"""
<div style="
    background: linear-gradient(180deg, #000000 0%, #141414 100%);
    padding: 25px 40px;
    width: 100vw;
    box-sizing: border-box;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5);
">
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 30px;
    ">
        <div style="flex: 1 1 300px; min-width: 280px;">
            <div style="display: flex; align-items: baseline; gap: 15px; margin-bottom: 4px;">
                <span style="color: #E50914; font-size: 40px; font-weight: 900; letter-spacing: 1px; line-height: 1;">NETFLIX</span>
                <span style="color: #ffffff; font-size: 13px; font-weight: 600; letter-spacing: 1px; color: #808080;">FINAL PROJECT</span>
            </div>
            <h2 style="color: white; margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">
                CONTENT LANDSCAPE DASHBOARD
            </h2>
            <p style="color: #999999; margin: 4px 0 0 0; font-size: 13px;">
                Advanced Data Visualization • Exploring Global Streaming Content
            </p>
        </div>

        <div style="display: flex; align-items: center; gap: 40px; flex-wrap: wrap;">
            <div style="text-align: left; min-width: 110px;">
                <div style="font-size: 12px; font-weight: 600; color: #E50914; letter-spacing: 1px; margin-bottom: 2px;">TOTAL TITLES</div>
                <div style="font-size: 32px; font-weight: 800; color: #ffffff; line-height: 1;">{total_titles:,}</div>
            </div>
            <div style="width: 1px; height: 35px; background: #333333;"></div>
            <div style="text-align: left; min-width: 90px;">
                <div style="font-size: 12px; font-weight: 600; color: #999999; letter-spacing: 1px; margin-bottom: 2px;">MOVIES</div>
                <div style="font-size: 32px; font-weight: 800; color: #ffffff; line-height: 1;">{movies:,}</div>
            </div>
            <div style="width: 1px; height: 35px; background: #333333;"></div>
            <div style="text-align: left; min-width: 100px;">
                <div style="font-size: 12px; font-weight: 600; color: #999999; letter-spacing: 1px; margin-bottom: 2px;">TV SHOWS</div>
                <div style="font-size: 32px; font-weight: 800; color: #ffffff; line-height: 1;">{tvshows:,}</div>
            </div>
            <div style="width: 1px; height: 35px; background: #333333;"></div>
            <div style="text-align: left; min-width: 100px;">
                <div style="font-size: 12px; font-weight: 600; color: #999999; letter-spacing: 1px; margin-bottom: 2px;">COUNTRIES</div>
                <div style="font-size: 32px; font-weight: 800; color: #ffffff; line-height: 1;">{countries:,}</div>
            </div>
        </div>
    </div>
</div>
""", sizing_mode="stretch_width", height=120)

# ==================================
# NEW INSIGHT BOXES (GENRE & RATING) - CLEAN VERSION
# ==================================
genre_insight = Div(
    text="""
    <div style="background:#FCEAEA; border-radius:12px; padding:15px; max-width:100%; margin:0 auto; font-family:sans-serif;">
        <div style="display:flex; align-items:flex-start; gap:10px;">
            <div style="font-size:20px;">⭕</div>
            <div style="font-size:12px; color:#333; line-height:1.5;">
                International Movies and Dramas lead the overall Netflix library, showcasing a strong global narrative focus.
            </div>
        </div>
    </div>
    """, sizing_mode="stretch_width"
)

rating_insight = Div(
    text="""
    <div style="background:#FCEAEA; border-radius:12px; padding:15px; max-width:100%; margin:0 auto; font-family:sans-serif;">
        <div style="display:flex; align-items:flex-start; gap:10px;">
            <div style="font-size:20px;">⚖️</div>
            <div style="font-size:12px; color:#333; line-height:1.5;">
                The platform is dominated by mature content, with TV-MA being the most frequent rating across all categories.
            </div>
        </div>
    </div>
    """, sizing_mode="stretch_width"
)

# ==================================
# DURATION INSIGHT BOX (ROW 2 KANAN)
# ==================================
duration_insight = Div(
    text="""
    <div style="background:#FCEAEA; border-radius:12px; padding:15px; max-width:100%; margin:0 auto; font-family:sans-serif;">
        <div style="display:flex; align-items:flex-start; gap:10px;">
            <div style="font-size:20px;">⏱️</div>
            <div style="font-size:12px; color:#333; line-height:1.5;">
                Most content length varies based on type, with movies clustering in standard feature lengths and TV shows focusing on varied season counts.
            </div>
        </div>
    </div>
    """, sizing_mode="stretch_width"
)

# ==================================
# INTERACTIVE JAVASCRIPT CALLBACK
# ==================================
callback = CustomJS(
    args=dict(
        source=source, all_source=all_source, movie_source=movie_source, tv_source=tv_source,
        genre_source=genre_source, genre_all_source=genre_all_source, genre_movie_source=genre_movie_source, genre_tv_source=genre_tv_source,
        rating_source=rating_source, rating_all_source=rating_all_source, rating_movie_source=rating_movie_source, rating_tv_source=rating_tv_source,
        country_source=country_source, country_all_source=country_all_source, country_movie_source=country_movie_source, country_tv_source=country_tv_source,
        duration_source=duration_source, duration_all_source=duration_all_source, duration_movie_source=duration_movie_source, duration_tv_source=duration_tv_source,
        duration_chart=duration_chart, duration_insight=duration_insight, 
        genre_chart=genre_chart, genre_insight=genre_insight,
        rating_chart=rating_chart, rating_insight=rating_insight
    ),
    code="""
    let selected = cb_obj.value;

    // Fungsi helper untuk template box minimalis (Tanpa Judul)
    function getBox(icon, text) {
    return `<div style="background:#FCEAEA; border-radius:12px; padding:15px; width:100%; box-sizing:border-box; font-family:sans-serif;">
        <div style="display:flex; align-items:flex-start; gap:10px;">
            <div style="font-size:20px;">${icon}</div>
            <div style="font-size:12px; color:#333; line-height:1.5;">${text}</div>
        </div>
    </div>`;
    }

    if(selected==="All"){
        source.data = {...all_source.data};
        genre_source.data = {...genre_all_source.data};
        rating_source.data = {...rating_all_source.data};
        duration_source.data = {...duration_all_source.data};
        
        duration_chart.x_range.factors = ['<60', '60-90', '90-120', '120-150', '150-180', '>180'];
        genre_chart.y_range.factors = Array.from(genre_all_source.data['genre']).reverse();
        rating_chart.y_range.factors = ["R", "TV-MA", "TV-14", "TV-PG", "PG-13", "PG", "TV-G", "NR", "TV-Y7", "TV-Y"].reverse();

        genre_insight.text = getBox("⭕", "International Movies and Dramas lead the overall Netflix library, showcasing a strong global narrative focus.");
        rating_insight.text = getBox("⚖️", "The platform is dominated by mature content, with TV-MA being the most frequent rating across all categories.");
        duration_insight.text = getBox("⏱️", "Most content length varies based on type, with movies clustering in standard feature lengths and TV shows focusing on varied season counts.");
    
    } else if(selected==="Movie"){
        source.data = {...movie_source.data};
        genre_source.data = {...genre_movie_source.data};
        rating_source.data = {...rating_movie_source.data};
        duration_source.data = {...duration_movie_source.data};
        
        duration_chart.x_range.factors = ['<60', '60-90', '90-120', '120-150', '150-180', '>180'];
        genre_chart.y_range.factors = Array.from(genre_movie_source.data['genre']).reverse();
        rating_chart.y_range.factors = ["R", "TV-MA", "TV-14", "TV-PG", "PG-13", "PG", "TV-G", "NR"].reverse();
        
        genre_insight.text = getBox("⭕", "The film catalog is heavily dominated by International Movies and Dramas, forming the backbone of Netflix's cinema collection.");
        rating_insight.text = getBox("⚖️", "Movies show a strong concentration in TV-MA ratings, followed by a significant volume of TV-14 content.");
        duration_insight.text = getBox("⏱️", "The runtime distribution reveals a strong concentration around the 90-120 minute mark, the standard sweet-spot for global feature films.");

    } else {
        source.data = {...tv_source.data};
        genre_source.data = {...genre_tv_source.data};
        rating_source.data = {...rating_tv_source.data};
        duration_source.data = {...duration_tv_source.data};
        
        duration_chart.x_range.factors = ["1 Season", "2 Season", "3 Season", "4 Season", "5+ Seasons"];
        genre_chart.y_range.factors = Array.from(genre_tv_source.data['genre']).reverse(); 
        rating_chart.y_range.factors = ["TV-MA", "TV-14", "TV-PG", "TV-G", "NR", "TV-Y7", "TV-Y"].reverse();
        
        genre_insight.text = getBox("⭕", "International TV Shows significantly outperform other genres, showcasing the massive global appeal of localized television content.");
        rating_insight.text = getBox("⚖️", "For TV series, TV-MA is the dominant rating, reflecting a clear strategy to prioritize mature, high-engagement series.");
        duration_insight.text = getBox("⏱️", "An overwhelming majority of TV shows stop precisely after 1 Season. Only top-performing flagship franchises reach the 5+ Seasons tier.");
    }

    // Emit Perubahan
    genre_insight.change.emit();
    rating_insight.change.emit();
    duration_insight.change.emit();
    source.change.emit();
    genre_source.change.emit();
    rating_source.change.emit();
    duration_source.change.emit();
    duration_chart.x_range.change.emit();
    genre_chart.y_range.change.emit();
    rating_chart.y_range.change.emit();
    growth_label.change.emit();
    """
)

content_filter.js_on_change("value", callback)

# ==================================
# KEY INSIGHTS DATA PREPARATION
# ==================================

peak_year = trend.loc[trend['count'].idxmax(), 'year_added']
peak_titles = int(trend['count'].max())

# ==================================
# GLOBAL CHART LIMITATION SETTINGS
# ==================================

for chart in [growth_chart, country_map, genre_chart, rating_chart, duration_chart]:
    chart.sizing_mode = "stretch_width"
    chart.xgrid.grid_line_color = None
    chart.ygrid.grid_line_color = None
    chart.grid.grid_line_alpha = 0.0

# ==================================
# GAYA VISUALISASI KARTU CHART
# ==================================
CHART_CARD_STYLE = {
    "border": "1px solid #EAEAEA",
    "border-radius": "14px",
    "padding": "15px",
    "background": "#FFFFFF",
    "box-shadow": "0 2px 10px rgba(0,0,0,0.04)"
}

# ==================================
# TEXT INSIGHT BOXES (ROW 1)
# ==================================
growth_text_inline = Div(
    text=f"""
    <div id="growth-insight-container" style="
        background: #FCEAEA; border-radius: 14px; padding: 20px; 
        height: 320px; 
        //width: 240px; 
        box-sizing: border-box; 
        display: flex; flex-direction: column; justify-content: center; font-family: sans-serif;
    ">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="font-size: 22px;">📈</div>
            <div>
                <h3 style="margin: 0; font-size: 13px; font-weight: 800; color: #111111; letter-spacing: 0.5px; line-height:1.2;">GROWTH<br>ANALYSIS</h3>
                <p style="margin: 2px 0 0 0; font-size: 9px; color: #B20710;">Key trends in content additions per year</p>
            </div>
        </div>
        <ul style="margin: 0; padding-left: 14px; font-size: 10px; color: #222222; line-height: 1.5; max-width: 180px;">
            <li style="margin-bottom: 6px;">Things begin to pick up in <b>2015</b>, followed by a <b>rapid increase</b> from 2016 onwards.</li>
            <li style="margin-bottom: 6px;">Content additions hit their historic peak in <b>{int(peak_year)}</b> with over <b>{peak_titles:,}</b> titles added.</li>
            <li style="margin-bottom: 6px;">Additions show a slowdown in <b>2020</b>, likely due to the COVID-19 pandemic production halts.</li>
            <li>Netflix has focused more attention on increasing <b>Movie</b> content than TV shows.</li>
        </ul>
    </div>
    """,
    width=180, height=320
)

map_text_inline = Div(
    text=f"""
    <div id="map-insight-container" style="
        background: #FCEAEA; border-radius: 14px; padding: 20px; 
        height: 320px; 
        //width: 240px; 
        box-sizing: border-box; 
        display: flex; flex-direction: column; justify-content: center; font-family: sans-serif;
    ">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <div style="font-size: 22px;">🌍</div>
            <div>
                <h3 style="margin: 0; font-size: 13px; font-weight: 800; color: #111111; letter-spacing: 0.5px; line-height:1.2;">REGIONAL<br>ANALYSIS</h3>
                <p style="margin: 2px 0 0 0; font-size: 9px; color: #B20710;">Top content producing countries</p>
            </div>
        </div>
        <ul style="margin: 0; padding-left: 14px; font-size: 10px; color: #222222; line-height: 1.5; max-width: 180px;">
            <li style="margin-bottom: 6px;">The <b>United States</b> heavily dominates Netflix production globally compared to all other nations.</li>
            <li style="margin-bottom: 6px;"><b>India</b> follows as a massive secondary production hub, heavily fueled by its robust cinematic market.</li>
            <li>The <b>United Kingdom</b> firmly holds the third position, showcasing strong continuous volume in European content streaming.</li>
        </ul>
    </div>
    """,
    width=180, height=320
)

# ==================================
# DASHBOARD GRID LAYOUT CONTEXT (PROPER FLEX SPLIT)
# ==================================

# KARTU 1: Growth Chart (Diberi flex agar mendominasi ruang) + Boks Pink (Diberi lebar kaku lebih ramping)
growth_card_combined = row(
    growth_chart,
    styles={
        **CHART_CARD_STYLE, 
        "display": "flex !important", 
        "flex-direction": "row !important", 
        "align-items": "stretch !important"
    }, 
    css_classes=["growth-flex-card"],
    sizing_mode="stretch_width"
)

# KARTU 2: Country Map (Diberi flex agar mendominasi ruang) + Boks Pink (Diberi lebar kaku lebih ramping)
country_map_card_combined = row(
    country_map, 
    map_text_inline, 
    styles={
        **CHART_CARD_STYLE, 
        "display": "flex !important", 
        "flex-direction": "row !important", 
        "align-items": "stretch !important"
    }, 
    css_classes=["map-flex-card"],
    sizing_mode="stretch_width"
)

# BARIS 1 UTAMA
chart_row1 = row(growth_card_combined, country_map_card_combined, spacing=20, sizing_mode="stretch_width")

# KARTU 3 (DURATION)
duration_card_combined = column(duration_chart, duration_insight, styles=CHART_CARD_STYLE, spacing=10, sizing_mode="stretch_width")

# BARIS 2 UTAMA
chart_row2 = row(
    column(genre_chart, genre_insight, styles=CHART_CARD_STYLE, sizing_mode="stretch_width", spacing=10),
    column(rating_chart, rating_insight, styles=CHART_CARD_STYLE, sizing_mode="stretch_width", spacing=10),
    column(duration_chart, duration_insight, styles=CHART_CARD_STYLE, sizing_mode="stretch_width", spacing=10),
    spacing=20,
    sizing_mode="stretch_width"
)

charts_layout = column(
    filter_panel,
    chart_row1,
    chart_row2,
    spacing=20,
    sizing_mode="stretch_width"
)

# ==================================
# SAKTI: BREAKPOINT JAVASCRIPT RESPONSIVE (ANTI-SHADOW DOM COMPONENT)
# ==================================

# Karena CSS tidak sanggup menembus proteksi Shadow DOM komponen kaku milik Bokeh, 
# kita gunakan window event listener resize via JavaScript murni. 
# JS ini akan memantau lebar layar. Begitu di bawah 1024px (Inspect/HP):
# 1. Boks pink otomatis di-HAPUS total tanpa jejak (display: none).
# 2. Grid baris otomatis ditumpuk patah ke bawah murni (1 Baris = 1 Chart).
# 3. Canvas grafik Bokeh secara pintar langsung melar 100% memenuhi sisa sela kartu.
responsive_js_engine = Div(
    text="""
    <script>
        function applyResponsiveGrid() {
            let width = window.innerWidth;
            let rows = document.querySelectorAll('.bk-Row');
            
            rows.forEach(row => {
                // Cari Baris 1 Utama (Mendeteksi jika dia menampung dua kartu gabungan)
                if (row.children.length === 2 && row.querySelectorAll('canvas').length >= 2) {
                    if (width <= 1024) {
                        row.style.flexDirection = 'column';
                        row.style.height = 'auto';
                        
                        // Eksekusi pemotongan layout internal kartu putih
                        let cards = row.children;
                        for(let card of cards) {
                            card.style.width = '100%';
                            card.style.height = 'auto';
                            card.style.flexDirection = 'column';
                            
                            // Ambil boks pink di dalam kartu dan KILL total wujudnya
                            let pinkBox = card.querySelector('#growth-insight-container, #map-insight-container');
                            if(pinkBox) {
                                pinkBox.parentElement.style.display = 'none';
                                pinkBox.parentElement.style.width = '0px';
                            }
                            
                            // Paksa canvas chart melar penuh 100% mengisi kekosongan
                            let chartDiv = card.children[0];
                            if(chartDiv) {
                                chartDiv.style.width = '100%';
                            }
                        }
                    } else {
                        // KEMBALIKAN KE KEJAYAAN MONITOR DEKTOP LO SEMULA (DEFAULT 100%)
                        row.style.flexDirection = 'row';
                        row.style.height = '370px';
                        
                        let cards = row.children;
                        for(let card of cards) {
                            card.style.width = '100%';
                            card.style.height = '350px';
                            card.style.flexDirection = 'row';
                            
                            let pinkBox = card.querySelector('#growth-insight-container, #map-insight-container');
                            if(pinkBox) {
                                pinkBox.parentElement.style.display = 'block';
                                //pinkBox.parentElement.style.width = '240px';
                            }
                        }
                    }
                }
                
                // Cari Baris 2 Utama (Meniadakan kekakuan 3 kolom berjejer di HP)
                if (row.children.length === 3 && row.querySelectorAll('canvas').length >= 2) {
                    if (width <= 1024) {
                        row.style.flexDirection = 'column';
                        for(let child of row.children) {
                            child.style.width = '100%';
                            child.style.marginBottom = '15px';
                        }
                    } else {
                        row.style.flexDirection = 'row';
                        for(let child of row.children) {
                            child.style.width = '100%';
                            child.style.marginBottom = '0px';
                        }
                    }
                }
            });
        }

        // Jalankan serentak saat dokumen dimuat dan setiap kali jendela diciutkan
        window.addEventListener('resize', applyResponsiveGrid);
        window.addEventListener('DOMContentLoaded', () => {
            setTimeout(applyResponsiveGrid, 200);
        });
    </script>
    """,
    visible=False
)

favicon_injector = Div(
    text="""
    <script>
        let link = document.querySelector("link[rel*='icon']") || document.createElement('link');
        link.type = 'image/x-icon'; link.rel = 'shortcut icon'; link.href = 'https://www.netflix.com/favicon.ico';
        document.getElementsByTagName('head')[0].appendChild(link);
    </script>
    """,
    visible=False
)

responsive_css_injector = Div(
    text="""
    <style>
        /* ==================================================
           1. LAYAR LEBAR / DEFAULT (DESKTOP LAPTOP)
           ================================================== */
        @media (min-width: 1025px) {
            /* Grafik utama dipaksa agresif melar menghabiskan sisa sela kartu */
            .growth-flex-card > div:nth-child(1),
            .map-flex-card > div:nth-child(1) {
                flex-grow: 1 !important;
                flex-shrink: 1 !important;
                flex-basis: auto !important;
            }
            
            /* Boks pink dipaksa mengecil kaku, ramping (160px), dan merapat manis di kanan kartu */
            #growth-insight-container, #map-insight-container {
                width: 160px !important;
                max-width: 160px !important;
                min-width: 160px !important;
                height: 100% !important;
                display: flex !important;
            }
        }

        /* ==================================================
           2. LAYAR KECIL / RESPONSIVE (INSPECT MODE < 1024px)
           ================================================== */
        @media (max-width: 1024px) {
            /* 1. KUNCI MATI: Lenyapkan boks pink dari muka bumi beserta kontainer Bokeh-nya! */
            #growth-insight-container, 
            #map-insight-container,
            .growth-flex-card > div:nth-child(2),
            .map-flex-card > div:nth-child(2),
            .growth-flex-card > .bk-Panel:nth-child(2),
            .map-flex-card > .bk-Panel:nth-child(2) {
                display: none !important;
                width: 0px !important;
                height: 0px !important;
                max-width: 0px !important;
                min-width: 0px !important;
                flex: 0 0 0px !important; /* Hancurkan sisa ruang flex-basis Bokeh */
                margin: 0 !important;
                padding: 0 !important;
            }
            
            /* 2. PAKSA grafik area dan peta melar murni 100% horizontal penuh tanpa celah bolong */
            .growth-flex-card > div:nth-child(1),
            .map-flex-card > div:nth-child(1),
            .growth-flex-card > .bk-Component,
            .map-flex-card > .bk-Component,
            .growth-flex-card > .bk-Panel:nth-child(1),
            .map-flex-card > .bk-Panel:nth-child(1) {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 100% !important;
                flex: 1 1 100% !important;
            }

            /* 3. Paksa baris utama dasbor patah vertikal (1 Baris = 1 Kartu Grafik Penuh) */
            .main-dashboard-row-wrap, .bk-Row {
                flex-direction: column !important;
                align-items: stretch !important;
                height: auto !important;
            }
            
            .main-dashboard-row-wrap > div,
            .main-dashboard-row-wrap > .bk-Component,
            .main-dashboard-row-wrap > .bk-Panel {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 100% !important;
                margin-bottom: 15px !important;
            }
        }
    </style>
    """,
    visible=False
)

# ==================================
# ASSEMBLY DOCUMENT PACKAGING
# ==================================
layout = column(
    header_banner,
    Spacer(height=15),
    charts_layout,
    favicon_injector,
    responsive_css_injector,
    responsive_js_engine,  # <--- Injeksi kontroler JS pintar anti-omong kosong disini
    sizing_mode="stretch_width"
)

header_banner.sizing_mode = "stretch_width"
charts_layout.sizing_mode = "stretch_width"
chart_row1.sizing_mode    = "stretch_width"
chart_row2.sizing_mode    = "stretch_width"

output_file("netflix_dashboard.html")
curdoc().theme = None
save(layout)

print("Dashboard created successfully with flawless native javascript responsiveness!")