""" Hist Plot Routes """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from flask import make_response, request, render_template, send_file
import time
import numpy as np
import pandas as pd
import datetime
from dateutil import parser
import os,glob,re,shutil
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from . import app, utilities
        
cmap=pd.read_csv('/opt/soundscene/yamnet_class_map.csv')
opts=={_n['index']:_n['display_name'] for _i, _n in d.loc[
    [0,1,2,3]
    ].iterrows()}

def _load_inf_data(from_dir,from_dt,to_dt,idxs=None):
    p = re.compile(r'([\d]+)-(infs)\.npy')
    idxs=idxs or range(521)

    infs=np.full((0,521),np.nan)
    times=[]
    for _n in glob.glob(f'{from_dir}/*-infs.npy'):
        infs = np.load(_n)
        m=p.match(os.path.basename(_n))
        f_dt=datetime.fromtimestamp(int(m.group(1)))
        
        if f_dt >= from_dt and f_dt < to_dt:
            times.append(f_dt)
            infs=np.expand_dims(infs,axis=0)
            res=np.concatenate((res,infs))
    return times,infs

    
def _create_figure(times,infs):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    xs = times
    ys = infs
    axis.plot(xs, ys)
    return fig

@app.route('/ss/hist_plot', methods=['GET'])
def home(**kwargs):
    
    return render_template('home.html',
                           idx_options=opts)
      
@app.route('/ss/hist_plot/generate_plot', methods=['GET'])
def generate_plot(**kwargs):
    idxs=[int(_n) for _n in request.args.getlist('idxs',[])]
    from_dt=parser.parse(request.args.get('from')) if 'from' in request.args else datetime.datetime.utcnow()
    to_dt=parser.parse(request.args.get('to')) if 'to' in request.args else datetime.datetime.utcnow()
    
    times,infs = _load_inf_data(from_dir='/ss/archive/inference', 
                                from_dt=from_dt, 
                                to_dt=to_dt, 
                                idxs=idxs)
    
    fig = create_figure(times,infs)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')



    
