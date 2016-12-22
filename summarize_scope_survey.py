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

parser = argparse.ArgumentParser(description='Create a spreadsheet that summarizes SCOPE P&S results in matrix form.')
parser.add_argument('-o', '--output', default='SCOPE peer and self reviews.html')
parser.add_argument('CSV_FILE')
test_args = (['inputs/SCOPE PandS 12.14.16 - STEELE.csv'],) if 'ipykernel' in sys.modules else ()
args = parser.parse_args(*test_args)

def create_unique_names_map(entities, short_key_fn=lambda seq:seq[0], long_key_fn=lambda seq:' '.join(seq)):
    short_names = list(map(short_key_fn, entities))
    return {entity: short_key if short_names.count(short_key) == 1 else long_key_fn(entity)
            for entity, short_key in ((entity, short_key_fn(entity)) for entity in entities)}

df = pd.DataFrame.from_csv(args.CSV_FILE, encoding="ISO-8859-1")

participant_tuples = set(zip(df['part_fname'], df['part_lname']))
participant_name_map = create_unique_names_map(participant_tuples)
df['part_name'] = df.apply(lambda row: (row.part_fname, row.part_lname), axis=1).map(participant_name_map)

part_name_dict = {row.part_uname: row.part_name for row in df[['part_uname', 'part_name']].itertuples()}
df['eval_name'] = df['eval_uname'].map(part_name_dict)

first_response_ix = 1 + list(df.columns).index('part_id')
df2 = df.drop(set(df.columns[:first_response_ix]) - set(['part_name']), axis=1)

overall_responses = df2.loc[df['resp_fac'] == '(overall)'].set_index('part_name').dropna(axis=1).select_dtypes(exclude=[int])
peer_responses = df2.loc[df['resp_fac'] != '(overall)'].set_index(['part_name', 'eval_name']).dropna(axis=1)

HTML_HEADER = """
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/0.97.8/css/materialize.min.css">
<style>
    body { margin: 5pt; }
    section.survey-question { font-style: italic; page-break-inside: avoid; }
    section.participant::after { page-break-after: always; }
    div.survey-question { font-size: 120% }
    dt { font-style: italic; margin-top: 10pt; }
    table { width: 90%; margin-left: 20%; }
    th, td { vertical-align: top; }
</style>
"""

PARTICIPANT_TEMPLATE_TEXT = """
<section class="participant"><h1>{{ participant_name }}</h1>
    <dl>
        {% for q, a in overall_responses %}
            <dt>{{ q }}</dt>
            <dd>{{ a }}</dd>
        {% endfor %}
    </dl>
    {% for q, a in peer_responses %}
        <section class="survey-question"><div class="survey-question">{{ q }}</div>{{ a|dataframe }}</section>
    {% endfor %}
</section>
"""

env = Environment()
env.filters['dataframe'] = lambda df, **kwargs:df.to_html(**kwargs)
ParticipantTemplate = env.from_string(PARTICIPANT_TEMPLATE_TEXT)

def make_peer_df(part_name, col_name):
    p1 = peer_responses.xs(part_name, level='part_name')
    p2 = peer_responses.xs(part_name, level='eval_name')
    df = pd.DataFrame([p1[col_name].rename('Rated'), p2[col_name].rename('Rated by')]).T.replace(0, '')
    df.index.name = 'other'
    return df

with open(args.output, 'w') as report_file:
    report_file.write(HTML_HEADER)
    for part_name in sorted(participant_name_map.values()):
        peer_response_records = [(survey_question, make_peer_df(part_name, survey_question))
                                 for survey_question in peer_responses.columns]
        report_file.write(ParticipantTemplate.render(participant_name=part_name,
                                                     overall_responses=overall_responses.loc[part_name].iteritems(),
                                                     peer_responses=peer_response_records))
