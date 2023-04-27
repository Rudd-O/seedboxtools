# See https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/#_example_spec_file

%define debug_package %{nil}

%define mybuildnumber %{?build_number}%{?!build_number:1}

Name:           seedboxtools
Version:        1.6.7
Release:        %{mybuildnumber}%{?dist}
Summary:        A tool to automate downloading finished torrents from a seedbox

License:        LGPLv2.1
URL:            https://github.com/Rudd-O/%{name}
Source:         %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  systemd-rpm-macros
Requires:       python3-requests
Requires:       python3-iniparse

%description
The seedbox tools will help you download all those Linux ISOs that you
downloaded on your remote seedbox (whether it's a Transmission Web, or
TorrentFlux-b4rt, or a PulsedMedia seedbox) 100% automatically, without any
manual intervention on your part.

%prep
%autosetup -p1 -n %{name}-%{version}

%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install

%pyproject_save_files %{name}

%post
%systemd_post 'leechtorrents@.service'

%preun
%systemd_preun 'leechtorrents@*.service'

%postun
%systemd_postun_with_restart 'leechtorrents@*.service'


%files -f %{pyproject_files}
%doc README.md BUGS
%{_bindir}/configleecher
%{_bindir}/leechtorrents
%{_bindir}/uploadtorrents
%{_unitdir}/leechtorrents@.service
%{_datadir}/applications/uploadtorrents.desktop
%{_prefix}/etc/default/leechtorrents

%changelog
* Wed Jul 27 2022 Manuel Amador <rudd-o@rudd-o.com> 1.5.0-1
- First spec-based RPM packaging release

