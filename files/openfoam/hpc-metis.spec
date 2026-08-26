# SPDX-License-Identifier: MIT
#
# RPM spec for the METIS graph/mesh partitioning library, built for the HPC
# system role and installed under /opt/hpc.  See docs/openfoam-build.md for
# the full OpenFOAM-13 build process.
#
# The source tree is passed in via --define "srcdir <path>" (a checksum-
# verified download), not a bundled Source0.
#
# METIS 5.2.1 does not bundle GKlib and cannot build without it, so hpc-gklib
# must be installed first; the build is pointed at it with gklib_path=/opt/hpc.

%define hpc_prefix /opt/hpc

Name:           hpc-metis
Version:        5.2.1
Release:        1%{?dist}
Summary:        METIS serial graph and mesh partitioning library (HPC build)

License:        Apache-2.0
URL:            https://github.com/KarypisLab/METIS

# %%{srcdir} must point at the extracted METIS 5.2.1 source root (the
# directory containing the top-level Makefile and conf/gkbuild.cmake).
%global srcdir %{?srcdir}%{!?srcdir:%{_sourcedir}/metis-%{version}}

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  cmake
# GKlib headers and libGKlib.a must be present under /opt/hpc at build time.
BuildRequires:  hpc-gklib

%description
METIS is a set of serial programs for partitioning graphs, partitioning finite
element meshes, and producing fill-reducing orderings for sparse matrices.
This package provides the shared library (libmetis) and the command-line tools,
installed under %{hpc_prefix}, for use by HPC applications such as OpenFOAM.
METIS is built with 32-bit indices and reals, matching OpenFOAM's expectations.

%package devel
Summary:        Development files for hpc-metis
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
The metis.h header for developing against the HPC build of METIS. The shared
library lives in the main hpc-metis package.

%prep
# Copy the caller-supplied source tree into the build directory.
rm -rf %{_builddir}/%{name}-%{version}
cp -a "%{srcdir}" %{_builddir}/%{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version}

# conf/gkbuild.cmake forces -march=native and -Werror. -march=native produces
# a non-portable binary (this RPM is built once and installed on other
# machines), and -Werror breaks the build on newer GCC. Neutralise both
# before configuring: use a conservative baseline arch and drop -Werror.
sed -i \
    -e 's/-march=native/-march=x86-64-v2 -mtune=generic/g' \
    -e 's/-Werror//g' \
    conf/gkbuild.cmake

# METIS's libmetis/CMakeLists.txt builds the metis library target but never
# links its dependencies into it (only the command-line programs link
# "metis GKlib m"). For a shared libmetis.so this leaves the GKlib symbols
# (gk_*) and the libm math symbols (sqrt, pow, log, ...) undefined, so a
# downstream consumer that links only -lmetis (e.g. OpenFOAM) fails with
# "undefined reference". Link GKlib and libm into the metis target so the
# shared library is self-contained; GKlib is the static, position-independent
# libGKlib.a from hpc-gklib on the link path, so its objects are absorbed.
echo 'target_link_libraries(metis GKlib m)' >> libmetis/CMakeLists.txt

# METIS is a CMake project behind a Makefile wrapper. "make config" runs cmake
# into build/. shared=1 builds libmetis.so; cc=gcc (METIS is serial, no MPI);
# gklib_path points cmake at the installed hpc-gklib under /opt/hpc. The
# default 32-bit IDXTYPEWIDTH/REALTYPEWIDTH are kept (OpenFOAM expects them).
make config shared=1 cc=gcc prefix=%{hpc_prefix} gklib_path=%{hpc_prefix}
make %{?_smp_build_ncpus:-j%{_smp_build_ncpus}}

%install
cd %{_builddir}/%{name}-%{version}

# The Makefile "install" target proxies to the CMake-generated install, which
# honours DESTDIR; CMAKE_INSTALL_PREFIX (/opt/hpc) was baked in at config time.
make install prefix=%{hpc_prefix} DESTDIR=%{buildroot}

# Ensure the runtime linker can find libmetis.so under /opt/hpc/lib.
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{hpc_prefix}/lib" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/hpc-metis.conf

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%{hpc_prefix}/bin/gpmetis
%{hpc_prefix}/bin/ndmetis
%{hpc_prefix}/bin/mpmetis
%{hpc_prefix}/bin/m2gmetis
%{hpc_prefix}/bin/graphchk
%{hpc_prefix}/bin/cmpfillin
%{hpc_prefix}/lib/libmetis.so
%config(noreplace) %{_sysconfdir}/ld.so.conf.d/hpc-metis.conf

%files devel
%{hpc_prefix}/include/metis.h

%changelog
* Tue Aug 18 2026 HPC System Role <hpc@example.com> - 5.2.1-1
- Initial hpc-metis package for the OpenFOAM-13 build.
