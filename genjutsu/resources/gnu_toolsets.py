'''
Clang genjutsu toolset
'''
from pathlib import Path
from platform import system
from os import environ

from genjutsu import Default, Flavour, Flag, Inject, escape

_RESOURCE_DIR = Path(__file__).resolve().parent


class GnuToolset:
    KIND_COMPILER, KIND_LINKER = 'compiler', 'linker'
    __FLAGS = { KIND_COMPILER: ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS'),
                KIND_LINKER: ('LDFLAGS',)}

    def __init_subclass__(cls, compiler_name, kind=KIND_COMPILER, flavours=('debug', 'release'), **kwargs):  #pylint: disable=missing-docstring
        super().__init_subclass__(**kwargs)
        cls.__COMPILER_NAME = compiler_name
        cls.__KIND = kind
        cls.__FLAVOURS = flavours

    @classmethod
    def apply_to_env(cls):  #pylint: disable=missing-docstring
        system_name, *_ = system().lower().split('-')
        Inject(lambda env, flavour: '\n'.join((f'include {escape(_RESOURCE_DIR / f"{cls.__COMPILER_NAME}-{system_name}.ninja_inc")}',
                                               f'include {escape(_RESOURCE_DIR / f"gnu_{cls.__KIND}.ninja_inc")}')), key=cls)
        flavours = [Flavour(flavour, flags=[Flag(flags, ('$' + flags + '_' + flavour.upper(),)) for flags in cls.__FLAGS[cls.__KIND]]) for flavour in cls.__FLAVOURS]
        Default(flavours[0])
#        # set by vcvars.bat
#        if system_name == 'windows':
#            for path in environ.get('INCLUDE', '').split(';'):
#                IncludeDir(path)

    @classmethod
    def add_rules(cls, globals_):  #pylint: disable=missing-docstring
        gnu_rules = Path(__file__).with_name(f'gnu_{cls.__KIND}_rules.py')
        with gnu_rules.open() as stream: #pylint: disable=no-member
            exec(compile(stream.read(), str(gnu_rules), 'exec', optimize=0), globals_, globals_) #pylint: disable=exec-used


class BundleToolset:
    def __init_subclass__(cls, toolsets, **kwargs):  #pylint: disable=missing-docstring
        super().__init_subclass__(**kwargs)
        cls.__TOOLSETS = toolsets

    @classmethod
    def apply_to_env(cls):  #pylint: disable=missing-docstring
        for toolset in cls.__TOOLSETS:
            toolset.apply_to_env()

    @classmethod
    def add_rules(cls, globals_):  #pylint: disable=missing-docstring
        for toolset in cls.__TOOLSETS:
            toolset.add_rules(globals_)
