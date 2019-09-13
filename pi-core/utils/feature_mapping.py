'''
Created on Jul 17, 2018

@author: bstaley
'''

import pandas as pd


def get_feature_mapping(f):
    return pd.read_csv(f)


def get_idx_for_mid(df, mid):
    return df.iloc[df.loc[df['mid'] == mid].index[0]]['index']


def get_mid_for_idx(df, idx):
    return df.iloc[df.loc[df['index'] == idx].index[0]]['mid']


def get_mid_for_name(df, name):
    return df.iloc[df.loc[df['display_name'] == name].index[0]]['mid']


def get_name_for_idx(df, idx):
    return df.iloc[df.loc[df['index'] == idx].index[0]]['display_name']


def get_name_for_mid(df, mid):
    return df.iloc[df.loc[df['mid'] == mid].index[0]]['display_name']


def get_idxs_for_mids(df, mids):
    results = []

    for mid in mids:
        results.append(get_idx_for_mid(df, mid))
    return results


def get_mids_for_names(df, names):
    results = []

    for n in names:
        results.append(get_mid_for_name(df, n))
    return results


def get_class_mapping(df, mids):
    mapping = []
    c_cnt = 0
    for mid in mids:
        mapping.append((mid, c_cnt, get_idx_for_mid(df, mid)))
        c_cnt += 1

    return mapping


def get_name_for_cm_idx(df, cm, cm_idx):
    for n in cm:
        if n[1] == cm_idx:
            return get_name_for_idx(df, n[2])
    raise Exception('idx %s not found' % cm_idx)
