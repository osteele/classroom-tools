#!/usr/bin/env python3

# Author: Oliver Steele
# Date: 2016-12-19
# License: MIT

# Intended as throw-away code.

import argparse
import math
import sys

try:
    from jinja2 import Template
    import pandas as pd
except ImportError as e:
    sys.stderr.write('%s. Try running pip install %s' % (e, e.name))
    sys.exit(1)

parser = argparse.ArgumentParser(description='Create a spreadsheet that summarizes SCOPE P&S results in matrix form.')
parser.add_argument('-o', '--output', default='SCOPE peer and self reviews.html')
parser.add_argument('CSV_FILE')
args = parser.parse_args(['inputs/SCOPE PandS 12.14.16 - STEELE.csv'])

def resp_fac_to_first_last_name(fullname):
    return ' '.join(reversed(fullname.split(', ', 2)))

def row_to_first_last_name(row):
    return ' '.join([row.part_fname, row.part_lname])

def resp_fac_to_name_tuple(surname_comma_firstname):
    return tuple(reversed(surname_comma_firstname.split(', ', 2)))

def unique_name_among(name_tuple, name_tuples):
    first_name, *_ = name_tuple
    short_names = [first_name for first_name, *_ in name_tuples]
    return first_name if short_names.count(first_name) == 1 else ' '.join(*name_tuple)

def unique_names_for(name_tuples):
    short_names = [first_name for first_name, *_ in name_tuples]
    return [first_name if short_names.count(first_name) == 1 else ' '.join(first_name, *last_names)
            for first_name, *last_names in name_tuples]

OVERALL_S = '(overall)'
OVERALL_KEY = (OVERALL_S,)

def survey_question_matrix(df, column_name):
    ratings_t = [((row.part_fname, row.part_lname), resp_fac_to_name_tuple(row.resp_fac), getattr(row, column_name))
                 for row in df.itertuples()]
    ratings_d = {(rater, ratee): rating for rater, ratee, rating in ratings_t}
    raters = sorted(set(student for student, _, _ in  ratings_t))
    ratees = sorted(set(student for _, student, _ in ratings_t))
    assert raters == [student for student in ratees if student != OVERALL_KEY], '%s != %s' % (raters, ratees)
    # `or None` converts empty string to None, so that `df.dropna` can eliminate it
    data = [[ratings_d[rater, ratee] or None
             for ratee in ratees]
            for rater in raters]
    return (
        # `dropna` drops student columns from team questions
        pd.DataFrame(data, columns=unique_names_for(ratees), index=unique_names_for(raters)).dropna(axis=1, how='all'),
        # ratings_t
        {k:v for k, v in ratings_d.items() if not isinstance(v, float) or not math.isnan(v)}
        )

df = pd.DataFrame.from_csv(args.CSV_FILE, encoding="ISO-8859-1")

first_response_ix = 1 + list(df.columns).index('part_id')
response_columns = [('_%d' % (1 + i), title) for i, title in enumerate(df.columns) if i >= first_response_ix]

participants = sorted(list(set((row.part_fname, row.part_lname) for row in df.itertuples())))

HTML_HEADER = """
<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/0.97.8/css/materialize.min.css">
<style>
    body { margin: 5pt; }
    dt { font-style: italic; margin-top: 10pt; }
    dd { ; }
    section.survey-question { font-style: italic; page-break-inside: avoid; }
    div.survey-question { font-size: 120% }
    table { width: 90%; margin-left: 20%; }
    th, td { vertical-align: top; }
    section.participant::after { page-break-after: always; }
</style>
"""

PARTICIPANT_TEMPLATE_TEXT = """
<section class="participant"><h1>{{ participant }}</h1>
<dl>
{% for q in overall_responses %}
<dt>{{ q[0] }}</dt><dd>{{ q[1] }}</dd>
{% endfor %}
</dl>
{% for q in peer_responses %}
<section class="survey-question"><div class="survey-question">{{ q[0] }}</div>{{ q[1]|safe }}</section>
{% endfor %}
</section>
"""
ParticipantTemplate = Template(PARTICIPANT_TEMPLATE_TEXT)

pd.set_option('display.max_colwidth', -1)  # don't truncate cells

def participant_responses(df, participant):
    overall_responses = []
    peer_responses = []
    for column_name, survey_question in response_columns:
        dfs, r = survey_question_matrix(df, column_name)
        if list(dfs.columns) == [OVERALL_S]:
            response = r[participant, OVERALL_KEY]
            overall_responses.append((survey_question, response))
        else:
            data = [[r.get((participant, p), None), r.get((p, participant), None)] for p in participants]
            dfs = pd.DataFrame(data, columns=["Rated others", "Rated by others"], index=unique_names_for(participants))
            peer_responses.append((survey_question, dfs.to_html()))
    return overall_responses, peer_responses

participant_responses = [(participant, *participant_responses(df, participant)) for participant in participants]

with open(args.output, 'w') as f:
    print(HTML_HEADER, file=f)
    for participant, overall_responses, peer_responses in participant_responses:
        print(ParticipantTemplate.render(participant=unique_name_among(participant, participants),
                                         overall_responses=overall_responses,
                                                                        peer_responses=peer_responses),
              file=f)
