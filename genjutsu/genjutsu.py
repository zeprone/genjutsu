#!/usr/bin/env python3
from argparse import ArgumentParser
from collections import namedtuple, OrderedDict
from collections.abc import Callable, Iterable
from contextlib import ExitStack, contextmanager, suppress
from functools import lru_cache, partial, reduce
from importlib.machinery import SourceFileLoader
from inspect import stack
from itertools import chain, groupby, repeat
import logging.config
from operator import itemgetter
from os import environ, pathsep
from os.path import expandvars
from pathlib import Path, PurePath
from sys import getprofile, setprofile
import sys
from typing import AbstractSet, Any, Callable, Iterable, Iterator, Union
from uuid import uuid4

if __name__ == '__main__' and __package__ is None:
    __package__ = 'genjutsu'  # pylint: disable=redefined-builtin

assert sys.version_info > (3, 6)

__version__ = '1.0.0+20170613.0'

_TOOLSETS = tuple(filter(None, expandvars(environ.get('GENJUTSU_TOOLSETS', '')).split(pathsep))) or ('clang',)
_LOADED_TOOLSETS = ()
_RESOURCE_DIR = Path(__file__).parent / 'resources'
_RESOURCE_PATH = tuple(chain(expandvars(environ.get('GENJUTSU_RESOURCE_PATH', '')).split(pathsep), (Path.cwd(), _RESOURCE_DIR)))

_BUILD_DIR = None

_Variable = namedtuple('_Variable', ('name', 'value', 'append'))
_Flavour = namedtuple('_Flavour', ('name', 'flags'))
_Target = namedtuple('_Target', ('env', 'inputs', 'implicit_inputs', 'order_only_inputs' , 'rule', 'flags', 'outputs', 'implicit_outputs', 'output_flags'))
_Filter = namedtuple('_Filter', ('inputs', 'outputs'))

_Ninja = namedtuple('_Ninja', ('includes', 'subninjas', 'variables', 'builds', 'defaults'))

''' `Variable` overrides, `Flags` concatenates '''
Variable, Flag = partial(_Variable, append=False), partial(_Variable, append=True)  # pylint: disable=invalid-name

DEFAULT_FLAVOUR = _Flavour('default', ())


def _get_resource_file(filename, search_base_dir=None) -> PurePath:
    candidates = (Path(search_dir) / filename for search_dir in filter(None, (search_base_dir, *_RESOURCE_PATH)))
    with suppress(StopIteration):
        return next(path.resolve() for path in candidates if path.is_file())
    raise FileNotFoundError(filename)


def _extract_globals(func, initial_globals=None, additional_entries=None) -> tuple:
    globals_ = initial_globals or globals().copy()
    initial_keys = frozenset(globals_.keys())
    func(globals_)
    globals_ = {k: v for k, v in globals_.items() if k not in initial_keys and not k.startswith('_')}
    globals_.update(additional_entries or ())
    return namedtuple('globals_' + uuid4().hex, globals_.keys())(**globals_)


@lru_cache(maxsize=None)
def toolset_class(toolset, search_base_dir=Path.cwd()) -> type:
    filename, classname = (*toolset.split('.', 1), 'Toolset')[:2]
    filename = _get_resource_file(filename + '.py', search_base_dir=search_base_dir)
    module_ = SourceFileLoader(filename.stem, str(filename)).load_module()
    return getattr(module_, classname)


