import streamlit as st
import pandas as pd
import datetime
import base64
from scipy import stats
import matplotlib.pyplot as plt
from matplotlib.pyplot import rc
import numpy as np
import os
from bs4 import BeautifulSoup
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import dataretrieval.nwis as nwis

st.set_page_config(page_title="USBR API Data Explorer", page_icon=None, layout='wide', initial_sidebar_state='auto')

sdids = ['2166','2336','7777','2337','2146','2119','2021','20179','20189','2020','20184','2013','21877','2731','1872']
sites = ['Davis Release','BBBLC','BNBLC','RS41LC','Parker Release','PGLC','WWLC','BIBLC','BMPLC','TFLC','BOBLC','CLC','PPGLC','MLLC','Powell Release']
bor_sites = dict(zip(sdids, sites))

col1, col2, col3 = st.columns((1,3,1))
col1.title("Glen Canyon to Imperial Dam Stretch")
sdid_list = ",".join(sdids[:-3])
sdid_yao = '21877,2731'
sdid_powell = '1872'
today = datetime.date.today() + datetime.timedelta(days=1)
previous = today + datetime.timedelta(days=-6)
start_date = col1.date_input('Start Date',previous)
end_date = col1.date_input('End Date',today)
t1 = start_date.strftime("%Y-%m-%d")
t2 = end_date.strftime("%Y-%m-%d")


def load_data(sdid, sel_int, t1, t2, db='lchdb'):
    url = "https://www.usbr.gov/pn-bin/hdb/hdb.pl?svr=" + db + "&sdi=" + str(sdid) + "&tstp=" + \
          str(sel_int) + "&t1=" + str(t1) + "&t2=" + str(t2) + "&table=R&mrid=0&format=2"
    html = pd.read_html(url)
    df1 = html[0]
    cnames = [bor_sites.get(key) for key in sdid.split(',')]
    cnames.insert(0,'datetime')
    df1.columns = cnames
    df1['datetime'] = pd.to_datetime(df1['datetime'])
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
    df = df.resample('60min').mean()
    return (df)

def bor_usgs(bor,usgs,t1,t2):
    df_bor = load_data(bor,'HR',t1,t2)
    df_usgs = usgs_data(usgs,t1,t2)
    df_comb = df_bor.join(df_usgs, how='inner')
    return df_comb

def set_pub():
    rc('font', weight='bold')
    rc('grid', c='0.5', ls='-', lw=0.5)
    rc('figure', figsize = (10,6))
    plt.style.use('bmh')
    rc('lines', linewidth=1.3, color='b')


def plotData(df, colm):
    href = createhref(df)
    df = df.dropna()
    set_pub()
    plot_name = ' & '.join(df.columns)
    fig = make_subplots(rows=1, cols=1, subplot_titles=[plot_name])
    fig.append_trace(go.Scatter(x = df.index, y=df.iloc[:,0], mode='lines+markers', name=df.columns[0]), row=1, col=1)
    fig.append_trace(go.Scatter(x=df.index, y=df.iloc[:, 1], mode='lines+markers', name=df.columns[1]), row=1, col=1)
    fig.update_layout(height=500, width=850, legend=dict(orientation="h"))
    colm.plotly_chart(fig)
    colm.markdown(href, unsafe_allow_html=True)

def createhref(df):
    csv = df.to_csv(index=True)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}">Download Data as CSV File</a> (right-click and save as &lt;some_name&gt;.csv)'
    return href

def flow_stats(df):
    rmse1 = round(((df.iloc[:,0]-df.iloc[:,1])**2).mean() ** 0.5,2)
    me1 = round((df.iloc[:,0]-df.iloc[:,1]).mean(),2)
    corr1 = round(df.iloc[:,0].corr(df.iloc[:,1]),3)
    _, _, r_value, _, _ = stats.linregress(df.iloc[:,0], df.iloc[:,1])
    r2 = round(r_value**2,3)
    def nashsutcliffe(evaluation,simulation):
        if len(evaluation) == len(simulation):
            s, e = np.array(simulation), np.array(evaluation)
            mean_observed = np.nanmean(e)
            numerator = np.nansum((e - s) ** 2)
            denominator = np.nansum((e - mean_observed) ** 2)
            return 1 - (numerator / denominator)
    nse = round(nashsutcliffe(df.iloc[:,0], df.iloc[:,1]),3)
    data = {'Name':['Correlation','ME','RMSE','R Squared','NSE'],
            'Value':[corr1,me1,rmse1,r2,nse]}
    stat_tbl = pd.DataFrame(data)
    return stat_tbl

