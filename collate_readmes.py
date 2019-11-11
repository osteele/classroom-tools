"""Collate the README.md files of all repos generated from a template, into a single Markdown file
that contains a section for each repo.

Each individual README is prepended with a header that includes the GitHub login, as inferred from the name of the
generated repo. If the README already begins with a header, the login is appended, or substituted if the header is
simply "About Me".

If a file Roster.csv with columns "GitHub Login", "Preferred Name", and "Last Name" is present in the current directory,
these names are used instead of the GitHub login.

Usage:
    python collate_readmes.py
    python collate_readmes.py | pandoc --from markdown --metadata pagetitle="About Me" -s -o about.html
"""

from datetime import datetime
from dateutil import tz
import re
import sys
import json
import os
import subprocess
from pathlib import Path
from string import Template

import numpy as np
import pandas as pd

from graphqlclient import GraphQLClient


def get_git_config(name):
    result = subprocess.run(
        "git config".split() + [name], capture_output=True, text=True
    )
    if result.returncode:
        raise Exception(result.stderr.strip())
    return result.stdout.rstrip()


GITHUB_ACCESS_TOKEN = os.environ.get("GITHUB_ACCESS_TOKEN") or get_git_config(
    "user.accesstoken"
)


GH_CLIENT = GraphQLClient("https://api.github.com/graphql")
GH_CLIENT.inject_token(f"token {GITHUB_ACCESS_TOKEN}")


def query(gql, variables=None):
    """Perform a GraphQL query, with error detection and variable substition."""
    variables = variables or {}
    q = Template(gql).substitute(**{k: json.dumps(v) for k, v in variables.items()})
    result = json.loads(GH_CLIENT.execute(q, variables))
    if "errors" in result:
        # TODO include err['locations'] = {'line', 'column'}
        raise Exception("\n".join(err["message"] for err in result["errors"]))
    return result["data"]


ORG_REPOS_GQL = """
query {
  organization(login: $organization_login) {
    repositories(first: 100, after: $cursor) {
      nodes {
        name
        nameWithOwner
        readme: object(expression: "master:README.md") {
          ... on Blob {
            text
          }
        }
        templateRepository {
          nameWithOwner
        }

        ref(qualifiedName: "master") {
          target {
            ... on Commit {
              history(first: 100) {
                edges {
                  node {
                    oid
                    authoredDate
                    committedDate
                    pushedDate
                    author {
                      name
                      email
                      date
                    }
                  }
                }
              }
            }
          }
        }
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""


def get_generated_repos(name_with_owner):
    org_login = name_with_owner.split("/")[0]
    cursor = None
    repos = []

    while True:
        variables = {"organization_login": org_login, "cursor": cursor}
        result = query(ORG_REPOS_GQL, variables)
        repos += result["organization"]["repositories"]["nodes"]
        pageInfo = result["organization"]["repositories"]["pageInfo"]
        if not pageInfo["hasNextPage"]:
            break
        cursor = pageInfo["endCursor"]

    master = next(r for r in repos if r["nameWithOwner"] == name_with_owner)
    forks = [
        r
        for r in repos
        if r["templateRepository"]
        and r["templateRepository"]["nameWithOwner"] == name_with_owner
    ]
    return master, forks


def longest_prefix(names):
    """Find the longest common prefix of the repository names."""
    return next(
        names[0][:n]
        for n in range(min(len(s) for s in names), 0, -1)
        if len({s[:n] for s in names}) == 1
    )


def annotate_repos(repos, roster):
    """Annotate repo['login'] with the login of the student who generated the repo
    Find the longest common prefix of the repository names.
    """
    common_prefix = longest_prefix([r["name"] for r in repos])
    for r in repos:
        login = r["name"][len(common_prefix) :]
        r["login"] = login
        r["author"] = roster.get(login, login)
        # Annotate repo['commits'] with commits that Christian didn't author
        r["commits"] = [
            c["node"]
            for c in r["ref"]["target"]["history"]["edges"]
            if c["node"]["author"]["email"] != "christian@nyu.edu"
        ]


def read_roster():
    # Set login_names to a dict login -> name
    roster_path = Path("Roster.csv")
    if not roster_path.exists():
        return {}
    roster = pd.read_csv(roster_path)
    column_first_names = ["Preferred", "English", "First"]
    first_names = next(
        (roster[name] for name in column_first_names if name in roster), None
    )
    names = first_names + " " + roster["Last"]
    login_names = {
        login: name
        for login, name in zip(roster["GitHub Login"], names)
        if isinstance(name, str)
    }
    return login_names


def is_late_commit(commit):
    return commit["author"]["date"] > "2019-09-09T03:00:00+08:00"


def print_late_commits(repos):
    # Show repos that were turned in late or not at all
    # report missing and late assignments
    warnings = {
        "No commits": [r for r in repos if not r["commits"]],
        "Late": [r for r in repos if all(map(is_late_commit, r["commits"]))],
        "Some late commits": [
            r for r in repos if any(map(is_late_commit, r["commits"]))
        ],
    }
    # only reported
    reported = []
    for label, rs in warnings.items():
        rs = [r for r in rs if r not in reported]
        reported += rs
        if rs:
            print(f"{label}: {', '.join(sorted(r['login'] for r in rs))}")
    for r in repos:
        commits = [c for c in r["commits"] if is_late_commit(c)]
        if not commits:
            continue
        print(f"  {r['login']}:")
        timestamps = {c["author"]["date"] for c in commits}
        for ts in timestamps:
            dt = (
                datetime.fromisoformat(ts)
                .astimezone(tz.gettz("China"))
                .strftime("%H:%M %a, %b %-d")
            )
            print(f"    {dt}")


def increment_headings(markdown):
    """Increment all the heading levels of a markdown string, if it contains level-one heading.
    This also normalizes heading lines "#\s*title" -> "# title"

    Note: this doesn't know not to look in fenced blocks
    """
    # Normalize the '## ' spacing
    markdown = re.sub(r"^(#+)\s*", r"\1 ", markdown, 0, re.M)
    # If there's an H1, increment all the Hn's
    if re.compile(r"^# ", re.M).search(markdown):
        markdown = re.sub(r"^(#+)", r"\1# ", markdown, 0, re.M)
    return markdown


def print_collated_readme(repos):
    # print collated readme
    for r in repos:
        name = r["author"]
        title, about = None, r["readme"]["text"].strip()
        if about.startswith("# "):
            title, about = about.split("\n", 1)
        if not title or title == "# About Me":
            title = "# " + name
        if name not in title:
            title += f" ({name})"
        print(increment_headings(title + "\n" + about))
        print("\n---\n")


def main():
    master, repos = get_generated_repos("application-lab/1-WELCOME-TO-APPLAB")
    annotate_repos(repos, read_roster())
    repos = [r for r in repos if r["commits"]]
    repos.sort(key=lambda r: r["author"])

    if False:
        print_late_commits(repos)
    if True:  # print collated readme
        print_collated_readme(repos)


if __name__ == "__main__":
    main()

