#!/usr/bin/env python

from setuptools import setup
import os

dir = os.path.dirname(__file__)
path_to_main_file = os.path.join(dir, "src/seedboxtools/__init__.py")
for line in open(path_to_main_file):
	if line.startswith('__version__'):
		version = line.split()[-1].strip("'").strip('"')
		break
else:
	raise ValueError, '"__version__" not found in "src/seedboxtools/__init__.py"'

setup(
	name = 'seedboxtools',
	version=version,
	description = 'A tool to automate downloading finished torrents from a seedbox',
	long_description = """seedboxtools is a tool to automate the download of finished torrents from a seedbox, whether it be TorrentFlux-b4rt or Transmission with its Web and API interface.""",
	author='Manuel Amador (Rudd-O)',
	author_email='rudd-o@rudd-o.com',
	license="GPL",
	url = 'http://github.com/Rudd-O/seedboxtools',
	package_dir=dict([
					("seedboxtools", "src/seedboxtools"),
					]),
	packages = ["seedboxtools"],
	scripts = ["bin/configleecher", 'bin/leechtorrents'],
	keywords = "seedbox TorrentFlux Transmission torrents",
	zip_safe=False,
)
