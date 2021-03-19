r"""
Convert a formatted data log into a report.

Converts a text file formatted to work with log_parser
(https://github.com/brhubbar/log_parser) into a markdown report, where
the data is converted into plots of the user's specification.

Plots can be called out in notes surrounding the data using the
following format:
    \p{x_variable, y_variable1(#, ...), y_variable2(#, ...), ...}
        (x_label, y_label, title)

Where (#, ...) is a list of test indices, indexing from 0. A single
newline is allowed (but not required) between the {} and () sets, but
nowhere else. For example:
    \p{time, temp(0, 2), mass(1, 2)}
        (time [s], temperature [K], some title)

will result in a plot with time on the x-axis, the variable `temp` from
tests 0 and 2, and the variable `mass` from tests 1 and 2. The x-axis
will be labeled `time [s]` the y-axis will be labeled `temperature [K]`,
and the title/filename will be `some title`. The plot will be generated,
saved, then a markdown-style callout for inclusion will replace the
callout.



Revisions
---------
    v0.0.1:

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

Ben Hubbard / v0.0.1
"""

import matplotlib.pyplot as plt
import re
import os


def generate_report(log, savepath, reportname="report.md"):
    """
    Convert a log file to a markdown-style report with links to plots.

    Converts plot callouts to markdown links and generates plots for
    markdown to find at those links. Tailored to Obsidian-flavored
    markdown (https://obsidian.md/)

    Parameters
    ----------
    log : log_parser.Log
        Object managing a log file.
    savepath : str
        Folder to save figures and report in.
    reportname : str, optional
        Name of the report file. The default is "report.md".

    Returns
    -------
    None.

    """
    # Instantiate the log reader.
    n_logs = log.n_logs

    # Make sure the target folder is available.
    if not os.path.isdir(savepath):
        os.mkdir(savepath)

    # Container for information (variables, names) of each plot.
    plot_info = []
    # Container for data from every log.
    data = []
    # Open the report markdown file, ensuring that it'll be closed when
    # all is said and done. Truncate (overwrite) the report file.
    with open(os.path.join(savepath, reportname),
              'w',
              encoding='utf-8',
              ) as report_file:
        # Print the log's header information and make note of the
        # requested plots.
        plot_info.extend(add_to_report(log.header,
                                       report_file,
                                       tuple(range(n_logs)),
                                       ))

        # Add test-specific notes and save off information about the
        # requested plots. Store each dataset as an item in the list.
        for test_idx in range(log.n_logs):
            dat = log.get_log(test_idx)
            data.append(dat['Data'])

            plot_info.extend(add_to_report(dat['Notes'],
                                           report_file,
                                           (test_idx,),
                                           ))

    # Generate plots. This is a very nested sequence.
    # - For each requested figure, find the x variable's key.
    # - For each y variable, find the y variable's key.
    # - For each requested curve of said y variable (test_idx), plot the
    #   x and y data.
    for info in plot_info:
        fig, ax = plt.subplots()
        x_key = info['variables']['x']

        for y in info['variables']['y']:
            y_key = y['name']
            for test_idx in y['tests']:
                ax.plot(data[test_idx][x_key], data[test_idx][y_key],
                        marker='*',
                        markersize=2,
                        label=f"{y_key} : Test {test_idx}",
                        )
        ax.set_xlabel(info['labels']['xlabel'])
        ax.set_ylabel(info['labels']['ylabel'])
        ax.set_title(info['labels']['title'])
        ax.legend()
        fig.savefig(os.path.join(savepath, info['savename']))


