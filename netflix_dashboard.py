import pandas as pd
from bokeh.plotting import figure
from bokeh.io import output_file, save, curdoc
from bokeh.layouts import column, row, Spacer
from bokeh.models import Div, ColumnDataSource, HoverTool, Select, BoxAnnotation, LabelSet, Label
from bokeh.models import CustomJS, GeoJSONDataSource
from bokeh.transform import cumsum
import numpy as np
import geopandas as gpd
import json
from math import pi

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
# CHART CARD STYLE
# ==================================
CHART_CARD_STYLE = {
    "border": "1px solid #EAEAEA",
    "border-radius": "14px",
    "padding": "15px",
    "background": "#FFFFFF",
    "box-shadow": "0 2px 10px rgba(0,0,0,0.04)"
}

# ==================================
# COLOR PALETTE
# ==================================
RED        = "#E50914"
RED_DARK   = "#B0060F"
BLACK      = "#221F1F"
GREY       = "#B3B3B3"
PINK_BOX   = "#FBE0E0"
BG         = "#FFFFFF"
PANEL_BG   = "#FAF4F4"
TEXT_DARK  = "#141414"
CARD_BORDER = "#E5DCDC"

CARD_PAD = 14

def panel_title(title, subtitle):
    return Div(text=f"""
    <div style="font-family:Arial, sans-serif; padding:0 0 6px 0;">
      <div style="font-size:15px; font-weight:900; color:{TEXT_DARK};">{title}</div>
      <div style="font-size:11px; color:#555;">{subtitle}</div>
    </div>
    """, width=480, height=40)


def caption_box(text, height=80):
    return Div(
        text=f"""
        <div style="
            background:{PINK_BOX};
            border-radius:8px;
            padding:10px 14px;
            margin-top:8px;
            font-family:Arial, sans-serif;
            font-size:11px;
            color:{TEXT_DARK};
            height:{height - 28}px;
            box-sizing:border-box;
            display:flex;
            align-items:center;
            width:100%;
        ">
            <div>{text}</div>
        </div>
        """,
        height=height,
        sizing_mode="stretch_width"
    )

def card(content, width, height):
    return column(
        content,
        width=width, height=height,
        styles={
            "border": f"1px solid {CARD_BORDER}",
            "border-radius": "10px",
            "padding": f"{CARD_PAD}px {CARD_PAD}px {CARD_PAD + 8}px {CARD_PAD}px",
            "box-sizing": "border-box",
            "background": BG,
        }
    )

# ==================================
# FILTER PANEL
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
        "align-items": "center",

        # STICKY
        "position": "sticky",
        "top": "130px",
        "z-index": "9999"
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


# Label Insight Growth Chart
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

growth_chart.grid.grid_line_alpha = 0.0
growth_chart.outline_line_color = None
growth_chart.ygrid.grid_line_color = None
growth_chart.xgrid.grid_line_color = None

growth_chart.add_layout(growth_label)

# ==================================
# WHERE NETFLIX CONTENT COMES FROM
# ==================================
def country_counts_for(subset):
    return subset['country'].value_counts()

TOP5_COUNTRIES_ALL = country_counts_for(df).head(5).index.tolist()

# Posisi bubble (lon, lat)
CENTERS = {
    "United States": (-98, 38),
    "Canada": (-98, 63),
    "United Kingdom": (-15, 58),
    "France": (8, 48),
    "India": (80, 21),
}
# Posisi label nama negara
LABEL_POS = {
    "United States": (-127, 10),
    "Canada": (-98, 73),
    "United Kingdom": (-6, 73),
    "France": (24, 54),
    "India": (80, 9),
}

def map_values(subset):
    cc = country_counts_for(subset)
    return [int(cc.get(c, 0)) for c in TOP5_COUNTRIES_ALL]

map_all_vals = map_values(df)
map_movie_vals = map_values(df[df['type'] == 'Movie'])
map_tv_vals = map_values(df[df['type'] == 'TV Show'])

def bubble_sizes(vals):
    m = max(vals) if max(vals) > 0 else 1
    return [22 + (v / m) ** 0.5 * 48 for v in vals]

