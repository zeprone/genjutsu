'''
Rules for toolsets following the CLI of GCC (namely GCC and Clang)
'''
from itertools import chain
from pathlib import Path
from genjutsu import E, Flag, Target


def LinkFlag(*args): #pylint: disable=invalid-name,missing-docstring
    return Flag('LDFLAGS', tuple(args))


def LibDir(path): #pylint: disable=invalid-name,missing-docstring
    return LinkFlag('-L', Path(path))


def Lib(lib): #pylint: disable=invalid-name,missing-docstring
    return Flag('LDLIBS', ('-l', lib))


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