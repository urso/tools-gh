
import datetime

from clidec import namespace, command_name, argument

from . import project
from . import api
from . import fmt

from .util import parse_timedelta

ns = namespace("user")



@ns.command(
    argument("user", default="", nargs='?', help='git user name'),
    argument("--labels", default="", help='pr labels'),
    argument("--org", default="", help='filter by organisation'),
    argument("--state", default="",
             help='issue state (open, closed, all)'),
    argument("--last", default="",
             help="list issue with updates since today-<last>"),
    argument("--sort", default="",
             help='issue order (<field>-<direction>)'),
)
def interactions(args):
    client = api.client(args.token)
    user = args.user
    if not user:
        user = client.query_viewer_login()['viewer']['login']

    query = [f"involves:{user}"]
    if args.state and args.state != "all":
        query += [f"state:{args.state}"]
    for label in args.labels:
        query += [f"label:{label}"]

    if args.org:
        query += [f"org:{args.org}"]

    if args.last:
        delta = parse_timedelta(args.last)
        since = datetime.datetime.utcnow() - delta
        query += [f"updated:{since.replace(microsecond=0).isoformat()}..*"]

    if args.sort:
        query += [f"sort:{args.sort}"]

    iter_issues = api.iter_gql(client.query_user_issues_search, 'search.edges',
            50, " ".join(["type:issue"] + query))
    for issue in iter_issues:
        try:
            fmt.issue_info(issue)
        finally:
            print("\n")

    iter_prs = api.iter_gql(client.query_user_prs_search, 'search.edges',
            50, " ".join(["type:pr"] + query))
    for pr in iter_prs:
        try:
            fmt.pr_info(pr)
        finally:
            print("\n")

