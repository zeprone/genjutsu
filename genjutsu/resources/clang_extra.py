'''
Clang genjutsu toolset including profile/sanitize flavours
'''
from genjutsu import Flavour, Flag, Toolset as Toolset_

class Toolset:
    __FLAGS = ('CPPFLAGS', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS')
    __FLAVOURS = ('profile', 'profile_instr_record', 'profile_instr_use', 'profile_sample_record', 'profile_sample_use',
                  'sanitize_address', 'sanitize_thread', 'sanitize_memory', 'sanitize_undefined')

    def __init__(self):
        self.__super = Toolset_('clang')

    def apply_to_env(self):
        self.__super.apply_to_env()
        for flavour in self.__FLAVOURS:
            Flavour(flavour, flags=[Flag(flags, ('$' + flags + '_' + flavour.upper(),)) for flags in self.__FLAGS])

    def add_rules(self, globals_):
        self.__super.add_rules(globals_)
