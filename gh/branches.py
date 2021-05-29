import os
import re

from clidec import namespace, argument, command_name

from . import project
from . import api


ns = namespace("branches")


@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--dry", default=False, help="dry run"),
        argument("remote", default="origin", nargs='?',
                 help='git remote to delete from'),
)
def prune_merged(args):
    proj = project.open(args.path, remote=args.remote)

    branches = {}

    client = api.client(args.token)
    count = 50

    iter_branches = api.iter_gql(
        client.query_iter_branch_prs, 'repository.refs.edges',
        count, proj.user, proj.name)

    for branch in iter_branches:
        prs = []
        if branch['associatedPullRequests'] is not None:
            prs = branch['associatedPullRequests']['nodes']

        name = branch['name']
        branches[branch['name']] = {
            'github': {
                'id': branch['id'],
                'prs': prs,
            }
        }

        if name in proj.repo.branches:
            branches[name]['local'] = proj.repo.branches[name]

    for name, info in branches.items():
        numPRs = len(info['github']['prs'])
        if numPRs == 0:
            print('No PR branch: {}'.format(name))
            continue

        unmerged = [p for p in info['github']['prs'] if p['state'] != 'MERGED']
        if len(unmerged) > 0:
            print('branch with unmerged PRs: {}'.format(name))
            for pr in unmerged:
                print('    {}: {}'.format(pr['number'], pr['state']))
            continue

        if proj.active_branch.name == name:
            print('Skip current branch "{}". Branch is already merged'.format(
                name
            ))
            continue

        if 'local' in info:
            print('delete local branch: {}'.format(name))
            if not args.dry:
                proj.repo.delete_head(name, force=True)

        print('delete remote branch: {}'.format(name))
        if not args.dry:
            proj.remote.push(refspec=":{}".format(name))
