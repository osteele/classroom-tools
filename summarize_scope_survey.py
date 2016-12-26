#!/usr/bin/env python3

# Author: Oliver Steele
# License: MIT

import argparse
import math
import sys
from collections import Counter, defaultdict

try:
    from jinja2 import Environment
    import pandas as pd
except ImportError as e:
    sys.stderr.write('%s. Try running pip install %s' % (e, e.name))
    sys.exit(1)

if 'ipykernel' in sys.modules: sys.argv = ['script', 'downloads/SCOPE PandS 12.14.16 - STEELE.csv']

parser = argparse.ArgumentParser(description='Create a spreadsheet that summarizes SCOPE P&S results in matrix form.')
parser.add_argument('-o', '--output', default='SCOPE peer and self reviews.html')
parser.add_argument('CSV_FILE')
args = parser.parse_args(sys.argv[1:])

df = pd.DataFrame.from_csv(args.CSV_FILE, encoding="ISO-8859-1")

participant_tuples = set(zip(df['part_fname'], df['part_lname']))
short_name_count = Counter(first for first, _ in participant_tuples)
participant_name_map = {name: name[0] if short_name_count[name[0]] == 1 else ' '.join(name) for name in participant_tuples}
df['part_name'] = df.apply(lambda row: (row.part_fname, row.part_lname), axis=1).map(participant_name_map)

part_name_dict = {row.part_uname: row.part_name for row in df[['part_uname', 'part_name']].itertuples()}
df['eval_name'] = df['eval_uname'].map(part_name_dict)
df['self_eval'] = df['part_name'] == df['eval_name']
df

first_response_ix = 1 + list(df.columns).index('part_id')
responses_df = df.drop(df.columns[:first_response_ix], axis=1)
responses_df['has_peer'] = pd.notnull(responses_df['eval_name'])
responses_df.set_index(['has_peer', 'self_eval', 'part_name', 'eval_name'], inplace=True)
responses_df

overall_responses = responses_df.loc[False].reset_index(level=[0,2], drop=True).dropna(axis=1).select_dtypes(exclude=[int])
overall_responses

self_reviews = responses_df.loc[True].loc[True].reset_index(level=0, drop=True).dropna(axis=1)

peer_reviews = responses_df.loc[True].loc[False].dropna(axis=1)
peer_reviews

reviews_of_others = peer_reviews.copy()
reviews_of_others.index.names = ['self', 'Teammate']
reviews_of_others.columns = [['This person rated teammates'] * len(reviews_of_others.columns), reviews_of_others.columns]
reviews_of_others

reviews_by_others = peer_reviews.copy()
reviews_by_others.index.names = reviews_of_others.index.names[::-1]
reviews_by_others = reviews_by_others.reorder_levels([-1, -2], axis=0)
reviews_by_others.columns = [['This person rated by teammates'] * len(reviews_by_others.columns), reviews_by_others.columns]
reviews_by_others

nested_peer_reviews = pd.concat([reviews_by_others, reviews_of_others], axis=1)
nested_peer_reviews.columns = nested_peer_reviews.columns.swaplevel(0, 1)
nested_peer_reviews.sortlevel(0, axis=1, inplace=True)
nested_peer_reviews

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

PARTICIPANT_TEMPLATE_TEXT = """
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

def dataframe_filter(df, **kwargs):
    saved_max_colwidth = pd.get_option('display.max_colwidth')
    try:
        pd.set_option('display.max_colwidth', -1)
        return df.to_html(**kwargs)
    finally:
        pd.set_option('display.max_colwidth', saved_max_colwidth)

env = Environment()
env.filters['dataframe'] = dataframe_filter
participant_template = env.from_string(PARTICIPANT_TEMPLATE_TEXT)

with open(args.output, 'w') as report_file:
    report_file.write(HTML_HEADER)
    for part_name in sorted(participant_name_map.values()):
        report_file.write(participant_template.render(participant_name=part_name,
                                                      overall_responses=overall_responses.loc[part_name].iteritems(),
                                                      peer_survey_questions=peer_reviews.columns,
                                                      peer_reviews=nested_peer_reviews.loc[part_name],
                                                      self_reviews=self_reviews.loc[part_name]))
    report_file.write(HTML_FOOTER)
