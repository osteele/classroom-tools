#!/usr/bin/env python3

"Create an HTML report from a SCOPE P&S survey."

__author__    = "Oliver Steele"
__copyright__ = "Copyright 2016, Olin College"
__license__   = "MIT"

# Code conventions:
# - this module is written in workbook style, not OO style
# - single-variable lines are for development in Hydrogen
# - 'single quotes' for strings used as symbols; "double quotes" for strings that appear in the output
# - 'part' abbreviates 'participant', for compatibility with the input CSV columns

import argparse
import math
import os
import sys
from collections import Counter, defaultdict

try:
    from jinja2 import Environment
    import pandas as pd
except ImportError as e:
    sys.stderr.write('%s. Try running pip install %s' % (e, e.name))
    sys.exit(1)

# Hydrogen development
if 'ipykernel' in sys.modules:
    sys.argv = ['script', "tests/files/SCOPE PandS test.csv", "-o", "tests/outputs/SCOPE PandS.html"]

# command-line arguments
parser = argparse.ArgumentParser(description="Create an HTML report from a SCOPE P&S survey.")
parser.add_argument("-o", "--output")
parser.add_argument('input', metavar="CSV_FILE")
args = parser.parse_args(sys.argv[1:])

# command-line argument defaults
args.output = args.output or os.path.splitext(args.input)[0] + ".html"

df = pd.DataFrame.from_csv(args.input, encoding='ISO-8859-1', index_col=None)
survey_name = df.surveyname[0]

# part_short_name: participant's first name if that's uniquely identifying, else their full name
part_name_pairs = set(zip(df.part_fname, df.part_lname))
short_name_count = Counter(first_name for first_name, _ in part_name_pairs)
part_tuple_names = {name: name[0] if short_name_count[name[0]] == 1 else ' '.join(name) for name in part_name_pairs}
df['part_short_name'] = df.apply(lambda row: (row.part_fname, row.part_lname), axis=1).map(part_tuple_names)

# add columns:
# - eval_short_name; short name of the evaluatee
# - self_eval: True for a peer-response question where the participant is evaluating themeself
df['eval_short_name'] = df.eval_uname.map(dict(zip(df.part_uname, df.part_short_name)))
df['self_eval'] = df.part_short_name == df.eval_short_name
df

# drop columns up to and including part_id. This leaves only survey questions, and the columns added above.
first_response_ix = 1 + list(df.columns).index('part_id')
response_df = df.drop(df.columns[:first_response_ix], axis=1)
response_df['has_peer'] = pd.notnull(response_df['eval_short_name'])
response_df.set_index(['has_peer', 'self_eval', 'part_short_name', 'eval_short_name'], inplace=True)
response_df

# Use the has_peer and self_eval indices added above, to separate response_df into three dataframes
# (and drop the used indices):
# - overall_response_df
# - self_review_df: peer-review responses evaluating self
# - peer_review_df: peer-review responses evaluating others
#
# These are separate dataframes because the first has different columns, and the second two have different indices
# from each other.

overall_response_df = response_df.loc[False].reset_index(level=[0,2], drop=True).dropna(axis=1).select_dtypes(exclude=[int])
overall_response_df

self_review_df = response_df.loc[True].loc[True].reset_index(level=0, drop=True).dropna(axis=1)
peer_review_df = response_df.loc[True].loc[False].dropna(axis=1)
peer_review_df

# Create a new dataframe `nested_peer_review_df`. This has a two-level column index. The first level divides
# into reviews *by* others and reviews *of* others. Construct the second level as separate dataframes, and then
# concatenate them.

review_others_df = peer_review_df.copy()
review_others_df.index.names = ['self', "Teammate"]
# Add a top-level index:
review_others_df.columns = [["This person rated teammates"] * len(review_others_df.columns), review_others_df.columns]
review_others_df

# review_others_df renamed part_{short,long}_name -> {self,Teammate}.
# reviews_by_others_df renames them the opposite way, and then swaps the indices so that they match the order
# in review_others_df.
reviews_by_others_df = peer_review_df.copy()
reviews_by_others_df.index.names = review_others_df.index.names[::-1]
reviews_by_others_df = reviews_by_others_df.reorder_levels([-1, -2], axis=0)
# Add a top-level index:
reviews_by_others_df.columns = [["This person rated by teammates"] * len(reviews_by_others_df.columns), reviews_by_others_df.columns]
reviews_by_others_df

nested_peer_review_df = pd.concat([reviews_by_others_df, review_others_df], axis=1)
nested_peer_review_df.columns = nested_peer_review_df.columns.swaplevel(0, 1)
nested_peer_review_df.sortlevel(0, axis=1, inplace=True)
nested_peer_review_df

# Templates are inline. This makes it possible to distribute this script as a single file.

HTML_HEADER = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/0.97.8/css/materialize.min.css">
<title>{{ survey_name }}</title>
<style>
    body { margin: 5pt; }
    section.participant::after { page-break-after: always; }
    dt { margin-top: 10pt; font-weight: bold; }
    th { font-weight: normal; font-style: italic; }
    th, td { vertical-align: top; padding: 2pt; }
    div.self-review { margin-top: 5pt; }
    span.label { padding-right: 5pt; font-style: italic; }
</style>
</head>
<body>
"""

HTML_FOOTER = "</body></html>"

PARTICIPANT_TEMPLATE_TEXT = """\
<section class="participant"><h1>{{ participant_name }}</h1>
    <dl>
        {% for q, a in overall_responses %}
            <dt>{{ q }}</dt>
            <dd>{{ a }}</dd>
        {% endfor %}
        {% for q in peer_survey_questions %}
            <dt>{{ q }}</dt>
            <dd>
                {{ peer_reviews[q] | dataframe }}
                <div class="self-review">
                    <span class="label">Self:</span>
                    {{ self_reviews[q] }}
                 </div>
            </dd>
        {% endfor %}
    </dl>
</section>
"""

env = Environment()

def dataframe_filter(df, **kwargs):
    """A Jinja filter that turns a Pandas DataFrame into HTML, with the specified options and with
    the Pandas display option temporarily set to allow full-width text in the cells."""

    saved_max_colwidth = pd.get_option('display.max_colwidth')
    try:
        pd.set_option('display.max_colwidth', -1)
        return df.to_html(**kwargs)
    finally:
        pd.set_option('display.max_colwidth', saved_max_colwidth)

env.filters['dataframe'] = dataframe_filter

participant_template = env.from_string(PARTICIPANT_TEMPLATE_TEXT)

with open(args.output, 'w') as report_file:
    report_file.write(env.from_string(HTML_HEADER).render(survey_name=survey_name))
    for part_short_name in sorted(list(set(df.part_short_name))):
        report_file.write(participant_template.render(participant_name=part_short_name,
                                                      overall_responses=overall_response_df.loc[part_short_name].iteritems(),
                                                      peer_survey_questions=peer_review_df.columns,
                                                      peer_reviews=nested_peer_review_df.loc[part_short_name],
                                                      self_reviews=self_review_df.loc[part_short_name]))
    report_file.write(HTML_FOOTER)
print("Wrote", args.output)
