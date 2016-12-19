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

OVERALL_S = '(overall)'
OVERALL_KEY = (OVERALL_S,)

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

def isnan(v):
    return isinstance(v, float) and math.isnan(v)

def survey_question_matrix(df, column_name):
    ratings_t = [((row.part_fname, row.part_lname), resp_fac_to_name_tuple(row.resp_fac), getattr(row, column_name))
                 for row in df.itertuples()]
    ratings_d = {(rater, ratee): rating for rater, ratee, rating in ratings_t}
    raters = sorted(set(participant for participant, _, _ in  ratings_t))
    ratees = sorted(set(participant for _, participant, _ in ratings_t))
    assert raters == [participant for participant in ratees if participant != OVERALL_KEY], '%s != %s' % (raters, ratees)
    if set(participant for _, participant, v in ratings_t if not isnan(v)) == set([OVERALL_KEY]):
        return {participant: ratings_d[participant, OVERALL_KEY] for participant in raters}, True
    else:
        return {k: None if isnan(v) else v for k, v in ratings_d.items()}, False

def get_participant_responses(df, participant):
    responses = [(survey_question, *survey_question_matrix(df, column_name))
                 for column_name, survey_question in response_columns]
    overall_responses = [(survey_question, response_matrix[participant])
                         for survey_question, response_matrix, is_overall_response in responses
                         if is_overall_response]
    peer_responses = [(survey_question, response_matrix)
                      for survey_question, response_matrix, is_overall_response in responses
                      if not is_overall_response]
    return overall_responses, peer_responses

survey_df = pd.DataFrame.from_csv(args.CSV_FILE, encoding="ISO-8859-1")
first_response_ix = 1 + list(survey_df.columns).index('part_id')
response_columns = [('_%d' % (1 + i), title) for i, title in enumerate(survey_df.columns) if i >= first_response_ix]
participants = sorted(list(set((row.part_fname, row.part_lname) for row in survey_df.itertuples())))
participant_responses = [(participant, *get_participant_responses(survey_df, participant)) for participant in participants]

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

def make_df_html(response_matrix):
    data = [[response_matrix[participant, p], response_matrix[p, participant]] for p in participants]
    return pd.DataFrame(data, columns=["Rated others", "Rated by others"], index=unique_names_for(participants))

with open(args.output, 'w') as html_report_f:
    print(HTML_HEADER, file=html_report_f)
    for participant, overall_responses, peer_responses in participant_responses:
        peer_response_htmls = [(survey_question, make_df_html(response_matrix).to_html())
                               for survey_question, response_matrix in peer_responses]
        print(ParticipantTemplate.render(participant=unique_name_among(participant, participants),
                                         overall_responses=overall_responses,
                                         peer_responses=peer_response_htmls),
              file=html_report_f)
