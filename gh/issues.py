import re
from urllib.parse import urlparse

from clidec import namespace, argument, command_name

from . import api


ns = namespace("issue")


@ns.command(
    argument("repo_and_issue", nargs="+", help="issue id or full url"),
)
def info(args):
    if len(args.repo_and_issue) == 1:
        try:
            u = urlparse(args.repo_and_issue[0])
            tmp = u.path.split('/')
            user, name, num = tmp[1], tmp[2], int(tmp[4])
        except:
            res = re.match("(.*)/(.*)#(.*)", args.repo_and_issue[0])
            user, name, num = res.group(1), res.group(2), int(res.group(3))
    else:
        repo, num = args.repo_and_issue
        user, name = repo.split('/')
        num = int(num)

    client = api.client(args.token)
    issue = client.query_issue_info(user, name, num)['repository']['issue']
    fmt.issue_info(issue)

@ns.command(
    command_name("list"),
    argument("--states", default="open",
             help='pr states (open, closed, all)'),
    argument("--labels", default="", help='labels'),
    argument("--user", default="", nargs='?',
             help='only display issues created by this user'),
    argument("--assignee", default="", help="list issues assigned to this user only"),
    argument("--mentioned", default="", help="list issues with mentioned user only"),
    argument("repo", default="", help="repository to list issues for")
)
def cmd_list(args):
    owner, repo = args.repo.split("/")
    client = api.client(args.token)

    labels = args.labels.split(',') if args.labels else None

    states = [s.upper() for s in args.states.split(',')]
    if 'ALL' in states:
        states = []

    filters = {}
    if args.assignee:
        filters['assignee'] = args.assignee
    if args.user:
        filters['createdBy'] = args.user
    if args.mentioned:
        filters['mentioned'] = args.mentioned

    iter_issues = api.iter_gql(client.query_iter_list_issues, 'repository.issues.edges',
            50, owner, repo, labels, states, filters)

    for issue in iter_issues:
        fmt.issue_info(issue)
        print()
