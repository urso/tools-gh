from urllib.parse import urlparse
import datetime
import editor
import os
import re
import tempfile
import textwrap
import webbrowser

from clidec import namespace, command_name, argument

from . import project
from . import api
from . import fmt
from .util import parse_timedelta



ns = namespace("pr")


@ns.command(
        argument("--repo", default="", nargs='?',
                 help='git remote for reference'),
        argument("--states", default="open",
                 help='pr states (open, closed, merged, all)'),
        argument("--labels", default="", help='pr labels'),
        argument("--title", default="", help='title regex filter'),
        argument("user", default="", nargs='?',
                 help='git user to filter for'),
)
def userlist(args):
    if args.repo:
        regex_repo = re.compile(f".*{args.repo}.*")

        def filter_repo(pr):
            r = pr['repository']
            path = f"{r['owner']['login']}/{r['name']}"
            return regex_repo.match(path)
    else:
        def filter_repo(x): return True

    if args.title:
        regex_title = re.compile(f".*{args.title}.*")

        def filter_title(pr):
            return regex_title.match(pr['title'])
    else:
        def filter_title(pr): return True

    def show(x):
        return filter_repo(x) and filter_title(x)

    client = api.client(args.token)

    states = [s.upper() for s in args.states.split(',')]
    if 'ALL' in states:
        states = []

    labels = args.labels.split(',') if args.labels else None

    user = args.user
    if not user:
        user = client.query_viewer_login()['viewer']['login']

    iter_pulls = api.iter_gql(client.query_user_prs, 'user.pullRequests.edges',
                              50, user, states, labels)

    for pr in iter_pulls:
        if show(pr):
            fmt.pr_info(pr)
            print()


@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--remote", default="origin", help='git remote '),
        argument("pr", nargs="?", help="pull request id"),
)
def info(args):
    client = api.client(args.token)
    if not args.pr:
        prs = find_branch_prs(client, args.path, args.remote)
        if len(prs) == 0:
            print("No PRs found")
        for pr in prs:
            fmt.pr_info(fetch_pr_info(client, args, pr['number']))
    else:
        fmt.pr_info(fetch_pr_info(client, args, args.pr))


@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--remote", default="upstream", help='git remote '),
        argument("commit", help="commit id"),
)
def of(args):
    client = api.client(args.token)
    prs = find_commit_prs(client, args.path, args.remote, args.commit)
    if len(prs) == 0:
        print("No PRs found")

    for pr in prs:
        fmt.pr_info(fetch_pr_info(client, args, pr['number']))


@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--remote", default="origin", help='git remote '),
        argument("pr", nargs="?", type=int, help="pull request id"),
)
def open(args):
    client = api.client(args.token)
    proj = project.open(args.path)

    if not args.pr:
        prs = find_branch_prs(client, args.path, args.remote)
        if len(prs) == 0:
            print("No PRs found")
    else:
        resp = client.query_pr_info(proj.user, proj.name, args.pr)
        prs = [resp['repository']['pullRequest']]

    for pr in prs:
        webbrowser.open(pr['permalink'])


@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--remote", default="origin", help='git remote '),
        argument("label", help="label to add"),
        argument("prs", nargs="+", type=int, help="pull request id"),
)
def all_addlabel(args):
    client = api.client(args.token)
    proj = project.open(args.path)

    if args.remote:
        remote = proj.repo.remotes[args.remote]
    else:
        remote = proj.origin

    if proj.has_remote('upstream'):
        target_owner, target_repo = proj.repo_owner('upstream')
    else:
        target_owner, target_repo = proj.repo_owner(remote.name)

    pr_ids = []
    for number in args.prs:
        res = client.query_repo_pr_id(target_owner, target_repo, number)
        id = res["repository"]["pullRequest"]["id"]
        pr_ids.append(id)

    label_id = None
    iter_labels = api.iter_gql(
            client.query_repo_label_ids, 'repository.labels.edges',
            20, target_owner, target_repo, args.label)
    for label in iter_labels:
        if label['name'] == args.label:
            label_id = label['id']


    if not label_id:
        print(f"unknown label {args.label}")
        return
    label_ids = [label_id]

    for pr in pr_ids:
        client.mut_add_labels({
            "labelableId": pr,
            "labelIds": label_ids,
        })


@ns.command(
    command_name("list"),
    argument("repo", default="", nargs='?', help='git repository'),
    argument("--remote", default="", help='git remote '),
    argument("--labels", default="", help='pr labels'),
    argument("--last", default="",
             help="list prs merged since today-<last>"),
    argument("--sort", default="",
             help='issue order (<field>-<direction>)'),
    argument("--event", default="updated",
             help='find issues by event type (created, updated, merged, closed)'),
)
def list_prs(args):
    event_types = {
      "updated": {
          "filters": ["is:open"],
          "date_filter": "updated",
      },
      "created": {
          "filters": ["is:open"],
          "date_filter": "created",
      },
      "closed": {
          "filters": ["is:closed", "is:unmerged"],
          "date_filter": "closed",
      },
      "merged": {
          "filters": ["is:closed", "is:merged"],
          "date_filter": "merged",
      },
    }

    client = api.client(args.token)
    repo = args.repo
    if not repo:
        proj = project.open(".", remote=args.remote)
        repo = f"{proj.user}/{proj.name}"

    query = [f"repo:{repo}"]
    for label in args.labels:
        query += [f"label:{label}"]

    if args.event not in event_types:
        print(f"Unknown event type {args.event}. Must be one of {event_types.keys()}")
    event_type = event_types[args.event]
    query += event_type['filters']
    date_filter_key = event_type['date_filter']

    if args.last:
        delta = parse_timedelta(args.last)
        since = datetime.datetime.utcnow() - delta
        query += [f"{date_filter_key}:{since.replace(microsecond=0).isoformat()}..*"]

    iter_prs = api.iter_gql(client.query_user_prs_search, 'search.edges',
            50, " ".join(["type:pr"] + query))
    for pr in iter_prs:
        fmt.pr_info(pr)
        print("\n")


