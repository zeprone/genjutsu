'''
Clang genjutsu toolset
'''
from pathlib import Path
from platform import system
from os import environ

from genjutsu import Default, Flavour, Flag, FormatExpression, Inject


class Toolset:
    __FLAGS = ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS')
    __FLAVOURS = ('debug', 'release')
            
    __SYSTEM_NAME, *_ = system().lower().split('-')

    @classmethod
    def apply_to_env(cls):
        def inject(env, flavour):
            root = Path(__file__).parent
            return tuple(('include', Path(__file__).parent / f) for f in (f'clang-{cls.__SYSTEM_NAME}.ninja_inc', 'gnu_rules.ninja_inc'))
        Inject(inject, key=cls)
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