def show_stats(df):
    df1 = flow_stats(df.dropna()).style.set_properties(**{'background-color': 'black',
                                                         'color': 'lawngreen',
                                                         'font-size': '9pt',
                                                         'border-color': 'white', **{'width': '120px'}})
    df1.style.set_precision(3)
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
    col3.subheader('Here are some stats!')
    col3.dataframe(df1)
    col3.markdown("""
            ***
            ***
            ***
            ***
            ***
            ***
            """)

def setup_reach(df,hr):
    col2.subheader('Lagged Hours: ' + str(hr))
    df.iloc[:, [0]] = df.iloc[:, [0]].shift(hr)
    plotData(df, col2)
    show_stats(df)
@st.cache
def get_all_data(t1,t2):
    lc1 = load_data(sdid_list, 'HR', t1, t2)
    yao1 = load_data(sdid_yao, 'HR', t1, t2, db='yaohdb')
    all = lc1.join(yao1.round(), how='inner')
    # all = all.join(usgs_data('09423000', t1, t2), how='inner')
    # all = all.join(usgs_data('09427520', t1, t2), how='inner')
    all = all.join(usgs_data('09429100', t1, t2), how='inner')
    uc1 = load_data(sdid_powell, 'HR', t1, t2, db='uchdb2')
    all = all.join(uc1.round(), how='inner')
    all = all.join(usgs_data('09380000', t1, t2), how='inner')
    all = all.join(usgs_data('09402500', t1, t2), how='inner')
    all = all.join(usgs_data('09404200', t1, t2), how='inner')
    return all


