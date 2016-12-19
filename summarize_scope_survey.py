#!/usr/bin/env python3

# Author: Oliver Steele
# Date: 2016-12-18
# License: MIT

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
parser.add_argument('-o', '--output', default='SCOPE PandS matrices.xlsx')
parser.add_argument('CSV_FILE')
args = parser.parse_args()

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

writer = pd.ExcelWriter(args.output)
for column_name, title in response_columns:
    if len(title) > 31:
        title = title[:31-1] + '\u2026' # ellipsis
    dfs, _ = survey_question_matrix(df, column_name)
    dfs.to_excel(writer, title)
writer.save()

participants = sorted(list(set((row.part_fname, row.part_lname) for row in df.itertuples())))

template1 = Template('<section class="participant"><h1>{{ participant }}</h1>')
template2 = Template('<section><div class="survey-question">{{ survey_question }}</div><p>{{ response }}</p></section>')
template3 = Template('<section><div class="survey-question">{{ survey_question }}</div>{{ df|safe }}</section>')
css = """<meta charset="UTF-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/0.97.8/css/materialize.min.css">
<style>
section.survey-question { break-inside: avoid; }
th, td { vertical-align: top; }
.survey-question { font-size: 120% }
section.participant::after { page-break-after: always; }
</style>
"""

pd.set_option('display.max_colwidth', -1)

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
            peer_responses.append((survey_question, dfs))
    return overall_responses, peer_responses

with open('SCOPE peer and self reviews.html', 'w') as f:
    print(css, file=f)
    for participant in participants:
        overall_responses, peer_responses = participant_responses(df, participant)
        print(template1.render(participant=unique_name_among(participant, participants)), file=f)
        for survey_question, response in overall_responses:
            print(template2.render(survey_question=survey_question, response=response), file=f)
        for survey_question, response_df in peer_responses:
            print(template3.render(survey_question=survey_question, df=response_df.to_html()), file=f)
