
# coding: utf-8

# # FOCS Homework Times
#
# Collect times that each homework was submitted.

import argparse
import os
import re
import sys
from collections import defaultdict
from functools import reduce
from multiprocessing import Pool

import pandas as pd
import yaml
from github import Github, GithubException

DEFAULT_CONFIG_FILE = 'config/source_repos.yaml'
IGNORE_FILES_RE = re.compile(r'.*\.(bak|csv|exe|jff|jpe?g|JE?PG|png|pyc|svg)|.*~|\.gitignore|FETCH_HEAD')

parser = argparse.ArgumentParser(description="Collect file times.")
parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, help="YAML configuration file")
parser.add_argument("repo", help="source repo")
test_args = ['sd16fall/ReadingJournal']
args = parser.parse_args(*((test_args,) if 'ipykernel' in sys.modules else ()))

GITHUB_API_TOKEN = os.environ.get('GITHUB_API_TOKEN', None)
if not GITHUB_API_TOKEN:
    print("warning: GITHUB_API_TOKEN is not defined. API calls are rate-limited.", file=sys.stderr)

gh = Github(GITHUB_API_TOKEN)

with open(args.config) as f:
    config = yaml.load(f)
repo_config = config.get(args.repo) or next((rc for rc in config.values() if rc['source_repo'] == args.repo), None)

SOURCE_REPO_NAME = repo_config.get('source_repo', args.repo)
ORGANIZATION_NAME = SOURCE_REPO_NAME.split('/')[0]
INSTRUCTOR_LOGINS = repo_config.get('instructors', [])  # instructors who have forked the repo, but are not in the GitHub tea
DROPPED_LOGINS = repo_config.get('dropped', [])  # students who have forked the repo, but are not in the course

team = next((team for team in gh.get_organization(ORGANIZATION_NAME).get_teams() if team.name == 'Instructors'), None)
instructors = list(team.get_members()) if team else []

source_repo = gh.get_repo(SOURCE_REPO_NAME)
student_repos = sorted((repo for repo in source_repo.get_forks()
                        if repo.owner not in instructors and repo.owner.login not in INSTRUCTOR_LOGINS + DROPPED_LOGINS),
                       key=lambda repo:repo.owner.login.lower())
student_login_names = {repo.owner.login: (repo.owner.name or repo.owner.login) for repo in student_repos}

## File commit dates

def is_merge_commit(commit):
    return len(commit.parents) > 1

def get_repo_file_commit_mod_times(repo):
    """Return a list [(repo_owner_login, filename, last_modified)] of the last modified date of each file
    modified by the repo owner."""
    print('fetching commits for', student_login_names[repo.owner.login])
    owner_commits = (commit for commit in repo.get_commits()
                     if commit.author == repo.owner
                     and not is_merge_commit(commit))
    # collect these into a dict in order to collect only the last date for each file
    file_mod_times = {file.filename: commit.last_modified
                      for commit in owner_commits
                      for file in commit.files}
    return [(repo.owner.login, *data) for data in file_mod_times.items()]

student_file_mods = [item
                      for repo_file_commit_mod_times in map(get_repo_file_commit_mod_times, student_repos)
                      for item in repo_file_commit_mod_times]
student_file_mods

# def exercise_group(filename):
#     return os.path.dirname(filename) or filename


## File hashes

def collect_repo_file_hashes(repo):
    """Return a dict filename -> git_hash"""
    latest_commit = repo.get_commits()[0]
    return {tree.path: tree.sha
            for tree in repo.get_git_tree(latest_commit.sha, recursive=True).tree}

master_file_hashes = collect_repo_file_hashes(source_repo)
master_file_hashes

# pd.DataFrame(list(master_file_hashes.values()), index=master_file_hashes.keys(), columns=['hash'])


# Build a table of hashes of all the student files, to test for duplicates against the source

def get_repo_and_file_hashes(repo):
    print('get file hashes for', repo.owner.login)
    return repo, collect_repo_file_hashes(repo)

student_file_hashes = {(repo.owner.login, filename): git_hash
                       for repo, file_hashes in map(get_repo_and_file_hashes, student_repos)
                       for filename, git_hash in file_hashes.items()}
student_file_hashes

filtered_student_file_mods = \
    [(login, filename, mod_time) for login, filename, mod_time in student_file_mods
     if student_file_hashes.get((login, filename), 1) != master_file_hashes.get(filename, None)
     and not re.match(IGNORE_FILES_RE, filename)]

def filename_sort_key(f):
    return tuple(int(s) if re.match(r'\d+', s) else s for s in re.split(r'(\d+)', f))

student_names = sorted(set(student for student, *_ in filtered_student_file_mods), key=str.lower)
filenames = sorted(set(filename for _, filename, *_ in filtered_student_file_mods if not re.match(IGNORE_FILES_RE, filename)), key=filename_sort_key)
filenames

data = [[next((d for s, f, d in filtered_student_file_mods if s == student and f == filename), None)
          for student in student_names]
         for filename in filenames]
df = pd.DataFrame(data, index=filenames, columns=student_names)
df.to_csv('reading journal times.csv')
df
