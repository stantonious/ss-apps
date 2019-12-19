""" Labeler Routes """
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
from . import app, utilities

ss_root='/ss'
ss_archive=os.path.join(ss_root,'archive')
ss_audio=os.path.join(ss_archive,'audio')
ss_inf=os.path.join(ss_archive,'inference')
ss_labels=os.path.join(ss_root,'labels')
ss_data=os.path.join(ss_root,'data')

inf_pattern = re.compile(r'([\d]+)-(infs|mel).npy')
#(time)-(len secs)-(rate)-(channels)
aud_pattern = re.compile(r'([\d]+\.[\d]+)-([\d]+)-([\d]+).raw')


def _index_data(ss_root,
                for_idx=None,
                confidence=None,
                max_results=100,
                separation=None,
                from_dt=None,
                to_dt=None):
    for_idx=for_idx or 0
    confidence=confidence or .5
    
    print ('indexing for idx:',for_idx)
    ds=[]

    last_sample_dt=None
    for _f in sorted(glob.glob(ss_inf+'/*-infs.npy')):
        if len(ds)>=max_results:break
        m=inf_pattern.match(os.path.basename(_f))
        if m is None:
            print ('regex miss!')
            continue
        
        dt=datetime.datetime.fromtimestamp(float(m.group(1)))
        if (from_dt and dt < from_dt) or (to_dt and dt > to_dt):
            continue
        if last_sample_dt and separation:
            next_dt = last_sample_dt + datetime.timedelta(seconds=separation)
            if dt < next_dt:
                continue
        mel_fname=_f.replace('infs','mel')
        
        if not os.path.exists(mel_fname):
            print ('mel miss!')
            continue
        
        infs=np.load(_f)

        if infs[for_idx]<confidence:
            continue
        d=dict(time=int(m.group(1)),
               dt=dt,
               mel_file=mel_fname)
        d['conf']=infs[for_idx]
        ds.append(d)

        last_sample_dt=dt
        
    return pd.DataFrame(ds)
        
        

@app.route('/ss/labeler', methods=['GET'])
def home(**kwargs):
    return render_template('home.html',)
      
@app.route('/ss/labeler/work', methods=['GET'])
def work(**kwargs):
    max_samples = int(request.args.get('max_samples',10))
    confidence=float(request.args.get('confidence',.3))
    separation=float(request.args.get('separation',3))
    class_idx=int(request.args.get('index',0))
    from_dt = parser.parse(request.args.get('from','1999-01-01'))
    to_dt = parser.parse(request.args.get('to','2999-01-01'))
    print ('times',from_dt,to_dt)
    index = _index_data(ss_root=ss_root, 
                        for_idx=class_idx,
                        confidence=confidence,
                        max_results=max_samples,
                        separation=separation,
                        from_dt=from_dt,
                        to_dt=to_dt)

    if len(index) == 0:
        return 'No data'
    return render_template('label.html',
                           index=index[index['conf']>confidence][:max_samples],
                           classes=['unknown']+[f'person-{_i}' for _i in range(5)],
                           span=separation,
                           time=time.time())

@app.route('/ss/labeler/play', methods=['GET'])
def play(**kwargs):
    aud_time = float(request.args.get('aud_time'))
    duration = float(request.args.get('aud_duration',10))
    
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

@app.route('/ss/labeler/label', methods=['POST'])
def label(**kwargs):
    label_pattern = re.compile(r'label-([\d]+).*')
    span=request.form.get('span',0)
    span=float(span)

    spanned_ts = [int(_v) for _k,_v in request.form.items() if _k == 'span_t']
   

    for _k,_v in request.form.items():
        if label_pattern.match(_k):
            m=label_pattern.match(_k)
            t=int(m.group(1))
            ts=range(t-int(span/2),t+int(span/2)+1) if t in spanned_ts else [t]

            for _t in ts:
                try:
                    #find mel/inf
                    src_inf = os.path.join(ss_inf,f'{m.group(1)}-infs.npy')
                    src_mel = os.path.join(ss_inf,f'{m.group(1)}-mel.npy')
            
                    if os.path.exists(src_inf) and os.path.exists(src_mel):
                        label_dir=_v.strip()
                        dst_inf = os.path.join(ss_labels,label_dir,f'{m.group(1)}-infs.npy')
                        dst_mel = os.path.join(ss_labels,label_dir,f'{m.group(1)}-mel.npy')
                    
                        label_dir = os.path.dirname(dst_inf)
                        if not os.path.exists(label_dir):
                            print (f'labeled dir:{label_dir} does not exist..creating')
                            os.makedirs(label_dir)
                        shutil.move(src_inf,dst_inf)
                        shutil.move(src_mel,dst_mel)
                except Exception as e:
                    print (e)
        
    return 'ok'
    

    