class Env(object):
    __stack = []

    @classmethod
    @contextmanager
    def _pushed(cls, env):  # pylint:disable=redefined-outer-name
        logging.debug(f'Push {env}')
        cls.__stack.append(env)
        yield env
        cls.__stack.pop()
        logging.debug('Pop')

    @classmethod
    def _head(cls):
        return cls.__stack[-1] if cls.__stack else None

    def __init__(self, prj_file, *, source_dir='.', build_dir='build', ninja_file='build.ninja', supenv=None):
        '''
            args:
                prj_file: project file
                source_dir: base directory for sources
                build_dir: build output dir
                ninja_file: generated ninja file
                supenv: parent environment
        '''
        super().__init__()
        self.__prj_file, self.__ninja_file, self.__source_dir, self.__build_dir = Path(prj_file).resolve() if prj_file else None, ninja_file, Path(source_dir), PurePath(build_dir)
        self.__supenv = supenv

        self.__flags = ()
        self.__targets = {}
        self.__subenvs = ()
        self.__defaults = ()
        self.__injections = {}

        self.__lineno = next((lineno for _, frame_filename, lineno, *_ in stack(context=0) if self.__prj_file.samefile(frame_filename)), 0)
        self.__dependencies = set()

        self.__toolsets = ()
        self.__flavours = OrderedDict()

        with self._pushed(self):
            for toolset in self.all_toolsets:
                toolset.apply_to_env()

    def __str__(self):
        return f'{self.prj_file!s}:{self.__lineno}'

    @property
    def prj_file(self):
        '''Absolute'''
        return self.__prj_file

    @property
    def base_dir(self):
        '''Absolute'''
        return self.prj_file.parent

    def get_source_path(self, absolute=True):
        return self.base_dir / self.__source_dir if absolute else self.__source_dir

    '''Relative to base_dir'''
    source_dir = source_path = property(partial(get_source_path, absolute=False))

    @property
    def build_dir(self):
        '''Relative to base_dir'''
        return self.__build_dir

    def get_build_path(self, flavour=None, absolute=True):
        return (self.base_dir / self.build_dir if absolute else self.build_dir) / (flavour.name if flavour else '{flavour}')

    '''Relative to base_dir'''
    build_path = property(partial(get_build_path, flavour=None, absolute=False))

    @property
    def ninja_file(self):
        '''Absolute'''
        return (self.base_dir / self.__ninja_file) if self.__ninja_file else None

    @property
    def dependencies(self):
        return frozenset(Path(dependency).resolve() for dependency in chain(self.__dependencies, *(env.dependencies for env in self.all_subenvs)))

    def add_dependency(self, dependency):
        self.__dependencies.add(dependency)

    @property
    def supenv(self):
        return self.__supenv
    
    @property
    def first_class_supenv(self):
        return self if self.ninja_file or not self.supenv else self.supenv.first_class_supenv 

    @property
    def all_subenvs(self) -> AbstractSet['Env']:
        return frozenset(self.__subenvs).union(*(env.all_subenvs for env in self.__subenvs))

    @property
    def local_subenvs(self) -> AbstractSet['Env']:
        local_subenvs = {env for env in self.__subenvs if not env.ninja_file}
        return frozenset(local_subenvs).union(*(env.local_subenvs for env in local_subenvs))

    @property
    def first_class_subenvs(self) -> AbstractSet['Env']:
        return frozenset(env for env in self.all_subenvs if env.ninja_file)

    def add_subenv(self, env):  # pylint:disable=redefined-outer-name
        self.__subenvs += (env,)
        return env

    @property
    def flags(self) -> Iterator[_Variable]:
        return self.__flags

    @property
    def parent_flags(self) -> Iterator[_Variable]:
        return (*(self.supenv.parent_flags if self.supenv else ()), *self.flags)

    @property
    def local_flags(self) -> Iterator[_Variable]:
        return (*(self.supenv.local_flags if self.supenv else ()), *(self.flags if not self.ninja_file else ()))

    def add_flag(self, flag: _Variable):
        self.__flags += (flag,)
        return flag

    @property
    def targets(self) -> Iterator[_Target]:
        return self.__targets.values()

    def add_target(self, target: _Target):
        logging.debug('Add target %s', ','.join(map(str, target.outputs)))
        target = target._replace(env=self)
        self.__targets.update((output, target) for output in target.outputs)
        return target

    @property
    def all_targets(self) -> AbstractSet[_Target]:
        return frozenset(self.targets).union(*(env.targets for env in self.all_subenvs))

    @property
    def local_targets(self) -> AbstractSet[_Target]:
        return frozenset(self.targets).union(*(env.targets for env in self.local_subenvs))

    @property
    def terminal_targets(self) -> AbstractSet[_Target]:
        return self.local_targets.difference(*(chain(target.inputs, target.implicit_inputs) for target in self.local_targets))

    @property
    def all_flavours(self):
        return dict(chain(((flavour.name, flavour) for flavour in self.supenv.all_flavours) if self.supenv and not self.ninja_file else (), self.__flavours.items())).values() or (DEFAULT_FLAVOUR,)

    def add_flavour(self, flavour: _Flavour):
        self.__flavours[flavour.name] = flavour
        return flavour

    @property
    def all_toolsets(self):
        return tuple(chain(self.__toolsets, self.supenv.all_toolsets if self.supenv and not self.ninja_file else _LOADED_TOOLSETS))

    def add_toolset(self, toolset):
        logging.debug('Add toolset %s', type(toolset))
        self.__toolsets += (toolset,)
        return toolset

    @property
    def all_defaults(self):
        return tuple(chain(self.__defaults, *(env.all_defaults for env in self.all_subenvs)))

    def add_default(self, default):
        self.__defaults += (default,)

    @property
    def all_injections(self):
        def injections_recursive(env):
            return chain(env.__injections.items(), *(injections_recursive(subenv) for subenv in env.all_subenvs))
        return tuple(dict(injections_recursive(self)).values())

    def add_injection(self, injection, *, key=None):
        self.__injections[key if key is not None else injection] = injection



