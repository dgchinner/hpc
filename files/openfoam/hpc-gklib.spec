# SPDX-License-Identifier: MIT
#
# RPM spec for GKlib, the support library required to build METIS/ParMETIS.
# Built for the HPC system role and installed under /opt/hpc.  See
# docs/openfoam-build.md for the full OpenFOAM-13 build process.
#
# The source tree is passed in via --define "srcdir <path>" (a checksum-
# verified download), not a bundled Source0.
#
# Versioning: GKlib has no upstream version releases -- it is tracked only by
# git commit. This package pins the commit that METIS 5.2.1 was released
# against (KarypisLab/GKlib 8bd6bad750b2b0d90800c632cf18e8ee93ad72d7,
# 2023-03-26, the last GKlib commit before the METIS 5.2.1 release), and
# takes METIS's version, 5.2.1, as its own so the coupling is obvious. The
# newer GKlib master branch has a different source/install layout that METIS
# 5.2.1 does not build against, so the commit must stay pinned.

%define hpc_prefix /opt/hpc

Name:           hpc-gklib
Version:        5.2.1
Release:        1%{?dist}
Summary:        GKlib support library for the HPC build of METIS/ParMETIS

License:        Apache-2.0
URL:            https://github.com/KarypisLab/GKlib

# %%{srcdir} must point at the extracted GKlib source root (the commit noted
# above), i.e. the directory containing CMakeLists.txt and GKlibSystem.cmake.
%global srcdir %{?srcdir}%{!?srcdir:%{_sourcedir}/GKlib}

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  cmake

%description
GKlib is a library of helper routines (memory, I/O, sorting, hashing, random
number generation, etc.) developed by the Karypis Lab and required to build
METIS and ParMETIS.  This package provides the static library, headers, and
the csrcnv CSR-format conversion tool, installed under %{hpc_prefix}, so the
HPC builds of METIS and ParMETIS can link against it.

%prep
# Copy the caller-supplied source tree into the build directory.
rm -rf %{_builddir}/%{name}-%{version}
cp -a "%{srcdir}" %{_builddir}/%{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version}

# GKlibSystem.cmake forces -march=native and -Werror. -march=native produces
# a non-portable binary (this RPM is built once and installed on other
# machines), and -Werror breaks the build on newer GCC. Neutralise both
# before configuring: use a conservative baseline arch and drop -Werror.
sed -i \
    -e 's/-march=native/-march=x86-64-v2 -mtune=generic/g' \
    -e 's/-Werror//g' \
    GKlibSystem.cmake

# GKlib is a CMake project behind a Makefile wrapper. "make config" runs
# cmake into a build subdirectory; a plain build produces the static
# libGKlib.a (BUILD_SHARED_LIBS defaults OFF), which is what METIS links.
make config prefix=%{hpc_prefix} cc=gcc
make %{?_smp_build_ncpus:-j%{_smp_build_ncpus}}

%install
cd %{_builddir}/%{name}-%{version}

# The CMake-generated install target honours DESTDIR; CMAKE_INSTALL_PREFIX
# (/opt/hpc) was baked in at config time.
make install DESTDIR=%{buildroot}

%files
%{hpc_prefix}/bin/csrcnv
%{hpc_prefix}/lib/libGKlib.a
%{hpc_prefix}/include/GKlib.h
%{hpc_prefix}/include/gk_*.h
%{hpc_prefix}/include/gkregex.h

%changelog
* Tue Aug 18 2026 HPC System Role <hpc@example.com> - 5.2.1-1
- Initial hpc-gklib package (METIS-5.2.1-era commit 8bd6bad) for the
  OpenFOAM-13 build.
