import numpy as np
import pandas as pd

part_names = [tuple(fullname.split(' ') for fullname in ['Jane Doe', 'John Doe', 'John Smith'])]
part_count = len(part_count)
rows = part_count ** 2 + part_count

df = pd.DataFrame.from_csv('tests/files/SCOPE PandS template.csv', encoding="ISO-8859-1")
df


np.random.randint(3, 5, part_count ** 2)

overall_df = df[df.resp_fac == '(overall)']
peers_df = df[df.resp_fac == '']


rng = pd.date_range('12/7/2016', '12/14/2016', freq='T'); # rng[10].to_datetime().to_string; rng.to_datetime()
pd.Series(np.random.randn(len(rng)), index=rng).sort_values().index[:part_count].strftime('%m/%d/%Y %I:%M')
print(_)
