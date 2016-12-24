#!/usr/bin/env python3

# Author: Oliver Steele
# License: MIT

import argparse
import math
import sys
from collections import defaultdict

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
short_names = [first for first, _ in participant_tuples]
participant_name_map = {name: name[0] if short_names.count(name[0]) == 1 else ' '.join(name) for name in participant_tuples}
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

self_responses = responses_df.loc[True].loc[True].reset_index(level=0, drop=True).dropna(axis=1)

peer_responses = responses_df.loc[True].loc[False].dropna(axis=1)
peer_responses

rated_other = peer_responses.copy()
rated_other.index.names = ['self', 'Teammate']
rated_other.columns = [['This person rated teammates'] * len(rated_other.columns), rated_other.columns]
rated_other

rated_by = peer_responses.copy()
rated_by.index.names = rated_other.index.names[::-1]
rated_by = rated_by.reorder_levels([-1, -2], axis=0)
rated_by.columns = [['This person rated by teammates'] * len(rated_by.columns), rated_by.columns]
rated_by

nested_peer_responses = pd.concat([rated_by, rated_other], axis=1)
nested_peer_responses.columns = nested_peer_responses.columns.swaplevel(0, 1)
nested_peer_responses.sortlevel(0, axis=1, inplace=True)
nested_peer_responses

HTML_HEADER = """
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/0.97.8/css/materialize.min.css">
<style>
    body { margin: 5pt; }
    section.participant::after { page-break-after: always; }
    dt { margin-top: 10pt; font-weight: bold; }
    th { font-weight: normal; font-style: italic; }
    th, td { vertical-align: top; padding: 2pt; }
    div.rated-self { margin-top: 5pt; }
    span.rated-self-label { padding-right: 5pt; font-style: italic; }
</style>
"""

PARTICIPANT_TEMPLATE_TEXT = """
<section class="participant"><h1>{{ participant_name }}</h1>
    <dl>
        {% for q, a in overall_responses %}
            <dt>{{ q }}</dt>
            <dd>{{ a }}</dd>
        {% endfor %}
        {% for q, a, s in peer_responses %}
            <dt>{{ q }}</dt>
            <dd>
                {{ a|dataframe(max_cols=2) }}
                <div class="rated-self"><span class="rated-self-label">Self:</span> {{ s }}</div>
            </dd>
        {% endfor %}
    </dl>
</section>
"""

env = Environment()
env.filters['dataframe'] = lambda df, **kwargs:df.to_html(**kwargs)
ParticipantTemplate = env.from_string(PARTICIPANT_TEMPLATE_TEXT)

with open(args.output, 'w') as report_file:
    report_file.write(HTML_HEADER)
    for part_name in sorted(participant_name_map.values()):
        peer_response_records = [(survey_question,
                                  nested_peer_responses.loc[part_name][survey_question],
                                  self_responses.loc[part_name][survey_question])
                                 for survey_question in peer_responses.columns]
        report_file.write(ParticipantTemplate.render(participant_name=part_name,
                                                     overall_responses=overall_responses.loc[part_name].iteritems(),
                                                     peer_responses=peer_response_records))
