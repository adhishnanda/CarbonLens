import streamlit as st
import pandas as pd
import plotly.express as px

# ─── 1. Load & clean ────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("data/owid-co2-data.csv")
    df = df[df['iso_code'].str.len()==3].copy()
    for c in ['co2','co2_per_capita','gdp','population',
              'coal_co2','oil_co2','gas_co2','flaring_co2','cement_co2']:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.sort_values(['country','year'])
    df[['co2','co2_per_capita','gdp','population',
        'coal_co2','oil_co2','gas_co2','flaring_co2','cement_co2']] = (
      df.groupby('country')[['co2','co2_per_capita','gdp','population',
                              'coal_co2','oil_co2','gas_co2','flaring_co2','cement_co2']]
        .transform(lambda s: s.interpolate().ffill().bfill())
    )
    return df

df = load_data()
latest = int(df['year'].max())

st.title("🌍 Global CO₂ & Energy Interactive Dashboard")

# ─── Sidebar ────────────────────────────────────────────────────────
st.sidebar.header("Configuration")
viz = st.sidebar.multiselect(
    "Select visualizations", 
    ["Bar-Chart Race","Bubble Map","Country Radar","Source Sunburst"],
    default=["Bar-Chart Race","Bubble Map","Country Radar","Source Sunburst"]
)

# ─── 1. Bar-Chart Race ───────────────────────────────────────────────
if "Bar-Chart Race" in viz:
    st.subheader("🏁 Top-10 CO₂ Emitters Over Time")
    # prepare top10_each as before
    annual = df.groupby(['year','country'], as_index=False)['co2'].sum()
    top10_each = (annual.groupby('year', group_keys=False)
                         .apply(lambda d: d.nlargest(10,'co2')))
    fig = px.bar(
        top10_each, x='co2', y='country', color='country', orientation='h',
        animation_frame='year', range_x=[0, top10_each['co2'].max()*1.05],
        title="Top 10 CO₂ Emitters (1750–{})".format(latest),
        labels={'co2':'Mt CO₂','country':''}
    )
    fig.update_layout(showlegend=False, height=500)
    st.plotly_chart(fig, use_container_width=True)

# ─── 2. Bubble Map ───────────────────────────────────────────────────
if "Bubble Map" in viz:
    st.subheader("💡 CO₂ per Capita Bubble Map")
    df_map = df.dropna(subset=['co2_per_capita','co2'])
    df_map['bubble_size'] = (df_map['co2']/df_map['co2'].max())*60+5
    fig2 = px.scatter_geo(
        df_map, locations='iso_code', color='co2_per_capita', size='bubble_size',
        animation_frame='year', projection="natural earth", 
        color_continuous_scale='viridis', size_max=60,
        title="Scale & Intensity of Emissions (1750–{})".format(latest),
        labels={'co2_per_capita':'tCO₂ per person'}
    )
    fig2.update_layout(margin=dict(l=0,r=0,t=50,b=0), height=500)
    st.plotly_chart(fig2, use_container_width=True)

# ─── 3. Country Profile Radar Chart ─────────────────────────────────
if "Country Radar" in viz:
    st.subheader("📈 Multimetric Radar Chart (Latest Year)")
    # Prepare latest‐year data
    df_radar = df[df['year']==latest].dropna(
        subset=['co2','co2_per_capita','gdp','population']
    ).copy()
    df_radar['gdp_per_capita'] = df_radar['gdp'] / df_radar['population']

    # Let user pick countries
    choices = st.multiselect(
        "Select countries to compare",
        options=df_radar['country'].unique(),
        default=['United States','China','India']
    )
    if choices:
        metrics = ['population','gdp_per_capita','co2','co2_per_capita']
        # Normalize each metric to [0,1] for fair comparison
        norm = df_radar[metrics].max()
        df_norm = df_radar.set_index('country').loc[choices, metrics] / norm

        # Melt for Plotly
        radar_df = df_norm.reset_index().melt(
            id_vars='country', var_name='metric', value_name='value'
        )

        # Radar chart
        fig3 = px.line_polar(
            radar_df,
            r='value',
            theta='metric',
            color='country',
            line_close=True,
            template='plotly_dark',
            title=f"Country Metric Comparison in {latest}"
        )
        fig3.update_traces(fill='toself')
        fig3.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0,1])
            ),
            legend=dict(title='', orientation='h', x=0.3, y=-0.1)
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Select at least one country to display the radar chart.")

# ─── 4. Sunburst Breakdown ───────────────────────────────────────────
if "Source Sunburst" in viz:
    st.subheader("🌳 Emissions by Source (Top 5 Emitters)")
    df5 = df[df['year']==latest]
    top5 = df5.nlargest(5,'co2')['country']
    melt = (
      df5[df5['country'].isin(top5)]
        .melt(
          id_vars=['country'],
          value_vars=['coal_co2','oil_co2','gas_co2','flaring_co2','cement_co2'],
          var_name='source', value_name='emissions'
        )
    )
    melt['source'] = (melt['source']
                      .str.replace('_co2','')
                      .str.title()
                      .str.replace('Flaring','Flaring'))
    fig4 = px.sunburst(
        melt, path=['country','source'], values='emissions',
        color='emissions', color_continuous_scale='Blues',
        title="CO₂ by Source in {}".format(latest),
        labels={'emissions':'Mt CO₂','source':'Source'}
    )
    st.plotly_chart(fig4, use_container_width=True)