@ns.command(
        argument("--draft", default=False, action="store_true"),
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--labels", default="", help="labels"),
        argument("--remote", default="", help="remote to push branch to"),
        argument("--target", default="", help="target repository"),
        argument("--branch", default="master", help="target branch"),
)
def create(args):
    proj = project.open(args.path)
    branch = proj.active_branch

    if args.remote:
        remote = proj.repo.remotes[args.remote]
    else:
        remote = proj.origin

    client = api.client(args.token)

    if branch.name not in proj.remote.refs:
        proj.repo.git.push(
            '--set-upstream',
            remote.name,
            branch.name,
        )
    else:
        remote.push()
    remote_owner, _ = proj.repo_owner(remote.name)

    logs = branch.log()

    if '/' in args.target:
        target_owner, target_repo = split(args.target, '/')
    elif args.target:
        target_owner, target_repo = proj.repo_owner(args.target)
    else:
        if proj.has_remote('upstream'):
            target_owner, target_repo = proj.repo_owner('upstream')
        else:
            target_owner, target_repo = proj.repo_owner(remote.name)

    if remote_owner == target_owner:
        headRef = branch.name
    else:
        headRef = f"{remote_owner}:{branch.name}"

    target = client.query_repo_id(target_owner, target_repo)

    label_ids = []
    if args.labels:
        labels = args.labels.split(",")
        found = set()
        iter_labels = api.iter_gql(
            client.query_repo_label_ids, 'repository.labels.edges',
            20, target_owner, target_repo, " ".join(labels))
        for label in iter_labels:
            if label['name'] in labels:
                found.add(label['name'])
                label_ids.append(label['id'])

        if len(labels) != len(found):
            missing = set(labels).difference(found)
            print(f"unknown labels: {missing}")
            exit(1)

    msg = textwrap.dedent("""

    # PR title and message.
    # Lines starting with '#' will be ignored.
    # Operation is cancelled if the first line is empty
    """)

    msg += f"#\n#Push: {remote.name} - {remote.url}"
    msg += f"\n#Target: {target_owner}/{target_repo}"
    if args.labels:
        msg += f"\n#Labels: {args.labels}"

    if len(logs) > 1: # first reflog entry is 'branch command'
        commit = proj.repo.commit(logs[1].newhexsha)
        msg = commit.message + msg
    msg = editor.edit(contents=msg).decode()

    msg = [l for l in msg.split('\n') if not l.startswith('#')]
    if len(msg) == 0:
        print("cancelled")
        exit(1)

    title = msg[0].strip()
    if len(title) == 0:
        print("cancelled")
        exit(1)

    body = "\n".join(msg[1:]).strip()

    meta = {
        "title": title,
        "body": body,
        "maintainerCanModify": True,
        "headRefName": headRef,
        "baseRefName": args.branch,
        "repositoryId": target['repository']['id'],
    }

    if args.draft:
        # draft is github experimental feature. Don't mention it if not required
        meta['draft'] = True

    res = client.mut_pr_create(meta)
    pr = res['createPullRequest']['pullRequest']
    print("Created New PR")
    print(f"{pr['title']}")
    print('-' * len(pr['title']))
    print(f"{pr['state']} {pr['number']} - {pr['author']['login']}")
    if pr['state'] == 'MERGED':
        commit = pr['mergeCommit']
        print(f"  {commit['committedDate']} - {commit['oid']}")
    print(f"{pr['headRefName']}")
    print(f"{pr['permalink']}\n")

    client.mut_add_labels({
        "labelableId": pr['id'],
        "labelIds": label_ids,
    })


def fetch_pr_info(client, args, pr):
    try:
        u = urlparse(pr)
        tmp = u.path.split('/')
        user, name, pr = tmp[1], tmp[2], int(tmp[4])
    except:
        if not isnum(pr):
            raise f"{pr} must be a number of URL"
        proj = project.open(args.path)
        user, name, pr = proj.user, proj.name, int(pr)

    resp = client.query_pr_info(user, name, pr)
    return resp['repository']['pullRequest']


def find_branch_prs(client, path, remote=None):
    proj = project.open(path, remote=remote)
    branch = proj.active_branch
    if branch.name not in proj.remote.refs:
        raise "Branch {} not found in remote {}".format(
            proj.repo.head.ref.name,
            proj.remote.name,
        )

    ref = f"refs/heads/{proj.repo.head.ref.name}"
    resp = client.query_branch_prs(proj.user, proj.name, ref)
    return resp['repository']['ref']['associatedPullRequests']['nodes']


def find_commit_prs(client, path, remote, commit):
    proj = project.open(path, remote=remote)
    resp = client.query_commit_prs(proj.user, proj.name, commit)
    return resp['repository']['object']['associatedPullRequests']['nodes']


def isnum(x):
    try:
        int(x)
        return True
    except:
        return False
