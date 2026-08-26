# SPDX-License-Identifier: MIT
#
# RPM spec for the Zoltan parallel partitioning toolkit, built for the HPC
# system role and installed under /opt/hpc.  See docs/openfoam-build.md for
# the full OpenFOAM-13 build process.
#
# The source tree is passed in via --define "srcdir <path>" (a checksum-
# verified download), not a bundled Source0.
#
# Zoltan 3.90 uses GNU autotools and can only build a STATIC library
# (libzoltan.a) via this path -- there is no shared-library option. Because
# the artifact is a static archive it has no runtime .so dependencies, so no
# libmpi.so Requires filtering and no ldconfig handling are needed. The MPI
# dependency is resolved when a consumer (OpenFOAM) links libzoltan.a.

%define hpc_prefix /opt/hpc

Name:           hpc-zoltan
Version:        3.90
Release:        1%{?dist}
Summary:        Zoltan parallel partitioning toolkit (HPC build, static)

License:        BSD-3-Clause
URL:            https://github.com/sandialabs/Zoltan

# %%{srcdir} must point at the extracted Zoltan 3.90 source root (the
# directory containing the pre-generated configure script).
%global srcdir %{?srcdir}%{!?srcdir:%{_sourcedir}/zoltan-%{version}}

BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make
# perl is required by configure's --with-gnumake / export-makefile generation.
BuildRequires:  perl

%description
Zoltan is a toolkit of parallel services for dynamic, unstructured, and
adaptive simulations, including dynamic load balancing and graph/hypergraph
and geometric partitioning.  This package provides the static library and
headers, installed under %{hpc_prefix}, for use by HPC applications such as
OpenFOAM.  It is built against the openmpi-5.0.8-cuda MPI provided by the role.

%prep
# Copy the caller-supplied source tree into the build directory.
rm -rf %{_builddir}/%{name}-%{version}
cp -a "%{srcdir}" %{_builddir}/%{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version}

# Zoltan mandates an out-of-tree (VPATH) build; in-source configure is
# refused. A pre-generated configure ships in the tarball (no autoreconf).
# MPI is enabled and mpicc/mpicxx are taken from the MPI environment module
# loaded for the build; no MPI paths are hard-coded. No third-party
# partitioners and no Fortran interface are needed for OpenFOAM.
#
# Build the objects position-independent. Zoltan only produces a static archive
# (libzoltan.a), and consumers such as OpenFOAM link it into shared objects
# (libzoltanDecomp.so); without -fPIC the archive's objects carry absolute
# relocations and the .so link fails with "recompile with -fPIC".
#
# The -fPIC must reach the actual C object compilation, which automake drives
# from CFLAGS. Zoltan's --with-ccflags populates a separate CCFLAGS variable
# that is NOT applied to the .c -> .o rule (the compile line shows only -g -O2),
# so pass CFLAGS/CXXFLAGS directly to configure instead. -g -O2 is added back
# because setting CFLAGS overrides automake's default.
mkdir -p build
cd build
../configure \
    --prefix=%{hpc_prefix} \
    --libdir=%{hpc_prefix}/lib \
    --enable-mpi \
    --with-gnumake \
    --disable-examples \
    --disable-tests \
    CC=mpicc CXX=mpicxx \
    CFLAGS="-fPIC -g -O2" CXXFLAGS="-fPIC -g -O2"
make %{?_smp_build_ncpus:-j%{_smp_build_ncpus}}

%install
cd %{_builddir}/%{name}-%{version}/build
make install DESTDIR=%{buildroot}

# The build is a single static library plus headers; there is no runtime
# shared object, so this is packaged as one -devel-style package.
%files
%{hpc_prefix}/lib/libzoltan.a
%{hpc_prefix}/include/*.h
%{hpc_prefix}/include/Makefile.export.zoltan
%{hpc_prefix}/include/Makefile.export.zoltan.macros

%changelog
* Tue Aug 18 2026 HPC System Role <hpc@example.com> - 3.90-1
- Initial hpc-zoltan package for the OpenFOAM-13 build.
