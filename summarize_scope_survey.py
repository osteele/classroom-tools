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
responses_df = df.drop(set(df.columns[:first_response_ix]) - set(['part_name']), axis=1)

overall_responses = responses_df.loc[df['resp_fac'] == '(overall)'].set_index('part_name').dropna(axis=1).select_dtypes(exclude=[int])
peer_responses = responses_df.loc[df['resp_fac'] != '(overall)'].set_index(['part_name', 'eval_name']).dropna(axis=1)

rated_other = peer_responses.copy()
rated_other.index.names = ['self', 'Teammate']
rated_other.columns = [['This person rated teammates'] * len(rated_other.columns), rated_other.columns]
rated_other

rated_by = peer_responses.copy()
rated_by.index.names = ['Teammate', 'self']
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
    section.survey-question { font-style: italic; page-break-inside: avoid; }
    section.participant::after { page-break-after: always; }
    div.survey-question { font-size: 120% }
    dt { font-style: italic; margin-top: 10pt; }
    table { margin-left: 25pt; }
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
        <section class="survey-question"><div class="survey-question">{{ q }}</div>{{ a|dataframe(max_cols=2) }}</section>
    {% endfor %}
</section>
"""

env = Environment()
env.filters['dataframe'] = lambda df, **kwargs:df.to_html(**kwargs)
ParticipantTemplate = env.from_string(PARTICIPANT_TEMPLATE_TEXT)

with open(args.output, 'w') as report_file:
    report_file.write(HTML_HEADER)
    for part_name in sorted(participant_name_map.values()):
        peer_response_records = [(survey_question, nested_peer_responses.loc[part_name][survey_question])
                                 for survey_question in peer_responses.columns]
        report_file.write(ParticipantTemplate.render(participant_name=part_name,
                                                     overall_responses=overall_responses.loc[part_name].iteritems(),
                                                     peer_responses=peer_response_records))
