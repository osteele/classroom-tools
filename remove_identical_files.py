import os
import hashlib
import filecmp

symlink_targets = {}
file_hashes = {}

def file_hash(fname):
    m = hashlib.md5()
    with open(fname) as f:
        m.update(f.read().encode('utf-8'))
    return m.digest()

def replace_by_links(src, master):
    if master not in symlink_targets: symlink_targets[master] = os.path.realpath(master)
    # if os.path.realpath(src) == symlink_targets[master]: return
    if not os.path.exists(master): return
    if os.path.isdir(src):
        for f in os.listdir(src):
            replace_by_links(os.path.join(src, f), os.path.join(master, f))
    else:
        if filecmp.cmp(src, master):
            print('equal', src, master)
            # os.remove(src)
            # os.symlink(os.path.relpath(master, os.path.dirname(src)), src)

src = 'build/focs-hw'
student_dirs = [f for f in os.listdir(src) if os.path.isdir(os.path.join(src, f)) and f != 'master']
for dir in student_dirs:
  replace_by_links(os.path.join(src, dir), os.path.join(src, 'master'))
