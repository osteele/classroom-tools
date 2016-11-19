import base64
import itertools
import hashlib
import os
import sys
from github import Github, GithubException

SKIP_DOWNLOADED = 1
REPO_LIMIT = 0
PRINT_SKIPPED = 1
DONT_SKIP = []

if 0:
    DONT_SKIP = ['day14_reading_journal.ipynb']
    DROPPED_LOGINS = ['rwong3']
    DST_DIR = 'build/sd16-reading-repos'
    INSTRUCTOR_LOGINS = ['osteele']
    SOURCE_REPO = 'sd16fall/ReadingJournal'
elif 1:
    INSTRUCTOR_LOGINS = ['osteele', 'lynnandreastein', 'alisonberkowitz']
    DROPPED_LOGINS = ['DhashS', 'DHZBill']
    DST_DIR = 'build/focs-hw'
    SOURCE_REPO = 'focs16fall/focs-assignments'

# REPO_LIMIT = 3

INSTRUCTOR_LOGINS.append('LucyWilcox')

gh_token = os.environ['GITHUB_API_TOKEN']
gh = Github(gh_token)

def download_contents(repo, dst_path, master_shas, is_master, src_path='', indent='  '):
    files = [c for c in repo.get_dir_contents(src_path)]
    if not files:
        print('%s: no files' % repo.name, file=sys.stderr)
        return

    for c in files:
        if c.name == '.DS_Store': continue

        dst_name = os.path.join(dst_path, c.name)
        if False and len(files) > 1:
            dst_path + os.path.splitext(c.name)[1]

        if c.type == 'dir':
            print('%s%s/' % (indent, os.path.join(src_path, c.name)))
            download_contents(repo, os.path.join(dst_path, c.name), master_shas, is_master, os.path.join(src_path, c.name), indent + '  ')
            continue

        assert c.type == 'file'

        if is_master:
            master_shas[src_path] = c.sha

        if os.path.exists(dst_name):
            if not is_master and c.sha == master_shas.get(src_path):
                print('%s%s/%s: same as in master; deleting' % (indent, src_path, c.name))
                os.remove(dst_name)
                continue
            if c.sha == file_sha1(dst_name):
                continue
            else:
                print('%s%s: %s != %s' % (indent, c.name, c.sha, file_sha1(dst_name)))

        try:
            content = c.content
        except GithubException:
            if PRINT_SKIPPED: print('%s%ss: skipping (too large)' % (indent, c.name))
            continue

        print('%s%s (%d bytes)' % (indent, c.name, c.size))
        os.makedirs(dst_path, exist_ok=True)
        with open(dst_name, 'wb') as f:
            f.write(base64.b64decode(c.content))

def file_sha1(filename):
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()
    sha1.update(('blob %d\0' % os.stat(filename).st_size).encode('utf-8'))
    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


master = gh.get_repo(SOURCE_REPO)
repos = master.get_forks()

repos = [r for r in repos if r.owner.login not in INSTRUCTOR_LOGINS + DROPPED_LOGINS]
repos = sorted(repos, key=lambda r:r.owner.login)

if REPO_LIMIT:
    # repos = itertools.islice(repos, REPO_LIMIT)
    repos = repos[:REPO_LIMIT]

master_shas = {}

for repo in [master] + repos:
    owner = repo.owner
    print(owner.login)
    dirname = 'master' if repo is master else owner.login
    download_contents(repo, os.path.join(DST_DIR, dirname), master_shas, repo == master)
