#!/usr/bin/env python

from setuptools import setup
import os

dir = os.path.dirname(__file__)
path_to_main_file = os.path.join(dir, "src/seedboxtools/__init__.py")
path_to_readme = os.path.join(dir, "README")
for line in open(path_to_main_file):
	if line.startswith('__version__'):
		version = line.split()[-1].strip("'").strip('"')
		break
else:
	raise ValueError, '"__version__" not found in "src/seedboxtools/__init__.py"'
readme = open(path_to_readme).read(-1)

classifiers = [
'Development Status :: 5 - Production/Stable',
'Environment :: Console',
'Environment :: No Input/Output (Daemon)',
'Intended Audience :: End Users/Desktop',
'Intended Audience :: System Administrators',
'License :: OSI Approved :: GNU General Public License (GPL)',
'Operating System :: POSIX :: Linux',
'Programming Language :: Python :: 2 :: Only',
'Programming Language :: Python :: 2.7',
'Topic :: Communications :: File Sharing',
'Topic :: Utilities',
]

setup(
	name = 'seedboxtools',
	version=version,
	description = 'A tool to automate downloading finished torrents from a seedbox',
	long_description = readme,
	author='Manuel Amador (Rudd-O)',
	author_email='rudd-o@rudd-o.com',
	license="GPL",
	url = 'http://github.com/Rudd-O/seedboxtools',
	package_dir=dict([
					("seedboxtools", "src/seedboxtools"),
					]),
	classifiers = classifiers,
	packages = ["seedboxtools"],
	scripts = ["bin/configleecher", 'bin/leechtorrents'],
	keywords = "seedbox TorrentFlux Transmission torrents",
	requires = ["iniparse"],
	zip_safe=False,
)
