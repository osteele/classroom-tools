#!/usr/bin/env python3

"""
Create an HTML report from a SCOPE P&S survey.

Author: Oliver Steele
Copyright: Copyright 2016, Olin College
License: MIT
"""

# Code conventions:
# - this module is written in workbook style, not OO style
# - single-variable lines are for development in Hydrogen
# - 'single quotes' for strings used as symbols; "double quotes" for strings that appear in the output
# - 'part' abbreviates 'participant', for compatibility with the input CSV columns

import argparse
import os
import sys
from collections import Counter

try:
    from jinja2 import Environment
    import pandas as pd
except ImportError as e:
    sys.stderr.write("%s. Try running pip install %s" % (e, e.name))
    sys.exit(1)

# Hydrogen development
if 'ipykernel' in sys.modules:
    __file__ = '.'
    sys.argv = [__file__, "tests/files/SCOPE PandS test.csv", "-o", "tests/outputs/SCOPE PandS.html"]
    sys.argv = [__file__, "../downloads/SCOPE PandS 12.14.16 - STEELE.csv"]


# Constants
#

SURVEY_RESPONSE_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '../templates/scope_survey_results.html')


# Command-line arguments
#

parser = argparse.ArgumentParser(description="Create an HTML report from a SCOPE P&S survey.")
parser.add_argument("-o", "--output")
parser.add_argument('input', metavar="CSV_FILE")
args = parser.parse_args(sys.argv[1:])

# command-line argument defaults
args.output = args.output or os.path.splitext(args.input)[0] + ".html"


# Read the CSV file
#

df = pd.DataFrame.from_csv(args.input, encoding='ISO-8859-1', index_col=None)
survey_name = df.surveyname[0]


# Create the survey responses.
#
# In lieu of documentation, run this with the Atom Hydrogen plug-in or the Visual Studio Code
# Python extension, and evaluate the *.head() lines to see the table shapes and contents at
# each point in the computation.

# part_short_name: participant's first name if that's uniquely identifying, else their full name
part_name_pairs = set(zip(df.part_fname, df.part_lname))
short_name_count = Counter(first_name for first_name, _ in part_name_pairs)
part_tuple_names = {name: name[0] if short_name_count[name[0]] == 1 else ' '.join(name) for name in part_name_pairs}
df['part_short_name'] = df.apply(lambda row: (row.part_fname, row.part_lname), axis=1).map(part_tuple_names)
df.head()

# add columns:
# - eval_short_name; short name of the evaluatee
# - self_eval: True for a peer-response question where the participant is evaluating themeself
df['eval_short_name'] = df.eval_uname.map(dict(zip(df.part_uname, df.part_short_name)))
df['self_eval'] = df.part_short_name == df.eval_short_name
df.head()

# drop columns up to and including part_id. This leaves only survey questions, and the columns added above.
first_response_ix = 1 + list(df.columns).index('part_id')
response_df = df.drop(df.columns[:first_response_ix], axis=1)
response_df['has_peer'] = pd.notnull(response_df['eval_short_name'])
response_df.set_index(['has_peer', 'self_eval', 'part_short_name', 'eval_short_name'], inplace=True)
response_df.head()

# Use the has_peer and self_eval indices added above, to separate response_df into three dataframes
# (and drop the used indices):
# - overall_response_df
# - self_review_df: peer-review responses evaluating self
# - peer_review_df: peer-review responses evaluating others
#
# These are separate dataframes because the first has different columns, and the second two have different indices
# from each other.

overall_response_df = response_df.loc[False].reset_index(level=[0, 2], drop=True).dropna(axis=1).select_dtypes(exclude=[int])

self_review_df = response_df.loc[True].loc[True].reset_index(level=0, drop=True).dropna(axis=1)
peer_review_df = response_df.loc[True].loc[False].dropna(axis=1)

# Create a new dataframe `nested_peer_review_df`. This has a two-level column index. The first level divides
# into reviews *by* others and reviews *of* others. Construct the second level as separate dataframes, and then
# concatenate them.

review_others_df = peer_review_df.copy()
review_others_df.index.names = ['self', None]
# Add a top-level index:
review_others_df.columns = [["Rated teammates"] * len(review_others_df.columns), review_others_df.columns]
review_others_df.head()

# review_others_df renamed part_{short,long}_name -> {self,Teammate}.
# reviews_by_others_df renames them the opposite way, and then swaps the indices so that they match the order
# in review_others_df.
reviews_by_others_df = peer_review_df.copy()
reviews_by_others_df.index.names = review_others_df.index.names[::-1]
reviews_by_others_df = reviews_by_others_df.reorder_levels([-1, -2], axis=0)
# Add a top-level index:
reviews_by_others_df.columns = [["Rated by teammates"] * len(reviews_by_others_df.columns), reviews_by_others_df.columns]
reviews_by_others_df.head()

nested_peer_review_df = pd.concat([reviews_by_others_df, review_others_df], axis=1)
nested_peer_review_df.columns = nested_peer_review_df.columns.swaplevel(0, 1)
nested_peer_review_df.sortlevel(0, axis=1, inplace=True)
nested_peer_review_df.head()


# Create the HTML file
#

def dataframe_filter(df, **kwargs):
    """A Jinja filter that turns a Pandas DataFrame into HTML.

    Keyword arguments are passed to DataFrame.to_html.
    The Pandas display option is dynamically set to allow full-width text in the cells.
    """
    pd_display_max_colwidth_key = 'display.max_colwidth'
    saved_max_colwidth = pd.get_option(pd_display_max_colwidth_key)
    try:
        pd.set_option(pd_display_max_colwidth_key, -1)
        return df.to_html(**kwargs)
    finally:
        pd.set_option(pd_display_max_colwidth_key, saved_max_colwidth)

env = Environment()
env.filters['dataframe'] = dataframe_filter
env.filters['dataframe_type'] = lambda df: df.dtypes[0].name

participant_template = env.from_string(open(SURVEY_RESPONSE_TEMPLATE_PATH).read())

participant_records = [dict(participant_name=part_short_name,
                            overall_responses=overall_response_df.loc[part_short_name].iteritems(),
                            peer_survey_questions=peer_review_df.columns,
                            peer_reviews=nested_peer_review_df.loc[part_short_name],
                            self_reviews=self_review_df.loc[part_short_name])
                       for part_short_name in sorted(list(set(df.part_short_name)))]

with open(args.output, 'w') as report_file:
    report_file.write(participant_template.render(survey_name=survey_name, participants=participant_records))
print("Wrote", args.output)
