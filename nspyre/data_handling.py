from nspyre.utils import custom_encode, custom_decode, connect_to_master, get_configs
from collections import OrderedDict
import json
import pymongo
import pandas as pd
from nspyre.instrument_manager import Instrument_Manager
import traceback
# from lantz import Q_

def gen_exp_state(debug=False):
    state_dict = OrderedDict()
    try:
        m = Instrument_Manager()
    except:
        print("Could not start the instrument manager")
        if debug: traceback.print_exc()

    cfg = get_configs()

    if 'experimental_state' in cfg and \
        'device_feat' in cfg['experimental_state'] and \
        not cfg['experimental_state']['device_feat'] is None:
        for name, vals in cfg['experimental_state']['device_feat'].items():
            try:
                ans = getattr(m.get(vals[0])['dev'],vals[1])
                # if type(ans) == Q_:
                #     ans = {'__type__':'Quantity', 'm':ans.m, 'units':str(ans.units)}
                state_dict[name] = str(ans)
            except:
                print("Could not save {}".format(name))
                if debug: traceback.print_exc()
    if 'experimental_state' in cfg and \
        'device_dictfeat' in cfg['experimental_state'] and \
        not cfg['experimental_state']['device_dictfeat'] is None:
        for name, vals in cfg['experimental_state']['device_dictfeat'].items():
            try:
                ans = getattr(m.get(vals[0])['dev'],vals[1])[vals[2]]
                # if type(ans) == Q_:
                #     ans = {'__type__':'Quantity', 'm':ans.m, 'units':str(ans.units)}
                state_dict[name] = str(ans)
            except:
                print("Could not save {}".format(name))
                if debug: traceback.print_exc()
    return state_dict

def save_data(spyrelet, filename, name=None, description=None, save_state = True, debug=False):
    d = spyrelet.data.drop(['_id'], axis=1)
    data_dict = OrderedDict([
        ('dataset',name),
        ('description',description),
        ('spyrelet_name',spyrelet.name),
        ('spyrelet_class',"{}.{}".format(spyrelet.__class__.__module__, spyrelet.__class__.__name__)),
        ('data_col', list(d.columns)),
        ('data', d.to_json(orient='values')),
    ])

    child_dict = OrderedDict()
    for c_name, data_list in spyrelet.child_data.items():
        child_dict[c_name] = OrderedDict([
            ('spyrelet_class',"{}.{}".format(getattr(spyrelet,c_name).__class__.__module__, getattr(spyrelet,c_name).__class__.__name__)),
            ('data_col', list(data_list[0].drop(['_id'], axis=1).columns)),
            ('data_list',[dl.drop(['_id'], axis=1).to_json(orient='values') for dl in data_list]),
        ])
    data_dict['children'] = child_dict

    #This takes care of writting the experimental state
    try:
        state_dict = gen_exp_state(debug=debug) if save_state else {}
    except:
        print("Could generate state dict")
        state_dict = dict()
        if debug: traceback.print_exc()

    #Write the file
    finally:
        data_dict['experimental_state'] = state_dict
        if filename is None:
            return data_dict
        else:
            with open(filename, 'w') as f:
                results = json.dump(data_dict, f)
            return results

def load_data(filename, mongodb_addrs=None, db_name='Spyre_Data_Loaded'):
    with open(filename, 'r') as f:
        ans = json.load(f)
    ans['data'] = pd.read_json(ans['data']).rename(columns={i:x for i,x in enumerate(ans['data_col'])})

    for c_name, c_dict in ans['children'].items():
        data_list = list()
        for d in c_dict['data_list']:
            data_list.append(pd.read_json(d).rename(columns={i:x for i,x in enumerate(c_dict['data_col'])}))
        ans['children'][c_name]['data_list'] = data_list

    if not mongodb_addrs is None:
        client = connect_to_master(mongodb_addrs)
        client.drop_database(db_name)
        db = client[db_name]
        def add_spyrelet_data(sname, sclass, data):
            reg_entry = {'_id':sname,'class':sclass}
            db['Register'].update_one({'_id':sname},{'$set':reg_entry}, upsert=True)
            db[sname].insert_many(data.to_dict(orient='records'))
        
        add_spyrelet_data(ans['spyrelet_name'], ans['spyrelet_class'], ans['data'])
        for c_name, c_dict in ans['children'].items():
            for i, d in enumerate(c_dict['data_list']):
                add_spyrelet_data(c_name+'_'+str(i), c_dict['spyrelet_class'], d)
    return ans
