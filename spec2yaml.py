import sys, specparser, yaml

def spec2yaml(infname, outfname):
    p = specparser.specparser(open(infname))
    dd = p.parse()
    fout = open(outfname, 'w')
    yaml.dump(dd, fout)
    fout.close()

def main():
    spec2yaml(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()

