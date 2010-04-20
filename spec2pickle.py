import sys, specparser, pickle

def spec2pickle(infname, outfname):
    p = specparser.specparser(open(infname))
    dd = p.parse()
    fout = open(outfname, 'w')
    pickle.dump(dd, fout)
    fout.close()

def main():
    spec2pickle(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()

