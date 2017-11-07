'''
Filesystem genjutsu toolset
'''
from pathlib import Path
from platform import system

from genjutsu import E, Inject, Target, escape


_RESOURCE_DIR = Path(__file__).resolve().parent

class Toolset:
    @classmethod
    def apply_to_env(cls):
        system_name, *_ = system().lower().split('-')
        filename = f'filesystem-{system_name}.ninja_inc'
        Inject(lambda env, flavour: f'include {escape(_RESOURCE_DIR / filename)}', key=cls)

    @staticmethod
    def add_rules(globals_):
        globals_['Copy'] = lambda from_, to=None, **kwargs: Target((E.source_path / from_,), (E.build_path / (to or from_),), 'copy', **kwargs)
