# Olin Computing Assignment Tools

This repository contains tools for teaching computing, mostly related to GitHub and Jupyter notebooks.

## Status

The scripts in this file are still under (occasional) active development, and are under-tested and under-documented.

## Setup

1\. Install Python 3.5 or greater.

To check whether Python 3.5 is installed, execute `python3 --version`, and verify the output version:

``` bash
$ python3 --version
Python 3.5.2 :: Anaconda custom (x86_64)
```

[An easy way to install Python is to follow the [install instructions for Anaconda](https://docs.continuum.io/anaconda/install).]

2\. Install required Python packages:

``` bash
$ pip3 install -r requirements.txt
```

Depending on how Python is installed, you may need to prefix `pip3 install …` by `sudo`.


## Usage

`REPO_NAME` is a GitHub repository full name, in the format *$GitHub_organization*/*$repo_short_name*.

Invoke these with `--help` to see additional options.

### `./create_course_enrollment_flashcards.py HTML_FILE`

Turns a Course Enrollment page downloaded from the Portal into:

1. A file and directory suitable for consumption by [FlashCard Deluxe](http://orangeorapple.com/Flashcards/)
2. An HTML "contact sheet" page, that displays all the student names and faces in a grid.

### `./download_repo_fork_files.py REPO_NAME`

Download all the forks of a repo. Suitable for collecting assignments.

This script downloads files into the directory structure:

```
downloads/
└── ${github_organization}-${github_repo}/
    └── ${student_github_id}/
        └── files…
```

Only files that are different from the version in the origin repository are downloaded.

This script can also download all the individual copies of a [GitHub Classroom](https://classroom.github.com) assignment, even though these are not forks. Use the `--classroom` option to invoke it in this mode.

### `./github_fork_file_mod_times.py REPO_NAME`

Create a spreadsheet that contains the student names and file modification dates, for each file in a forked repository.

### `./summarize_scope_survey.py CSV_FILE`

Give a SCOPE Peer and Self review spreadsheet, create an HTML report organized by student.

### `./combine_notebooks.py REPO_NAME NOTEBOOK_FILE_NAME`

Combine notebooks into a single notebook.

This script expects a directory structure created by the `download_repo_fork_files` script. It creates:

```
build/${github_organization}-${github_repo}
├── processed_notebooks/
│   └── notebook_name.ipynb
└── summaries/
    ├── poll1.csv
    ├── poll2.csv
    └── …
```

## Under Development

### `./collect_notebooks.py`

Collect downloaded notebooks into a common directory.

This script expects a directory structure created by the `download_repo_fork_files` script. It creates:

```
downloads/
└── ${github_organization}-${github_repo}-combined/
    └── ${filename_without_extension}/
        ├── ${student1_github_login}.${filename_extension}
        ├── ${student2_github_login}.${filename_extension}
        └── …
```

The name of the repository is currently hardcoded into the script.

This script is derived from,
and documented at, [osteele/assignment-tools](https://github.com/osteele/assignment-tools) (which was in turn forked from [paulruvolo/SoftDesSp16Prep](https://github.com/paulruvolo/SoftDesSp16Prep)).


## Other Files

`utils.py`
: Utility functions, potentially shared by multiple scripts.
