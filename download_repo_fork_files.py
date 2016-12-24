import argparse
import base64
import itertools
import hashlib
import os
import sys
import yaml
from github import Github, GithubException
from utils import get_file_git_hash, collect_repo_hashes

DEFAULT_CONFIG_FILE = 'config/source_repos.yaml'
ORIGIN_DIRNAME = 'origin'

parser = argparse.ArgumentParser(description="Download all the forks of a GitHub repository.")
parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, help="YAML configuration file")
parser.add_argument("--limit", type=int, metavar='N', help="download only the first N repos")
parser.add_argument("--match", metavar='SUBSTRING', help="download only repos that contains SUBSTRING")
parser.add_argument("repo", help="source repo")
test_args = ['softdes']
args = parser.parse_args(*((test_args,) if 'ipykernel' in sys.modules else ()))

config = {}
if os.path.exists(args.config) or args.config != DEFAULT_CONFIG_FILE:
    with open(args.config) as f:
        config = yaml.load(f)

repo_config = config.get(args.repo, None) or next((item for item in config.values() if item['source_repo'] == args.repo), None)

DROPPED_LOGINS = repo_config.get('dropped', [])
DOWNLOAD_PATH = repo_config.get('download_path')
INSTRUCTOR_LOGINS = repo_config.get('instructors', [])
SOURCE_REPO = repo_config.get('source_repo', args.repo)

GH_TOKEN = os.environ['GITHUB_API_TOKEN']
gh = Github(GH_TOKEN)

def download_contents(repo, dst_path):
    commit = repo.get_commits()[0]
    entries = [item for item in repo.get_git_tree(commit.sha, recursive=True).tree
               if item.type == 'blob'
               and item.sha != source_repo_hashes.get(item.path, None)]

    changed_entries = [entry for entry in entries
                       if entry.sha != get_file_git_hash(os.path.join(dst_path, entry.path), None)]

    if not entries:
        print("%s: no files" % repo.owner.login)
        return

    if not changed_entries:
        print("%s: no new files" % repo.owner.login)
        return

    print("%s:" % repo.owner.login)
    for entry in changed_entries:
        print("  %s" % (entry.path))
        dst_name = os.path.join(dst_path, entry.path)
        os.makedirs(os.path.dirname(dst_name), exist_ok=True)
        blob = repo.get_git_blob(entry.url.split('/')[-1])
        with open(dst_name, 'wb') as f:
            f.write(base64.b64decode(blob.content))


origin = gh.get_repo(SOURCE_REPO)
repos = origin.get_forks()

repos = [repo for repo in repos if repo.owner.login not in INSTRUCTOR_LOGINS + DROPPED_LOGINS]
repos = sorted(repos, key=lambda r:r.owner.login)
if args.match: repos = [repo for repo in repos if args.match in repo.owner.login]
if args.limit: repos = repos[:args.limit]

source_repo_hashes = collect_repo_hashes(origin)

for repo in repos:
    owner = repo.owner
    dirname = ORIGIN_DIRNAME if repo is origin else owner.login
    download_contents(repo, os.path.join(DOWNLOAD_PATH, dirname))
