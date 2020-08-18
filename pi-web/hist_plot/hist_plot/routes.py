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
from . import app, Inference, utilities, db_session
from sqlalchemy import func,desc

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

def _get_class_map(idxs):
    return {_n['index']:_n['display_name'] for _i, _n in cmap.loc[idxs].iterrows()}

def _get_significant_idxs(from_dt,to_dt,maximum=None,exclude_idxs=None):
    from_dt=datetime.datetime.fromtimestamp(from_dt) if isinstance(from_dt,int) else from_dt
    to_dt=datetime.datetime.fromtimestamp(to_dt) if isinstance(to_dt,int) else to_dt
    
    q=db_session.query(Inference.idx,func.avg(Inference.conf).label('confavg')).filter(Inference.at >= from_dt).filter(Inference.at < to_dt).group_by(Inference.idx).order_by(desc('confavg'))
    
    if exclude_idxs:
        q=q.filter(~Inference.idx.in_(exclude_idxs))
    q=q.group_by(Inference.idx).order_by(desc('confavg'))
    if maximum:
        q=q.limit(maximum)
    
    d=q.all()
    return [_n.idx for _n in d]

    
def _get_sample_times(from_dt,to_dt,criteria):
    
    from_dt=datetime.datetime.fromtimestamp(from_dt) if isinstance(from_dt,int) else from_dt
    to_dt=datetime.datetime.fromtimestamp(to_dt) if isinstance(to_dt,int) else to_dt
    res=[]
    for _n in criteria:
        q=Inference.query.filter(Inference.at >= from_dt).filter(Inference.at < to_dt)
        q=q.filter(Inference.idx == _n[0]).filter(Inference.conf>= _n[1])
        
        for _n in q.all():
            t=time.mktime(_n.at.timetuple())
            res.append(t)
    return res

