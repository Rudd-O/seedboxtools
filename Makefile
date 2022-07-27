ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: clean dist rpm srpm

clean:
	cd $(ROOT_DIR) && find -name '*~' -print0 | xargs -0r rm -fv && rm -fr build dist *.tar.gz *.rpm

dist: clean
	python -m build -s

srpm: dist
	@which rpmbuild || { echo 'rpmbuild is not available.  Please install the rpm-build package with the command `dnf install rpm-build` to continue, then rerun this step.' ; exit 1 ; }
	cd $(ROOT_DIR) || exit $$? ; rpmbuild --define "_srcrpmdir ." --define "_sourcedir dist" -bs *spec

rpm: srpm
	@which rpmbuild || { echo 'rpmbuild is not available.  Please install the rpm-build package with the command `dnf install rpm-build` to continue, then rerun this step.' ; exit 1 ; }
	cd $(ROOT_DIR) || exit $$? ; rpmbuild --define "_srcrpmdir ." --define "_rpmdir dist" --rebuild *.src.rpm
	cd $(ROOT_DIR) ; mv -f dist/*/* . && rm -rf dist/*/*