def add_to_report(text, file, default_tests):
    """
    Add notes to file, replacing plot callouts with markdown links.

    Also collects requested plot contents for later generation.

    If the tests requested by the callout are not listed, only the
    current test (indicated by test_idx) will be used. If there is no
    current test (i.e. the header, indicated by test_idx=-1), all tests
    will be used.

    Parameters
    ----------
    text : string
        Notes to be added.
    file : io.TextIOWrapper
        Opened, writeable file to send the text to.
    test_idx : tuple
        List of log indices to use if none were provided by the user.

    Returns
    -------
    plot_info : list
        List of data dictionaries containing labels, variables, and
        savename information for each plot.

    """
    # Find a plot callout.
    callout = pattern_callout.search(text)
    plot_info = []
    while callout:
        # Get request from the callout.
        labels = extract_labels(callout)
        variables = extract_vars(callout)

        # Fill in missing test index callouts using test_idx.
        for y in variables['y']:
            if not y['tests']:
                y['tests'] = default_tests

        # Store request so plots can be generated later.
        plot_info.append({'labels': labels,
                          'variables': variables,
                          })
        savename = f"{labels['title']}.png"
        # Keep the savename for when the plot is generated.
        plot_info[-1].update({'savename': savename})
        # Markdown gets confused by spaces, so use percent-encoding.
        savename = savename.replace(' ', '%20')
        # Replace callout with markdown link.
        text = pattern_callout.sub(f"![]({savename})", text, count=1)

        # Find the next callout.
        callout = pattern_callout.search(text)
    # Write reformatted text to the file.
    print(text, file=file)
    return plot_info


def extract_labels(callout):
    """
    Extract plot labels from plot callout.

    Parameters
    ----------
    callout : re.Match
        Match from pattern_callout.search(), containing a 'labels'
        group.

    Returns
    -------
    dict
        Dictionary of plot labels: xlabel, ylabel, title.

    """
    # The labels must be comma delimited. Remove whitespace and
    # store in a list.
    labels = [s.strip() for s in callout['labels'].split(',')]
    # Labels must be in a fixed order. Convert to a dictionary for
    # code readability.
    label_names = ['xlabel', 'ylabel', 'title']
    return dict(zip(label_names, labels))


def extract_vars(callout):
    """
    Return variable keys and test indices in a data dictionary.

    Parameters
    ----------
    callout : re.Match
        Match from pattern_callout.search(), containing a 'labels'
        group.

    Returns
    -------
    dict
        Dictionary of data callouts:
            x : str
                Key of the x variable.
            y : list
                list of dictionaries of y variable information:
                    name : str
                        Key of the y variable.
                    tests : tuple
                        Tuple of test indices.

    """
    variables = pattern_variables.finditer(callout['vars'])
    # Pull variable names.
    # X variable comes first; uses test number for the y variable,
    # so only store the name.
    x_key = next(variables).groupdict()['name'].strip()

    # Store the name and tests to be used for each y variable.
    y_dict = [y.groupdict() for y in variables]
    # Clean up contents of y_dict so they're useful to the rest of the
    # world.
    for y in y_dict:
        # Clean up variable names.
        y['name'] = y['name'].strip()

        # Convert test numbers from a string to a tuple.
        # re.findall() can't handle a None, so replace with an
        # empty string. This results in y['tests']=()
        if not y['tests']:
            y['tests'] = ''
        # Identify numbers and store in a tuple.
        y_tests = tuple(int(n) for n in re.findall(r'\d+', y['tests']))
        y.update({'tests': y_tests})

    return {'x': x_key, 'y': y_dict}


# Detect plot callout.
pattern_callout = re.compile(
    r'''
    \\p                 # \p is the 'plot' callout character
    \{(?P<vars>.+)\}    #   variable information is stored between {}
                        #     (group 1 = vars)
    \n?\s*              # Optional single newline/whitespace.
    \((?P<labels>.+)\)  # label information is stored between ()
                        #     (group 2 = labels)
    ''', re.VERBOSE)

# Identify variable names and test identifiers (if present).
# Variable callout format: name(test_no, test_no, ...).
# Commas are required between test numbers. Whitespace is optional.
pattern_variables = re.compile(
    r'''
    (?:                 # Start of group
     (?P<name>[\w\s]+)  # Variable name (group 1 = name)
     (?P<tests>         # Test number callout (group 2 = tests)
      \(                # Opening parenthesis
      (?:               # Uncaptured group - possible repeating #, ...
       \s*\d+\s*,       # Leading test numbers (#,) possible whitespace
      )*                # May be several, or none.
      \s*\d+\s*         # final number, no trailing comma.
      \)                # Closing paerenthesis
     )?                 # May or may not include (#, ...)
    ),?                 # End of group, may or may not be trailed by
                        # comma.
    ''', re.VERBOSE)
