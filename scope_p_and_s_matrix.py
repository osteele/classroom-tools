#!/usr/bin/env python

# Author: Oliver Steele
# Date: 2016-12-14
# License: MIT

import argparse
import sys

try:
    import pandas as pd
except ImportError:
    sys.stderr.write('Error: unmet dependency. try: pip install pandas')
    sys.exit(1)

parser = argparse.ArgumentParser(description='Create a spreadsheet that summarizes SCOPE P&S results in matrix form.')
parser.add_argument('-o', '--output', default='SCOPE PandS matrices.xlsx')
parser.add_argument('CSV_FILE')
args = parser.parse_args()

def resp_fac_to_first_last_name(fullname):
    return ' '.join(reversed(fullname.split(', ', 2)))

def row_to_first_last_name(row):
    return ' '.join([row.part_fname, row.part_lname])

def make_df(column_name):
    if isinstance(column_name, int):
        column_name = '_%d' % (1 + column_name)
    scores = {(row_to_first_last_name(row), resp_fac_to_first_last_name(row.resp_fac)): getattr(row, column_name) or None
              for row in df.itertuples()}
    students = sorted(set(student for student, _ in  scores.keys()))
    evaluatees = sorted(set(student for _, student in scores.keys()))
    assert students == [student for student in evaluatees if student != '(overall)']
    data = [[scores[evaluator, evaluatee] for evaluatee in evaluatees]
            for evaluator in students]
    return pd.DataFrame(data, columns=evaluatees, index=students).dropna(axis=1, how='all')

df = pd.DataFrame.from_csv(args.CSV_FILE, encoding="ISO-8859-1"); df

first_response_ix = 1 + list(df.columns).index('part_id')

writer = pd.ExcelWriter(args.output)
for i, title in enumerate(df.columns):
    if i >= first_response_ix:
        dfs = make_df(i)
        if len(title) > 31:
            title = title[:30] + '…'
        dfs.to_excel(writer, title)
writer.save()
