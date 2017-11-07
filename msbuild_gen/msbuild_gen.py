#!/usr/bin/env python3
from argparse import ArgumentParser
from collections import namedtuple
from glob import glob
from hashlib import md5
from itertools import chain
import logging
from os import environ
from pathlib import Path
from uuid import UUID
import sys


assert sys.version_info > (3, 5)

__version__ = "1.0.0+20170613.0"

_Flags = namedtuple('_Flags', ('preprocessor_definitions', 'include_dirs'))
_Cxx = namedtuple('_Cxx', ('path', 'flags_by_configuration'))
_VCXProj = namedtuple('_VCXProj', ('name', 'path', 'guid', 'sources', 'includes', 'ninja_file', 'flags_by_configuration', 'build_dir'))

_RESOURCE_DIR = Path(__file__).parent / 'resources'

def vcxproj_files(project_directory):  #pylint: disable=missing-docstring
    def target_file(template_path):  #pylint: disable=missing-docstring
        return project_directory / str(template_path.relative_to(_RESOURCE_DIR / 'vcxproj')).replace('template', project_directory.name)
    return {target_file(template_path): template_path for template_path in _RESOURCE_DIR.glob('vcxproj/**/*') if template_path.is_file()}


def VCXProj(env, *, include_file_patterns=[], **kwargs):  #pylint: disable=invalid-name,missing-docstring,redefined-outer-name
    from genjutsu import resolve, get_env_flags, get_target_flags

    def make_flags(flags):  #pylint: disable=missing-docstring
        flags = {flag.name: list(resolve(flag.value)) for flag in flags}
        preprocessor_definitions = tuple(chain.from_iterable((value[2:].strip() for value in values
                                   if name == 'CXXFLAGS' and value.startswith('-D') or name == 'CLDEFINEFLAGS') for name, values in flags.items()))
        include_dirs = tuple(chain.from_iterable((value[2:].strip() for value in values
                       if name == 'CXXFLAGS' and value.startswith('-I') or name == 'CLINCLUDEFLAGS') for name, values in flags.items()))
        return _Flags(preprocessor_definitions, include_dirs)

    def make_cxx(target):  #pylint: disable=missing-docstring
        return [_Cxx(input_, {flavour.name: make_flags(get_target_flags(target, flavour)) for flavour in target.env.all_flavours}) for input_ in target.inputs]

    name = env.base_dir.name
    vcproj_file = env.base_dir / (name + '.vcxproj')
    sources = tuple(chain.from_iterable(make_cxx(target) for target in env.local_targets if target.rule == 'cxx'))
    includes = tuple(path.relative_to(env.base_dir) for path in chain.from_iterable(env.get_source_path().glob(pattern) for pattern in include_file_patterns))
    guid = UUID(bytes=md5(bytes(str(env.base_dir), 'utf-8')).digest(), version=4)
    flags = {flavour.name: make_flags(get_env_flags(env, flavour)) for flavour in env.all_flavours}
    return _VCXProj(name=name, path=vcproj_file, guid=guid, sources=sources, includes=includes, ninja_file=env.ninja_file, flags_by_configuration=flags, build_dir=env.build_dir)


def vcxproj(prjdef, **kwargs):  #pylint: disable=missing-docstring
    from genjutsu import parse

    env = parse(prjdef).E
    project = VCXProj(env, **kwargs)

    from jinja2 import Template
    for output_path, template_path in vcxproj_files(env.base_dir).items():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(Template(template_path.read_text()).render(project=project, **kwargs))


class Toolset:  #pylint: disable=missing-docstring
    @classmethod
    def apply_to_env(cls):  #pylint: disable=missing-docstring
        from genjutsu import Alias, E, Inject, Target, Variable, resolve_escape_join
        Inject(lambda env, flavour: f'include {resolve_escape_join(_RESOURCE_DIR / "msbuild.ninja_inc", env=env, flavour=flavour)}', key=(cls, 0))
        if E.ninja_file:
            Inject(lambda env, flavour: f'build {resolve_escape_join(env.build_path / "msbuild_cookie", env=env, flavour=flavour)} : msbuild_cookie {flavour.name}', key=(cls, 1))
            Inject(lambda env, flavour: f'build {flavour.name}_msbuild_cookie : phony {resolve_escape_join(env.build_path / "msbuild_cookie", env=env, flavour=flavour)}', key=(cls, 2))
            Alias('msbuild', [Target(inputs=(E.prj_file,),
                                     implicit_inputs=(E.ninja_file,),
                                     outputs=vcxproj_files(E.ninja_file.parent),
                                     rule='msbuild_vcxproj',
                                     flags=(Variable(var, (environ.get(var, ''),)) for var in ('GENJUTSU_RESOURCE_PATH', 'GENJUTSU_TOOLSETS')))])

    @staticmethod
    def add_rules(globals_):  #pylint: disable=missing-docstring
        pass


def main(argv=None):  #pylint: disable=missing-docstring
    argv = argv or sys.argv[1:] + [arg for arg in environ.get('MSBUILD_GEN_VCPROJX_OPTS', '').split(' ') if arg]

    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    vcxproj_parser = subparsers.add_parser('vcxproj')
    vcxproj_parser.set_defaults(callback=vcxproj)
    vcxproj_parser.add_argument('--ms-tools-version', default=environ.get('VisualStudioVersion', '15.0'))
    vcxproj_parser.add_argument('--ms-toolset', default='v141', help='will determine standard compiler include/lib directories') #v141_clang_c2
    vcxproj_parser.add_argument('--ms-windows-target-platform', default=environ.get('UCRTVersion', '10.0.14393.0'))
    vcxproj_parser.add_argument('--platform', nargs='*', dest='platforms', default=['Win32'])
    vcxproj_parser.add_argument('--use-ninja-extension', action='store_true', help='only work with VS professionnal')
    vcxproj_parser.add_argument('--ninja-extension-dir', type=Path, default=_RESOURCE_DIR)
    vcxproj_parser.add_argument('--ninja-exe', default=environ.get('NINJA', 'ninja.exe'), help='ninja executable (NINJA environment variable)')
    vcxproj_parser.add_argument('--genjutsu-toolsets', default=environ.get('GENJUTSU_TOOLSETS', 'overloads $GENJUTSU_TOOLSETS'))
    vcxproj_parser.add_argument('--genjutsu-resource-path', default=environ.get('GENJUTSU_RESOURCE_PATH', ''), help='overloads $GENJUTSU_RESOURCE_PATH')
    vcxproj_parser.add_argument('--include-file-pattern', nargs='*', dest='include_file_patterns', default=['**/*.h'])
    vcxproj_parser.add_argument('prjdef', type=Path, default=Path.cwd(), help='prjdef file (or directory containing one)')

    args = vars(parser.parse_args(argv))
    environ['GENJUTSU_TOOLSETS'] = args.pop('genjutsu_toolsets')
    environ['GENJUTSU_RESOURCE_PATH'] = args.pop('genjutsu_resource_path')
    args.pop('callback')(**args)


if __name__ == '__main__':
    main()
