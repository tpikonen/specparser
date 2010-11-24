import re, logging, time, datetime


# FIXME: Allow multiple headers (for SPEC restarts etc.)


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

    :attr:`curscan`
        The scan dictionary which is currently being read to, or was read
        last.

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
        self.curscan = None
        self.lineno = -1
        # Private variables
        self.__curline = None
        # Get first line
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
        fdict = {}
        while True:
            m = re.match('^#([A-Z]+[A-Z0-9]*) *(.*[^\W]).*$', cl)
            if m == None:
                break
            ltype, lval = m.group(1,2)
            if ltype[0] != 'G':
                break
            ind = int(ltype[1])
            fdict[ind] = map(float, lval.split())
            cl = self.__getline()
        keys = fdict.keys()
        keys.sort()
        fourclist = [ fdict[k] for k in keys ]
        return fourclist


# Public methods

    def header(self):
        """Returns the spec-file header in a dictionary.

        The keys corresponding to spec-file header lines are

        ======  =============== =====
        SPEC    key             value
        ======  =============== =====
        #F      filename        String, original filename.
        #E      epoch           Int, seconds since epoch.
        #D      date            Date in datetime format.
        #On     motornames      List of motorname strings.
        #C      comments        List of [lineno, commentline] lists.
        #x      unknown_headers List of [lineno, linestring] lists.
        ======  =============== =====

        If the complete header is not written to the spec-file after waiting
        :attr:`timeout` seconds, or if some header lines are missing,
        then the header dictionary will be returned incomplete.
        """
        self.state = self.in_header
        logging.debug("Parsing header")
        hdict = {}
        hdict['comments'] = []
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
            elif ltype == 'C':
                # Comments before the first scan
                hdict['comments'].append([self.lineno, cl])
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

        See :meth:`next_scan_header` for the keys in the return value
        dictionary.

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

        return self.curscan


    def next_scan_header(self):
        """Return a dictionary with the contents of the next scan header.

        Can raise InputTimeout if a complete header can not be read.

        The keys corresponding to spec-file header lines are

        ======  =============== =====
        SPEC    key             value
        ======  =============== =====
        #S      number          Integer, the scan number.
        #S      command         String, the command which started the scan.
        #D      date            Date in :mod:`datetime` format.
        #T      time            Float, time per scan point.
        #T      time_units      String, units of time.
        #M      monitor         Float, monitor counts per scan point.
        #M      monitor_units   String, units of monitor counts.
        N/A     counting-to     Either 'time' or 'monitor' depending on
                                which was used to end counting.
        #Gn     fourc           List of four lists giving four-circle values.
        #Q      hklstart        List of HKL coords at the start of the scan.
        #Pn     motorpositions  List of floats giving motor positions at
                                the start of the scan.
        #N      ncols           Integer, number of counter columns.
        #L      columns         Names of the columns in the scan.
        #x      unknown_headers List of [lineno, linestring] headers which
                                were not recognized.
        N/A     npoints         Number of points in the scan (so far).
        N/A     counters        Dictionary with counter names as keys,
                                lists of counter values at each point as values.
        #C      comments        List of [lineno, commentline, pointno] lists.
        ======  =============== =====

        """
        cl = self.__curline
        while cl[0:2] != '#S':
            # FIXME: Reparse motor positions and add comments to previous scan
            if cl[0:2] == '#O' or cl[0:2] == '#C':
                pass
            elif not is_blankline(cl):
                logging.warning('Garbage before scan header: %s' % cl)
            cl = self.__getline()
        self.state = self.in_scan_header
        logging.debug("Parsing scan header")
        sdict = {}
        sdict['npoints'] = 0
        sdict['comments'] = []
        sdict['unknown_headers'] = []
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
            elif ltype == 'C':
                # Comments before the first scan point
                sdict['comments'].append([self.lineno, cl, sdict['npoints']-1])
            else:
                # Unknown line of format #XXnn
                logging.info('Unknown scan header: %s' % cl)
                sdict['unknown_headers'].append([self.lineno, cl])
            cl = self.__getline()
        counters = {}
        for c in sdict['columns']:
            counters[c] = []
        sdict['counters'] = counters
        self.curscan = sdict
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
                if len(pts) != self.curscan['ncols']:
                    logging.error("Invalid number of columns in line")
                    raise ParseError(cl)
                else:
                    self.state = self.in_scan
                    self.lastpoint = pts
                    self.curscan['npoints'] += 1
                    for ctr, val in zip(self.curscan['columns'], pts):
                        self.curscan['counters'][ctr].append(val)
                    cl = self.__getline()
                    break # Got our line
            except ValueError:
                m = re.match('^#([A-Z]+[0-9]*) (.*)$', cl)
                if m == None:
                    logging.error("Bad line in scan")
                    raise ParseError(cl)
                if m.group(1) == 'C':
                    # Add line comments to header
                    self.curscan['comments'].append(\
                        [self.lineno, cl, self.curscan['npoints']-1])
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
                or scans[-1]['number'] == self.curscan['number']-1):
                # Append the last, possibly incomplete scan
                scans.append(self.curscan)
            elif scans != [] \
                and scans[-1]['number'] != self.curscan['number']:
                raise ParseError()
            specdict['scans'] = scans
        self.state = self.done
        return specdict