map_lons = [CENTERS[c][0] for c in TOP5_COUNTRIES_ALL]
map_lats = [CENTERS[c][1] for c in TOP5_COUNTRIES_ALL]
label_lons = [LABEL_POS[c][0] for c in TOP5_COUNTRIES_ALL]
label_lats = [LABEL_POS[c][1] for c in TOP5_COUNTRIES_ALL]

# Load world boundaries (Natural Earth via geopandas)
def load_world():
    try:
        return gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    except Exception:
        url = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
               "master/geojson/ne_110m_admin_0_countries.geojson")
        world = gpd.read_file(url)
        name_col = 'NAME' if 'NAME' in world.columns else 'name'
        world = world.rename(columns={name_col: 'name'})
        return world[['name', 'geometry']]

world = load_world()
name_col = 'name' if 'name' in world.columns else world.columns[0]
world = world[world[name_col] != 'Antarctica']
world_geojson = json.dumps(json.loads(world.to_json()))
geo_src = GeoJSONDataSource(geojson=world_geojson)

# View di-crop ke kawasan top 5 negara
country_map = figure(
            height=320,
            x_range=(-140, 110),
            y_range=(0, 80),
            tools="pan,wheel_zoom,reset,save", toolbar_location="above",
            background_fill_color="#F2EDED", border_fill_color="#FFFFFF"
            )

country_map.axis.visible = False
country_map.grid.visible = False
country_map.outline_line_color = None

country_map.patches('xs', 'ys', source=geo_src, fill_color="#E5E0E0",
           line_color="#FFFFFF", line_width=0.6, fill_alpha=1)

map_src = ColumnDataSource(data=dict(
    country=TOP5_COUNTRIES_ALL,
    lon=map_lons, lat=map_lats,
    n=map_all_vals,
    size=bubble_sizes(map_all_vals),
    label=[f"{v:,}" for v in map_all_vals],
))

# Ripple ring
for scale, alpha in [(2.2, 0.05), (1.6, 0.09)]:
    ring_src = ColumnDataSource(data=dict(
        lon=map_lons, lat=map_lats,
        size=[s * scale for s in bubble_sizes(map_all_vals)]
    ))
    country_map.scatter('lon', 'lat', size='size', source=ring_src, color=RED,
               alpha=alpha, line_color=None, marker="circle")



# Leader line
for c in TOP5_COUNTRIES_ALL:
    cx, cy = CENTERS[c]
    lx, ly = LABEL_POS[c]
    if (cx, cy) != (lx, ly):
        country_map.line([cx, lx], [cy, ly], line_color="#999999", line_width=1.1)
        country_map.scatter([lx], [ly], size=4, color="#999999", line_color=None)

bubbles = country_map.scatter('lon', 'lat', size='size', source=map_src, color=RED, alpha=0.88,
                      line_color="white", line_width=1.5,
                      hover_color=RED_DARK, hover_alpha=1)

country_map.add_tools(HoverTool(renderers=[bubbles], tooltips=[
    ("Country", "@country"),
    ("Number of titles", "@n{0,0}")
]))


country_map.legend.location = "top_left"
country_map.legend.orientation = "horizontal"
country_map.add_tools(HoverTool(renderers=[bubbles], attachment="right", tooltips=[
    ("Country", "@country"),
    ("Number of titles", "@n{0,0}")
]))


# Angka jumlah judul di dalam bubble
country_map.text('lon', 'lat', text='label', source=map_src, text_align="center",
        text_baseline="middle", text_color="white",
        text_font_size="10px", text_font_style="bold")

# Nama negara di posisi label
label_src = ColumnDataSource(data=dict(
    lon=label_lons, lat=label_lats, country=TOP5_COUNTRIES_ALL
))
country_map.text('lon', 'lat', text='country', source=label_src, text_align="center",
        text_baseline="middle", text_color=TEXT_DARK, text_font_size="9.5px",
        text_font_style="bold")

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
    height=320,
    tools="pan,wheel_zoom,reset,save"
)

genre_chart.grid.grid_line_alpha = 0.0
genre_chart.outline_line_color = None
genre_chart.ygrid.grid_line_color = None
genre_chart.xgrid.grid_line_color = None

genre_chart.hbar(y='genre', right='count', height=0.6, source=genre_source, fill_color='color', line_color='color')
genre_labels = LabelSet(
    x='count',
    y='genre',
    text='count',
    source=genre_source,
    x_offset=5,
    text_font_size="9pt"
)

