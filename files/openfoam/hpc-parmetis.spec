# SPDX-License-Identifier: MIT
#
# RPM spec for the ParMETIS parallel graph partitioning library, built for
# the HPC system role and installed under /opt/hpc.  See docs/openfoam-build.md
# for the full OpenFOAM-13 build process.
#
# The source tree is passed in via --define "srcdir <path>" (a checksum-
# verified download), not a bundled Source0.
#
# ParMETIS bundles its own copy of METIS 5.1.0 and GKlib and builds against
# them internally. The bundled METIS is NOT installed (its CMake install is
# guarded off), so there is no file collision with the separate hpc-metis
# package. parmetis.h #includes <metis.h>, so hpc-metis (which provides
# /opt/hpc/include/metis.h) is required.

%define hpc_prefix /opt/hpc

Name:           hpc-parmetis
Version:        4.0.3
Release:        1%{?dist}
Summary:        ParMETIS parallel graph partitioning library (HPC build)

License:        Apache-2.0
URL:            https://github.com/KarypisLab/ParMETIS

# %%{srcdir} must point at the extracted ParMETIS 4.0.3 source root (the
# directory containing the top-level CMakeLists.txt, metis/ and libparmetis/).
%global srcdir %{?srcdir}%{!?srcdir:%{_sourcedir}/parmetis-%{version}}

# ParMETIS links the OpenMPI runtime, which is a source install under /opt
# (not an RPM). Nothing provides libmpi.so.40 to the depsolver; it is found at
# run time via the MPI environment module's LD_LIBRARY_PATH. Drop the
# auto-generated Requires on the OpenMPI runtime libraries.
%global __requires_exclude ^libmpi\\.so.*$

BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make
BuildRequires:  cmake
# metis.h (from hpc-metis) is needed to compile against parmetis.h.
BuildRequires:  hpc-metis

# parmetis.h #includes <metis.h>, provided by hpc-metis at /opt/hpc/include.
Requires:       hpc-metis

%description
ParMETIS is an MPI-based parallel library that extends the functionality of
METIS to distributed graph and mesh partitioning and fill-reducing matrix
ordering.  This package provides the shared library (libparmetis) and its
tools, installed under %{hpc_prefix}, for use by HPC applications such as
OpenFOAM. It is built against the openmpi-5.0.8-cuda MPI provided by the role.

%package devel
Summary:        Development files for hpc-parmetis
Requires:       %{name}%{?_isa} = %{version}-%{release}
Requires:       hpc-metis-devel

%description devel
The parmetis.h header for developing against the HPC build of ParMETIS. The
shared library lives in the main hpc-parmetis package.

%prep
# Copy the caller-supplied source tree into the build directory.
rm -rf %{_builddir}/%{name}-%{version}
cp -a "%{srcdir}" %{_builddir}/%{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version}

# Configure with cmake directly rather than via the Makefile wrapper, so the
# CMake policy version can be forced: ParMETIS 4.0.3 declares
# cmake_minimum_required(VERSION 2.8), which modern cmake rejects.
#
# GKLIB_PATH/METIS_PATH point at the bundled copies (absolute paths, matching
# the wrapper's $(abspath ...)). SHARED=1 builds libparmetis.so; PIC is forced
# so the static bundled libmetis links cleanly into the shared library.
# mpicc/mpicxx come from the MPI environment module loaded for the build; no
# MPI paths are hard-coded.
mkdir -p builddir
cd builddir
cmake .. \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DCMAKE_INSTALL_PREFIX=%{hpc_prefix} \
    -DCMAKE_C_COMPILER=mpicc \
    -DCMAKE_CXX_COMPILER=mpicxx \
    -DGKLIB_PATH=%{_builddir}/%{name}-%{version}/metis/GKlib \
    -DMETIS_PATH=%{_builddir}/%{name}-%{version}/metis \
    -DSHARED=1 \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON
make %{?_smp_build_ncpus:-j%{_smp_build_ncpus}}

%install
cd %{_builddir}/%{name}-%{version}/builddir
make install DESTDIR=%{buildroot}

# Defensive: the bundled METIS/GKlib install rules are guarded off, so nothing
# from them should reach the buildroot. Remove any such files anyway so this
# package can never collide with hpc-metis / hpc-gklib, regardless of upstream
# or CMake changes.
rm -f %{buildroot}%{hpc_prefix}/lib/libmetis.* \
      %{buildroot}%{hpc_prefix}/lib/libGKlib.* \
      %{buildroot}%{hpc_prefix}/include/metis.h \
      %{buildroot}%{hpc_prefix}/include/gk_*.h \
      %{buildroot}%{hpc_prefix}/include/GKlib.h \
      %{buildroot}%{hpc_prefix}/include/gkregex.h \
      %{buildroot}%{hpc_prefix}/bin/gpmetis \
      %{buildroot}%{hpc_prefix}/bin/ndmetis \
      %{buildroot}%{hpc_prefix}/bin/mpmetis \
      %{buildroot}%{hpc_prefix}/bin/m2gmetis \
      %{buildroot}%{hpc_prefix}/bin/graphchk \
      %{buildroot}%{hpc_prefix}/bin/cmpfillin

# Ensure the runtime linker can find libparmetis.so under /opt/hpc/lib.
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{hpc_prefix}/lib" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/hpc-parmetis.conf

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%{hpc_prefix}/bin/parmetis
%{hpc_prefix}/bin/ptest
%{hpc_prefix}/bin/mtest
%{hpc_prefix}/bin/pometis
%{hpc_prefix}/lib/libparmetis.so
%config(noreplace) %{_sysconfdir}/ld.so.conf.d/hpc-parmetis.conf

%files devel
%{hpc_prefix}/include/parmetis.h

%changelog
* Tue Aug 18 2026 HPC System Role <hpc@example.com> - 4.0.3-1
- Initial hpc-parmetis package for the OpenFOAM-13 build.
