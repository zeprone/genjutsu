# 幻術 Genjutsu

> Medieval Japan secret art of Illusi^H^H^H build file generation  
げんじゅつ (_romaji_ genjutsu)  
__gen__: _Shortened from 'generate'_, To generate using an automated process, especially a computer program  
__じゅつ__ / __術__: art, craft, skill, special feat; method, technique


## Introduction
Genjutsu is yet-another generator for the Ninja build system (https://ninja-build.org/).  
View it as
- a Slim-down version of [Scons](http://scons.org) (to which it borrows the usage of python as a turing-complete DSL) in which the management of the graph of dependencies has been outsourced to Ninja
- An anti-[CMake](http://cmake.org), as it focuses on remaining lightweight (500 LOC), extendible (see Toolsets()), and  (Genjutsu input files are python scripts, and then runnable in a debugger)


## Examples

### Hello World !
``` python
Executable('hello_world', objects=[Cxx('hello_world.cxx')]])
```

### Real life, yet simple, example
``` python
Apply(IncludeDir('include'))

with env(path='src'):
	pch = Pch('precompiled_header')
	objects = [Cxx(s, pch=pch) for s in Glob('*.cxx',)]
	lib = Archive('lib', objects=objects)
```

##Invoking Genjutsu

###Environment variables
Separated by the system path separator (`;` on Windows systems, `:` on Unix-like)
* `GENJUTSU_TOOLSETS` = `path\to\3rdparty:path\to\msbuild_gen`
* `GENJUTSU_RESOURCE_PATH` = `cl:3rdparty:msbuild_gen`

```eval_rst
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

* [genjutsu API](genjutsu.md)
* [Default toolsets](default_toolsets.md)

# Heading

## Sub-heading

### Another deeper heading
 
Paragraphs are separated
by a blank line.

Two spaces at the end of a line leave a  
line break.

Text attributes _italic_, *italic*, __bold__, **bold**, `monospace`.

Horizontal rule:

---

Bullet list:

  * apples
  * oranges
  * pears

Numbered list:

  1. apples
  2. oranges
  3. pears

A [link](http://example.com).