genre_chart.add_layout(genre_labels)
genre_chart.x_range.end = 4000

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
    height=320,
    x_range=list(duration_all_df['bucket']),
    tools="pan,wheel_zoom,reset,save"
)

duration_chart.vbar(x='bucket', top='count', width=0.7, source=duration_source, color="#E50914")

duration_labels = LabelSet(
    x='bucket',
    y='count',
    text='count',
    source=duration_source,
    y_offset=5,
    text_align="center",
    text_font_size="9pt"
)

duration_chart.add_layout(duration_labels)

duration_chart.add_tools(HoverTool(tooltips=[("Duration", "@bucket"), ("Titles", "@count")]))

duration_chart.grid.grid_line_alpha = 0.0
duration_chart.outline_line_color = None
duration_chart.ygrid.grid_line_color = None
duration_chart.xgrid.grid_line_color = None

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
""", sizing_mode="stretch_width", height=120, styles={
        "position": "sticky",
        "top": "0px",
        "z-index": "9999"
    })

# ==================================
# INSIGHT BOXES (GENRE & RATING)
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
# DURATION INSIGHT BOX
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
# CONTENT TYPE BY MAJOR MARKETS
# ==================================
DONUT_FIG_W = 190
DONUT_GAP = 15

def donut(country_name):
    sub = df[df['country'] == country_name]
    m = (sub['type'] == 'Movie').sum()
    t = (sub['type'] == 'TV Show').sum()
    tot = m + t
    mp, tp = (m / tot * 100, t / tot * 100) if tot else (0, 0)
    data = pd.DataFrame({'type': ['Movie', 'TV Show'], 'value': [m, t]})
    data['angle'] = data['value'] / data['value'].sum() * 2 * pi
    data['color'] = [RED, BLACK]
    data['pct'] = [mp, tp]
    src = ColumnDataSource(data)

    p = figure(width=DONUT_FIG_W, height=DONUT_FIG_W, toolbar_location=None, tools="",
               x_range=(-1.3, 1.3), y_range=(-1.3, 1.3), background_fill_color=BG,
               border_fill_color=BG)
    wedges = p.annular_wedge(x=0, y=0, inner_radius=0.55, outer_radius=0.95,
                              start_angle=cumsum('angle', include_zero=True), end_angle=cumsum('angle'),
                              line_color=BG, fill_color='color', source=src,
                              hover_fill_alpha=0.7)
    p.add_tools(HoverTool(renderers=[wedges],
                           tooltips=[("Type", "@type"), ("Count", "@value{0,0}"), ("Percentage", "@pct{0.1f}%")]))
    p.axis.visible = False
    p.grid.visible = False
    p.outline_line_color = None
    pct_label = Label(
    x=0,
    y=0.05,
    text=f"{mp:.1f}%",
    text_align="center",
    text_baseline="middle",
    text_font_size="15px",
    text_font_style="bold",
    text_color=RED
    )

    type_label = Label(
        x=0,
        y=-0.2,
        text="Movie",
        text_align="center",
        text_baseline="middle",
        text_font_size="10px",
        text_color=RED
    )

    p.add_layout(pct_label)
    p.add_layout(type_label)

    return p, mp, tp, pct_label, type_label

p7a, mp_us, tp_us, pct_us, type_us = donut("United States")
p7b, mp_in, tp_in, pct_in, type_in = donut("India")
p7c, mp_kr, tp_kr, pct_kr, type_kr = donut("South Korea")
p7d, mp_uk, tp_uk, pct_uk, type_uk = donut("United Kingdom")
p7e, mp_ca, tp_ca, pct_ca, type_ca = donut("Canada")
p7f, mp_jp, tp_jp, pct_jp, type_jp = donut("Japan")

def market_card_content(p, name, tp, insight):

    title_div = Div(
        text=f"""
        <div style="
        width:{DONUT_FIG_W}px;
        margin:0 auto;
        text-align:center;
        font-weight:bold;
        font-size:12px;
        color:{TEXT_DARK};
        ">
        {name}<br>
        <span style="font-weight:normal;color:#555;">
        TV Show {tp:.1f}%
        </span>
        </div>
        """,
        align="center",
        sizing_mode="stretch_width"
    )

    insight_div = Div(
        text=f"""
        <div style="
        width:{DONUT_FIG_W}px;
        margin:0 auto;

        background:{PINK_BOX};
        border-radius:8px;
        padding:8px;

        text-align:center;
        font-size:11px;
        line-height:1.3;
        min-height:42px;
        box-sizing:border-box;
        height:60px;
        display:flex;
        align-items:center;
        justify-content:center;
        ">
        {insight}
        </div>
        """,
        align="center",
        sizing_mode="stretch_width"
    )

    card = column(
        title_div,
        p,
        insight_div,
        spacing=5,
        sizing_mode="stretch_width",
        align="center"
    )

    return card, title_div


card_us, title_us = market_card_content(
    p7a,
    "United States",
    tp_us,
    "🇺🇸 Balanced mix<br>Movies & TV Shows"
)

card_in, title_in = market_card_content(
    p7b,
    "India",
    tp_in,
    "🇮🇳 Strongest movie-oriented market"
)

card_kr, title_kr = market_card_content(
    p7c,
    "South Korea",
    tp_kr,
    "🇰🇷 74% TV Show → Strongest TV preference"
)

card_uk, title_uk = market_card_content(
    p7d,
    "United Kingdom",
    tp_uk,
    "🇬🇧 Balanced composition→Still slightly movie-led"
)

card_ca, title_ca = market_card_content(
    p7e,
    "Canada",
    tp_ca,
    "🇨🇦 72% Movie share→Clearly movie-dominant"
)

card_jp, title_jp = market_card_content(
    p7f,
    "Japan",
    tp_jp,
    "🇯🇵 TV-oriented market→Strong serialized content"
)

market_inner_row = row(
    card_us,
    card_in,
    card_kr,
    card_uk,
    card_ca,
    card_jp,
    sizing_mode="stretch_width"
)


market = column(
    panel_title(
        "CONTENT TYPE BY MAJOR MARKETS",
        "Movie vs TV Show share across the 6 biggest content-producing countries"
    ),
    market_inner_row,
    sizing_mode="stretch_width"
)

panel7 = column(market, sizing_mode="stretch_width", styles=CHART_CARD_STYLE)

# ==================================
# INTERACTIVE JAVASCRIPT CALLBACK
# ==================================
callback = CustomJS(
    args=dict(
        source=source, all_source=all_source, movie_source=movie_source, tv_source=tv_source,
        genre_source=genre_source, genre_all_source=genre_all_source, genre_movie_source=genre_movie_source, genre_tv_source=genre_tv_source,
        rating_source=rating_source, rating_all_source=rating_all_source, rating_movie_source=rating_movie_source, rating_tv_source=rating_tv_source,
        duration_source=duration_source, duration_all_source=duration_all_source, duration_movie_source=duration_movie_source, duration_tv_source=duration_tv_source,
        duration_chart=duration_chart, duration_insight=duration_insight, 
        genre_chart=genre_chart, genre_insight=genre_insight,
        rating_chart=rating_chart, rating_insight=rating_insight,
        map_src=map_src, map_all=map_all_vals,map_movie=map_movie_vals, map_tv=map_tv_vals,
        title_us=title_us, title_in=title_in, title_kr=title_kr, title_uk=title_uk, title_ca=title_ca, title_jp=title_jp,
        mp_us=mp_us,tp_us=tp_us, mp_in=mp_in, tp_in=tp_in, mp_kr=mp_kr, tp_kr=tp_kr, mp_uk=mp_uk, tp_uk=tp_uk, mp_ca=mp_ca,tp_ca=tp_ca, mp_jp=mp_jp,tp_jp=tp_jp,
        pct_us=pct_us,type_us=type_us, pct_in=pct_in, type_in=type_in, pct_kr=pct_kr, type_kr=type_kr,
        pct_uk=pct_uk, type_uk=type_uk, pct_ca=pct_ca, type_ca=type_ca, pct_jp=pct_jp, type_jp=type_jp,
    ),
    code="""
    let selected = cb_obj.value;
    let mvals;

    // Helper template box
    function getBox(icon, text) {
    return `<div style="background:#FCEAEA; border-radius:12px; padding:15px; width:100%; box-sizing:border-box; font-family:sans-serif;">
        <div style="display:flex; align-items:flex-start; gap:10px;">
            <div style="font-size:20px;">${icon}</div>
            <div style="font-size:12px; color:#333; line-height:1.5;">${text}</div>
        </div>
    </div>`;
    }

    function setDonutTitle(div, country, label, pct){
        div.text = `
        <div style="
            width:190px;
            margin:0 auto;
            text-align:center;
            font-weight:bold;
            font-size:12px;
            color:#333;
        ">
            ${country}<br>
            <span style="font-weight:normal;color:#555;">
                ${label} ${pct.toFixed(1)}%
            </span>
        </div>`;
    } 


    if(selected==="All"){
        source.data = {...all_source.data};
        genre_source.data = {...genre_all_source.data};
        rating_source.data = {...rating_all_source.data};
        duration_source.data = {...duration_all_source.data};
        mvals = map_all;
        
        duration_chart.x_range.factors = ['<60', '60-90', '90-120', '120-150', '150-180', '>180'];
        genre_chart.y_range.factors = Array.from(genre_all_source.data['genre']).reverse();
        rating_chart.y_range.factors = ["R", "TV-MA", "TV-14", "TV-PG", "PG-13", "PG", "TV-G", "NR", "TV-Y7", "TV-Y"].reverse();

        genre_insight.text = getBox("⭕", "International Movies and Dramas lead the overall Netflix library, showcasing a strong global narrative focus.");
        rating_insight.text = getBox("⚖️", "The platform is dominated by mature content, with TV-MA being the most frequent rating across all categories.");
        duration_insight.text = getBox("⏱️", "Most content length varies based on type, with movies clustering in standard feature lengths and TV shows focusing on varied season counts.");

        setDonutTitle(title_us,"United States","TV Show",tp_us);
        setDonutTitle(title_in,"India","TV Show",tp_in);
        setDonutTitle(title_kr,"South Korea","TV Show",tp_kr);
        setDonutTitle(title_uk,"United Kingdom","TV Show",tp_uk);
        setDonutTitle(title_ca,"Canada","TV Show",tp_ca);
        setDonutTitle(title_jp,"Japan","TV Show",tp_jp);

        pct_us.text = `${mp_us.toFixed(1)}%`;
        type_us.text = "Movie";
        pct_in.text = `${mp_in.toFixed(1)}%`;
        type_in.text = "Movie";
        pct_kr.text = `${mp_kr.toFixed(1)}%`;
        type_kr.text = "Movie";
        pct_uk.text = `${mp_uk.toFixed(1)}%`;
        type_uk.text = "Movie";
        pct_ca.text = `${mp_ca.toFixed(1)}%`;
        type_ca.text = "Movie";
        pct_jp.text = `${mp_jp.toFixed(1)}%`;
        type_jp.text = "Movie";

    } else if(selected==="Movie"){
        source.data = {...movie_source.data};
        genre_source.data = {...genre_movie_source.data};
        rating_source.data = {...rating_movie_source.data};
        duration_source.data = {...duration_movie_source.data};
        mvals = map_movie;
        
        duration_chart.x_range.factors = ['<60', '60-90', '90-120', '120-150', '150-180', '>180'];
        genre_chart.y_range.factors = Array.from(genre_movie_source.data['genre']).reverse();
        rating_chart.y_range.factors = ["R", "TV-MA", "TV-14", "TV-PG", "PG-13", "PG", "TV-G", "NR"].reverse();
        
        genre_insight.text = getBox("⭕", "The film catalog is heavily dominated by International Movies and Dramas, forming the backbone of Netflix's cinema collection.");
        rating_insight.text = getBox("⚖️", "Movies show a strong concentration in TV-MA ratings, followed by a significant volume of TV-14 content.");
        duration_insight.text = getBox("⏱️", "The runtime distribution reveals a strong concentration around the 90-120 minute mark, the standard sweet-spot for global feature films.");

        setDonutTitle(title_us,"United States","TV Show",tp_us);
        setDonutTitle(title_in,"India","TV Show",tp_in);
        setDonutTitle(title_kr,"South Korea","TV Show",tp_kr);
        setDonutTitle(title_uk,"United Kingdom","TV Show",tp_uk);
        setDonutTitle(title_ca,"Canada","TV Show",tp_ca);
        setDonutTitle(title_jp,"Japan","TV Show",tp_jp);

        pct_us.text = `${mp_us.toFixed(1)}%`;
        type_us.text = "Movie";
        pct_in.text = `${mp_in.toFixed(1)}%`;
        type_in.text = "Movie";
        pct_kr.text = `${mp_kr.toFixed(1)}%`;
        type_kr.text = "Movie";
        pct_uk.text = `${mp_uk.toFixed(1)}%`;
        type_uk.text = "Movie";
        pct_ca.text = `${mp_ca.toFixed(1)}%`;
        type_ca.text = "Movie";
        pct_jp.text = `${mp_jp.toFixed(1)}%`;
        type_jp.text = "Movie";

    } else {
        source.data = {...tv_source.data};
        genre_source.data = {...genre_tv_source.data};
        rating_source.data = {...rating_tv_source.data};
        duration_source.data = {...duration_tv_source.data};
        mvals = map_tv;
        
        duration_chart.x_range.factors = ["1 Season", "2 Season", "3 Season", "4 Season", "5+ Seasons"];
        genre_chart.y_range.factors = Array.from(genre_tv_source.data['genre']).reverse(); 
        rating_chart.y_range.factors = ["TV-MA", "TV-14", "TV-PG", "TV-G", "NR", "TV-Y7", "TV-Y"].reverse();
        
        genre_insight.text = getBox("⭕", "International TV Shows significantly outperform other genres, showcasing the massive global appeal of localized television content.");
        rating_insight.text = getBox("⚖️", "For TV series, TV-MA is the dominant rating, reflecting a clear strategy to prioritize mature, high-engagement series.");
        duration_insight.text = getBox("⏱️", "An overwhelming majority of TV shows stop precisely after 1 Season. Only top-performing flagship franchises reach the 5+ Seasons tier.");

        setDonutTitle(title_us,"United States","Movie",mp_us);
        setDonutTitle(title_in,"India","Movie",mp_in);
        setDonutTitle(title_kr,"South Korea","Movie",mp_kr);
        setDonutTitle(title_uk,"United Kingdom","Movie",mp_uk);
        setDonutTitle(title_ca,"Canada","Movie",mp_ca);
        setDonutTitle(title_jp,"Japan","Movie",mp_jp);
        
        pct_us.text = `${tp_us.toFixed(1)}%`;
        type_us.text = "TV Show";
        pct_in.text = `${tp_in.toFixed(1)}%`;
        type_in.text = "TV Show";
        pct_kr.text = `${tp_kr.toFixed(1)}%`;
        type_kr.text = "TV Show";
        pct_uk.text = `${tp_uk.toFixed(1)}%`;
        type_uk.text = "TV Show";
        pct_ca.text = `${tp_ca.toFixed(1)}%`;
        type_ca.text = "TV Show";
        pct_jp.text = `${tp_jp.toFixed(1)}%`;
        type_jp.text = "TV Show";
    }

    const mmax = Math.max(...mvals,1);
    const sizes = mvals.map(
        v => 22 + Math.sqrt(v/mmax)*48
    );

    map_src.data = {
        country: map_src.data.country,
        lon: map_src.data.lon,
        lat: map_src.data.lat,
        n: mvals,
        size: sizes,
        label: mvals.map(v => v.toLocaleString())
    };


    // Emit
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
    map_src.change.emit();
    title_us.properties.text.change.emit();
    title_us.change.emit(); title_in.change.emit();title_kr.change.emit();title_uk.change.emit(); title_ca.change.emit();title_jp.change.emit();
    pct_us.change.emit(); type_us.change.emit(); pct_in.change.emit(); type_in.change.emit(); pct_kr.change.emit();
    type_kr.change.emit(); pct_uk.change.emit(); type_uk.change.emit(); pct_ca.change.emit(); type_ca.change.emit(); pct_jp.change.emit(); type_jp.change.emit();
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
# TEXT INSIGHT BOXES
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
# DASHBOARD GRID LAYOUT
# ==================================

