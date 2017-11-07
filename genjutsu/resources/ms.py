'''
MS CL genjutsu toolset
'''
from itertools import chain
from pathlib import Path

from genjutsu import Alias, Apply, E, F, Flag, Inject, Target, Variable, escape


_RESOURCE_DIR = Path(__file__).resolve().parent

class CompilerToolset:
    @classmethod
    def apply_to_env(cls):  #pylint: disable=missing-docstring
        Inject(lambda env, flavour: f'include {escape(_RESOURCE_DIR / "mscl.ninja_inc")}', key=cls)
        Apply(Flag('CLDEFINEFLAGS', f'/D"{define}"') for define in ('_WIN32', '_DEBUG', 'NOMINMAX', 'CRIPPLED'))

    @staticmethod
    def add_rules(globals_):  #pylint: disable=missing-docstring
        globals_['CxxDef'] = lambda key, value=None: Flag('CLDEFINEFLAGS', (F('/D"', key, '"="', value, '"'),) if value else (F('/D"', key, '"'),))
        globals_['IncludeDir'] = lambda path, system=False: Flag('CLINCLUDEFLAGS', (F('/I"', Path(path), '"'),))

        CxxFlag = globals_['CxxFlag'] = lambda value: Flag('CLFLAGS', value) #pylint:disable=invalid-name

        def Pch(pch, *, flags=(), **kwargs): #pylint:disable=invalid-name,missing-docstring
            cxx = Target((E.source_path / pch,), ((E.build_path / pch).with_suffix('.cxx'),), 'make_pch_cxx')
            flags = tuple(chain(flags, (Variable('PCH', (cxx.inputs[0],)), Variable('COMPILED_PCH', ((E.build_path / pch).with_suffix('.pch'),)), Variable('PDB', (E.first_class_supenv.build_dir / (E.first_class_supenv.base_dir.name + '.pdb'),)))))
            return Target((cxx,), ((E.build_path / pch).with_suffix('.obj'),), 'pch', flags=flags, **kwargs)
        globals_['Pch'] = Pch

        def Cxx(cxx, pch=None, *, implicit_inputs=(), flags=(), output_flags=(), quick_build_alias='{source}:{flavour}', **kwargs): #pylint:disable=invalid-name,missing-docstring
            if pch:
                pch_cxx, pch_obj = pch.inputs[0], pch.outputs[0]
                flags = tuple(chain(flags, (CxxFlag(F('/Yu"', pch_cxx, '"')), CxxFlag(F('/FI"', pch_cxx, '"')))))
                output_flags = tuple(chain(output_flags, (Variable('PCH_OBJ', pch_obj),)))
                implicit_inputs += (pch_cxx, pch_obj)
            flags = (Variable('PDB', (E.first_class_supenv.build_dir / (E.first_class_supenv.base_dir.name + '.pdb'),)),)
            result = Target((E.source_path / cxx,), ((E.build_path / cxx).with_suffix('.obj'),), 'cxx', implicit_inputs=implicit_inputs, flags=flags, output_flags=output_flags, **kwargs)
            if quick_build_alias is not None:
                Alias(quick_build_alias.format(source=E.get_source_path() / cxx, flavour='{flavour}'), (result,))
            return result
        globals_['Cxx'] = Cxx


class LinkerToolset:
    @classmethod
    def apply_to_env(cls):  #pylint: disable=missing-docstring
        Inject(lambda env, flavour: f'include {escape(_RESOURCE_DIR / "mslink.ninja_inc")}', key=cls)

    @staticmethod
    def add_rules(globals_):  #pylint: disable=missing-docstring
        LinkFlag = globals_['LinkFlag'] = lambda value: Flag('LINKFLAGS', value) #pylint:disable=invalid-name
        Lib = globals_['Lib'] = lambda lib: LinkFlag(f'"{lib}.lib"') #pylint:disable=invalid-name
        LibDir = globals_['LibDir'] = lambda path: LinkFlag(F('/LIBPATH:"', Path(path), '"')) #pylint:disable=invalid-name

        def LinkerTarget(*args, libs=(), implicit_inputs=(), flags=(), output_flags=(), **kwargs): #pylint:disable=invalid-name,missing-docstring
            flags = tuple(chain(flags, *((LibDir(lib.env.base_dir / lib.outputs[0].parent), Lib(lib.outputs[0].stem)) for lib in libs)))
            return Target(*args, implicit_inputs=chain(implicit_inputs, libs), flags=flags, output_flags=output_flags, **kwargs)
        globals_['LinkerTarget'] = LinkerTarget

        globals_['Archive'] = lambda lib, objects, **kwargs: LinkerTarget(objects, (E.build_path / (lib + '.lib'),), 'lib', **kwargs)

        def Dll(lib, objects, *, flags=(), **kwargs): #pylint:disable=invalid-name,missing-docstring
            flags = tuple(chain(flags, (Variable('DLL', (E.build_path / lib).with_suffix('.dll')),)))
            return LinkerTarget(objects, (E.build_path / (lib + '.lib'),), 'dll', implicit_outputs=(E.build_path / (lib + '.dll'),), flags=flags, **kwargs)
        globals_['SharedObject'] = Dll

        globals_['PieExecutable'] = globals_['Executable'] = lambda executable, objects, **kwargs: LinkerTarget(objects, ((E.build_path / executable).with_suffix('.exe'),), 'exe', **kwargs)


class Toolset:
    @classmethod
    def apply_to_env(cls):  #pylint: disable=missing-docstring
       CompilerToolset.apply_to_env()
       LinkerToolset.apply_to_env()

    @staticmethod
    def add_rules(globals_):  #pylint: disable=missing-docstring
       CompilerToolset.add_rules(globals_)
       LinkerToolset.add_rules(globals_)