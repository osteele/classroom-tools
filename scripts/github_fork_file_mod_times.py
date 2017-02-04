#!/usr/bin/env python3
# coding: utf-8

# Collect times that each homework was submitted.

import argparse
import os
import re
import sys

import pandas as pd
import yaml
from github import Github

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

OUTPUT_FILE = "%s file times.csv" % re.sub(r'[./]', ' ', args.repo)

gh = Github(GITHUB_API_TOKEN)

with open(args.config) as f:
    config = yaml.load(f)
repo_config = config.get(args.repo) or next((rc for rc in config.values() if rc['source_repo'] == args.repo), None)

SOURCE_REPO_NAME = repo_config.get('source_repo', args.repo)
ORGANIZATION_NAME = SOURCE_REPO_NAME.split('/')[0]
# instructors who have forked the repo, but are not in the GitHub team:
INSTRUCTOR_LOGINS = repo_config.get('instructors', [])
DROPPED_LOGINS = repo_config.get('dropped', [])  # students who have forked the repo, but are not in the course

team = next((team for team in gh.get_organization(ORGANIZATION_NAME).get_teams() if team.name == 'Instructors'), None)
instructors = list(team.get_members()) if team else []

source_repo = gh.get_repo(SOURCE_REPO_NAME)
student_repos = sorted((repo for repo in source_repo.get_forks()
                        if repo.owner not in instructors and repo.owner.login not in INSTRUCTOR_LOGINS + DROPPED_LOGINS),
                       key=lambda repo: repo.owner.login.lower())
student_login_names = {repo.owner.login: (repo.owner.name or repo.owner.login) for repo in student_repos}


# File commit dates
#


def is_merge_commit(commit):
    return len(commit.parents) > 1


def get_repo_file_commit_mod_times(repo):
    """Return last-modified times of all the files in the repo.

    Return a list [(repo_owner_login, filename, last_modified)] of the last modified date of each file
    modified by the repo owner.
    """
    print('fetching commits for', student_login_names[repo.owner.login])
    owner_commits = (commit for commit in repo.get_commits()
                     if commit.author == repo.owner
                     and not is_merge_commit(commit))
    # collect these into a dict in order to collect only the last date for each file
    file_mod_times = {file.filename: commit.last_modified
                      for commit in owner_commits
                      for file in commit.files}
    return [(repo.owner.login, *data) for data in file_mod_times.items()]


student_file_mod_times = [item
                          for repo_file_commit_mod_times in map(get_repo_file_commit_mod_times, student_repos)
                          for item in repo_file_commit_mod_times]


# File hashes
#

def collect_repo_file_hashes(repo):
    """Return a dict filename -> git_hash"""
    latest_commit = repo.get_commits()[0]
    return {tree.path: tree.sha
            for tree in repo.get_git_tree(latest_commit.sha, recursive=True).tree}


def get_repo_and_file_hashes(repo):
    print('get file hashes for', repo.owner.login)
    return repo, collect_repo_file_hashes(repo)


master_file_hashes = collect_repo_file_hashes(source_repo)

# Build a table of hashes of all the student files, to test for duplicates against the source

student_file_hashes = {(repo.owner.login, filename): git_hash
                       for repo, file_hashes in map(get_repo_and_file_hashes, student_repos)
                       for filename, git_hash in file_hashes.items()}
student_file_hashes

student_file_records = \
    [(login, filename, mod_time) for login, filename, mod_time in student_file_mod_times
     if student_file_hashes.get((login, filename), 1) != master_file_hashes.get(filename, None)
     and not re.match(IGNORE_FILES_RE, filename)]


def filename_sort_key(f):
    return tuple(int(s) if re.match(r'\d+', s) else s for s in re.split(r'(\d+)', f))


df = pd.DataFrame(student_file_records, columns=['student', 'file', 'mod_time'])\
    .pivot(index='student', columns='file', values='mod_time')
df = df.reindex_axis(sorted(df.columns, key=filename_sort_key), axis=1)
df.to_csv(OUTPUT_FILE)
df.head()
