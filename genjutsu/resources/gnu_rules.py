'''
Rules for toolsets following the CLI of GCC (namely GCC and Clang)
'''
from itertools import chain
from pathlib import Path
from genjutsu import Alias, E, F, Flag, Target


def CxxFlag(flag): #pylint: disable=invalid-name,missing-docstring
    return Flag('CXXFLAGS', flag)


def IncludeDir(path, *, system=False): #pylint: disable=invalid-name,missing-docstring
    return CxxFlag(F('-isystem' if system else '-I', Path(path)))


def LinkFlag(value): #pylint: disable=invalid-name,missing-docstring
    return Flag('LDFLAGS', value)


def LibDir(path): #pylint: disable=invalid-name,missing-docstring
    return LinkFlag(F('-L', Path(path)))


def Lib(lib): #pylint: disable=invalid-name,missing-docstring
    return Flag('LDLIBS', F('-l', lib))


def CxxDef(key, value=None): #pylint: disable=invalid-name,missing-docstring
    return CxxFlag(F('-D', key, '=', value) if value is not None else F('-D', key))


def Pch(pch, **kwargs): #pylint: disable=invalid-name,missing-docstring
    return Target((E.source_path / pch,), ((E.build_path / pch).with_suffix('.pch'),), 'pch', **kwargs)


def Cxx(cxx, *, pch=None, implicit_inputs=(), flags=(), quick_build_alias='{source}:{flavour}', **kwargs): #pylint: disable=invalid-name,missing-docstring
    if pch:
        flags = chain(flags, (CxxFlag(F('-include ', pch.inputs[0])),))
        implicit_inputs = chain(implicit_inputs, pch.outputs)
    result = Target((E.source_path / cxx,), ((E.build_path / cxx).with_suffix('.o'),), 'cxx', implicit_inputs=implicit_inputs, flags=flags, **kwargs)
    if quick_build_alias is not None:
        Alias(quick_build_alias.format(source=E.source_path / cxx, flavour='{flavour}'), (result,))
    return result


def LinkerTarget(*args, libs=(), implicit_inputs=(), flags=(), **kwargs): #pylint: disable=invalid-name,missing-docstring
    flags = chain(flags, *((LibDir(lib.outputs[0].parent), Lib(lib.outputs[0].stem[3:])) for lib in libs))
    return Target(*args, implicit_inputs=chain(libs, implicit_inputs), flags=flags, **kwargs)


def Archive(archive, objects, **kwargs): #pylint: disable=invalid-name,missing-docstring
    return LinkerTarget(objects, (E.build_path / ('lib' + archive + '.a'),), 'ar', **kwargs)


def SharedObject(so, objects, **kwargs): #pylint: disable=invalid-name,missing-docstring
    return LinkerTarget(objects, (E.build_path / ('lib' + so + '.so'),), 'lib', **kwargs)


def Executable(executable, objects, **kwargs): #pylint: disable=invalid-name,missing-docstring
    return LinkerTarget(objects, (E.build_path / executable,), 'exe', **kwargs)

def PieExecutable(executable, objects, *, flags=(), **kwargs): #pylint: disable=invalid-name,missing-docstring
    flags = tuple(chain(flags, (LinkFlag('-pie'), LinkFlag('-rdynamic'))))
    return LinkerTarget(objects, (E.build_path / executable,), 'exe', flags=flags, **kwargs)