def _get_audio_spans(from_t,to_t,criteria,span):
    res = _get_sample_times(from_t,to_t,criteria)
    res = sorted([(_n-span//2,_n+span//2) for _n in res])
    raw_audio = np.full((0,2),0,dtype=np.int16)
    
    if len(res) == 0:
        return raw_audio
    simplified=[res[0]]
    
    for _n in res[1:]:
        if _n[0] < simplified[-1][1]:
            if _n[1] > simplified[-1][1]:
                simplified[-1]=(simplified[-1][0],_n[1])
        else:
            simplified.append(_n)
    
    for _n in simplified:
        mid=(_n[0]+_n[1])//2
        half_width=mid-_n[0]
        audio_bytes=utilities._get_audio_bytes(d=ss_audio,
                                               t=mid,
                                               secs_prior=half_width,
                                               secs_aft=half_width,)
        raw_audio=np.concatenate((raw_audio,audio_bytes))
        
    return raw_audio
    
    
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
        #d=res.setdefault(_n.at,np.full((len(idxs)),np.nan))
        d[idxs.index(_n.idx)]=_n.conf
    
    #To DF
    d=[]
    for _k,_v in res.items():
        d.append([_k] + _v.tolist())
    df = pd.DataFrame(d,columns = ['t'] + [_n for _n in idxs])
    df=df.set_index('t')
    df=df.ix[:, df.mean(axis=0).sort_values(ascending=False).index] #reorder columns min->max
    return df
        

    
def _create_figure(times,infs,inf_names=None,stacked=False):
    fig = Figure(figsize=(12, 8))
    axis = fig.add_subplot(1, 1, 1)
    xs = times
    ys = infs
    if stacked:
        axis.stackplot(xs,ys.T)
    else:
        axis.plot(xs, ys,'o')
    axis.legend(labels=inf_names)
    return fig

def create_bokeh_figure(times,infs,inf_names=None,stacked=False):

    p = figure(plot_height=600, plot_width=600,
               title='Sound Scene',
               x_axis_label='Times',
               y_axis_label='Number of Flights')

    source = ColumnDataSource(
        data=dict(
            xvals=times,
            yvals=infs,
        )
    )
    p.hline_stack("xvals", "yvals", source=source, fill_alpha=0.2, size=5)

    callback = CustomJS(args=dict(source=source), code="""
        // get data source from Callback args
        
        var ind=source.selected.indices
        console.log('ind',source.selected.indices);
        console.log(source.data.xvals);
        console.log(source.data.yvals);

        for (i =0; i<ind.length;i++){
          
            console.log(source.data.xvals[ind[i]]);
            console.log(source.data.yvals[ind[i]]);
        }
        t0=source.data.xvals[ind[0]]
        t1=source.data.xvals[ind[ind.length-1]]
        window.location.href =  '/ss/hist_plot/play_threshold?idx_thresh=.1&from_t=' + t0 + '&to_t=' + t1
    """)
    p.add_tools(BoxSelectTool(dimensions="width", callback=callback))

    return p

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
    
    dt=datetime.datetime.utcnow()
    idxs=_get_significant_idxs(dt-datetime.timedelta(seconds=600),
                               dt, 
                               maximum=10)
    return render_template('prior_select.html',
                           idx_options=_get_class_map(idxs))

@app.route('/ss/hist_plot/play_select', methods=['GET'])
def play_select(**kwargs):
    
    return render_template('play_select.html',
                           idx_options=opts)

@app.route('/ss/hist_plot/prior_plot', methods=['GET'])
def prior_plot(**kwargs):   
    idxs=[int(_n) for _n in request.args.getlist('idxs')]
    max_classes=int(request.args.get('max_classes',10))
    max_samples=int(request.args.get('max_samples',-1))
    secs_prior=int(request.args.get('secs_prior',0))
    idx_thresh=float(request.args.get('idx_thresh',0))
    stacked=True if 'stacked' in request.args else False
    
    dt=datetime.datetime.utcnow()
    aud_end_t=int(time.mktime(dt.timetuple()))
    aud_start_t=int(aud_end_t-secs_prior)
    exclude_idxs=[494] if 'filter_silence' in request.args else None
    idxs=idxs or _get_significant_idxs(aud_start_t, aud_end_t, maximum=max_classes, exclude_idxs=exclude_idxs)
    
    plot_url =f'/ss/hist_plot/generate_prior_plot?stacked={stacked}&max_classes={max_classes}&max_samples={max_samples}&secs_prior={secs_prior}'
    for _n in idxs:
        plot_url=plot_url+f'&idxs={_n}'

    
    return render_template('prior_show.html',
                           from_t=aud_start_t,
                           to_t=aud_end_t,
                           idx_options=_get_class_map(idxs),
                           plot_url=plot_url) 
    
@app.route('/ss/hist_plot/generate_prior_plot', methods=['GET'])
def generate_prior_plot(**kwargs):  
    idxs=[int(_n) for _n in request.args.getlist('idxs')]
    max_classes=int(request.args.get('max_classes',10))
    max_samples=int(request.args.get('max_samples',-1))
    prior_secs=int(request.args.get('secs_prior',0))
    stacked=True if 'stacked' in request.args else False
    to_dt=datetime.datetime.utcnow()
    from_dt=datetime.datetime.utcnow() - datetime.timedelta(seconds=prior_secs)
    
    #times,infs,idxs = _load_inf_data(from_dt=from_dt, 
    df = _load_inf_data(from_dt=from_dt, 
                        to_dt=to_dt, 
                        idxs=idxs)
    
    #reduce to N best
    df = df.iloc[:,:max_classes]
    #reduce to M bins
    delta_secs = int((df.index[-1]-df.index[0]).total_seconds())
    if max_samples > 0 and delta_secs > 0:
        sample_secs=delta_secs/max_samples
        td = datetime.timedelta(seconds=sample_secs)
        df=df.resample(td).mean()
    idxs=[int(_n) for _n in df.columns]
    times=[_n for _n in df.index] #TODO .to_pydatetime?
    class_names=[all_idxs[_i] for _i in idxs]
    fig = _create_figure(times,
                         df.to_numpy(),
                         class_names,
                         stacked=stacked)
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

@app.route('/ss/hist_plot/play_threshold', methods=['GET'])
def play_threshold(**kwargs):
    max_aud_len=16000*120 #120 secs of audio
    from_t=int(request.args.get('from_t'))
    to_t=int(request.args.get('to_t'))
    idxs=[int(_n) for _n in request.args.getlist('idxs')]
    idx_threshold=float(request.args.get('idx_thresh',0.0))

    raw_audio=_get_audio_spans(from_t=from_t, 
                               to_t=to_t, 
                               criteria=[(_n,idx_threshold) for _n in idxs], 
                               span=2) #TODO 
    
    raw_audio=raw_audio[-max_aud_len:,...]
    mp3_f = utilities._to_wav(raw_audio,rate=16000,channels=2)
    res = make_response(send_file(mp3_f,
                                  mimetype='audio/mpeg',
                                  attachment_filename='test-{}.mp3'.format(time.time())))
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    res.headers['Cache-Control'] = 'public, max-age=0'

    return res


    