class _EnvHead(object):
    @property
    def actual(self):
        return Env._head()  # pylint:disable=protected-access

    def __getattr__(self, name):
        return getattr(self.actual, name)

''' Read-only proxy to the current (ie. top of stack) :class:`Env` instance'''
E = _EnvHead()


@contextmanager
def env(path=Path(), **kwargs):
    ''' Convenient function to create a new sub environment to the current :class:`Env`

        args:
            path: relative path of the new environment
            kwargs: forwarded to the constructor of :class:`Env`
        yields:
            Env: new environment
    '''
    default_kwargs = dict(prj_file=E.prj_file, source_dir=E.source_dir / path, build_dir=E.build_dir / path, ninja_file=None, supenv=E.actual)
    subenv = Env(**dict(chain(default_kwargs.items(), kwargs.items())))  # pylint:disable=redefined-outer-name
    with Env._pushed(subenv):
        yield subenv
    E.add_subenv(subenv)


def Target(inputs: Iterable[Union[PurePath, _Target, _Filter]], outputs: Iterable[Union[PurePath, str]], rule: str, *, implicit_inputs: Iterable[Union[PurePath, _Target, _Filter]]=(), order_only_inputs: Iterable[Union[PurePath, str]]=(), implicit_outputs: Iterable[Union[PurePath, str]]=(), flags: Iterable[_Variable]=(), output_flags: Iterable[_Variable]=()):  # pylint: disable=invalid-name
    ''' Base type of every node in the graph of dependencies
        Outputs a `build` statement in the Ninja file

        args:
            inputs : 
            outputs : 
            rule :
            implicit_inputs :
            order_only_inputs :
            implicit_outputs :
            flags :
            output_flags :
        returns:
            Target
    '''
    return E.add_target(_Target(None, tuple(inputs), tuple(implicit_inputs), tuple(order_only_inputs), rule, tuple(flags), tuple(outputs), tuple(implicit_outputs), tuple(output_flags)))

#   Target(outputs=(E.ninja_file,), rule='genjutsu', inputs=(E.prj_file,), variables=(Variable('GENJUTSU', sys.executable + ' ' + sys.argv[0]),))


def Alias(name, targets):  # pylint: disable=invalid-name
    ''' "Phony" target

        args:
            name : alias name
            targets : target referenced under the alias
        returns:
            Target
    '''
    return Target(targets, (name,), 'phony')


def Flavour(name, flags):  # pylint: disable=invalid-name
    ''' Flavours are configurations
        Express debug/release build configurations

        args:
            name
            flags
        returns:
            Flavour
    '''
    return E.add_flavour(_Flavour(name, flags=flags))


def Default(target):  # pylint: disable=invalid-name
    ''' Add `target` to the default targets of the build (`default` statement in the Ninja file) '''
    E.add_default(target)


def Inject(injection: Callable[[Env, _Flavour], None], *, key=None):  # pylint: disable=invalid-name
    ''' Injections are extensibility mechanism

        args:
            injection : function taking an Env and a Flavour arg as parameters, called during generation
            key : uniquely defines an injection. A new :class:`Injection` override an existing one sharing the same key 
    '''
    E.add_injection(injection, key=key)


def Apply(*args):  # pylint: disable=invalid-name
    ''' Applies a set of :class:`Flag` to the current environment

        args:
            args : single or sequence of :class:`Flag`
    '''
    return tuple(chain.from_iterable((E.add_flag(flag),) if not isinstance(flag, Iterable) or isinstance(flag, _Variable) else chain.from_iterable(map(Apply, flag)) for flag in args))


