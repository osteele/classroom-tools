#!/usr/bin/env python
""" This script is designed to support active reading.  It takes as input
    a set of ipython notebook as well as some target cells which define a set
    of reading exercises.  The script processes the collection of notebooks
    and builds a notebook which summarizes the responses to each question.
"""

import argparse
import io
import json
import os
import re
import sys
import urllib
from collections import OrderedDict
from copy import deepcopy
from multiprocessing import Pool

import Levenshtein
import pandas as pd
import nbformat
import nbconvert
from numpy import argmin

from disk_cache import disk_cache

PROJECT_DIR = os.path.relpath(os.path.join(os.path.dirname(__file__), '..'))
PROCESSED_NOTEBOOK_DIR = os.path.join(PROJECT_DIR, "processed_notebooks")
SUMMARY_DIR = os.path.join(PROJECT_DIR, 'summaries')

CACHE_DIR = os.path.join(PROJECT_DIR, '_cache')
use_disk_cache = False  # the --use-disk-cache CLI arg sets this

class NotebookExtractor(object):
    """ The top-level class for extracting answers from a notebook.
        TODO: add support multiple notebooks
    """

    MATCH_THRESH = 10  # maximum edit distance to consider something a match

    def __init__(self, users_df, notebook_template_file, include_usernames=False):
        """ Initialize with the specified notebook URLs and
            list of question prompts """
        self.users_df = users_df
        self.question_prompts = self.build_question_prompts(notebook_template_file)
        self.include_usernames = include_usernames
        nb_basename = os.path.basename(notebook_template_file)
        self.nb_name_stem = os.path.splitext(nb_basename)[0]

    def build_question_prompts(self, notebook_template_file):
        """Returns a list of `QuestionPrompt`. Each cell with metadata `is_question` truthy
        produces an instance of `QuestionPrompt`."""
        with open(notebook_template_file, 'r') as fid:
            self.template = json.load(fid)

        prompts = []
        prev_prompt = None
        for idx, cell in enumerate(self.template['cells']):
            is_final_cell = idx + 1 == len(self.template['cells'])
            metadata = cell['metadata']
            if metadata.get('is_question', False):
                cell_source = ''.join(cell['source'])
                if prev_prompt is not None:
                    prompts[-1].stop_md = cell_source
                is_poll = metadata.get('is_poll', 'Reading Journal feedback' in cell_source.split('\n')[0])
                prompts.append(QuestionPrompt(question_heading=u"",
                                              name=metadata.get('problem', None),
                                              index=len(prompts),
                                              start_md=cell_source,
                                              stop_md=u'next_cell',
                                              is_optional=metadata.get('is_optional', None),
                                              is_poll=is_poll
                                              ))
                if metadata.get('allow_multi_cell', False):
                    prev_prompt = prompts[-1]
                    # if it's the last cell, take everything else
                    if is_final_cell:
                        prompts[-1].stop_md = u""
                else:
                    prev_prompt = None
        return prompts

    def fetch_notebooks(self):
        """Returns a dictionary {github_username -> url, json?}.

        Unavailable notebooks have a value of `None`."""

        p = Pool(20)  # HTTP fetch parallelism. This number is empirically good.
        print "Fetching %d notebooks..." % self.users_df['notebook_urls'].count()
        return dict(zip(self.users_df['gh_username'],
                        p.map(p_read_json_from_url, self.users_df['notebook_urls'])))

    def gh_username_to_fullname(self, gh_username):
        return self.users_df[users_df['gh_username'] == gh_username]['Full Name'].iloc[0]

    def extract(self):
        """ Filter the notebook at the notebook_URL so that it only contains
            the questions and answers to the reading.
        """

        nbs = self.fetch_notebooks()
        self.usernames = sorted([name for name, nb in nbs.items() if nb], key=self.gh_username_to_fullname)

        users_missing_notebooks = [u for u, notebook_content in nbs.items() if not notebook_content]
        if users_missing_notebooks:
            fullnames = map(self.gh_username_to_fullname, users_missing_notebooks)
            print "Users missing notebooks:", ', '.join(sorted(fullnames))

        if self.include_usernames:
            # Sort by username iff including the usernames in the output.
            # This makes it easier to find students.
            nbs = OrderedDict(sorted(nbs.items(), key=lambda t: t[0].lower()))

        for prompt in self.question_prompts:
            prompt.answer_status = {}
            for gh_username, notebook_content in nbs.items():
                if notebook_content is None:
                    continue
                suppress_non_answer = bool(prompt.answers)
                response_cells = \
                    prompt.get_closest_match(notebook_content['cells'],
                                             NotebookExtractor.MATCH_THRESH,
                                             suppress_non_answer)
                if not response_cells:
                    status = 'missed'
                elif not response_cells[-1]['source'] or not NotebookUtils.cell_list_text(response_cells):
                    status = 'blank'
                else:
                    status = 'answered'
                    if not suppress_non_answer:
                        # If it's the first notebook with this answer, extract the questions from it.
                        # This is kind of a bass-ackwards way to do this; it's incremental from the previous
                        # strategy.
                        prompt.cells = [cell for cell in response_cells
                                        if cell['metadata'].get('is_question', False)]
                        response_cells = [cell for cell in response_cells if cell not in prompt.cells]
                    prompt.answers[gh_username] = response_cells
                prompt.answer_status[gh_username] = status

        sort_responses = not self.include_usernames
        sort_responses = False  # FIXME doesn't work because questions are collected into first response
        if sort_responses:
            def cell_slines_length(response_cells):
                return len('\n'.join(u''.join(cell['source']) for cell in response_cells).strip())
            for prompt in self.question_prompts:
                prompt.answers = OrderedDict(sorted(prompt.answers.items(), key=lambda t: cell_slines_length(t[1])))

    def report_missing_answers(self):
        # Report missing answers
        mandatory_questions = [prompt for prompt in self.question_prompts
                               if not prompt.is_poll and not prompt.is_optional]
        for prompt in mandatory_questions:
            unanswered = sorted((username, status)
                                for username, status in prompt.answer_status.items()
                                if status != 'answered')
            for username, status in unanswered:
                print "{status} {prompt_name}: {username}".format(
                    status=status.capitalize(),
                    prompt_name=prompt.name,
                    username=self.gh_username_to_fullname(username))

    def write_notebook(self, include_html=True):
        suffix = "_responses_with_names" if self.include_usernames else "_responses"
        nb_name = self.nb_name_stem + suffix
        output_file = os.path.join(PROCESSED_NOTEBOOK_DIR, nb_name + '.ipynb')
        html_output = os.path.join(PROCESSED_NOTEBOOK_DIR, nb_name + '.html')

        remove_duplicate_answers = not self.include_usernames

        filtered_cells = []
        for prompt in self.question_prompts:
            filtered_cells += prompt.cells
            answers = prompt.answers_without_duplicates if remove_duplicate_answers else prompt.answers
            for gh_username, response_cells in answers.items():
                if self.include_usernames:
                    filtered_cells.append(
                        NotebookUtils.markdown_heading_cell(self.gh_username_to_fullname(gh_username), 4))
                filtered_cells.extend(response_cells)

        answer_book = deepcopy(self.template)
        answer_book['cells'] = filtered_cells
        nb = nbformat.from_dict(answer_book)

        print "Writing", output_file
        with io.open(output_file, 'wt') as fp:
            nbformat.write(nb, fp, version=4)

        if include_html:
            # TODO why is the following necessary?
            nb = nbformat.reads(nbformat.writes(nb, version=4), as_version=4)
            html_content, _ = nbconvert.export_html(nb)
            print "Writing", html_output
            with io.open(html_output, 'w') as fp:
                fp.write(html_content)

    def write_answer_counts(self):
        output_file = os.path.join(SUMMARY_DIR, '%s_response_counts.csv' % self.nb_name_stem)

        df = pd.DataFrame(
            data=[[u in prompt.answers for u in self.usernames] for prompt in self.question_prompts],
            columns=[self.gh_username_to_fullname(name) for name in self.usernames],
        )
        df.index = [prompt.name for prompt in self.question_prompts]
        df.sort_index(axis=1, inplace=True)
        df.insert(0, 'Total', df.sum(axis=1))
        df = pd.concat([df, pd.DataFrame(df.sum(axis=0).astype(int), columns=['Total']).T])

        print "Writing", output_file
        print 'Answer counts:'
        print df['Total']
        df.to_csv(output_file)

    def write_poll_results(self):
        poll_questions = [prompt for prompt in self.question_prompts if prompt.is_poll]
        for prompt in poll_questions:
            slug = prompt.name.replace(' ', '_').lower()
            output_file = os.path.join(SUMMARY_DIR, '%s_%s.csv' % (self.nb_name_stem, slug))
            print "Writing %s: poll results for %s" % (output_file, prompt.name)

            def user_response_text(username):
                return NotebookUtils.cell_list_text(prompt.answers.get(username, []))

            df = pd.DataFrame(
                index=[self.gh_username_to_fullname(name) for name in self.usernames],
                data=[user_response_text(username) for username in self.usernames],
                columns=['Response'])
            df.index.name = 'Student'
            df.sort_index(axis=1, inplace=True)
            df = df[df['Response'] != '']

            df.to_csv(output_file)


