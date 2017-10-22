from pathlib import Path

def pytest_addoption(parser):
    parser.addoption('--profile', type=Path)