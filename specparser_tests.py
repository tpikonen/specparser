import specparser as sp
import datetime, time


def headerparse_t(p):
    h = p.header()
    print(h)
    assert(h['filename'] == '/sls/X12SA/Data10/e12608/spec/dat-files/specES1_started_2010_02_25_1420.dat')
    assert(h['epoch'] == 1267104014)
    assert(h['date'] == datetime.datetime.fromtimestamp(time.mktime(time.strptime('Thu Feb 25 14:20:14 2010'))))
    mlist = ['dummy', 'idgap', 'bm1trx', 'bm1try', 'bm2trx', 'bm2try', 'di2trx', 'di2try', 'bm3trx', 'bm3try', 'sl1trxo', 'sl1trxi', 'sl1tryt', 'sl1tryb', 'sl1ch', 'sl1cv', 'sl1wh', 'sl1wv', 'fi1try', 'fi2try', 'fi3try', 'motry', 'motrz1', 'motrz1e', 'mopush1', 'moth1', 'moth1e', 'moroll1', 'motrx2', 'motry2', 'mopush2', 'moth2', 'moth2e', 'mokev', 'moyaw2', 'moroll2', 'mobdai', 'mobdbo', 'mobdco', 'mobddi', 'mobd', 'bm4trx', 'bm4try', 'mitrx', 'mitry1', 'mitry2', 'mitry3', 'mitry', 'mith', 'miroll', 'mibd1', 'mibd2', 'mibd', 'bm5trx', 'bm5try', 'sl2trxo', 'sl2trxi', 'sl2tryt', 'sl2tryb', 'sl2ch', 'sl2cv', 'sl2wh', 'sl2wv', 'sttrx', 'sttry', 'stpush', 'stth', 'ebtrx', 'ebtry', 'ebtrz', 'sl3wv', 'sl3cv', 'sl3wh', 'sl3ch', 'sl4wv', 'sl4cv', 'sl4wh', 'sl4ch', 'ebfi1', 'ebfi2', 'ebfi3', 'ebfi4', 'attrx', 'attry', 'attrz', 'atpush', 'atth', 'bs1x', 'bs1y', 'bs2x', 'bs2y', 'dttrx', 'dttry', 'dttrz', 'dtpush', 'dtth', 'dettrx', 'hx', 'hy', 'hz', 'hrox', 'hroy', 'hroz', 'eyex', 'eyey', 'eyefoc', 'samx', 'samy', 'scatx', 'scaty']
    assert(h['motornames'] == mlist)


def separate_test():
    fname = 'mini.spec'
    fid = open(fname)
    p = sp.Specparser(fid)
    assert(p.state == p.initialized)
    headerparse_t(p)
    assert(p.state == p.between_scans)
    fid.close() 

def nonnil_points_test():
    fname = 'mini.spec'
    fid = open(fname)
    p = sp.Specparser(fid)
    fname = 'mini.spec'
    fid = open(fname)
    p = sp.Specparser(fid)
    ms = p.parse()
    for s in ms['scans']:
        for p in s['points']:
            assert(p != [])
    

def pickled_test():
    import pickle
    fs = open('mini.spec')
    p = sp.Specparser(fs)
    ms = p.parse()
    fp = open('mini.pickle')
    mp = pickle.load(fp)
    fs.close()
    fp.close()
    for k in ms['header'].keys():
        print(k)
        assert(ms['header'][k] == mp['header'][k])
    for i in range(len(ms['scans'])):
        print('Scan %d' % i)
        for k in ms['scans'][i].keys():
            print('    %s' % k)
            assert(ms['scans'][i][k] == mp['scans'][i][k])
    assert(mp == ms)
