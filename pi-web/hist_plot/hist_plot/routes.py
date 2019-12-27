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
from . import app, Inference, utilities

ss_root='/ss'
ss_archive=os.path.join(ss_root,'archive')
ss_audio=os.path.join(ss_archive,'audio')

        
cmap=pd.read_csv('/opt/soundscene/yamnet_class_map.csv')
opts={_n['index']:_n['display_name'] for _i, _n in cmap.loc[
    [0,1,2,3,36,38,132,494]
    #range(521)
    ].iterrows()}
#sort
opts={k:v for k,v in sorted(opts.items(), key=lambda x:x[1])}

all_idxs={_n['index']:_n['display_name'] for _i, _n in cmap.loc[:].iterrows()}

def _load_inf_data(from_dt,to_dt,idxs=None):
    conf_thresh = .1
    if len(idxs) > 0:
        infs=Inference.query.filter(Inference.at >= from_dt).filter(Inference.at < to_dt).filter(Inference.idx.in_(idxs)).order_by(Inference.at).all()
    else:
        infs=Inference.query.filter(Inference.conf >= conf_thresh).filter(Inference.at >= from_dt).filter(Inference.at < to_dt).order_by(Inference.at).all()
        idxs=Inference.query.filter(Inference.conf >= conf_thresh).filter(Inference.at >= from_dt).filter(Inference.at < to_dt).distinct(Inference.idx).all()
        idxs=[_n.idx for _n in idxs]

    res={}
    
    for _n in infs:
        d=res.setdefault(_n.at,np.zeros(len(idxs)))
        d[idxs.index(_n.idx)]=_n.conf
    
    return list(res.keys()),np.asarray(list(res.values())),idxs
        

    
def _create_figure(times,infs,inf_names=None):
    fig = Figure(figsize=(12, 8))
    axis = fig.add_subplot(1, 1, 1)
    xs = times
    ys = infs
    for _i,_n in enumerate(ys.T):
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

@app.route('/ss/hist_plot/date_select', methods=['GET'])
def date_select(**kwargs):
    
    return render_template('date_select.html',
                           idx_options=opts)

@app.route('/ss/hist_plot/prior_select', methods=['GET'])
def prior_select(**kwargs):
    
    return render_template('prior_select.html',
                           idx_options=opts)

@app.route('/ss/hist_plot/play_select', methods=['GET'])
def play_select(**kwargs):
    
    return render_template('play_select.html',
                           idx_options=opts)
    
@app.route('/ss/hist_plot/generate_prior_plot', methods=['GET'])
def generate_prior_plot(**kwargs):  
    idxs=[int(_n) for _n in request.args.getlist('idxs')]
    prior_secs=int(request.args.get('secs_prior',0))
    to_dt=datetime.datetime.utcnow()
    from_dt=datetime.datetime.utcnow() - datetime.timedelta(seconds=prior_secs)
    
    times,infs,idxs = _load_inf_data(from_dt=from_dt, 
                                     to_dt=to_dt, 
                                     idxs=idxs)
    
    class_names=[all_idxs[_i] for _i in idxs]
    fig = _create_figure(times,infs,class_names)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')
    
@app.route('/ss/hist_plot/generate_plot', methods=['GET'])
def generate_plot(**kwargs):
    idxs=[int(_n) for _n in request.args.getlist('idxs')]
    from_dt=parser.parse(request.args.get('from')) if 'from' in request.args else datetime.datetime.utcnow()
    to_dt=parser.parse(request.args.get('to')) if 'to' in request.args else datetime.datetime.utcnow()
    
    times,infs,idxs = _load_inf_data(from_dt=from_dt, 
                                     to_dt=to_dt, 
                                     idxs=idxs)
    
    class_names=[all_idxs[_i] for _i in idxs]
    fig = _create_figure(times,infs,class_names)
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

@app.route('/ss/hist_plot/play', methods=['GET'])
def play(**kwargs):
    dt=parser.parse(request.args.get('aud_time')) if 'aud_time' in request.args else datetime.datetime.utcnow()
    aud_time=time.mktime(dt.timetuple())
    duration = float(request.args.get('aud_duration',10))
    
    duration=min([duration,10])
    mp3_f = utilities._get_wav(d=ss_audio,
                               t=aud_time,
                               duration=duration)
    res = make_response(send_file(mp3_f,
                                  mimetype='audio/mpeg',
                                  attachment_filename='test-{}.mp3'.format(time.time())))
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    res.headers['Cache-Control'] = 'public, max-age=0'

    return res


    