# Kartu 1: Growth Chart
growth_card_combined = column(

    panel_title(
        "NETFLIX CONTENT GROWTH OVER TIME",
        "Number of titles added per year"
    ),

    growth_chart,

    styles=CHART_CARD_STYLE,
    css_classes=["growth-flex-card"],
    sizing_mode="stretch_both"
)

# Kartu 2: Country Map
country_map_card_combined = column(

    panel_title(
        "WHERE NETFLIX CONTENT COMES FROM",
        "Number of titles by country of production"
    ),

    row(
        country_map,
        map_text_inline,
        sizing_mode="stretch_width"
    ),

    styles={
        **CHART_CARD_STYLE,
        "display": "flex !important",
        "flex-direction": "column !important"
    },

    sizing_mode="stretch_both"
)

# Baris 1
chart_row1 = row(growth_card_combined, country_map_card_combined, spacing=20, sizing_mode="stretch_width")

# Kartu 3 (Duration)
duration_card_combined = column(duration_chart, duration_insight, styles=CHART_CARD_STYLE, spacing=10, sizing_mode="stretch_width")

# Baris 2
genre_card = column(
    panel_title(
        "TOP 10 GENRES",
        "Most frequent content categories"
    ),
    genre_chart,
    genre_insight,
    styles=CHART_CARD_STYLE,
    spacing=10,
    sizing_mode="stretch_width"
)

