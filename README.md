# Olin Computing Assignment Tools

This repository contains tools for collecting and processing projects and assignments,
mostly related to GitHub and Jupyter notebooks.

It also contains a smattering of other class-related tools.

Report issues [here](https://github.com/olin-computing/classroom-tools/issues).


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

    $ pip3 install -r requirements.txt

Depending on how Python is installed, you may need to prefix `pip3 install …` by `sudo`.


## Usage

### General Usage

The repository consists of a number of Python scripts, in the `scripts` directory.

Invoke a script with `--help` to see options that aren't listed below.

The scripts assume the following directory organization.
These subdirectories are not committed to the repository.

* `build`
: Files that are synthesized (as opposed to created) are placed here.

* `config`
: Optional configuration files.

* `downloads`
: Scripts look here for manually downloaded files. Scripts that download files also place them here.

`REPO_NAME` is a GitHub repository full name, in the format *$GitHub_organization*/*$repo_short_name*.

### The Scripts

#### `./scripts/create_course_enrollment_flashcards.py HTML_FILE`

Turns a Course Enrollment page downloaded from the Portal into:

1. A file and directory suitable for consumption by [FlashCard Deluxe](http://orangeorapple.com/Flashcards/)
2. An HTML "contact sheet" page, that displays all the student names and faces in a grid.

#### `./scripts/download_repo_fork_files.py REPO_NAME`

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

#### `./scripts/github_fork_file_mod_times.py REPO_NAME`

Create a spreadsheet that contains the student names and file modification dates, for each file in a forked repository.

#### `./scripts/summarize_scope_survey.py CSV_FILE`

Give a SCOPE Peer and Self review spreadsheet, create an HTML report organized by student.

#### `./scripts/combine_notebooks.py REPO_NAME NOTEBOOK_FILE_NAME`

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

#### `./scripts/collect_notebooks.py` (under development)

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


## Contributing

Some things to work on are listed [here](https://github.com/olin-computing/classroom-tools/issues).


## Style

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

`scripts`
: Script functions, invoked from the command line.

`lib`
: Utility functions, potentially shared by multiple scripts.
