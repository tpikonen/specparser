Specparser
==========

Introduction
------------

Specparser is a Python module providing, as the name implies, a parser
for the data files produced by the instrument control software spec_ by
*Certified Scientific Software*. It is pure Python and does not have
dependencies outside of the Python standard library.

.. _spec: http://www.certif.com/

Example usage
-------------

The parser is initialized by giving a file object containing the spec
data file as an argument.

 >>> import specparser
 >>> fid = open('testdata/oneline.spec')
 >>> p = specparser.Specparser(fid)

A Python representation of the full spec data file can be obtained with
the `parse` method.

 >>> scans = p.parse()

The result is a list, where the first item (list element 0) contains a
list of header blocks. Rest of the list elements (starting from 1) are
dictionaries corresponding to spec scans.

 >>> scans[1].keys()
 ['ncols', 'motors', 'number', 'comments', 'time_units', 'date', 'command', 'time', 'npoints', 'unknown_headers', 'counters', 'counting-to', 'fourc', 'columns', 'hklstart']
 >>> scans[1]['counters'].keys()
 ['Monitor', 'Seconds', 'H', 'K', 'Two Theta', 'Epoch', 'Detector 2', 'Detector 3', 'Detector']
 >>> scans[1]['counters']['Detector']
 [1.0]

API
---

Methods header(), next_scan(), next_scan_header(), and next_point() can
be used to read a spec-file incrementally. A typical use case would be
reading the scans or scan points immediately when they are created.

See the code and docstrings for details.

Other similar projects
----------------------

C library called *specfile* has been written at the ESRF_.
Somewhat maintained copy with Python bindings is included with the
sources of PyMca_, see for example here_.

.. _ESRF: http://www.esrf.eu
.. _PyMca: http://pymca.sourceforge.net/index.html
.. _here: http://pymca.svn.sourceforge.net/viewvc/pymca/PyMca/specfile/

License
-------

You can redistribute and/or modify Specparser under the terms of the
GNU General Public License as published by the Free Software Foundation;
either version 2 of the License, or (at your option) any later version.

See http://www.gnu.org/licenses/gpl2.html for the license text.

Author
------

Specparser was written by Teemu Ikonen <tpikonen@gmail.com>.

Copyright
---------
Copyright © 2010-2011 Paul Scherrer Institute (http://www.psi.ch/)
