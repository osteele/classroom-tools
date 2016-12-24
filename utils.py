import hashlib
import os

DEFAULT = object()

def get_file_git_hash(filename, default=DEFAULT):
    if default is not DEFAULT and not os.path.exists(filename):
        return default

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

def collect_repo_hashes(repo):
    commit = repo.get_commits()[0]
    return dict((item.path, item.sha)
                for item in repo.get_git_tree(commit.sha, recursive=True).tree)