bor_all = get_all_data(t1,t2)
selected_stretch = col1.radio("Stretch", ['Glen Canyon to Hoover','Below Davis Stretch', 'Below Parker Stretch'])
if (selected_stretch == 'Below Davis Stretch'):
    col1.markdown("""
    """)
   # Dvs_usgs_checkbox = col1.checkbox('Davis / Below Davis USGS Flows', value = False)
   # if Dvs_usgs_checkbox:
   #     df_dvsusgs = bor_all.iloc[:,[0,14]].copy()
   #     col2.subheader("Use the slider to lag flow.")
   #     hours01 = col2.slider('Travel Time Davis Dam to Blw Davis USGS Gage',0,15,0)
   #     setup_reach(df_dvsusgs, hours01)

    Dvs_BBB_checkbox = col1.checkbox('Davis / Below Big Bend Flows', value = False)
    if Dvs_BBB_checkbox:
        df_dvsbbb = bor_all.iloc[:,[0,1]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours1 = col2.slider('Travel Time Davis Dam to BBBLC',0,15,0)
        setup_reach(df_dvsbbb, hours1)

    BBB_BNB_checkbox = col1.checkbox('Blw Big Bend / Blw. Needles Bridge Flows', value = False)
    if BBB_BNB_checkbox:
        df_bbbbnb = bor_all.iloc[:,[1,2]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours2 = col2.slider('Travel Time BBBLC to BNBLC', 0, 15, 0)
        setup_reach(df_bbbbnb, hours2)

    BNB_RS41_checkbox = col1.checkbox('Blw. Needles Bridge / RS41 Flows', value = False)
    if BNB_RS41_checkbox:
        df_bnbrs41 = bor_all.iloc[:,[2,3]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours3 = col2.slider('Travel Time BNBLC to RS41', 0, 15, 0)
        setup_reach(df_bnbrs41, hours3)

    Dvs_RS41_checkbox = col1.checkbox('Davis / RS41 Flows', value = False)
    if Dvs_RS41_checkbox:
        df_dvsrs41 = load_data('2166,2337','HR',t1,t2)
        col2.subheader("Use the slider to lag flow.")
        hours4 = col2.slider('Travel Time Davis Dam to RS41',0,15,0)
        setup_reach(df_dvsrs41, hours4)
elif (selected_stretch == 'Below Parker Stretch'):
    col1.markdown("""
        """)
   # Pkr_usgs_checkbox = col1.checkbox('Parker / Below Parker Flows', value=False)
   # if Pkr_usgs_checkbox:
   #     df_pkrusgs = bor_all.iloc[:,[4,15]].copy()
   #     col2.subheader("Use the slider to lag flow.")
   #     hours01 = col2.slider('Travel Time Parker Dam to Blw Parker USGS Gage',0,15,0)
   #     setup_reach(df_pkrusgs, hours01)

    Pkr_pg_checkbox = col1.checkbox('Parker Release / Parker Gage Flows', value=False)
    if Pkr_pg_checkbox:
        df_pkrpg = bor_all.iloc[:, [4, 5]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours1 = col2.slider('Travel Time Parker Dam to Parker Gage', 0, 15, 0)
        setup_reach(df_pkrpg, hours1)

    pg_ww_checkbox = col1.checkbox('Parker gage / Water Wheel Flows', value=False)
    if pg_ww_checkbox:
        df_pgww = bor_all.iloc[:, [5, 6]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours2 = col2.slider('Travel Time Parker Gage to Water Wheel Gage', 0, 15, 0)
        setup_reach(df_pgww, hours2)

    pg_pvid_checkbox = col1.checkbox('Parker gage / Below Palo Verde Dam Flows', value=False)
    if pg_pvid_checkbox:
        df_pgpvid = bor_all.iloc[:, [5, 14]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours3 = col2.slider('Travel Time Parker Gage to Below Palo Verde Dam Gage', 0, 20, 0)
        setup_reach(df_pgpvid, hours3)

    pvid_tf_checkbox = col1.checkbox('Below Palo Verde Dam / Taylor Ferry Gage Flows', value=False)
    if pvid_tf_checkbox:
        df_pvidtf = bor_all.iloc[:, [14, 9]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours4 = col2.slider('Travel Time Below Palo Verde Dam Gage to Taylor Ferry', 0, 20, 0)
        setup_reach(df_pvidtf, hours4)

    tf_c_checkbox = col1.checkbox('Taylor Ferry / Cibola Gage Flows', value=False)
    if tf_c_checkbox:
        df_tfc = bor_all.iloc[:, [9, 11]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours5 = col2.slider('Travel Time Taylor Ferry to Cibola', 0, 20, 0)
        setup_reach(df_tfc, hours5)

    c_ml_checkbox = col1.checkbox('Cibola / Martinez Lake Gage Flows', value=False)
    if c_ml_checkbox:
        df_cml = bor_all.iloc[:, [11, 13]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours6 = col2.slider('Travel Time Cibola to Martinez Lake', 0, 20, 0)
        setup_reach(df_cml, hours6)

    Pkr_ml_checkbox = col1.checkbox('Parker Release / Martinez Lake Gage Flows', value=False)
    if Pkr_ml_checkbox:
        df_pkrml = bor_all.iloc[:, [4, 13]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours7 = col2.slider('Travel Time Parker Dam to Martinez Lake', 0, 70, 0)
        setup_reach(df_pkrml, hours7)

else:
    col1.markdown("""
    """)
    Glen_LF_checkbox = col1.checkbox('Glen Canyon / Lees Ferry USGS Flows', value = False)
    if Glen_LF_checkbox:
        df_glenlf = bor_all.iloc[:, [15,16]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours01 = col2.slider('Travel Time Glen Canyon to Lees Ferry USGS Gage',0,15,0)
        setup_reach(df_glenlf, hours01)

    LF_GC_checkbox = col1.checkbox('Lees Ferry / Grand Canyon USGS Flows', value = False)
    if LF_GC_checkbox:
        df_lfgc = bor_all.iloc[:, [16,17]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours1 = col2.slider('Travel Time Lees Ferry to Grand Canyon USGS Gage',0,30,0)
        setup_reach(df_lfgc, hours1)

    GC_DC_checkbox = col1.checkbox('Grand Canyon / Diamond Creek USGS Flows', value = False)
    if GC_DC_checkbox:
        df_gcdc = bor_all.iloc[:, [17,18]].copy()
        col2.subheader("Use the slider to lag flow.")
        hours2 = col2.slider('Travel Time Grand Canyon to Diamond Creek USGS Gage',0,30,0)
        setup_reach(df_gcdc, hours2)
