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
import os,glob,re
from . import app, utilities

ss_root='/tmp/ss'
ss_archive=os.path.join(ss_root,'archive')
ss_audio=os.path.join(ss_archive,'audio')
ss_inf=os.path.join(ss_archive,'inference')
ss_labels=os.path.join(ss_root,'labels')
ss_data=os.path.join(ss_root,'data')

inf_pattern = re.compile(r'([\d]+)-(infs|mel).npy')
#(time)-(len secs)-(rate)-(channels)
aud_pattern = re.compile(r'([\d]+\.[\d]+)-([\d]+)-([\d]+).raw')


def _index_data(ss_root,for_idx=None):
    for_idx=for_idx or 0
    
    ds=[]

    for _f in glob.glob(ss_inf+'/*-infs.npy'):
        m=inf_pattern.match(os.path.basename(_f))
        if m is None:
            print ('regex miss!')
            continue
        
        mel_fname=_f.replace('infs','mel')
        
        if not os.path.exists(mel_fname):
            print ('mel miss!')
            continue
        
        infs=np.load(_f)
        d=dict(time=float(m.group(1)),
               mel_file=mel_fname)
        d['conf']=infs[for_idx]
        ds.append(d)
        
    return pd.DataFrame(ds)
        
        
    
@app.route('/ss/', methods=['GET'])
def home(**kwargs):
    max_samples = int(request.args.get('max_samples',10))
    confidence=float(request.args.get('confidence',.3))
    class_idx=int(request.args.get('index',0))
    index = _index_data(ss_root=ss_root, for_idx=class_idx)
    print (index)
    for _i in index:
        print (_i)
    return render_template('home.html',
                           index=index[index['conf']>confidence][:max_samples],
                           classes=['a','b','c'],
                           time=time.time())

@app.route('/ss/play', methods=['GET'])
def play(**kwargs):
    aud_time = float(request.args.get('aud_time'))
    duration = request.args.get('aud_duration',10)
    
    mp3_f = utilities._get_wav(d='/tmp/ss/archive/audio',
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

@app.route('/ss/label', methods=['GET'])
def label(**kwargs):
    return 'ok'
    

    