def Toolset(toolset) -> tuple:  # pylint: disable=invalid-name
    ''' Declares

        args:
            toolset: toolset name (stem of the python file), path relative to the current :class:`Env` or `GENJUTSU_RESOURCE_PATH` system environment variable

        returns:
            namedtuple: namespace of the toolset
    '''
    instance = E.add_toolset(toolset_class(toolset, search_base_dir=E.base_dir)())
    instance.apply_to_env()
    for env_ in chain(E.all_subenvs):
        with env(env_):
            instance.apply_to_env()
    return _extract_globals(instance.add_rules)


@contextmanager
def _add_dependencies(env):
    parent_profiler = getprofile()

    def profilefunc(frame, event, arg):
        if event == 'call':
            filename = frame.f_code.co_filename
            if not filename.startswith('<'):
                env.add_dependency(filename)
        if parent_profiler:
            parent_profiler(frame, event, arg)
    setprofile(profilefunc)

    try:
        yield
    finally:
        setprofile(parent_profiler)


@lru_cache(maxsize=None)
def _Prjdef(path, kwargs_) -> tuple:  # pylint: disable=invalid-name
    logging.debug(f'Parse file {path!s}')
    with Env._pushed(Env(prj_file=path, **dict(kwargs_))) as env_:
        globals_ = {k: v for k, v in vars(sys.modules[__name__]).items() if not k.startswith('_')}
        globals_['__file__'] = globals_['__prjdef__'] = E.prj_file
        for toolset in E.all_toolsets:
            toolset.add_rules(globals_)
        with E.prj_file.open() as stream:
            def exec_(globals_):
                code = compile(stream.read(), stream.name, 'exec', optimize=0)
                with _add_dependencies(env_):
                    exec(code, globals_, globals_)
            return _extract_globals(exec_, initial_globals=globals_, additional_entries={'E': env_})  # pylint: disable=exec-used


def Prjdef(path, **kwargs) -> tuple:  # pylint: disable=invalid-name
    ''' Include other projects

        args:
            path: path to a prjdef file or a directory containing a `prjfdef` file
            kwargs: forwarded to the constructor of Env

        returns:
            namedtuple: namespace of the toolset
    '''
    path = E.base_dir / path
    path = path / 'prjdef' if path.is_dir() else path
    prjdef = _Prjdef(path.resolve(), frozenset(kwargs.items()))
    E.add_subenv(prjdef.E)
    return prjdef


def Glob(pattern, *, root=None) -> Iterator[PurePath]:  # pylint: disable=invalid-name
    ''' Just like glob module

        args:
            pattern: glob-style pattern
            root: search dir root, defaults to :class:`E``.source_path`

        yields:
            Path: matching file
    '''
    root = root or E.get_source_path()
    for k in root.glob(pattern):
        yield k.relative_to(root)


def Filter(inputs, function):  # pylint: disable=invalid-name
    ''' Filters among the outputs of declared :class:`Target`

        args:
            inputs: Targets which `outputs`
            function: only keep `outputs` for which `function(output)` is `True`
    '''
    return _Filter(inputs, tuple(chain.from_iterable(filter(function, input.outputs) for input in inputs)))


def file_match(pattern):
    ''' Returns filename pattern matching filter function for `Filter`

        example:
        `Filter(input_targets, file_match('*.o'))`

        args:
            pattern: glob-style pattern
    '''
    return lambda output: isinstance(output, PurePath) and output.match(pattern)


def resolve(value, *, env=None, flavour=None, quote_paths=False):
    recurse = partial(resolve, env=getattr(value, 'env', env), flavour=flavour, quote_paths=quote_paths)

    if isinstance(value, str):
        yield value if flavour is None else value.format(flavour=flavour.name)
    elif isinstance(value, PurePath):
        result = PurePath(next(recurse(str(env.base_dir / value if env else value))))
        yield f'"{result}"' if quote_paths else result
    elif isinstance(value, _Flavour):
        yield value.name
    elif hasattr(value, 'outputs'):
        yield from recurse(value.outputs)
    elif isinstance(value, Iterable):
        for item in value:
            yield from recurse(item)
    else:
        yield value


def parse(path):
    # load toolsets now that every symbol they might need to import from the current module is defined
    global _LOADED_TOOLSETS
    if not _LOADED_TOOLSETS:
        _LOADED_TOOLSETS = tuple(toolset_class(toolset)() for toolset in _TOOLSETS)

    path = path / 'prjdef' if path.is_dir() else path
    return _Prjdef(path.resolve(), frozenset())

