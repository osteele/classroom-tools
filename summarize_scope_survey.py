#!/usr/bin/env python3

"Create an HTML report from a SCOPE P&S survey."

__author__ = "Oliver Steele"
__copyright__ = "Copyright 2016, Olin College"
__license__ = "MIT"

# Code conventions:
# - "double quotes" for strings that appear in the output
# - single-variable lines are for development in Hydrogen

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

if 'ipykernel' in sys.modules:
    sys.argv = ['script', 'tests/files/SCOPE PandS test.csv', '-o', 'tests/outputs/SCOPE PandS.html']

parser = argparse.ArgumentParser(description="Create an HTML report from a SCOPE P&S survey.")
parser.add_argument('-o', '--output')
parser.add_argument('CSV_FILE')
args = parser.parse_args(sys.argv[1:])

args.output = args.output or os.path.splitext(args.CSV_FILE)[0] + '.html'

df = pd.DataFrame.from_csv(args.CSV_FILE, encoding='ISO-8859-1')

# part_short_name: participant's first name if that's uniquely identifying, else their full name
part_name_pairs = set(zip(df.part_fname, df.part_lname))
short_name_count = Counter(first for first, _ in part_name_pairs)
part_tuple_names = {name: name[0] if short_name_count[name[0]] == 1 else ' '.join(name) for name in part_name_pairs}
df['part_short_name'] = df.apply(lambda row: (row.part_fname, row.part_lname), axis=1).map(part_tuple_names)

# eval_short_name; short name of the evaluatee
# self_eval: True for a peer-response question where the participant is evaluating themeself
df['eval_short_name'] = df.eval_uname.map(dict(zip(df.part_uname, df.part_short_name)))
df['self_eval'] = df.part_short_name == df.eval_short_name
df

# drop columns up to and including part_id. This leaves only survey questions, and the columns added above
first_response_ix = 1 + list(df.columns).index('part_id')
response_df = df.drop(df.columns[:first_response_ix], axis=1)
response_df['has_peer'] = pd.notnull(response_df['eval_short_name'])
response_df.set_index(['has_peer', 'self_eval', 'part_short_name', 'eval_short_name'], inplace=True)
response_df

# Separate df into three dataframes:
# - overall_response_df
# - self_review_df (peer-review responses evaluating self)
# - peer_review_df (peer-review responses evaluating others)
#
# These are separate dataframes because the first has different columns, and they second two have different indices
# from each other.

overall_response_df = response_df.loc[False].reset_index(level=[0,2], drop=True).dropna(axis=1).select_dtypes(exclude=[int])
overall_response_df

self_review_df = response_df.loc[True].loc[True].reset_index(level=0, drop=True).dropna(axis=1)
peer_review_df = response_df.loc[True].loc[False].dropna(axis=1)
peer_review_df

review_others_df = peer_review_df.copy()
review_others_df.index.names = ['self', "Teammate"]
review_others_df.columns = [["This person rated teammates"] * len(review_others_df.columns), review_others_df.columns]
review_others_df

# Create a new df nested_peer_review_df. This has a two-level column index, that divides it into reviews *by*
# others and reviews *of* others. Construct these as separate dataframes, and combine them into nested_peer_review_df.

reviews_by_others_df = peer_review_df.copy()
reviews_by_others_df.index.names = review_others_df.index.names[::-1]
reviews_by_others_df = reviews_by_others_df.reorder_levels([-1, -2], axis=0)
reviews_by_others_df.columns = [["This person rated by teammates"] * len(reviews_by_others_df.columns), reviews_by_others_df.columns]
reviews_by_others_df

nested_peer_review_df = pd.concat([reviews_by_others_df, review_others_df], axis=1)
nested_peer_review_df.columns = nested_peer_review_df.columns.swaplevel(0, 1)
nested_peer_review_df.sortlevel(0, axis=1, inplace=True)
nested_peer_review_df

HTML_HEADER = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/0.97.8/css/materialize.min.css">
<title>SCOPE Self and Peer Survey Report</title>
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
    report_file.write(HTML_HEADER)
    for part_short_name in sorted(list(set(df.part_short_name))):
        report_file.write(participant_template.render(participant_name=part_short_name,
                                                      overall_responses=overall_response_df.loc[part_short_name].iteritems(),
                                                      peer_survey_questions=peer_review_df.columns,
                                                      peer_reviews=nested_peer_review_df.loc[part_short_name],
                                                      self_reviews=self_review_df.loc[part_short_name]))
    report_file.write(HTML_FOOTER)
print('Wrote', args.output)
