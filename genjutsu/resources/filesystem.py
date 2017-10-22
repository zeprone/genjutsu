'''
Filesystem genjutsu toolset
'''
from pathlib import Path
from platform import system

from genjutsu import E, Inject, Target


class Toolset:

    @classmethod
    def apply_to_env(cls):
        def inject(env, flavour):
            system_name, *_ = system().lower().split('-')
            root = Path(__file__).parent
            return (('include', Path(__file__).parent / f'filesystem-{system_name}.ninja_inc'),)
        Inject(inject, key=cls)

    @staticmethod
    def add_rules(globals_):
        globals_['Copy'] = lambda from_, to=None, **kwargs: Target((E.source_path / from_,), (E.build_path / (to or from_),), 'copy', **kwargs)
