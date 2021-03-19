# -*- coding: utf-8 -*-
"""
Interface for reading numeric data from a log file.

Efficiently reads and parses data from the log file. To start,
initialize a Log object on the file of interest. To pull log data,
request a log using Log.get_log(), providing the log number and
delimeter.

If something isn't parsing quite right, you can read a range of data
using read_data_in_range(), providing the start, stop, and delimeter.

Supports different standard formats for log headers. These are
specified when initializing an object.

Revisions:
    v0.0.1: Supports PuTTY .log files.
    v1.0.0: Add support for SignalExpress, NI Virtual Bench logs.

Copyright (C) 2021  Ben Hubbard

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Ben Hubbard / v1.0.0
"""

import re


# Text interpreter settings
# TODO: allow user to provide their own regex format. Make these
#       built-ins.
log_start_formats = {
    'lvm': re.compile(      # NI Signal Express
        r"""
        ^            # Start of the line
        (Test_Name)  # .lvm log start.
        """, re.VERBOSE),
    'lvmspl': re.compile(  # NI Signal Express Sound pressure data.
        r"""
        ^           # Start of the line
        (Packet_Notes)
        """, re.VERBOSE),
    'putty': re.compile(    # PuTTY log
        r'''
        ^           # Start of the line
        ([^=~]*)    # Anything not = or ~ (for header on line w/ data)
        (=~)        # Putty log start.
        ''', re.VERBOSE),
    'nivb': re.compile(     # NI Virtual Bench
        r"""            # There is no appending here, but the first
        (NI\sVB-\d*)    # line identifies the bench in use.
        """, re.VERBOSE),
        }
date_format = re.compile(
        r"""
        \d{4}   # YYYY
        [/.]
        \d{2}   # MM
        [/.]
        \d{2}   # DD
        """, re.VERBOSE)
time_format = re.compile(
        r"""
        \d\d    # HH
        :
        \d\d    # MM
        :
        \d\d    # SS
        """, re.VERBOSE)


