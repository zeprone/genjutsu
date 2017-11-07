'''
Clang genjutsu toolset
'''
from pathlib import Path
from platform import system
from os import environ
from textwrap import dedent

from genjutsu import Default, Flavour, Flag, Inject, escape


_RESOURCE_DIR = Path(__file__).resolve().parent

class Toolset:
    __FLAGS = ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS')
    __FLAVOURS = ('debug', 'release')
            
    @classmethod
    def apply_to_env(cls):
        system_name, *_ = system().lower().split('-')
        filename = f'clang-{system_name}.ninja_inc'))
        Inject(lambda env, flavour: dedent(f'''include {escape(_RESOURCE_DIR / filename)}
                                               include {escape(_RESOURCE_DIR / "gnu_rules.ninja_inc")}'''), key=cls)
        flavours = [Flavour(flavour, flags=[Flag(flags, ('$' + flags + '_' + flavour.upper(),)) for flags in cls.__FLAGS]) for flavour in cls.__FLAVOURS]
        Default(flavours[0])
        # set by vcvars.bat
        if cls.__SYSTEM_NAME == 'windows':
            for path in environ.get('INCLUDE', '').split(';'):
#                IncludeDir(path)
                pass
            for path in environ.get('LIB', '').split(';'):
#                LibDir(path)
                pass

    @staticmethod
    def add_rules(globals_):
        gnu_rules = Path(__file__).with_name('gnu_rules.py')
        with gnu_rules.open() as stream: #pylint: disable=no-member
            exec(compile(stream.read(), str(gnu_rules), 'exec', optimize=0), globals_, globals_) #pylint: disable=exec-used