rating_card = column(
    panel_title(
        "AUDIENCE RATING PROFILE",
        "Distribution of content ratings"
    ),
    rating_chart,
    rating_insight,
    styles=CHART_CARD_STYLE,
    spacing=10,
    sizing_mode="stretch_width"
)

duration_card = column(
    panel_title(
        "DURATION DISTRIBUTION",
        "Runtime and season count distribution"
    ),
    duration_chart,
    duration_insight,
    styles=CHART_CARD_STYLE,
    spacing=10,
    sizing_mode="stretch_width"
)

# Baris 2 utama
chart_row2 = row(
    genre_card,
    rating_card,
    duration_card,
    spacing=20,
    sizing_mode="stretch_width"
)

# Baris 3 utama
chart_row3 = row(
    panel7,
    spacing=20,
    sizing_mode="stretch_width"
)


charts_layout = column(
    filter_panel,
    chart_row1,
    chart_row2,
    chart_row3,
    spacing=20,
    sizing_mode="stretch_width"
)

# ==================================
# RESPONSIVE LAYOUT HANDLER (JAVASCRIPT)
# ==================================
responsive_js_engine = Div(
    text="""
    <script>
        function applyResponsiveGrid() {
            let width = window.innerWidth;
            let rows = document.querySelectorAll('.bk-Row');
            
            rows.forEach(row => {
                // Baris 1 utama (dua kartu chart)
                if (row.children.length === 2 && row.querySelectorAll('canvas').length >= 2) {
                    if (width <= 1024) {
                        row.style.flexDirection = 'column';
                        row.style.height = 'auto';
                        
                        let cards = row.children;
                        for(let card of cards) {
                            card.style.width = '100%';
                            card.style.height = 'auto';
                            card.style.flexDirection = 'column';
                            
                            let pinkBox = card.querySelector('#growth-insight-container, #map-insight-container');
                            if(pinkBox) {
                                pinkBox.parentElement.style.display = 'none';
                                pinkBox.parentElement.style.width = '0px';
                            }
                            
                            let chartDiv = card.children[0];
                            if(chartDiv) {
                                chartDiv.style.width = '100%';
                            }
                        }
                    } else {
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
                
                // Baris 2 utama (3 kolom)
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
           Desktop (>= 1025px)
           ================================================== */
        @media (min-width: 1025px) {
            .growth-flex-card > div:nth-child(1),
            .map-flex-card > div:nth-child(1) {
                flex-grow: 1 !important;
                flex-shrink: 1 !important;
                flex-basis: auto !important;
            }
            
            #growth-insight-container, #map-insight-container {
                width: 160px !important;
                max-width: 160px !important;
                min-width: 160px !important;
                height: 100% !important;
                display: flex !important;
            }
        }

        /* ==================================================
           Responsive (< 1024px)
           ================================================== */
        @media (max-width: 1024px) {
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
                flex: 0 0 0px !important;
                margin: 0 !important;
                padding: 0 !important;
            }
            
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
    responsive_js_engine,
    sizing_mode="stretch_width"
)

header_banner.sizing_mode = "stretch_width"
charts_layout.sizing_mode = "stretch_width"
chart_row1.sizing_mode    = "stretch_width"
chart_row2.sizing_mode    = "stretch_width"

output_file("netflix_dashboard.html")
curdoc().theme = None
save(layout)

print("Dashboard created successfully")
