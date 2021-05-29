import os
import re

from clidec import namespace, argument, command_name

from . import project
from . import api


ns = namespace("branches")


@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--dry", default=False, action='store_true', help="dry run"),
        argument("remote", default="origin", nargs='?',
                 help='git remote to delete from'),
)
def prune_gone(args):
    proj = project.open(args.path, remote=args.remote)

    # list of branches the remote tracking branch has been deleted for
    branches = [h
             for h in proj.repo.branches
             if (h.tracking_branch() is not None and
                 h.tracking_branch() not in proj.repo.references)]
    worktrees = dict((wd.branch.name, wd) for wd in proj.worktrees())
    for branch in branches:
        if branch.name in worktrees:
            wd = worktrees[branch.name]
            print(f"remove worktree: {wd.path}")
            if not args.dry:
                try:
                    wd.remove()
                except Exception as e:
                    print(f"failed to remove worktree: {e}")
                    continue

        print(f"delete gone branch: {branch.name}")
        if not args.dry:
            try:
                branch.delete(proj.repo, branch.name, force=True)
            except Exception as e:
                print(f"failed to remove branch: {e}")



@ns.command(
        argument("--path", default=os.path.curdir, help='git directory'),
        argument("--dry", default=False, action='store_true', help="dry run"),
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
