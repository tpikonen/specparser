import re, logging, time, datetime


# Exceptions emitted by the parser
class ParseError(Exception):
    """Raised when the parser encounters a line which is really broken"""
    def __init__(self, line):
        self.line = line
    def __str__(self):
        return repr(self.line)

class InputTimeout(Exception):
    """Raised when input could not be read in self.timeout seconds"""
    pass

class ScanEnd(Exception):
    """Raised when end of scan is encountered when reading points"""
    pass

def is_blankline(line):
    m = re.match('^\W*$', line)
    return (m != None)

WAITTIME = 1.0

class specparser:
    """Parses a scan file from SPEC. The parser can also be used while
    the scan file is being written.

    See http://www.certif.com/spec_manual/user_1_4_1.html for a rough
    description of the file format.
    """
# Class variables
    # Define 'enums' for parser state
    uninitialized, initialized, in_header, between_scans, in_scan_header, \
        in_scan, in_line, done = range(8)

# Constructor and destructor
    def __init__(self, fid):
        self.__fid = fid
        self.state = initialized
        # Time (in seconds) to wait for the next line before giving up
        self.timeout = 0
        # Copies of spec-file header, current scan header
        # and points of the current line in scan
        self.fileheader = None
        self.scanheader = None
        self.points = None
        self.lineno = -1
        # Private variables
        self.__curline = None
        self.__getline()

    def __del__(self):
        self.__fid.close()

# Private methods

    def __getline(self):
        """Return the next line, or raise InputTimeout exception"""
        try:
            self._curline = (self.fid.next())[:-1] # Clip the newline
            self.lineno = self.lineno + 1
        except StopIteration:
            if self.timeout <= 0.0:
                raise(InputTimeout)
            starttime = time.clock()
            while True:
                time.sleep(WAITTIME)
                try:
                    self._curline = self.fid.next()
                    break
                except StopIteration:
                    if (time.clock() - starttime) > self.timeout:
                        raise(InputTimeout)
        return self._curline


    def __parse_motornames(self):
        cl = self._curline
        n = 0
        motorlist = []
        while True:
            m = re.match('^#([A-Z]+[A-Z0-9]*) *(.*[^\W]).*$', cl)
            if m == None:
                break
            ltype, lval = m.group(1,2)
            if ltype != ('O%d' % n):
                break
            # Motor names are separated by two spaces
            motorlist.extend(re.split(r'  +', lval))
            cl = self.__getline()
            n = n+1
        return motorlist


    def __parse_motorpositions(self):
        cl = self._curline
        n = 0
        poslist = []
        while True:
            m = re.match('^#([A-Z]+[A-Z0-9]*) *(.*[^\W]).*$', cl)
            if m == None:
                break
            ltype, lval = m.group(1,2)
            if ltype != ('P%d' % n):
                break
            poslist.extend(map(float, lval.split()))
            cl = self.__getline()
            n = n+1
        return poslist


    def __parse_fourc(self):
        cl = self._curline
        fourclist = [None, None, None, None, None] # FIXME: More than 5?
        while True:
            m = re.match('^#([A-Z]+[A-Z0-9]*) *(.*[^\W]).*$', cl)
            if m == None:
                break
            ltype, lval = m.group(1,2)
            if ltype[0] != 'G':
                break
            ind = int(ltype[1])
            fourclist[ind] = map(float, lval.split())
            cl = self.__getline()
        return fourclist


