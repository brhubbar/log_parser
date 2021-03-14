# log_parser

Honestly, these 430 lines of code, comments, and whitespace have single-
handedly saved me hours of time processing data over the past year. Its purpose
is to read rows of delimited numerical data from a text file. A single file may
contain multiple datasets, provided that each dataset is denoted by a unique,
identifiable string of text. It is robust to interruptions in data streams
(such as commands or extra outputs in between rows of data), and stores any row
that is not strictly data within a 'Notes' section of the output data
dictionary. This detail sets this class apart from other data parsers like
MATLAB's `xlsread` or `importdata`, which require continuous blocks of data.

A continuous block of data may not be possible, for example, if you are logging
serial output from an Arduino and have a user interface set up which provides
other information beyond the data being logged. Other data logs with event
flags during the stream would similarly require additional attention to pull
out the data, while this library can coast through and grab all the information
of interest - particularly useful if you're looking to generate a quick plot
before running another test.

I wrote this library while learning the principles of python and efficiency
from [Diving Into Python
3](https://diveintopython3.problemsolving.io/table-of-contents.html#your-first-python-program),
specifically chapters 5 and 11, so shout out to Mark Pilgrim for his great
work.

## Details

`log_parser` defines the class `Log` which is a data manager for whatever file
it may be assigned:

```py3
mylog = Log('mydata.log', 'putty')
```

Upon construction, the object will take a quick gander through the file,
identifying the start of each log and saving a count for how many logs there
are (`mylog.n_logs`). It'll also store any header information above the first
log - this may contain test setup information, a description of all the tests
being run, a summary of what was seen the last time the data were looked at,
what you ate for lunch... anythin you like.

The owner of the object can then request any individual log using `thislog =
mylog.get_log(log_idx, delimeter)`. If the data has already been read in, the
object will spit back that log's data dictionary, containing any information it
was able to parse (test date, time, and any notes specific to that test) plus
the data. If the row immediately above the first row of numerical data
contains column headers, those will be used to label data in the dictionary.
Any unlabeled data will be stored in an additional column.

If the data has not been read in already, the object will open the file and
read the specific log, storing off information for future use and sharing it
with the caller. Any rows that don't look like data are stored in the 'Notes'
key as a multi-line string. 'Data' looks like delimited numbers. The delimeter
can be specified upon a call to `get_log()`.

Any information in the 'Data' key can be plotted or processed in any manner.
The header can be printed out, formatted, using `print(thislog['Notes'])` or
`print(mylog.header)`
