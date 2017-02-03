#!/usr/bin/env python
import filecmp
import os
import shutil

REPO_DIR = 'build/sd16-reading-repos'
BUILD_DIR = 'build/sd16-combined'

# NOTEBOOK_NAME = 'day15_reading_journal.ipynb'
NOTEBOOK_NAME = 'day18_code_kata.ipynb'

student_dirs = [f for f in os.listdir(REPO_DIR) if os.path.isdir(os.path.join(REPO_DIR, f)) and f != 'master']
dst_dir = os.path.join(BUILD_DIR, os.path.splitext(NOTEBOOK_NAME)[0])
master_file = os.path.join(REPO_DIR, 'master', NOTEBOOK_NAME)

os.makedirs(dst_dir, exist_ok=True)

for dir in student_dirs:
    fname = os.path.join(REPO_DIR, dir, NOTEBOOK_NAME)
    if not os.path.exists(fname):
        if False:
            print('missing: %s' % (fname))
    elif filecmp.cmp(fname, master_file):
        print('unchanged: %s' % fname)
    else:
        dst = os.path.join(dst_dir, os.path.split(dir)[1] + '.ipynb')
        print('copy:', fname)
        shutil.copyfile(fname, dst)