# Public methods

    def header(self):
        """Returns the spec-file header in a dictionary.

        The keys corresponding to spec-file header lines are

        ======  =============== =====
        SPEC    key             value
        ======  =============== =====
        #F      filename        string
        #E      epoch           int, seconds since epoch
        #D      date            date in datetime format
        #On     motornames      list of strings
        #x      unknown_headers list of [lineno, linestring] lists
        ======  =============== =====

        If the complete header is not written to the spec-file after waiting
        :attr:`timeout` seconds, or if some header lines are missing,
        then the header dictionary will be returned incomplete.
        """
        self.state = self.in_header
        logging.debug("Parsing header")
        hdict = {}
        hdict['unknown_headers'] = []
        cl = self._curline
        while is_blankline(cl):
            try:
                cl = self.__getline()
            except InputTimeout:
                logging.warning('InputTimeout before header')
                return hdict
        while True:
            m = re.match('^#([A-Z]+[0-9]*) (.*)$', cl)
            if m == None:
                break
            ltype, lval = m.group(1,2)
            if ltype == 'F':
                # Filename, original
                hdict['filename'] = lval
            elif ltype == 'E':
                # Epoch, seconds since
                hdict['epoch'] = int(lval)
            elif ltype == 'D':
                # Date in datetime format for proper yaml serialization
                # FIXME: Find out timezone info by comparing epoch and  date?
                hdict['date'] = datetime.datetime.fromtimestamp(\
                    time.mktime(time.strptime(lval)))
            elif ltype == 'O0':
                hdict['motornames'] = self.__parse_motornames()
                cl = self._curline
                continue # Start again with the last line
            else:
                # Unknown line of format #XXnn
                logging.info('Unknown header: %s' % cl)
                hdict['unknown_headers'].append([self.lineno, cl])
            try:
                cl = self.__getline()
            except InputTimeout:
                cl = ''
        if not is_blankline(cl):
            logging.warning("Garbage after header: %s" % cl)
        self.fileheader = hdict
        self.state = self.between_scans
        return hdict


    def next_scan(self):
        """Return a dictionary with the contents of the next scan in the
        parsed file, or a Timeout exception.

        In addition to the keys in the scan header
        (see :method:`next_scan_header` for the scan header keys) the
        following keys and values are present

        ==============  ================
        key             value
        ==============  ================
        points          list of point lists
        point_comments  list of [pointnum, commentline] lists
        ==============  ================

        If the complete scan is not written to the spec-file after waiting
        :attr:`timeout` seconds, then the scan dictionary will be returned
        incomplete.
        """
        self.next_scan_header()
        try:
            while True:
                self.next_point()
        except ScanEnd:
            pass
        sdict = self.scanheader
        sdict['points'] = self.points
        return sdict


    def next_scan_header(self):
        """Return a dictionary with the contents of the header of the
        next scan in the parsed file, or InputTimeout"""
        self.state = self.in_scan_header
        cl = self._curline
        while cl[0:2] != '#S':
            if not is_blankline(cl):
                logging.warning('Garbage before scan header: %s' % cl)
            cl = self.__getline()
        logging.debug("Parsing scan header")
        sdict = {}
        sdict['unknown_headers'] = []
        sdict['point_comments'] = []
        while True:
            m = re.match('^#([A-Z]+[0-9]*) (.*)$', cl)
            if m == None:
                break
            ltype, lval = m.group(1,2)
            if ltype == 'S':
                # Scan start
                try:
                    sm = re.match('^(\d+) +(.*)', lval)
                    sdict['number'] = int(sm.group(1))
                    sdict['command'] = sm.group(2)
                except:
                    logging.error('Invalid Scan header: %s' % cl)
            elif ltype == 'D':
                # Date in datetime format for proper yaml serialization
                sdict['date'] = datetime.datetime.fromtimestamp(\
                    time.mktime(time.strptime(lval)))
            elif ltype == 'T':
                # Counting to time, n sec. per point
                sdict['counting-to'] = 'time'
                tl = lval.split()
                sdict['time'] = float(tl[0]) # FIXME: try.... except
                sdict['time_units'] = tl[1]
            elif ltype == 'M':
                # Counting to monitor, n counts per point
                sdict['counting-to'] = 'monitor'
                tl = lval.split()
                sdict['monitor'] = float(tl[0]) # FIXME: try.... except
                sdict['monitor_units'] = tl[1]
            elif ltype == 'G0':
                # Four-circle parameters
                sdict['fourc'] = self.__parse_fourc()
                cl = self._curline
                continue # Start again with the last line
            elif ltype == 'Q':
                # HKL coordinates at the start of the scan
                sdict['hklstart'] = map(int, lval.split())
            elif ltype == 'P0':
                # Motor position at the start of the scan
                sdict['motorpositions'] = self.__parse_motorpositions()
                cl = self._curline
                continue
            elif ltype == 'N':
                # Number of columns in a scan
                sdict['ncols'] = int(lval)
            elif ltype == 'L':
                # Motor names in the scan
                lclean = re.search('\W*(.*[^\W]+).*', lval).group(1)
                sdict['columns'] = re.split('  +', lclean)
            else:
                # Unknown line of format #XXnn
                logging.info('Unknown scan header: %s' % cl)
                sdict['unknown_headers'].append([self.lineno, cl])
            cl = self.__getline()
        self.scanheader = sdict
        self.points = []
        self.state = self.in_scan
        return sdict


    def next_point(self):
        """Return a list with values of the next point on the scan,
        or raise either InputTimeout or ScanEnd exception"""
        self.state = self.in_line
        cl = self._curline
        while True:
            if is_blankline(cl):
                self.state = self.between_scans
                raise(ScanEnd)
            try:
                pts = map(float, cl.split())
                if len(pts) != self.scanheader['ncols']:
                    logging.error("Invalid number of columns in line")
                    raise ParseError(cl)
                else:
                    self.state = self.in_scan
                    cl = self.__getline()
                    break # Got our line
            except ValueError:
                m = re.match('^#([A-Z]+[0-9]*) (.*)$', cl)
                if m == None:
                    logging.error("Bad line in scan")
                    raise ParseError(cl)
                if m.group(1) == 'C':
                    # Add line comments to header
                    self.scanheader['point_comments'].append(\
                        [len(self.points), cl])
                    cl = self.__getline()
                else:
                    # Control line other than a comment ends the scan
                    self.state = self.between_scans
                    raise(ScanEnd)
        self.points.append(pts)
        return pts


    def parse(self):
        """Returns the specfile (possibly incomplete) in a dictionary"""
        specdict = {}
        scans = []
        try:
            specdict['header'] = self.header()
            while True:
                scans.append(self.next_scan())
        except InputTimeout:
            specdict['scans'] = scans
        self.state = self.done
        return specdict

