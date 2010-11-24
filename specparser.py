import re, logging, time, datetime


# Exceptions emitted by the parser
class ParseError(Exception):
    """Raised when the parser encounters a line which it cannot interpret"""
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

class Specparser:
    """Parses a scan file from SPEC.

    This parser can also be used while the scan file is being written.

    Instance variables:

    :attr:`state`
        The current state of the parser, one of (self.)initialized,
        in_header, between_scans, in_scan_header, in_scan, in_line,
        done.

    :attr:`timeout`
        Time in seconds to wait for more input, when reading in an
        incomplete file

    :attr:`fileheader`
        Header dictionary of the spec-file. Available, if it has been
        previously read with the :meth:`header` method.

    :attr:`scanheader`
        Header of the last read scan.

    :attr:`points`
        List of points which have been read so far from the current scan.

    :attr:`counters`
        Dictionary with counter names (scan columns) as keys. The values
        are lists of point values read so far from the current scan.
        This variable contains the same information as `points`, but
        organized by counter name instead of index. Counter indices can
        shift for example when the number of motors used for the scan changes
        (i.e. meshscan vs. ascan).

    :attr:`lineno`
        Current position in the file as line number.

    See http://www.certif.com/spec_manual/user_1_4_1.html for a rough
    description of the file format.
    """
# Class variables
    # Define 'enums' for parser state
    uninitialized, initialized, in_header, between_scans, in_scan_header, \
        in_scan, in_line, done = range(8)

# Constructor and destructor
    def __init__(self, fid):
        """Create a specparser instance from a file object."""
        self.__fid = fid
        self.state = self.initialized
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
            self.__curline = (self.__fid.next())[:-1] # Clip the newline
            self.lineno = self.lineno + 1
        except StopIteration:
            if self.timeout <= 0.0:
                raise(InputTimeout)
            starttime = time.clock()
            while True:
                time.sleep(WAITTIME)
                try:
                    self.__curline = self.__fid.next()
                    break
                except StopIteration:
                    if (time.clock() - starttime) > self.timeout:
                        raise(InputTimeout)
        return self.__curline


    def __parse_motornames(self):
        cl = self.__curline
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
        cl = self.__curline
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
        cl = self.__curline
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


    def __construct_scandict(self):
        sdict = self.scanheader
        sdict['points'] = self.points
        sdict['counters'] = self.counters
        return sdict


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
        cl = self.__curline
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
                cl = self.__curline
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
        (see :meth:`next_scan_header` for the scan header keys) the
        following keys and values are present

        ==============  ================
        key             value
        ==============  ================
        points          list of point lists, see :meth:`next_point`
        comments        list of [pointnumber, commentline] lists
        counters        dictionary with counter names as keys,
                        lists of counter values at each point as values.
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

        return self.__construct_scandict()


    def next_scan_header(self):
        """Return a dictionary with the contents of the next scan header.

        Can raise InputTimeout if a complete header can not be read.

        The keys corresponding to spec-file header lines are

        ======  =============== =====
        SPEC    key             value
        ======  =============== =====
        #S      number          integer, number of scan
        #S      command         string, the spec command which started the scan
        #D      date            date in :mod:`datetime` format
        #T      time            float, time per scan point
        #T      time_units      string, units of time
        #M      monitor         float, monitor counts per scan point
        #M      monitor_units   string, units of monitor counts
        N/A     counting-to     either 'time' or 'monitor' depending on which was used to end counting
        #Gn     fourc           List of four lists giving four-circle parameters
        #Q      hklstart        List of HKL coordinates at the start of the scan
        #Pn     motorpositions  List of motor positions (floats) at the start of the scan
        #N      ncols           integer, number of columns in a single scan point
        #L      columns         Names of the columns in the scan
        #x      unknown_headers List of [lineno, linestring] headers not recognized
        ======  =============== =====

        """
        self.state = self.in_scan_header
        cl = self.__curline
        while cl[0:2] != '#S':
            if cl[0:2] == '#O' or cl[0:2] == '#C':
                pass
            elif not is_blankline(cl):
                logging.warning('Garbage before scan header: %s' % cl)
            cl = self.__getline()
        logging.debug("Parsing scan header")
        sdict = {}
        sdict['unknown_headers'] = []
        sdict['comments'] = []
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
                cl = self.__curline
                continue # Start again with the last line
            elif ltype == 'Q':
                # HKL coordinates at the start of the scan
                sdict['hklstart'] = map(float, lval.split())
            elif ltype == 'P0':
                # Motor position at the start of the scan
                sdict['motorpositions'] = self.__parse_motorpositions()
                cl = self.__curline
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
        self.counters = {}
        for c in sdict['columns']:
            self.counters[c] = []
        self.state = self.in_scan
        return sdict


    def next_point(self):
        """Return a list with float values of the next point on the scan.

        Can raise either InputTimeout or ScanEnd exception."""
        self.state = self.in_line
        cl = self.__curline
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
                    self.points.append(pts)
                    for i in range(len(self.scanheader['columns'])):
                        self.counters[self.scanheader['columns'][i]].append(pts[i])
                    cl = self.__getline()
                    break # Got our line
            except ValueError:
                m = re.match('^#([A-Z]+[0-9]*) (.*)$', cl)
                if m == None:
                    logging.error("Bad line in scan")
                    raise ParseError(cl)
                if m.group(1) == 'C':
                    # Add line comments to header
                    self.scanheader['comments'].append(\
                        [len(self.points), cl])
                    self.state = self.in_scan
                    cl = self.__getline()
                else:
                    # Control line other than a comment ends the scan
                    self.state = self.between_scans
                    raise(ScanEnd)

        return pts


    def parse(self):
        """Return a dictionary with the information of the specfile.

        This function will return after waiting :attr:`timeout` seconds
        and can return an incomplete dictionary.

        The complete dictionary has the following keys:

        ==============  ================
        key             value
        ==============  ================
        header          header dictionary of the spec-file, see :meth:`header`
        scans           list of scan dictionaries, see :meth:`next_scan`
        ==============  ================
        """
        specdict = {}
        scans = []
        try:
            specdict['header'] = self.header()
            while True:
                scans.append(self.next_scan())
        except InputTimeout:
            if self.state == self.in_scan and (scans == [] \
                or scans[-1]['number'] == self.scanheader['number']-1):
                # Append the last, possibly incomplete scan
                scans.append(self.__construct_scandict())
            elif scans != [] \
                and scans[-1]['number'] != self.scanheader['number']:
                raise ParseError()
            specdict['scans'] = scans
        self.state = self.done
        return specdict

