from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree
import sys

import pytest
import pprofile

ROOT_DIR = Path(__file__).parent.resolve()
_RESOURCE_DIR = ROOT_DIR / 'resources'

sys.path.append(str(ROOT_DIR))
from genjutsu import main as genjutsu_main

@pytest.fixture
def profiler(request):
    profile = pprofile.Profile()
    yield profile
    filename = request.config.getoption('--profile')
    with filename.open('w', encoding='utf-8') as out:
        profile.annotate(out)
    with filename.with_suffix('.callgrind').open('w') as out:
        profile.callgrind(out)

@contextmanager
def __run_ninja(profiler, tmpdir, base_dir, *args):
    run_dir = Path(str(tmpdir)) / base_dir.name
    copytree(str(base_dir), str(run_dir))
    args = [str(arg).format(run_dir=run_dir) for arg in args]
    with profiler:
        genjutsu_main(args=[str(run_dir), *args])
    yield run_dir

def test_empty(profiler, tmpdir):
    with __run_ninja(profiler, tmpdir, _RESOURCE_DIR / 'empty') as d:
        pass

def test_full(profiler, tmpdir):
    with __run_ninja(profiler, tmpdir, _RESOURCE_DIR / 'full', '--verbose', '--depfile', '--toolset', 'cl') as d:
        ninja_file = Path(d) / 'prjdef.ninja'
        build_file = Path(d) / 'build.ninja'
        build_deps_file = Path(d) / 'prjdef.ninja.d'
        assert ninja_file.is_file()
        assert build_file.is_file()
        assert build_deps_file.is_file()