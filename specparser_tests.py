from __future__ import with_statement
import specparser as sp
import datetime, time

datadir = './testdata/'

def headerparse_t(p):
    h = p.header()
    print(h)
    assert(h['filename'] == '/sls/X12SA/Data10/e12608/spec/dat-files/specES1_started_2010_02_25_1420.dat')
    assert(h['epoch'] == 1267104014)
    assert(h['date'] == datetime.datetime.fromtimestamp(time.mktime(time.strptime('Thu Feb 25 14:20:14 2010'))))
    mlist = ['dummy', 'idgap', 'bm1trx', 'bm1try', 'bm2trx', 'bm2try', 'di2trx', 'di2try', 'bm3trx', 'bm3try', 'sl1trxo', 'sl1trxi', 'sl1tryt', 'sl1tryb', 'sl1ch', 'sl1cv', 'sl1wh', 'sl1wv', 'fi1try', 'fi2try', 'fi3try', 'motry', 'motrz1', 'motrz1e', 'mopush1', 'moth1', 'moth1e', 'moroll1', 'motrx2', 'motry2', 'mopush2', 'moth2', 'moth2e', 'mokev', 'moyaw2', 'moroll2', 'mobdai', 'mobdbo', 'mobdco', 'mobddi', 'mobd', 'bm4trx', 'bm4try', 'mitrx', 'mitry1', 'mitry2', 'mitry3', 'mitry', 'mith', 'miroll', 'mibd1', 'mibd2', 'mibd', 'bm5trx', 'bm5try', 'sl2trxo', 'sl2trxi', 'sl2tryt', 'sl2tryb', 'sl2ch', 'sl2cv', 'sl2wh', 'sl2wv', 'sttrx', 'sttry', 'stpush', 'stth', 'ebtrx', 'ebtry', 'ebtrz', 'sl3wv', 'sl3cv', 'sl3wh', 'sl3ch', 'sl4wv', 'sl4cv', 'sl4wh', 'sl4ch', 'ebfi1', 'ebfi2', 'ebfi3', 'ebfi4', 'attrx', 'attry', 'attrz', 'atpush', 'atth', 'bs1x', 'bs1y', 'bs2x', 'bs2y', 'dttrx', 'dttry', 'dttrz', 'dtpush', 'dtth', 'dettrx', 'hx', 'hy', 'hz', 'hrox', 'hroy', 'hroz', 'eyex', 'eyey', 'eyefoc', 'samx', 'samy', 'scatx', 'scaty']
    assert(h['motornames'] == mlist)


def iterate_scans(f, scanlist):
    if isinstance(scanlist[0], dict):
        scans = scanlist
    else:
        scans = scanlist[1:]
    for s in scans:
        f(s)


def scanheader_t(scanlist):
    def sht(s):
        assert(s['ncols'] == len(s['columns']))
    iterate_scans(sht, scanlist)


def nonnil_t(scanlist):
    def nnt(s):
        for val in s['counters'].values():
            assert(val != [])
        for val in s['motors'].values():
            assert(val != [])
    iterate_scans(nnt, scanlist)


def separate_test():
    with open(datadir + 'mini.spec') as fid:
        p = sp.Specparser(fid)
        assert(p.state == p.initialized)
        headerparse_t(p)
        assert(p.state == p.between_scans)


def minispec_test():
    with open(datadir + 'mini.spec') as fid:
        p = sp.Specparser(fid)
        scans = p.parse()
    nonnil_t(scans)
    scanheader_t(scans)


def pickled_test():
    import pickle
    with open(datadir + 'mini.spec') as fid:
        p = sp.Specparser(fid)
        scans = p.parse()
    with open(datadir + 'mini.pickle') as fp:
        pscns = pickle.load(fp)
    assert(pscns[0][-1][0] == scans[0][-1][0])
    hd = scans[0][-1][1]
    phd = pscns[0][-1][1]
    for k in hd.keys():
        print(k)
        assert(phd[k] == hd[k])
    assert(hd == phd)
    for i in range(1, len(scans)):
        print('Scan %d' % i)
        for k in scans[i].keys():
            print('    %s' % k)
            assert(scans[i][k] == pscns[i][k])
    assert(pscns == scans)


def read_simple_test():
    with open(datadir + 'simple.spec') as fid:
        p = sp.Specparser(fid)
        assert(p.state == p.initialized)
        scans = p.parse()
        assert(p.state == p.done)
        for val in scans[2]['counters'].values():
            assert(len(val) == 101)
        assert(scans[1]['motors']['Two Theta'] == 0.8)
        nonnil_t(scans)
        scanheader_t(scans)


def zeroline_test():
    with open(datadir + 'zeroline.spec') as fid:
        p = sp.Specparser(fid)
        assert(p.state == p.initialized)
        scans = p.parse()
        assert(p.state == p.done)
    assert(len(scans) == 1)
    assert(scans[0][-1][1]['epoch'] == 974979799)
    nonnil_t(scans)
    scanheader_t(scans)


def oneline_test():
    with open(datadir + 'oneline.spec') as fid:
        p = sp.Specparser(fid)
        assert(p.state == p.initialized)
        scans = p.parse()
        assert(p.state == p.done)
    assert(scans[0][-1][1]['epoch'] == 974979799)
    assert(len(scans) == 2)
    assert(len(scans[1]['counters'].values()) == 9)
    assert(scans[1]['motors']['Two Theta'] == 0.8)
    nonnil_t(scans)
    scanheader_t(scans)


def comment_end_test():
    with open(datadir + 'endcomment.spec') as fid:
        p = sp.Specparser(fid)
        assert(p.state == p.initialized)
        scans = p.parse()
        assert(p.state == p.done)
    assert(len(scans) == 3)
    assert(scans[1]['motors']['Two Theta'] == 0.8)
    nonnil_t(scans)
    scanheader_t(scans)

