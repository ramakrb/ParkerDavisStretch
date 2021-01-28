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
import dataretrieval.nwis as nwis

st.set_page_config(page_title="USBR API Data Explorer", page_icon=None, layout='wide', initial_sidebar_state='auto')

col1, col2, col3 = st.beta_columns((1,3,1))
col1.title("Davis and Parker Stretch")
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
    df1 = df1.rename(columns={'DATETIME': 'datetime'})
    df1.set_index('datetime', inplace=True)
    return df1


def usgs_data(siteNumber, t1, t2,sel_int = 'HR',parameterCd = '00060'):
    if (sel_int == 'HR'):
        service='iv'
    else:
        service='dv'
    data = nwis.get_record(sites=siteNumber, service=service, start=t1, end=t2,parameterCd=parameterCd)
    site_info, md = nwis.get_info(sites=siteNumber)
    df = data.iloc[:,0:1]
    cname = site_info['station_nm'].iloc[0].split(',')[0]
    df.columns = [cname.title() + ' (USGS)']
    df = df.tz_localize(None)
    return (df)

def set_pub():
    rc('font', weight='bold')
    rc('grid', c='0.5', ls='-', lw=0.5)
    rc('figure', figsize = (10,6))
    plt.style.use('bmh')
    rc('lines', linewidth=1.3, color='b')


def plotData(df, colm):
    set_pub()
    plot_name = ' & '.join(df.columns)
    fig = make_subplots(rows=1, cols=1, subplot_titles=[plot_name])
    fig.append_trace(go.Scatter(x = df.index, y=df.iloc[:,0], mode='lines+markers', name=df.columns[0]), row=1, col=1)
    fig.append_trace(go.Scatter(x=df.index, y=df.iloc[:, 1], mode='lines+markers', name=df.columns[1]), row=1, col=1)
    fig.update_layout(height=500, width=850, legend=dict(orientation="h"))
    colm.plotly_chart(fig)

def flow_stats(df):
    rmse1 = ((df.iloc[:,0]-df.iloc[:,1])**2).mean() ** 0.5
    corr1 = df.iloc[:,0].corr(df.iloc[:,1])
    _, _, r_value, _, _ = stats.linregress(df.iloc[:,0], df.iloc[:,1])
    r2 = r_value**2
    def nashsutcliffe(evaluation,simulation):
        if len(evaluation) == len(simulation):
            s, e = np.array(simulation), np.array(evaluation)
            mean_observed = np.nanmean(e)
            numerator = np.nansum((e - s) ** 2)
            denominator = np.nansum((e - mean_observed) ** 2)
            return 1 - (numerator / denominator)
    nse = nashsutcliffe(df.iloc[:,0], df.iloc[:,1])
    data = {'Name':['Correlation','RMSE','R Squared','NSE'],
            'Value':[corr1,rmse1,r2,nse]}
    stat_tbl = pd.DataFrame(data)
    return stat_tbl

def show_stats(df):
    df1 = flow_stats(df.dropna()).style.set_properties(**{'background-color': 'black',
                                                         'color': 'lawngreen',
                                                         'font-size': '9pt',
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
            """)

Dvs_usgs_checkbox = col1.checkbox('Davis / Below Davis USGS Flows', value = False)

if Dvs_usgs_checkbox:
    df_bor = load_data('2166','HR',t1,t2)
    df_bor.columns = ['Davis Release']
    df_usgs = usgs_data('09423000',t1,t2)
    df_bordata = df_bor.join(df_usgs, how='inner')

    col2.header("Use the slider to lag flow.")
    hours01 = col2.slider('Travel Time Davis Dam to Blw Davis USGS Gage',0,15,0)
    col2.header('Lagged Hours: ' + str(hours01))
    df_bordata.iloc[:,[0]] = df_bordata.iloc[:,[0]].shift(hours01)
    plotData(df_bordata.dropna(), col2)
    show_stats(df_bordata)

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