def escape(value):
    return str(value).replace('$ ', '$$ ').replace(' ', '$ ').replace(':', '$:')
    
def resolve_escape_join(value, *, env, flavour):
    return ' '.join(escape(item) for item in resolve(value, env=env, flavour=flavour))

def resolve_escape_join_flag(value, *, env, flavour):
    return ''.join(str(item) for item in resolve(value, env=env, flavour=flavour, quote_paths=True))

def merge_flags(flag0, flag):
    return flag._replace(value=(flag0.value, flag.value)) if flag0.value and flag.append else flag

def merge_flags_iterable(flags):
    return sorted(reduce(lambda flags_dict, flag: dict(chain(flags_dict.items(), ((flag.name, merge_flags(flags_dict.get(flag.name, Variable(flag.name, ())), flag)),))), flags, {}).values())

def get_target_flags(target, flavour):
    def resolve_flags(flags, target=target):
        return (flag._replace(value=resolve_escape_join_flag(flag.value, env=target.env, flavour=flavour)) for flag in flags)
    def inputs_flags(target):
        return chain(resolve_flags(target.output_flags, target), chain.from_iterable(inputs_flags(input_) for input_ in chain(target.inputs, target.implicit_inputs) if isinstance(input_, _Target)))
    return merge_flags_iterable(chain(resolve_flags(target.env.local_flags), inputs_flags(target), resolve_flags(target.flags)))

def get_env_flags(env, flavour):
    def resolve_flags(flags):
        return (flag._replace(value=resolve_escape_join_flag(flag.value, env=env, flavour=flavour)) for flag in flags)
    return merge_flags_iterable(chain(resolve_flags(env.parent_flags), resolve_flags(flavour.flags)))