class QuestionPrompt(object):
    def __init__(self, question_heading, start_md, stop_md, name=None, index=None, is_poll=False, is_optional=None):
        """ Initialize a question prompt with the specified
            starting markdown (the question), and stopping
            markdown (the markdown from the next content
            cell in the notebook).  To read to the end of the
            notebook, set stop_md to the empty string.  The
            heading to use in the summary notebook before
            the extracted responses is contined in question_heading.
            To omit the question heading, specify the empty string.
        """
        if is_optional is None and start_md:
            is_optional = bool(re.search(r'optional', start_md.split('\n')[0], re.I))
        self.question_heading = question_heading
        self._name = name
        self.start_md = start_md
        self.stop_md = stop_md
        self.is_optional = is_optional
        self.is_poll = is_poll
        self.index = index
        self.answers = OrderedDict()
        self.cells = []

    @property
    def answers_without_duplicates(self):
        answers = dict(self.answers)
        answer_strings = set()  # answers to this question, as strings; used to avoid duplicates
        for username, response_cells in self.answers.items():
            answer_string = '\n'.join(u''.join(cell['source']) for cell in response_cells).strip()
            if answer_string in answer_strings:
                del answers[username]
            else:
                answer_strings.add(answer_string)
        return answers

    @property
    def name(self):
        m = re.match(r'^#+\s*(.+)\n', self.start_md)
        if self._name:
            return self._name
        format_str = {
            (False, False): '',
            (False, True): '{title}',
            (True, False): '{number}',
            (True, True): '{number}. {title}'
        }[isinstance(self.index, int), bool(m)]
        return format_str.format(number=(self.index or 0) + 1, title=m and m.group(1))

    def get_closest_match(self,
                          cells,
                          matching_threshold,
                          suppress_non_answer_cells=False):
        """ Returns a list of cells that most closely match
            the question prompt.  If no match is better than
            the matching_threshold, the empty list will be
            returned. """
        return_value = []
        distances = [Levenshtein.distance(self.start_md, u''.join(cell['source']))
                     for cell in cells]
        if min(distances) > matching_threshold:
            return return_value

        best_match = argmin(distances)
        if self.stop_md == u"next_cell":
            end_offset = 2
        elif len(self.stop_md) == 0:
            end_offset = len(cells) - best_match
        else:
            distances = [Levenshtein.distance(self.stop_md, u''.join(cell['source']))
                         for cell in cells[best_match:]]
            if min(distances) > matching_threshold:
                return return_value
            end_offset = argmin(distances)
        if len(self.question_heading) != 0 and not suppress_non_answer_cells:
            return_value.append(NotebookUtils.markdown_heading_cell(self.question_heading, 2))
        if not suppress_non_answer_cells:
            return_value.append(cells[best_match])
        return_value.extend(cells[best_match + 1:best_match + end_offset])
        return return_value


