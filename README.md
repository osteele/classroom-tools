# Olin Computing Assignment Tools

This repository contains tools for teaching computing, mostly related to GitHub and Jupyter notebooks.

## Setup

Install Python 3.5 or greater.

To check whether Python 3.5 is installed, execute `python --version`, and verify the output version:

``` bash
$ python --version
Python 3.5.2 :: Anaconda custom (x86_64)
```

An easy way to install Python is to follow the [install instructions for Anaconda](https://docs.continuum.io/anaconda/install).

## Usage

`python create_course_enrollment_flashcards.py`
: Turns a Course Enrollment page downloaded from the Portal into:
- a file and directory suitable for consumption by [FlashCard Deluxe](http://orangeorapple.com/Flashcards/)
- an HTML page that displays all the student names and faces in a grid

`python download_repo_fork_files.py`
: Download all the forks of a repo. Suitable for collecting assignments.
- This can also download all the individual copies of a [GitHub Classroom](https://classroom.github.com) assignment, even though these are not forks.

`python github_fork_file_mod_times.py`
: Create a spreadsheet that contains the student names and file modification dates for file in a forked repository.

`python summarize_scope_survey.py`
: Give a SCOPE Peer and Self review spreadsheet, create an HTML report organized by student.

## Other Files

`utils.py`
: Utility functions potentially shared by multiple scripts.

### Undocumented Works in Progress

`collect_notebooks.py`
: Collect downloaded notebooks into a common directory.

`combine_notebooks.py`
: Combine notebooks into a single notebook. This is mastered from,
and documented at, [olin-computing/assignment-tools](https://github.com/olin-computing/assignment-tools) (which was in turn forked from (paulruvolo/SoftDesSp16Prep)[https://github.com/paulruvolo/SoftDesSp16Prep]).

`remove_identical_files.py`
: Remove files that are identical to a master.
