
import textwrap

def issue_info(issue):
    owner = issue['repository']['owner']['login']

    title = issue['title']
    if 'repository' in issue:
        repo = f"{owner}/{issue['repository']['name']}"
        link = f"https://github.com/{repo}/issues/{issue['number']}"
        title = f"{repo} - {title}"
    else:
        repo, link = None, None

    print(title)
    print('-' * len(title))
    print(issue['updatedAt'])

    info = f"{issue['state']} #{issue['number']}"
    if issue['author'] and 'login' in issue['author']:
        info += f" - {issue['author']['login']}"
    print(info)

    print_labels(issue)
    if link:
        print(link)
    print_participants(issue)
    print_project_cards(issue)

    if 'bodyText' in issue:
        print()
        print(bodyText)
        print()

    print_references(issue)

def pr_info(pr):
    title = pr['title']
    if 'repository' in pr:
        repo = f"{pr['repository']['owner']['login']}/{pr['repository']['name']}"
        title = f"{repo} - {title}"

    print(title)
    print('-' * len(title))
    print(
        f"{pr['state']} {pr['number']} - {pr['mergeable']} - {pr['author']['login']}")
    if pr['state'] == 'MERGED' and 'mergeCommit' in pr:
        commit = pr['mergeCommit']
        print(f"  {commit['committedDate']} - {commit['oid']}")


    if 'headRefName' in pr:
        print(f"{pr['headRefName']}")
    if 'permalink' in pr:
        print(f"{pr['permalink']}\n")

    print_labels(pr)
    print_participants(pr)
    print_project_cards(pr)

    if 'bodyText' in pr:
        print("\n".join(textwrap.wrap(pr['bodyText'], width=80)))

    if 'commits' in pr:
        status = pr['commits']['nodes'][-1]['commit']['status']
        if status:
            print("\n  status:")
            print("  -------")
            print("  " + status['state'])
            if status['state'] != "SUCCESS":
                for ctx in status['contexts']:
                    if ctx['state'] != 'SUCCESS':
                        url = ctx['targetUrl']
                        context_msg = f"{ctx['context']}: {ctx['state']}"
                        if url is not None:
                            context_msg += f"\n\t{url}\n"
                        print("  " + context_msg)


    if 'reviews' in pr:
        reviews = pr['reviews']['nodes']
        if len(reviews) > 0:
            print("\n  reviews:")
            print("  --------")
            for review in reviews:
                print(
                    f"  {review['createdAt']} {review['author']['login']} - {review['state']}")

    print_references(pr)


def print_labels(entry):
    if entry['labels'] and entry['labels']['nodes']:
        print("labels: " + " ".join("'{}'".format(n['name']) for n in entry['labels']['nodes']))


def print_participants(entry):
    if 'participants' in entry and entry['participants'] and entry['participants']['nodes']:
        print("participants: " + " ".join("'{}'".format(n['login']) for n in entry['participants']['nodes']))

def print_project_cards(entry):
    if 'projectCards' in entry and entry['projectCards'] and entry['projectCards']['nodes']:
        print("projects:")
        for card in entry['projectCards']['nodes']:
            info = card['project']['name']
            if 'column' in card and card['column'] and 'name' in card['column']:
                info += f" - {card['column']['name']}"
            if 'state' in card:
                info += f": {card['state']}"
            print(info)

def print_references(entry):
    if 'timelineItems' in entry:
        references = entry['timelineItems']['nodes']
        if len(references) > 0:
            print("\n  references:")
            print("  -----------")
            for node in references:
                info = node['source']
                kind = info['__typename']
                if kind == 'PullRequest':
                    kind = 'PR'
                    link = info['permalink']
                    reviews = info['reviews']['nodes']
                else:
                    link = "https://github.com/{}/{}/issues/{}".format(
                        info['repository']['owner']['login'], info['repository']['name'], info['number'])
                    reviews = []
                login = "<unknown>"
                if 'author' in info and info['author'] and 'login' in info['author']:
                    login = info['author']['login']
                print(
                    f"  {kind} {info['state']} {info['number']}\t{login}\t{info['title']}")
                if info['state'] == 'MERGED':
                    commit = info['mergeCommit']
                    print(f"    {commit['committedDate']} - {commit['oid']}")
                if info['labels']['nodes']:
                    print("  " + " ".join("'{}'".format(n['name'])
                                   for n in info['labels']['nodes']))
                print(f"  {link}")
                for review in reviews:
                    print(
                        f"  {review['createdAt']} {review['author']['login']} - {review['state']}")
                print()