def _generate_env(env):  # pylint:disable=redefined-outer-name
            
    def phony_inputs(targets):
        return reduce(frozenset.union, (phony_inputs(target.inputs) if target.rule == 'phony' else frozenset((target,)) for target in targets), frozenset())

    with ExitStack() as stack:
        def file_(filename, flavour=None):
            @contextmanager
            def context_(filename):
                try:
                    logging.debug(f'generate {filename!s}')
                    filename.parent.mkdir(parents=True, exist_ok=True)
                    with filename.open('w') as out:
                        yield out
                except:
                    filename.unlink()
                    raise
            return stack.enter_context(context_(Path(next(resolve(filename, env=env, flavour=flavour)))))

        main_build_file = file_(env.base_dir / env.ninja_file.name)
        common_build_file = file_(env.base_dir / (f'common_{env.ninja_file.name}'))
        build_files = {flavour.name: file_(dir_ / env.ninja_file.name, flavour) for flavour, dir_ in ((flavour, env.get_build_path(flavour)) for flavour in env.all_flavours)} 
        local_files = {flavour.name: file_(dir_ / (f'local_{env.ninja_file.name}'), flavour) for flavour, dir_ in ((flavour, env.get_build_path(flavour)) for flavour in env.all_flavours)}

        main_build_file.write(f'ninja_required_version=1.8\n')
        if _BUILD_DIR is not None:
            main_build_file.write(f'builddir={escape(_BUILD_DIR)}\n')
        main_build_file.write(f'include {escape(_get_resource_file("common.ninja_inc"))}\n')
        main_build_file.write(f'PYTHON={escape(sys.executable)}\n')
        main_build_file.writelines(f'{line}\n' for line in OrderedDict(zip(chain.from_iterable(injection(env, flavour).splitlines() for injection in env.all_injections for flavour in env.all_flavours), repeat(None))).keys())
        main_build_file.writelines(f'subninja {escape(subenv.base_dir / f"common_{subenv.ninja_file.name}")}\n' for subenv in (env, *env.first_class_subenvs))

        for flavour in env.all_flavours:
            resolve_escape_join_ = partial(resolve_escape_join, env=env, flavour=flavour)

            build_files[flavour.name].write(f'include {escape(_get_resource_file("common.ninja_inc"))}\n')
            build_files[flavour.name].write(f'PYTHON={escape(sys.executable)}\n')
            build_files[flavour.name].writelines(f'{line}\n' for line in OrderedDict(zip(chain.from_iterable(injection(env, flavour).splitlines() for injection in env.all_injections), repeat(None))).keys())
            build_files[flavour.name].writelines(f'subninja {resolve_escape_join_(subenv.base_dir / f"common_{subenv.ninja_file.name}")}\n' for subenv in (env, *env.first_class_subenvs))
            
            local_files[flavour.name].writelines(f'{flag.name}={resolve_escape_join_((f"${flag.name}", flag.value) if flag.append else flag.value)}\n' for flag in get_env_flags(env, flavour))

            for out_file in (main_build_file, build_files[flavour.name]):
                out_file.writelines(f'subninja {resolve_escape_join_(subenv.get_build_path() / f"local_{subenv.ninja_file.name}")}\n' for subenv in (env, *env.first_class_subenvs))
            
            defaults = phony_inputs(target for target in env.all_defaults if isinstance(target, _Target)) or tuple(phony_inputs(subenv.terminal_targets) for subenv in (env, *env.first_class_subenvs))
            main_build_file.write(f'build {flavour.name} : phony {resolve_escape_join_(defaults)}\n')

            for output, items in groupby(sorted(((resolve_escape_join_(target.outputs[0]), target) for target in env.all_targets if target.rule == 'phony'), key=itemgetter(0)), key=itemgetter(0)):
                build_files[flavour.name].write(f'build {output} : phony {resolve_escape_join_(phony_inputs(target for _, target in items))}\n')

        for output, items in groupby(sorted(((resolve_escape_join(target.outputs[0], env=env, flavour=flavour), target, flavour) for target in env.all_targets if target.rule == 'phony' for flavour in env.all_flavours), key=itemgetter(0)), key=itemgetter(0)):
            main_build_file.write(f'build {output} : phony {" ".join(resolve_escape_join(phony_inputs((target,)), env=env, flavour=flavour) for _, target, flavour in items)}\n')

        for target in filter(lambda target: target.rule != 'phony', env.local_targets):
            flavour_dependant = all('{flavour}' in str(output) for output in chain(target.outputs, target.implicit_outputs))
            for flavour in (env.all_flavours if flavour_dependant else (DEFAULT_FLAVOUR,)):
                resolve_escape_join_ = partial(resolve_escape_join, env=env, flavour=flavour)
                out_file = local_files[flavour.name] if flavour_dependant else common_build_file
                out_file.write(f'build {resolve_escape_join_(target.outputs)} {("| " + resolve_escape_join_(target.implicit_outputs)) if target.implicit_outputs else ""} : {target.rule} {resolve_escape_join_(target.inputs)} {("| " + resolve_escape_join_(target.implicit_inputs)) if target.implicit_inputs else ""}  {("|| " + resolve_escape_join_(target.order_only_inputs)) if target.order_only_inputs else ""}\n')
                out_file.writelines(f'  {flag.name}={resolve_escape_join_((f"${flag.name}", flag.value) if flag.append else flag.value)}\n' for flag in get_target_flags(target, flavour))

        for flavour in env.all_flavours:
            for out_file in (main_build_file, build_files[flavour.name]):
                if env.all_defaults:
                    out_file.write(f'default {" ".join(set(resolve_escape_join_(default) for default in env.all_defaults))}\n')

        with file_(env.base_dir / (f'{env.ninja_file.name}.d')) as deps_file:
            deps_file.write(str(env.ninja_file) + ' : ' + ' '.join(str(dep).replace(' ', r'\ ') for dep in sorted(env.dependencies)))


def generate(env):  # pylint:disable=redefined-outer-name
    for subenv in (env, *env.first_class_subenvs):
        _generate_env(subenv)


def main(**kwargs):
    parser = ArgumentParser()
    parser.add_argument('--logging-ini')
    parser.add_argument('--builddir', type=Path, default=None, help='ninja builddir variable')
    parser.add_argument('input', type=Path, default=Path.cwd(), help='prjdef file (or directory containing one)')
    args = parser.parse_args(**kwargs)

    global _BUILD_DIR
    _BUILD_DIR = args.builddir

    if args.logging_ini:
        logging.config.fileConfig(args.logging_ini)
    else:
        logging.basicConfig(level=logging.INFO)

    env = parse(args.input).E

    for name, attribute in vars(Env).items():
        if isinstance(attribute, property):
            setattr(Env, name, property(lru_cache(maxsize=1)(attribute.fget)))

    generate(env)


if __name__ == '__main__':
    sys.modules[__package__] = sys.modules['__main__']
    main()
