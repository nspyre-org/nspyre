from collections import OrderedDict
import traceback
import time

import json
import pymongo
import pandas as pd

from nspyre.misc.misc import get_mongo_client

def get_exp_state_from_db(mongodb_addr=None, debug=False):
    c = get_mongo_client(mongodb_addr=mongodb_addr)

    state = OrderedDict()
    dbs = [dbname for dbname in c.list_database_names() if 'Instrument_Server' in dbname]
    for dbname in dbs:
        for dname in c[dbname].list_collection_names():
            dev_col = c[dbname][dname]
            state[dname] = OrderedDict()
            try:
                for param in dev_col.find({},{'_id':False, 'name':True, 'type':True, 'units':True, 'value':True}):
                    if 'type' in param and 'name' in param:
                        if param['type'] == 'feat':
                            if param['units'] is None:
                                state[dname][param['name']] = param['value']
                            else:
                                state[dname][param['name']] = str(param['value']) + " " + param['units']
                        elif param['type'] == 'dictfeat':
                            if param['units'] is None:
                                state[dname][param['name']] = param['value']
                            else:
                                state[dname][param['name']] = [str(val) + " " + param['units'] for val in param['value']]
            except:
                print("Could not save the state for device: {}".format(dname))
                if debug: traceback.print_exc()
    return state

def gen_exp_state(mode='current', mongodb_addr=None, debug=False):
    if mode == 'current':
        return get_exp_state_from_db(mongodb_addr=mongodb_addr, debug=debug)
    # elif mode =='renew':
    #     #Here will directly query all the instrument for their states
    #     raise NotImplementedError()
    #     state_dict = OrderedDict()
    #     try:
    #         m = Instrument_Manager()
    #     except:
    #         print("Could not start the instrument manager")
    #         if debug: traceback.print_exc()
    # elif mode == 'disable':
    #     return {}
    else:
        raise Exception("Invalid mode to generate the experimental state")

def save_data(spyrelet, filename, name=None, description=None, save_state_mode='current', debug=False, **kwargs):
    d = spyrelet.data.drop(['_id'], axis=1)
    data_dict = OrderedDict([
        ('name',name),
        ('description',description),
        ('spyrelet_name',spyrelet.name),
        ('spyrelet_class',"{}.{}".format(spyrelet.__class__.__module__, spyrelet.__class__.__name__)),
        ('date', time.strftime('%Y-%m-%d')),
        ('time', time.strftime('%H:%M:%S')),
        ('save_format', 'spyrelet 1.0'),
        ('experimental_state', None),
        ('data_col', list(d.columns)),
        ('data', d.to_json(orient='values')),
    ])

    try:
        child_dict = OrderedDict()
        for c_name, data_list in spyrelet.child_data.items():
            c_real_name = next(real_name for real_name, obj in spyrelet.spyrelets.items() if obj.name == c_name)#This is not ideal...
            child_dict[c_name] = OrderedDict([
                ('spyrelet_class',"{}.{}".format(getattr(spyrelet,c_real_name).__class__.__module__, getattr(spyrelet,c_real_name).__class__.__name__)),
                ('data_col', list(data_list[0].drop(['_id'], axis=1).columns)),
                ('data_list',[dl.drop(['_id'], axis=1).to_json(orient='values') for dl in data_list]),
            ])
        data_dict['children'] = child_dict
    except:
        print("Could generate child dict")
        data_dict['children'] = child_dict
        if debug: traceback.print_exc()

    #This takes care of writting the experimental state
    state_dict = dict()
    try:
        if not save_state_mode is None:
            state_dict = gen_exp_state(mode=save_state_mode, debug=debug)
    except:
        print("Could generate state dict")
        if debug: traceback.print_exc()

    #Write the file
    finally:
        data_dict['experimental_state'] = state_dict
        data_dict.update(kwargs)

        if filename is None:
            return data_dict
        else:
            with open(filename, 'w') as f:
                results = json.dump(data_dict, f, indent=4)
            return results

def load_data(filename, load_to_mongo=False, mongodb_addr=None, db_name='Spyre_Data_Loaded'):
    with open(filename, 'r') as f:
        ans = json.load(f)
    ans['data'] = pd.read_json(ans['data']).rename(columns={i:x for i,x in enumerate(ans['data_col'])})

    for c_name, c_dict in ans['children'].items():
        data_list = list()
        for d in c_dict['data_list']:
            data_list.append(pd.read_json(d).rename(columns={i:x for i,x in enumerate(c_dict['data_col'])}))
        ans['children'][c_name]['data_list'] = data_list

    if load_to_mongo:
        client = get_mongo_client(mongodb_addr)
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
