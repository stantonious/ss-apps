""" Hist Plot Routes """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from flask import make_response, request, render_template, send_file,Response
import time
import numpy as np
import pandas as pd
import datetime
from dateutil import parser
import os,glob,re,shutil,io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from . import app, Inference
        
cmap=pd.read_csv('/opt/soundscene/yamnet_class_map.csv')
opts={_n['index']:_n['display_name'] for _i, _n in cmap.loc[
    [0,1,2,3,36,38]
    ].iterrows()}

def _load_inf_data(from_dir,from_dt,to_dt,idxs=None):
    
    
    infs=Inference.query.filter(Inference.at >= from_dt).filter(Inference.at < to_dt).filter(Inference.idx.in_(idxs)).order_by(Inference.at).all()

    res={}
    
    for _n in infs:
        d=res.setdefault(_n.at,np.zeros(len(idxs)))
        d[idxs.index(_n.idx)]=_n.conf
    
    return list(res.keys()),np.asarray(res.values())
        

    
def _create_figure(times,infs,inf_names=None):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    print (infs.shape)
    xs = times
    ys = infs
    for _i,_n in enumerate(ys.T):
        print (_n.shape)
        if inf_names:
            axis.plot(xs, _n,'o',label=inf_names[_i])
        else:
            axis.plot(xs, _n,'o')

    axis.legend()
    return fig

@app.route('/ss/hist_plot', methods=['GET'])
def home(**kwargs):
    
    return render_template('home.html',
                           idx_options=opts)
      
@app.route('/ss/hist_plot/generate_plot', methods=['GET'])
def generate_plot(**kwargs):
    idxs=[int(_n) for _n in request.args.getlist('idxs')]
    from_dt=parser.parse(request.args.get('from')) if 'from' in request.args else datetime.datetime.utcnow()
    to_dt=parser.parse(request.args.get('to')) if 'to' in request.args else datetime.datetime.utcnow()
    
    class_names=[opts[_i] for _i in idxs]
    times,infs = _load_inf_data(from_dir='/ss/archive/inference', 
                                from_dt=from_dt, 
                                to_dt=to_dt, 
                                idxs=idxs)
    
    fig = _create_figure(times,infs,class_names)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')



    