class Log:
    """
    Interfaces with a single log file.

    Parses Date, Start Time, and Data for all of the logs within a
    given .log file.

    Finds all individual logs within the file upon initialization,
    allowing for on-demand collection of data from those logs.

    Arguments
    ---------
        filepath -- Name of the file to read from.
        log_type -- Name of log header style.
    """

    def __init__(self, filepath, log_type, encoding="utf8"):
        """
        Parse the file for logs and return self to query the file.

        Inputs
        ------
            filepath -- path to the logfile, including extension
            log_type -- name specifying header style
            encoding -- encoding of the file. (default="utf8")
        """
        self.__encoding = "utf8"

        # Enforce log_type to exist in log_start_format.
        log_type = log_type.lower()
        supported_types = log_start_formats.keys()
        if log_type not in supported_types:
            raise ValueError(
                f"Log.__init__: log_type must be one of {supported_types}")
        # Set the log type.
        self.__log_start_format = log_start_formats[log_type]

        self.path = filepath
        # Immediately search out all of the log starts.
        self.__log_idxs = self.__find_log_starts()
        self.n_logs = len(self.__log_idxs)
        # Check for no logs
        # assert self.n_logs, "No logs found. Check your log_type."
        # Allocate a dictionary for each log's data.
        self.__init_dat()
        self.__read_header()

    # Data recognition. Edge cases handled by a gatekeeper below.
    def __make_name_format(delim):
        """Generate the regex for finding data column headers."""
        return re.compile(
            rf"""
            ([\w]+)                 # Any word (alphanumeric)
            \s*                     # There might be a space...
            [{{{delim}}}\[\(\r\n]   # Labels could run against '('
                                    #   '[', '\r', '\n', or delim
            """, re.VERBOSE)

    def __make_data_format(delim):
        """Generate the regex for finding data in columns."""
        return re.compile(
            rf"""
            ([-\d.\+Ee]*)       # Any (or no) number (with decimal,
                                # negative, exp)
            [{{{delim}}}\r\n]   # Numbers could run against the
                                #   delimiter or a new line.
            """, re.VERBOSE)

    def __re_get(regex, line):
        """
        Search line using regex and return the first group.

        Returns '' if no result is found.
        Returns the entire match if no groups.
        """
        result = regex.search(line)
        if result:
            if result.groups():
                return result.groups()[0]
            # If there are no groups...
            return result.group()
        # if there is no result
        return ''

    def __find_log_starts(self):
        """
        Open the file and locate all PuTTY Headers.

        Returns a tuple of (start, stop) tuples.
        """
        # Open the file with read-only access.
        with open(self.path, 'r', encoding=self.__encoding) as file:

            # Record the stream location.
            f_loc = file.tell()
            # Read the line. This changes the stream location.
            line = file.readline()
            # Storage objects for starts and stops.
            start_idxs = []
            stop_idxs = []
            while line:
                # Read the line and check for a log start.
                #

                parse = self.__log_start_format.search(line)

                if parse:
                    # We found a header.
                    # Save the end-point of the last (if there is one).
                    if start_idxs:
                        stop_idxs.append(f_loc)
                    # Save the start-point (file.tell() from before the
                    # line was read).
                    start_idxs.append(f_loc)
                    # Determine if there's data on the same line as
                    # the header.
                    parse = parse.groups()
                    if parse[0]:
                        # TODO: this detects data on the same line as the
                        # header, but cannot do anything about it.
                        pass

                # Record the stream location.
                f_loc = file.tell()
                # Read the line. This changes the stream location.
                line = file.readline()
            # Append the final end-point.
            stop_idxs.append(file.tell())
        return tuple(zip(start_idxs, stop_idxs))

    def __init_dat(self):
        """
        Initialize dictionaries for each log.

        The dictionaries are stored in a list of dictionaries.
        Each has the following format:
            Date -- string describing date that the log was recorded.
            Start Time -- string noting time that the log started.
            Notes -- Any information provided prior to the data stream.
            Data -- Any numerical data provided, with named and unnamed
                    data stored separately.
        """
        self.__dat = [{
                'Date': "",         # Stores the test date
                'Start Time': "",   # Stores the start time
                'Idx': self.__log_idxs[i],    # (start, stop)
                'Notes': "",        # Holds any header information
                'Data': {},         # Carries the data for each test
                } for i in range(self.n_logs)]

    def __read_header(self):
        """
        Read and save information from the header.

        The header is any text prior to the first log start.
        """
        # Allocate a dictionary to add information to.
        dat = ""
        stop = self.__log_idxs[0][0]
        with open(self.path, 'r', encoding=self.__encoding) as file:
            # There may not be a header.
            if file.tell() == stop:
                self.header = ""
                return
            # Read in the header
            line = file.readline()
            while line:
                # Stop if the first log has been reached.
                if file.tell() == stop:
                    break
                # Copy the line into the header info.
                dat += line
                # Read the next line.
                line = file.readline()
        self.header = dat

    def get_log(self, log=0, *, delim=','):
        """
        Return the information provided by a given logged dataset.

        If the data has already been read (i.e. is stored in self.__dat),
        then that set is returned. If not, it is fetched, then
        returned.

        Arguments
        ---------
            log -- index of the log to be read (default 0)

        Keyword Arguments
        -----------------
            delim -- delimeter to be used if reading data from the log
                        (default ',')

        Raises
        ------
            IndexError -- if requesting a log that does not exist.
        """
        # Check that log is in range
        assert log < self.n_logs, "Requested log does not exist!"
        # Assume that the presence of 'Data' indicates that this has
        # already been read.
        if self.__dat[log]['Data']:
            # Don't return a link to self.__dat()
            return self.__dat[log].copy()

        # The data has not been read in yet.
        return self.__read_log(log, delim)

    def __read_log(self, log, delim):
        """
        Read, cache, and return a given set of info from the log file.

        Uses the start/stop indices to call self.read_data_in_range().
        Also uses the start index to read Date and Start Time info
        from the PuTTy Header

        Arguments
        ---------
            log -- index of the log to be read
            delim -- delimiter to use when parsing the log file

        Returns
        -------
            dat -- a dictionary containing all gathered info. This is
                    also cached in self.__dat
        """
        # Give the log's cache a shorter name.
        dat = self.__dat[log]
        # Add logged data and notes.
        dat.update(self.read_data_in_range(
                *dat['Idx'],    # (start, stop)
                delim=delim))
        # Don't return a link to self.__dat
        return dat.copy()

    def read_data_in_range(self, start=0, stop=-1, *, delim=','):
        """
        Read logged data from start (inclusive) to stop (exclusive).

        All information prior to the first numeric line is assumed to
        be notes. The last line prior to numerics is assumed to be
        column headers.

        Keyword Arguments
        -----------------
            start -- filestream start-point (inclusive)
            stop -- filestream end-point (exclusive)
            delim -- data delimiter.

        Returns
        -------
            dat -- a dictionary of all read data with the fields:
                Notes -- any lines determined to be not data
                Data -- any lines determined to be data, named and cast
                    to floats.
        """
        data_format = Log.__make_data_format(delim)
        name_format = Log.__make_name_format(delim)
        with open(self.path, 'r', encoding=self.__encoding) as file:
            # Go to the starting point.
            file.seek(start)
            # Read the first line.
            line = file.readline()
            last_line = ''
            is_stop = False
            # The list of column names will be filled in the loop.
            names = []
            # Initialize the data structure. Notes is the only known
            # category.
            dat = {
                'Date': '',
                'Start Time': '',
                'Notes': '',
                'Data': {}
                }
            while line:
                # While the line is non-empty
                if is_stop:
                    break
                if file.tell() == stop:
                    # Quit if at cutoff. file.tell() returns an
                    # 'opaque' number not necessarily related to
                    # n_bytes since the start of the file...
                    # https://docs.python.org/3/library/
                    # io.html#io.TextIOBase.tell
                    #
                    # This is a delayed action, the break happens at
                    # next iteration.
                    is_stop = True

                # Gatekeeper:
                #
                # If the line contains data, it must be more than just
                # white space. If it contains something besides data,
                # it will be non-empty after stripping out all
                # whitespace, data-like substrings, and delimiters.
                line_minus_data = (
                    data_format.sub('', line)
                    .replace(delim, '')
                    .strip()
                    )
                if line_minus_data or not line.strip():
                    # Line is just whitespace, or the sub'd line
                    # was non-empty,meaning this is not data.
                    dat['Notes'] += line
                    # Parse the header for date and time.
                    if not dat['Date']:
                        dat['Date'] = Log.__re_get(date_format, line)
                    if not dat['Start Time']:
                        dat['Start Time'] = Log.__re_get(time_format, line)
                    last_line = line
                    line = file.readline()
                    continue
                # The line contains data, and data only.

                # Read each column of data.
                data = data_format.findall(line)

                # Replace any empty values (whitespace or '') (i.e.
                # from a csv) with NaN.
                data = [d if d.strip() else 'nan' for d in data]

                # The first time that the loop makes it to here, names
                # will be empty. Assume that the names are given in the
                # previous line. Prep this after parsing the data into
                # a list so the number of data points can be checked.
                if not names:
                    names = tuple(name_format.findall(last_line))
                    # Store the number of named pieces of data.
                    n_names = len(names)
                    # Add storage for any excess data.
                    names += ('',)
                    # Create a dictionary of lists (for each dataset).
                    dat['Data'].update({name: [] for name in names})

                # Group all unnamed data into a single list within a
                # tuple while separating named data. The gatekeeper has
                # ensured all information is numeric.
                data = tuple([float(d) for d in data[0:n_names]]
                             + [[float(d) for d in data[n_names:]]])
                # Match the named data with its name. Unnamed data will
                # go into ' ', and names w/o data will just see [].
                named_data = dict(zip(names, data))
                # Add all data to dat
                for name in named_data.keys():
                    # Cast the string into a float.
                    dat['Data'][name].append(named_data[name])

                # Finish by reading the next line. This ensures the
                # loop will stop at End-Of-File (EOF).
                last_line = line
                line = file.readline()
        return dat
