
from graphql.language.parser import parse
from graphql.language.printer import print_ast
from graphql.language.ast import (
    OperationDefinition,
    FragmentDefinition,
    FragmentSpread,
)

from gql import gql


def MakeClass(typeName, script):
    doc = parse(script)

    operations = {}
    fragments = {}

    dependencies = {}
    scripts = {}

    for definition in doc.definitions:
        if isinstance(definition, OperationDefinition):
            operations[definition.name.value] = definition
        elif isinstance(definition, FragmentDefinition):
            fragments[definition.name.value] = definition
        else:
            # ignore node type
            continue

        deps = [n.name.value for n in iter_fragment_spreads(definition)]
        dependencies[definition.name.value] = deps

    @classmethod
    def constructor(self, client):
        self._client = client

    namespace = {
        "__init__": constructor,
    }

    scripts = {}
    preps = {}

    for name, op in operations.items():
        deps = transitive_deps(dependencies, name)
        txt = print_ast(op) + "\n" + "\n".join(
            print_ast(fragments[dep]) for dep in deps
        )

        variables = [v.variable.name.value for v in op.variable_definitions]
        prep = make_prepare_params(variables)
        preps[name] = prep

        code = gql(txt)
        scripts[name] = code

        opname = op.operation
        if opname == "mutation":
            opname = "mut"

        namespace[f"{opname}_{name}"] = make_exec(prep, code)

    @classmethod
    def get_script(cls, name):
        return scripts[name]

    @classmethod
    def params(cls, name, *args, **kwargs):
        return preps[name](*args, **kwargs)

    def execute(self, *args, **kwargs):
        return self._client.execute(*args, **kwargs)

    namespace['get_script'] = get_script
    namespace['make_params'] = params
    namespace['execute'] = execute

    return type(typeName, (object,), namespace)


def make_prepare_params(variables):
    def prep(*args, **kwargs):
        if len(args) > len(variables):
            raise Exception(
                f"{len(args)} received, only f{len(variables)} expected")

        d = {}
        for i in range(len(args)):
            d[variables[i]] = args[i]
        d.update(kwargs)
        return d
    return prep


def make_exec(prep, code):
    def fn(self, *args, **kwargs):
        return self._client.execute(code, prep(*args, **kwargs))
    return fn


def transitive_deps(dependencies, name):
    visited = set([name])
    workset = [name]
    deps = []
    while len(workset) > 0:
        active = workset.pop()
        for dep in dependencies[active]:
            if dep in visited:
                continue
            deps.append(dep)
            workset.append(dep)
            visited.add(dep)
    return deps


def iter_fragment_spreads(node):
    return (f for f in iter_selections(node) if isinstance(f, FragmentSpread))


def iter_selections(node):
    if not hasattr(node, 'selection_set') or not node.selection_set:
        return

    for sel in node.selection_set.selections:
        for sub in iter_selections(sel):
            yield sub
        yield sel