class NotebookUtils:
    @staticmethod
    def markdown_heading_cell(text, heading_level):
        """ A convenience function to return a markdown cell
            with the specified text at the specified heading_level.
            e.g. mark_down_heading_cell('Notebook Title','#')
        """
        return {u'cell_type': u'markdown',
                u'metadata': {},
                u'source': unicode('#' * heading_level + " " + text)}

    @staticmethod
    def cell_list_text(cells):
        return u''.join(s for cell in cells for s in cell['source']).strip()


def validate_github_username(gh_name):
    """Return `gh_name` if that Github user has a `repo_name` repository; else None."""
    fid = urllib.urlopen("http://github.com/" + gh_name)
    fid.close()
    return gh_name if 200 <= fid.getcode() <= 299 else None


@disk_cache(active_fn=lambda: use_disk_cache, cache_dir=CACHE_DIR)
def validate_github_usernames(gh_usernames, repo_name):
    """Returns a set of valid github usernames.

    A name is valid iff a GitHub user with that name exists, and owns a repository named `repo_name`.

    `gh_usernames_path` is a path to a CSV file with a `gh_username` column.

    Prints invalid names as errors."""
    p = Pool(20)
    valid_usernames = filter(None, p.map(validate_github_username, gh_usernames))
    invalid_usernames = set(gh_usernames) - set(valid_usernames)
    if invalid_usernames:
        print >> sys.stderr, "Invalid github username(s):", ', '.join(invalid_usernames)
    return valid_usernames

if True:
    nbe = NotebookExtractor(users_df, template_nb_path, include_usernames=args.include_usernames)
    nbe.extract()
    nbe.report_missing_answers()
    nbe.write_notebook(include_html=args.html_output)
    nbe.write_poll_results()
    nbe.write_answer_counts()
