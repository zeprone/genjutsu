'''
Clang genjutsu toolset
'''
from genjutsu import toolset_class

_COMPILER_NAME = 'clang'
_EXTRA_FLAVOURS = ('debug', 'release',
                   'profile', 'profile_instr_record', 'profile_instr_use', 'profile_sample_record', 'profile_sample_use',
                   'sanitize_address', 'sanitize_thread', 'sanitize_memory', 'sanitize_undefined') 

_GnuToolset = toolset_class('gnu_toolsets.GnuToolset')
_BundleToolset = toolset_class('gnu_toolsets.BundleToolset')

class CompilerToolset(_GnuToolset, compiler_name=_COMPILER_NAME):
    pass

class CompilerToolset0(_GnuToolset, compiler_name=_COMPILER_NAME, flavours=_EXTRA_FLAVOURS):
    'Clang genjutsu toolset including profile/sanitize flavours'
    pass

class LinkerToolset(_GnuToolset, compiler_name=_COMPILER_NAME, kind=_GnuToolset.KIND_LINKER):
    pass

class Toolset(_BundleToolset, toolsets=(CompilerToolset, LinkerToolset)):
    pass
