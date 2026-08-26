# SPDX-License-Identifier: MIT
#
# RPM spec for the scotch/PT-Scotch mesh decomposition libraries, built
# for the HPC system role and installed under /opt/hpc.  See
# docs/openfoam-build.md for the full OpenFOAM-13 build process.
#
# The source tarball is the scotch GitLab archive.  It is passed to
# rpmbuild via --define "srcdir <path>" so that the Ansible role can
# build from a checksum-verified download rather than a bundled Source0.

%define hpc_prefix /opt/hpc

Name:           hpc-scotch
Version:        6.0.9
Release:        1%{?dist}
Summary:        Scotch and PT-Scotch graph and mesh decomposition libraries (HPC build)

License:        CeCILL-C
URL:            https://gitlab.inria.fr/scotch/scotch

# Build from a pre-extracted source tree supplied by the caller.
# %%{srcdir} must point at the extracted scotch-v6.0.9 source root.
%global srcdir %{?srcdir}%{!?srcdir:%{_sourcedir}/scotch-v%{version}}

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  flex
BuildRequires:  bison
BuildRequires:  zlib-devel

# PT-Scotch links against the openmpi-5.0.8-cuda MPI provided by the role.
# That MPI is a source install under /opt (not an RPM), so nothing provides
# libmpi.so.40 to the depsolver; it is found at run time via the MPI
# environment module's LD_LIBRARY_PATH. Drop the auto-generated Requires on
# the OpenMPI runtime libraries so the package installs cleanly.
%global __requires_exclude ^libmpi\\.so.*$

%description
Scotch is a software package for graph and mesh/hypergraph partitioning,
graph clustering, and sparse matrix ordering.  This package provides the
serial (libscotch) and MPI-parallel (libptscotch) libraries, their headers,
and the associated command-line tools, installed under %{hpc_prefix} for use
by HPC applications such as OpenFOAM.

%package devel
Summary:        Development files for hpc-scotch
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
Header files for developing against the HPC build of scotch and PT-Scotch.
The shared libraries live in the main hpc-scotch package.

%prep
# Copy the caller-supplied source tree into the build directory.
rm -rf %{_builddir}/%{name}-%{version}
cp -a "%{srcdir}" %{_builddir}/%{name}-%{version}

%build
cd %{_builddir}/%{name}-%{version}/src

# scotch selects its build configuration by symlinking Make.inc/Makefile.inc.
# The x86-64 shared-library template builds thread-safe .so libraries and
# already sets CCS=gcc, CCP=mpicc and the correct CFLAGS/LDFLAGS (gzip
# compression, pthreads, fixed random seed, SCOTCH_RENAME to avoid symbol
# clashes with metis, 64-bit indices). It expects mpicc on PATH, which the
# role provides via the openmpi-5.0.8-cuda environment module.
ln -sf Make.inc/Makefile.inc.x86-64_pc_linux2.shlib Makefile.inc

# Build the shared serial (scotch) and parallel (ptscotch) libraries plus
# their command-line tools.
#
# The template sets CCD=gcc (the compiler for the "dummysizes" helpers that
# generate the public headers). ptdummysizes pulls in mpi.h via dgraph.h, so
# it must be built with mpicc; plain gcc cannot find mpi.h because our
# OpenMPI lives under /opt and is only discoverable through the mpicc
# wrapper. Override CCD=mpicc so the parallel dummysizes step compiles. mpicc
# also works fine for the serial dummysizes step.
make -j%{?_smp_build_ncpus}%{!?_smp_build_ncpus:1} \
    CCD=mpicc \
    scotch ptscotch

%install
cd %{_builddir}/%{name}-%{version}/src

# scotch's "make install" honours a prefix= override.
make install prefix=%{buildroot}%{hpc_prefix}

# The x86-64 shlib template installs .so files under lib/; ensure the
# runtime linker cache can find them by shipping an ld.so.conf.d fragment.
mkdir -p %{buildroot}%{_sysconfdir}/ld.so.conf.d
echo "%{hpc_prefix}/lib" > %{buildroot}%{_sysconfdir}/ld.so.conf.d/hpc-scotch.conf

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig

%files
%{hpc_prefix}/bin/*
%{hpc_prefix}/lib/*.so*
%{hpc_prefix}/share/man/man1/*
%config(noreplace) %{_sysconfdir}/ld.so.conf.d/hpc-scotch.conf

%files devel
%{hpc_prefix}/include/*

%changelog
* Tue Aug 18 2026 HPC System Role <hpc@example.com> - 6.0.9-1
- Initial hpc-scotch package for the OpenFOAM-13 build.
