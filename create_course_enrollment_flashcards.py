#!/usr/bin/env python3
# coding: utf-8

"""
Create a `*.xlsx` file and `Media` folder that contain the names and photos of students enrolled in a course,
suitable for use with [FlashCard Deluxe](http://orangeorapple.com/Flashcards/).

The input is a Course Enrollment HTML page, saved from Chrome with Format="Webpage, complete".
"""

__author__    = "Oliver Steele"
__copyright__ = "Copyright 2016, Olin College"
__license__   = "MIT"

# Code conventions:
# - this module is written in workbook style, not OO style
# - single-variable lines are for development in Hydrogen
# - 'single quotes' for strings used as symbols; "double quotes" for strings that appear in the output

import argparse
import filecmp
import os
import re
import shutil
import sys
import unicodedata
from collections import namedtuple

try:
    import pandas as pd
    from bs4 import BeautifulSoup
except ImportError as e:
    sys.stderr.write('%s. Try running pip install %s' % (e, e.name))
    sys.exit(1)

# Jipyter / Hydrogen development
if 'ipykernel' in sys.modules:
    sys.argv = ['script', 'downloads/ENGR2510-1.html', '-d', 'build', '--nicknames', 'config/student-nicknames.txt']

parser = argparse.ArgumentParser(description="Create a Flashcard file and directory for students enrolled in a course.")
parser.add_argument("-d", "--output-dir", help="Output directory. Defaults to HTML_FILE's directory.")
parser.add_argument("-o", "--output", help="Output file. Should end in .csv or .xlsl.")
parser.add_argument("--course-name")
parser.add_argument("--delete", action='store_true')
parser.add_argument("--service", choices=["dropbox"], help="Place in Dropbox app directory. Use instead of --output-dir.")
parser.add_argument("--nicknames", default="config/student-nicknames.txt", help="Text file list of First “Nick” Last")
parser.add_argument("HTML_FILE")
args = parser.parse_args(sys.argv[1:])

RESIZE_IMAGES = None  # not currently in use

if args.service == "dropbox":
    assert not args.output, "Error: Use at most one of --service and --output-dir"
    args.output_dir = os.path.expanduser("~/Dropbox/Apps/Flashcards Deluxe")
    assert os.path.isdir(args.output_dir), "Error: ~s does not exist" % args.output_dir

##
## Create a dictionary mapping registrar names to student names
##

def normalize_name(s):
    return unicodedata.normalize('NFD', s).lower()

def name_key_series(fn_series, ln_series):
    return list(zip(fn_series.map(normalize_name), ln_series.map(normalize_name)))

nickname_lines = open(args.nicknames).readlines() if args.nicknames else [["First “Nickname” Last"]]
nickname = pd.DataFrame(nickname_lines)[0].str.extractall(r'(?P<fn>.+?)\s*["“](?P<nickname>.+)["”]\s*(?P<ln>.+)')
nickname['name_key'] = name_key_series(nickname.fn, nickname.ln)
nickname.head()

html_content = BeautifulSoup(open(args.HTML_FILE), 'html.parser')
html_content

course_term_field, _, course_number_field, course_name_field = \
    [s.strip() for s in html_content.select('#pg0_V_ggClassList thead tr')[0].text.split('|')]
course_season, course_year = re.search('(Spring|Fall) Term - (\d{4})', course_term_field).groups()
course_number, course_section = re.match(r'(.+)-(\d+)', course_number_field).groups()

student_elt = html_content.select('#pg0_V_ggClassList tbody td img')
student = pd.Series([e.text.strip() for e in student_elt]).str.replace('_', ' ')\
    .str.extract(r'(?P<last_name>.+?), (?P<first_name>\S+)', expand=True)
student['image_src'] = [e.attrs['src'] for e in student_elt]
student['name_key'] = name_key_series(student.first_name, student.last_name)
student['nickname'] = pd.merge(student, nickname, on='name_key', how='left')['nickname']
student.nickname.fillna(student.first_name, inplace=True)
student['fullname'] = student.first_name.str.cat(student.last_name, ' ')
student['image_extn'] = student.image_src.str.extract('(\.[^.]+)$', expand=True)
student['image_dst'] = student.fullname.str.cat(student.image_extn)
student.head()

df = pd.DataFrame({"Text 2": student.fullname, "Picture 1": student.image_dst})
df["Text 1"] = ""
df

# Default to Excel. Excel is more robust than CSV against unicode.
output_basename = "{} {} {} {}.xlsx".format(course_number, course_section, course_season, course_year)
output_path = args.output or os.path.join(args.output_dir or os.path.split(args.HTML_FILE)[0], (args.course_name or output_basename))
output_path

extn = os.path.splitext(output_path)[1]
if extn == '.xlsx':
    writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
    df.to_excel(writer, index=False)
    writer.save()
elif extn == '.csv':
    df.to_csv(output_path)
elif extn:
    raise Exception("Unknown file extension: %s" % extn[1:])
else:
    raise Exception("Missing file extension: %s" % output_path)
print('Wrote', output_path)

# copy media files
media_src_dir = os.path.split(args.HTML_FILE)[0]
media_dst_dir = os.path.splitext(output_path)[0]
os.makedirs(media_dst_dir, exist_ok=True)
for _, row in student.iterrows():
    srcfile = os.path.join(media_src_dir, row.image_src)
    dstfile = os.path.join(media_dst_dir, row.image_dst)
    ext = os.path.splitext(dstfile)[1][1:]
    if RESIZE_IMAGES and ext.lower() in ['jpeg', 'jpg', 'png']:
        from PIL import Image  # down here, so we needn't import PIL unless it's used
        print("convert", os.path.split(srcfile)[1], '->', os.path.split(dstfile)[1])
        im = Image.open(srcfile)
        w, h = im.size
        s = RESIZE_IMAGES / max(w, h)
        im = im.resize((int(s * w), int(s * h)), Image.ANTIALIAS)
        im.save(dstfile)
    elif not os.path.exists(dstfile) or not filecmp.cmp(srcfile, dstfile):
        print("cp", os.path.split(srcfile)[1], '->', os.path.split(dstfile)[1])
        shutil.copy(srcfile, dstfile)

# delete stale media files
if args.delete:
    print("remove dead files:")
    image_files = set(f for f in os.listdir(media_dst_dir) if os.path.isfile(os.path.join(media_dst_dir, f)))
    for dead_file in sorted(image_files - set(student.image_dst)):
        print("rm", dead_file)
        os.remove(os.path.join(media_dst_dir, dead_file))
