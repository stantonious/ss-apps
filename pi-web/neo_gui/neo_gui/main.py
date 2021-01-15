""" PI app inference GUI main """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
import numpy as np
import json
import time
import os
from functools import partial
import csv
from threading import Thread
from bokeh.plotting import figure, curdoc
from bokeh.layouts import layout, grid
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.palettes import inferno, Category20_20
from bokeh.models.formatters import DatetimeTickFormatter
from tornado import gen
import pika
import datetime


env_idxs=os.environ.get('INF_IDXS','0')
idxs=[int(_i) for _i in env_idxs.split(',')]

_CLASS_MAPPING = {}
class_mapping_csv = csv.DictReader(
    #open('/opt/audioset/class_labels_indices.csv'))
    open('/opt/soundscene/yamnet_class_map.csv'))
class_names = []

for _n in class_mapping_csv:
    _CLASS_MAPPING[int(_n['index'])] = _n['display_name']

inf_ds={}
for _n in idxs:
    inf_ds[_n]= ColumnDataSource(data=dict(time=[], conf=[]))

moto_int_ds = {}
for _n in range(4):
    moto_int_ds[_n]=ColumnDataSource(data=dict(time=[], intensity=[]))

running_avg_win = 2
running_avg_conv_win = 2
running_avg = None

@gen.coroutine
def update_inf(inferences, idxs,time_step):

    def conv(ys):
        global running_avg
        ys = np.expand_dims(ys, axis=0) if ys.ndim == 1 else ys
        if running_avg is None:
            running_avg = ys
            return ys
        # add another sample
        running_avg = np.concatenate((running_avg, ys), axis=0)
        running_avg = running_avg[-running_avg_win:]

        # compute running avg
        avgs = []
        for _n in running_avg.T:
            t = np.convolve(_n, np.ones(running_avg_conv_win,) /
                            running_avg_conv_win, mode='valid')
            avgs.append(t[-1])
        return avgs

    conf_avgs = conv(inferences)
    conf_avgs_idxs = zip(conf_avgs, idxs)
    for _i, (conf, idx) in enumerate(conf_avgs_idxs):
        inf_ds[idx].stream( dict(time=[datetime.datetime.fromtimestamp(time_step)],
                                 conf=[conf]), rollover=20 )
@gen.coroutine
def update_motor_int(motor_intensities, time_step):
    for _i,motor_int in enumerate(motor_intensities):
        moto_int_ds[_i].stream(
            dict(time=[datetime.datetime.fromtimestamp(time_step)], intensity=[motor_int]),
            rollover=200)

palette = Category20_20

inf_fig = figure(y_range=(0., 1.),
                 plot_width=800,
                 plot_height=800)
motors_fig = figure(y_range=(0., 255.),
                plot_width=800,
                plot_height=800)

time_formatter = DatetimeTickFormatter(
    microseconds=['%H:%M:%S'],
    milliseconds=['%H:%M:%S'],
    seconds=['%H:%M:%S'],
    minsec=['%H:%M:%S'],
    minutes=['%H:%M:%S'],
    hourmin=['%H:%M:%S'],
    hours=['%H:%M:%S'],)

inf_fig.xaxis.formatter = time_formatter
motors_fig.xaxis.formatter = time_formatter

for _i,(_k,_v) in enumerate(inf_ds.items()):
    inf_fig.line(x='time',
                 y='conf',
                 color=palette[_i],
                 legend='{} conf'.format(_k),
                 source=_v,)

for _k,_v in moto_int_ds.items():
    motors_fig.circle(x='time',
                  y='intensity',
                  color=palette[_k],
                  legend='moto{} intensity'.format(_k),
                  source=_v,)

motors_fig.legend.location = "top_right"
motors_fig.legend.background_fill_alpha = .2


app_layout = layout([
    [inf_fig],
    [motors_fig],
], sizing_mode='stretch_both')

doc = curdoc()
doc.add_root(app_layout)
doc.title = 'Neosensory Motor Intensities'

def process_inference_update():
    def _get_d(res, idxs):
        d = json.loads(res)
        sorted_idxs = np.argsort(d['idxs'])
        a = np.stack((d['idxs'], d['inferences']), axis=-1)
        a = a[sorted_idxs][idxs]
        idx = a[..., 0].astype(np.int)
        ys = a[..., 1]
        return idx, ys, d['time']

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    print ('connecting to inference mq',flush=True)

    def _callback(ch, method, properties, body):
        global idxs
        idxs,ys,time=_get_d(body,idxs)
        doc.add_next_tick_callback(partial(update_inf,
                                           inferences=ys,
                                           time_step=time,
                                           idxs=idxs))
    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()


def process_intensity_update():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='buzz',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='buzz')

    print ('connecting to mq',flush=True)

    def _callback(ch, method, properties, body):
        d = json.loads(body)
        hz = d['hz']
        fps = d['fps']


        pattern = np.asarray(d['pattern'])


        pattern = pattern.reshape(hz,fps,4)
        t = int(time.time())
        s = 1.0 / hz

        for _i,_n in enumerate(pattern): # hz
            doc.add_next_tick_callback(partial(update_motor_int,
                                               motor_intensities=_n[0],
                                               time_step=t+_i*s,))
    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()

update_inf_thread = Thread(target=process_inference_update, args=())
update_inf_thread.start()
update_thread = Thread(target=process_intensity_update, args=())
update_thread.start()

