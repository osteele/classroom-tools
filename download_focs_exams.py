import base64
import itertools
import os
import sys
from github import Github, GithubException

SKIP_DOWNLOADED = 1
REPO_LIMIT = 0

gh_token = os.environ['GITHUB_API_TOKEN']
gh = Github(gh_token)

TEAM_COLLABORATORS = ['osteele', 'lynnandreastein']
DIST_FILES = ["FOCS_F2016_Exam_1.pdf", "README.md", "Schemein1page.pdf", "day 4.rkt", "logic.pdf"]

def download_contents(repo, dst_path, src_path=''):
    files = [c for c in repo.get_dir_contents(src_path) if c.name not in DIST_FILES]
    if not files:
        print('%s: no files' % repo.name, file=sys.stderr)
        return
    if len(files) > 1:
        os.makedirs(dst_path, exist_ok=True)
    for c in files:
        dst_name = os.path.join(dst_path, c.name) if len(files) > 1 else dst_path + os.path.splitext(c.name)[1]
        if SKIP_DOWNLOADED and os.path.exists(dst_name):
            print('%s/%s: exists; skipping' % (repo.name, c.name))
            continue
        try:
            content = c.content
        except GithubException:
            print('%s/%s: too large; skipping' % (repo.name, c.name), file=sys.stderr)
            # -> DuncanDHall/completed_exam1.pdf, hannahtwiggsmith/focs-test.pdf, logandavis/Exam_Submission.pdf
            continue
        print('  %s' % c.name)
        if content is None:
            #download_contents(repo, os.path.join())
            print('skip %s' % c.path)
            continue
        with open(dst_name, 'wb') as f:
            f.write(base64.b64decode(c.content))

repos = (repo for repo in gh.get_user().get_repos()
    if repo.name.startswith('focs-2016fall-exam-1-')
    and not repo.name.endswith('-osteele'))

if REPO_LIMIT:
    repos = itertools.islice(repos, REPO_LIMIT)

for repo in repos:
    print(repo.name)
    users = [user for user in repo.get_collaborators() if user.login not in TEAM_COLLABORATORS]
    if len(users) != 1:
        print("%s: expected one user; got %s" % (repo.login, [user.login for user in users]), file=sys.stderr)
        continue
    download_contents(repo, os.path.join("build", users[0].login))
