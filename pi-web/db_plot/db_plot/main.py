import numpy as np
import pandas as pd
import argparse
import datetime
import os

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.plotting import figure
from bokeh.palettes import inferno, Category20_20

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from yamnet import yamnet as yamnet_model


palette = Category20_20

start = datetime.datetime.strptime(os.environ.get('DB_PLOT_START'), 
        '%Y-%m-%dT%H:%M:%S')
end = datetime.datetime.strptime(os.environ.get('DB_PLOT_END'), 
        '%Y-%m-%dT%H:%M:%S')
idxs = [int(_n) for _n in os.environ.get('DB_PLOT_IDXS').split(',')]

Base = automap_base()
db_uri = 'postgresql+psycopg2://pi:raspberry@127.0.0.1:5432/ss'

engine = create_engine(db_uri,
                       pool_size=2,
                       echo=False,
                       isolation_level='READ_COMMITTED',
                       pool_recycle=20,
                       pool_pre_ping=True,
                       echo_pool=True)

Base.prepare(engine, reflect=True)

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base.query = db_session.query_property()

Inference = Base.classes.inference

def _get_data(idxs,start,end):
    results = []
    for _n in idxs:
        q = Inference.query.filter(Inference.at >= start).filter(Inference.at < end).filter(Inference.idx == _n).order_by(Inference.at.desc()).all()
        confs=[]
        indexes=[]

        for _next_row in q:
            confs.append(_next_row.conf)
            indexes.append(_next_row.at)
        results.append(pd.Series(confs,indexes))
    df = pd.concat(results,axis=1)
    df.columns=idxs
    return df

# Set up data
data = _get_data(idxs,
                 start,
                 end)

ds={}

time_formatter = DatetimeTickFormatter(
    microseconds=['%H:%M:%S'],
    milliseconds=['%H:%M:%S'],
    seconds=['%H:%M:%S'],
    minsec=['%H:%M:%S'],
    minutes=['%H:%M:%S'],
    hourmin=['%H:%M:%S'],
    hours=['%H:%M:%S'],)

for _n in data.columns:
    print ('d',data[_n])
    ds[_n]= ColumnDataSource(data=dict(t=data[_n].index, conf=data[_n].values))


# Set up plot
plot = figure(plot_height=600, plot_width=900, title="SS Recorder inference:{}".format(idxs),
              tools="crosshair,pan,reset,save,wheel_zoom,box_zoom",
              #x_range=[start,end],
              x_range=[data.index.min(),data.index.max()],
              y_range=[.0,1.])

plot.xaxis.formatter = time_formatter
for _i,_n in enumerate(data.columns):
    plot.circle(x='t',
              y='conf', 
              color=palette[_i],
              source=ds[_n], 
              legend='{} conf'.format(_n),
              line_width=3, 
              line_alpha=0.6)


curdoc().add_root(row( plot, width=800))
curdoc().title = "SS Recorded Inference"
