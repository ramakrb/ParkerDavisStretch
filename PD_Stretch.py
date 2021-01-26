import streamlit as st
import pandas as pd
import datetime
import base64
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.pyplot import rc
import seaborn as sns
import numpy as np
import os
from bs4 import BeautifulSoup
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from climata.usgs import DailyValueIO
from climata.usgs import InstantValueIO

st.set_page_config(page_title="USBR API Data Explorer", page_icon=None, layout='wide', initial_sidebar_state='auto')

#maindf=pd.DataFrame()
col1, col2, col3 = st.beta_columns((1,3,1))
col1.title("Davis and Parker Stretch")
#st.header("Make Site / Parameter selection from the sidebar")
today = datetime.date.today() + datetime.timedelta(days=1)
previous = today + datetime.timedelta(days=-6)
start_date = col1.date_input('Start Date',previous)
end_date = col1.date_input('End Date',today)
t1 = start_date.strftime("%Y-%m-%d")
t2 = end_date.strftime("%Y-%m-%d")
col1.markdown("""
***
""")

def load_data(sdid, sel_int, t1, t2, db='lchdb'):
    url = "https://www.usbr.gov/pn-bin/hdb/hdb.pl?svr=" + db + "&sdi=" + str(sdid) + "&tstp=" + \
          str(sel_int) + "&t1=" + str(t1) + "&t2=" + str(t2) + "&table=R&mrid=0&format=2"
    html = pd.read_html(url)
    df1 = html[0]
    df1['DATETIME'] = pd.to_datetime(df1['DATETIME'])
    df1.set_index('DATETIME', inplace=True)
    return df1


def usgs_data(station_id, sel_int, t1, t2):
    if (sel_int == 'HR'):
        data = InstantValueIO(
            start_date=t1,
            end_date=t2,
            station=station_id,
            parameter="00060"
        )
    else:
        data = DailyValueIO(
            start_date=t1,
            end_date=t2,
            station=station_id,
            parameter="00060"
        )
    for series in data:
        flow = [r[1] for r in series.data]
        dates = [r[0] for r in series.data]
    site_name = data[0].site_name.split(",", 1)[0]
    dfusgsinst = pd.DataFrame({'Date': dates, 'Flow': flow})
    dfusgsinst.rename(columns={'Flow': site_name}, inplace=True)
    dfusgsinst['Date'] = dfusgsinst['Date'].dt.tz_localize(None)
    return (dfusgsinst)

def set_pub():
    rc('font', weight='bold')    # bold fonts are easier to see
    rc('grid', c='0.5', ls='-', lw=0.5)
    rc('figure', figsize = (10,6))
    plt.style.use('bmh')
    rc('lines', linewidth=1.3, color='b')


def plotData(df, colm):
    set_pub()
    fig = make_subplots(rows=1, cols=1, subplot_titles = ["Davis Release & BBBLC"])
    fig.append_trace(go.Scatter(x = df.index, y=df.iloc[:,0], mode='lines+markers', name=df.columns[0]), row=1, col=1)
    fig.append_trace(go.Scatter(x=df.index, y=df.iloc[:, 1], mode='lines+markers', name=df.columns[1]), row=1, col=1)
    fig.update_layout(height=700, width=1200, showlegend=True)#, title_text="Stacked Subplots")
    colm.plotly_chart(fig)

def flow_stats(df):
    rmse1 = ((df.iloc[:,0]-df.iloc[:,1])**2).mean() ** 0.5
    corr1 = df.iloc[:,0].corr(df.iloc[:,1])
    _, _, r_value, _, _ = stats.linregress(df.iloc[:,0], df.iloc[:,1])
    r2 = r_value**2
    def nashsutcliffe(evaluation,simulation):
        if len(evaluation) == len(simulation):
            s, e = np.array(simulation), np.array(evaluation)
            # s,e=simulation,evaluation
            mean_observed = np.nanmean(e)
            # compute numerator and denominator
            numerator = np.nansum((e - s) ** 2)
            denominator = np.nansum((e - mean_observed) ** 2)
            # compute coefficient
            return 1 - (numerator / denominator)
    nse = nashsutcliffe(df.iloc[:,0], df.iloc[:,1])
    data = {'Name':['Correlation','RMSE','R Squared','NSE'],
            'Value':[corr1,rmse1,r2,nse]}
    stat_tbl = pd.DataFrame(data)
    return stat_tbl #round(rmse1,4)

def show_stats(df):
    df1 = flow_stats(df.dropna()).style.set_properties(**{'background-color': 'black',
                                                         'color': 'lawngreen',
                                                         'font-size': '11pt',
                                                         'border-color': 'white', **{'width': '120px'}})
    col3.markdown("""
        ***
        ***
        ***
        ***
        ***
        ***
        *** 
        ***  
        """)
    col3.header('Here are some stats!')
    col3.dataframe(df1)
    col3.markdown("""
            ***
            ***
            ***
            ***
            ***
            ***
            ***
            ***
            ***
            ***
            *** 
            ***
            """)

Dvs_BBB_checkbox = col1.checkbox('Davis / Below Big Bend Flows', value = False)

if Dvs_BBB_checkbox:
    df_bordata = load_data('2166,2336','HR',t1,t2)
    df_bordata.columns = ['Davis Release','BBBLC']
    col2.header("Use the slider to lag flow.")
    hours1 = col2.slider('Travel Time Davis Dam to BBBLC',0,15,0)
    col2.header('Lagged Hours: ' + str(hours1))
    df_bordata.iloc[:,[0]] = df_bordata.iloc[:,[0]].shift(hours1)
    plotData(df_bordata.dropna(), col2)
    show_stats(df_bordata)

BBB_BNB_checkbox = col1.checkbox('Blw Big Bend / Blw. Needles Bridge Flows', value = False)

if BBB_BNB_checkbox:
    df_bordata = load_data('2336,7777', 'HR', t1, t2)
    df_bordata.columns = ['BBBLC', 'BNBLC']
    col2.header("Use the slider to lag flow.")
    hours2 = col2.slider('Travel Time BBBLC to BNBLC', 0, 15, 0)
    col2.header('Lagged Hours: ' + str(hours2))
    df_bordata.iloc[:, [0]] = df_bordata.iloc[:, [0]].shift(hours2)
    plotData(df_bordata.dropna(), col2)
    show_stats(df_bordata)

BNB_RS41_checkbox = col1.checkbox('Blw. Needles Bridge / RS41 Flows', value = False)

if BNB_RS41_checkbox:
    df_bordata = load_data('7777,2337', 'HR', t1, t2)
    df_bordata.columns = ['BNBLC', 'RS41']
    col2.header("Use the slider to lag flow.")
    hours3 = col2.slider('Travel Time BNBLC to RS41', 0, 15, 0)
    col2.header('Lagged Hours: ' + str(hours3))
    df_bordata.iloc[:, [0]] = df_bordata.iloc[:, [0]].shift(hours3)
    plotData(df_bordata.dropna(), col2)
    show_stats(df_bordata)

Dvs_RS41_checkbox = col1.checkbox('Davis / RS41 Flows', value = False)

if Dvs_RS41_checkbox:
    df_bordata = load_data('2166,2337','HR',t1,t2)
    df_bordata.columns = ['Davis Release','RS41']
    col2.header("Use the slider to lag flow.")
    hours4 = col2.slider('Travel Time Davis Dam to RS41',0,15,0)
    col2.header('Lagged Hours: ' + str(hours4))
    df_bordata.iloc[:,[0]] = df_bordata.iloc[:,[0]].shift(hours4)
    plotData(df_bordata.dropna(), col2)
    show_stats(df_bordata)