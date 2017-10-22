# Default toolsets

##C++ compilers support
clang (default)
g++
MS cl

* `CxxDef(key, value)`: Proprocessor definition
* `IncludeDir(path, system)`: Include directory
* `CxxFlag(flag)`: freeform flag
* `Lib(lib)`: library name
* `LibDir(path)`: library directory
* `Pch(pch, *, flags=(), **kwargs)`: precompiled header
* `Cxx(cxx, pch=None, *, implicit_inputs=(), flags=(), **kwargs)`: c++ compilation
* `Archive(lib, objects, **kwargs)`:
* `SharedObject(lib, objects, *, flags=(), **kwargs)`:
* `Executable(executable, objects, **kwargs)`:
* `Copy(from_, to=None, **kwargs)`: file copy


## MSBuild support (msbuild_gen)

Add to `GENJUTSU_TOOLSETS` (and to `GENJUTSU_RESOURCE_PATH`)
It will automatically declare an 'msbuild' target which generates _MSBuild_ `.vcxproj` file for each ninja file.

```eval_rst
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```