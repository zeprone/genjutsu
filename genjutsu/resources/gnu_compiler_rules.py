'''
Rules for toolsets following the CLI of GCC (namely GCC and Clang)
'''
from itertools import chain
from pathlib import Path
from genjutsu import Alias, E, Flag, Target


def CxxFlag(*args): #pylint: disable=invalid-name,missing-docstring
    return Flag('CXXFLAGS', tuple(args))


def IncludeDir(path, *, system=False): #pylint: disable=invalid-name,missing-docstring
    return CxxFlag('-isystem' if system else '-I', Path(path))


def CxxDef(key, value=None): #pylint: disable=invalid-name,missing-docstring
    return CxxFlag(*(('-D', key, '=', value) if value is not None else ('-D', key)))


def Pch(pch, **kwargs): #pylint: disable=invalid-name,missing-docstring
    return Target((E.source_path / pch,), ((E.build_path / pch).with_suffix('.pch'),), 'pch', **kwargs)


def Cxx(cxx, *, pch=None, implicit_inputs=(), flags=(), quick_build_alias='{source}:{flavour}', **kwargs): #pylint: disable=invalid-name,missing-docstring
    if pch:
        flags = chain(flags, (CxxFlag('-include ', pch.inputs[0]),))
        implicit_inputs = chain(implicit_inputs, pch.outputs)
    cxx = cxx.outputs[0] if hasattr(cxx, 'outputs') else E.source_path / cxx
    result = Target((cxx,), ((E.build_path / cxx).with_suffix('.o'),), 'cxx', implicit_inputs=implicit_inputs, flags=flags, **kwargs)
    if quick_build_alias is not None:
        Alias(quick_build_alias.format(source=E.source_path / cxx, flavour='{flavour}'), (result,))
    return result
