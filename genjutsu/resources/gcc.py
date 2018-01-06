'''
GCC genjutsu toolset
'''
from genjutsu import toolset_class

_COMPILER_NAME = 'gcc'

_GnuToolset = toolset_class('gnu_toolsets.GnuToolset')
_BundleToolset = toolset_class('gnu_toolsets.BundleToolset')

class CompilerToolset(_GnuToolset, compiler_name=_COMPILER_NAME):
    pass

class LinkerToolset(_GnuToolset, compiler_name=_COMPILER_NAME, kind=_GnuToolset.KIND_LINKER):
    pass

class Toolset(_BundleToolset, toolsets=(CompilerToolset, LinkerToolset)):
    pass
