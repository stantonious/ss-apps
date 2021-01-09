""" PI app inference GUI main """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"
import numpy as np
import json
import time
from functools import partial
import csv
import subprocess
from threading import Thread, Lock
from bokeh.plotting import figure, curdoc
from bokeh.layouts import layout, grid
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.palettes import inferno, Category20_20
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models.widgets import Button
from tornado import gen
import pika
import datetime

_CLASS_MAPPING = {}
class_mapping_csv = csv.DictReader(
    #open('/opt/audioset/class_labels_indices.csv'))
    open('/opt/soundscene/yamnet_class_map.csv'))
class_names = []

for _n in class_mapping_csv:
    _CLASS_MAPPING[int(_n['index'])] = _n['display_name']

moto_int_ds = [ ColumnDataSource(data=dict(pos=[], y=[])),
                ColumnDataSource(data=dict(pos=[], y=[])),
                ColumnDataSource(data=dict(pos=[], y=[])),
                ColumnDataSource(data=dict(pos=[], y=[])) ]

@gen.coroutine
def update(motor_intensities, time_step):
    for _i,motor_int in enumerate(motor_intensities):
        moto_int_ds[_i].stream(
            dict(pos=[motor_int], y=[time_step]), rollover=1)

palette = Category20_20

line_p = figure(y_range=(0., 255.),
                plot_width=800,
                plot_height=800)

line_p.xaxis.formatter = DatetimeTickFormatter(
    microseconds=['%H:%M:%S'],
    milliseconds=['%H:%M:%S'],
    seconds=['%H:%M:%S'],
    minsec=['%H:%M:%S'],
    minutes=['%H:%M:%S'],
    hourmin=['%H:%M:%S'],
    hours=['%H:%M:%S'],)

for _i,_n in enumnerate(moto_int_ds):
    line_p.line(x='time',
                y='y',
                color=palette[_i],
                legend=cname,
                # line_width=2,
                line_dash='dashed',
                source=_n, )

line_p.legend.location = "top_right"
line_p.legend.background_fill_alpha = .2


app_layout = layout([
    [line_p],
    # Uncomment to add pause capability
    #[button, button_pause],
], sizing_mode='stretch_both')

doc = curdoc()
doc.add_root(app_layout)
doc.title = 'Neosensory Motor Intensities'

def process_intensity_update():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    #channel.exchange_declare(exchange='buzz',
    #                         exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='buzz')

    def _callback(ch, method, properties, body):
        d = json.loads(body)
        hz = d['hz']
        fps - d['fps']

        pattern = np.asarray(d['pattern'])

        pattern = pattern.reshape(hz,fps,4)
        t = int(time.time())
        s = 1.0 / hz

        for _i,_n in enumerate(pattern): # hz
            doc.add_next_tick_callback(partial(update,
                                               motor_intensities=_n[0],
                                               time_step=t+_i*s,))
    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()

update_thread = Thread(target=process_intensity_update, args=())

