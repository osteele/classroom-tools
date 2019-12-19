# Olin Computing Assignment Tools

This repository contains tools for collecting and processing projects and assignments,
mostly related to GitHub, [GitHub Classroom](https://classroom.github.com), and [Jupyter notebooks](http://jupyter.org).

It also contains a smattering of other class-related tools, specific to the Olin College IT infrastructure.

Report issues [here](https://github.com/olin-computing/classroom-tools/issues).

## Status

The scripts in this file are still under (occasional) active development, and are under-tested and under-documented.

## Setup

### 1. Download this repository

```bash
$ git clone https://github.com/olin-computing/classroom-tools.git
```

### 2. Install Python

Install Python 3.7 or greater. [Lesser versions of Python 3 will likely work, but are untested. Python 2.x is right out.]

Testing whether Python 3.7 is installed:

1. Execute `python3 --version`,
2. Verify the output version:

```bash
$ python3 --version
Python 3.7.5
```

### 3. Install Poetry and packages

1. Install [Poetry](https://python-poetry.org)
2. `poetry install`

### 4. [Optional] Retrieve a GitHub personal API token

Some of these scripts use GitHub's API.

GitHub limits the rate at which a particular machine can make API calls.
If you repeatedly run these scripts on a repo with many forks, you may run into these limits.
(You may also run into them if you work on developing the scripts.)

You will also need a personal API token in order to access any private repositories.
You will need this for use with [GitHub Classroom](https://classroom.github.com).

To increase the limit, [create a personal GitHub API token](https://github.com/blog/1509-personal-api-tokens),
and set the `GITHUB_API_TOKEN` environment variable to this value.

For example, my macOS and Ubuntu shells are set to **zsh**, so my startup files include `~/.zshenv`.
My `~/.zshenv` includes this line (where `xxxxxxxx` is my personal GitHub API token):

    export GITHUB_API_TOKEN=xxxxxxxx

## Usage

### General Usage

The repository consists of a number of Python scripts in the `scripts` directory.

Invoke a script with `--help` to see options that aren't listed below.

The scripts assume the following directory organization.
These subdirectories are not committed to the repository.

    ./
    ├── build
    │     Files that are created by script (as opposed to downloaded) are placed here.
    ├── config – optional configuration files
    │     student-nicknames.txt
    └── downloads
          Scripts look here for manually downloaded files. Scripts that download files also place them here.

`REPO_NAME` is a GitHub repository full name, in the format *org_name*/*short_name*. For example, this repo is `olin-computing/classroom-tools`.

### GitHub Tools

#### Clone Forks

`./scripts/clone-repo-forks REPO_NAME`

`./scripts/clone-repo-forks --classroom REPO_NAME`

Clone the forks of a repo.

`REPO_NAME` is in `org_name/repo_name` format.

With the `--classroom` option, the script clones the repos `org_name/repo_name-$login` in the `org_name` account.
This is the format of repos created by GitHub Classroom.

I no longer use this script. [multiclone](https://github.com/osteele/multiclone) is an alternate golang implementation, that clones the repos in parallel.

#### Download Forked Files

`./scripts/download-repo-fork-files REPO_NAME`

`./scripts/download-repo-fork-files --classroom REPO_NAME`

Download a repo's forks' modified files.
(Files whose contents are different from the source repo.)
This is suitable for collecting assignments, and quickly inspecting which files have changed.

Only files that are different from the version in the origin repository are downloaded.

With the `--classroom` option, the script downloads repos `org_name/repo_name-$login` in the `org_name` account.
This is the format of repos created by GitHub Classroom.

This script also omits repos that belong to members of *org_name*.

(Both of these are suitable for my purposes, but could easily be turned into command-line options.)

This script downloads files into the directory structure:

    ./downloads/
    └── ${github_organization}-${github_repo}/
        └── ${student_github_id}/
            └── files…

#### Collect Fork File Modification Times

`./scripts/github-fork-file-modtimes REPO_NAME`

Create a spreadsheet that contains the student names and file modification dates, for each file in a forked repository.

#### Collate Downloaded Files

`./scripts/collate-downloaded-files` (under development)

Collect downloaded notebooks into a common directory.

This script expects a directory structure created by the `download-repo-fork-files` script. It creates:

    ./downloads/
    └── ${github_organization}-${github_repo}-combined/
        └── ${filename_without_extension}/
            ├── ${student1_github_login}.${filename_extension}
            ├── ${student2_github_login}.${filename_extension}
            ├── …
            └── ${student${n}_github_login}.${filename_extension}

The name of the repository is currently hardcoded into the script.

### Jupyter Tools

#### Collate Jupyter Notebooks

`./scripts/combine-notebooks REPO_NAME NOTEBOOK_FILE_NAME`

Combine notebooks into a single notebook.

This script expects a directory structure created by the `download-repo-fork-files` script. It creates:

    ./build/${github_organization}-${github_repo}
    ├── processed_notebooks/
    │   └── notebook_name.ipynb
    └── summaries/
        ├── poll1.csv
        ├── poll2.csv
        ├── …
        └── poll${n}.csv

This script is derived from,
and documented at, [osteele/assignment-tools](https://github.com/osteele/assignment-tools) (which was in turn forked from [paulruvolo/SoftDesSp16Prep](https://github.com/paulruvolo/SoftDesSp16Prep)).

The version in this directory is not the latest, and is not under active development here.
The [nbcollate package](https://github.com/olin-computing/nbcollate) is the successor.
`pip install nbcollate` to install this package, and the `nbcollate` command-line tool.

A web application with similar functionality is at [olin-computing/assignment-dashboard](https://github.com/olin-computing/assignment-dashboard).
That application caches the state of GitHub into a local **sqlite3** store, and provides a web interface for inspect completion status by student or by question and for browsing the original and collated notebooks.

### Other Scripts

#### Create Flashcards and Contact Sheet

`./scripts/create-enrollment-flashcards HTML_FILE`

Generate a file and media directory suitable for consumption by [FlashCard Deluxe](http://orangeorapple.com/Flashcards/),
from a Course Enrollment page downloaded from the Portal.

#### Create Student Contact Sheet

`./scripts/create-enrollment-contact-sheet HTML_FILE`

Generate HTML "contact sheet" page, that displays all the student names and faces in a grid,
from a Course Enrollment page downloaded from the Portal.


#### Summarize Scope Survey

`./scripts/summarize-scope-survey CSV_FILE`

Given a SCOPE Peer and Self review spreadsheet, create an HTML report organized by student.

## Contributing

Some things to work on are listed [here](https://github.com/olin-computing/classroom-tools/issues).

### Setting up a development environment

`pip install -r requirements-dev.txt`

To test in new conda environment:

```bash
$ conda create --name classroom-tools python=3.5 pip
$ source activate classroom-tools
$ pip install -r requirements-dev.txt
```

### Style

With exceptions listed in `setup.cfg`, code should conform to [PEP8](https://www.python.org/dev/peps/pep-0008/), [PEP257](https://www.python.org/dev/peps/pep-0257/), and the [Google Python Style Guide](http://google.github.io/styleguide/pyguide.html).

You can verify code against these style guides via:

    $ pip3 install -r requirements-dev.txt  # once
    $ flake8 scripts                        # before each commit

or by setting up a [git pre-commit hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) to run the latter command.

These scripts are written in a Jupyter-notebook-like style, for easy development with the [Hydrogen Atom plugin-in](https://atom.io/packages/hydrogen) and the [Python Visual Studio Code extension](https://github.com/DonJayamanne/pythonVSCode/wiki/Jupyter-(IPython)).

Specifically, they are light on functions and heavy on global variables.

This is an experiment, and may not have legs.
For example, it would be nice to be able to re-organize the scripts as modules,
and invoke them as subcommands from a single CLI entry point, or make them available to a web or desktop
application. The current style may not be compatible with that.

### Directory Organization

    classroom-tools/
    ├── build – not committed to the repo
    ├── config – not committed to the repo
    ├── downloads – not committed to the repo
    ├── scripts
    │     Script functions, invoked from the command line.
    ├── src
    │     Utility functions that aren't scripts; potentially shared by multiple scripts.
    └── templates
          HTML jinja2 template files

### Acknowledgements

`combine-notebooks.py` is derived from a script by
Paul Ruvolo at Olin [paulruvolo/SoftDesSp16Prep](https://github.com/paulruvolo/SoftDesSp16Prep).

`create-enrollment-flashcards` is based on an idea by Ben Hill at Olin.
His code was simpler and cleaner but I added more functionality (nicknames, HTML generation) before I saw his,
and haven't yet backed out my complexity in favor of his simplicity.

### License

MIT
