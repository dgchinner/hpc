# SPDX-License-Identifier: MIT
#
# RPM spec for OpenFOAM-13 (Foundation, openfoam.org), built for the HPC
# system role and installed under /opt/hpc/OpenFOAM-13.  See
# docs/openfoam-build.md for the full OpenFOAM-13 build process.
#
# The OpenFOAM and ThirdParty source trees are passed in via
# --define "srcdir <path>" and --define "tpsrcdir <path>" (checksum-verified
# downloads), not bundled Source0/Source1.
#
# OpenFOAM has no "make install": it builds in-tree and the built tree IS the
# installation. etc/bashrc auto-detects its own location via $BASH_SOURCE, so
# the tree is relocatable -- it is built in %%_builddir and copied into the
# buildroot at /opt/hpc/OpenFOAM-13, and resolves that path at run time.
#
# The build links against the HPC partitioning libraries under /opt/hpc
# (hpc-scotch, hpc-metis, hpc-parmetis, hpc-zoltan) and the openmpi-5.0.8-cuda
# MPI. OpenFOAM's *_TYPE=system config points at /usr by default, so the build
# overrides *_ARCH_PATH to /opt/hpc. mpicc must be on PATH (from the MPI module
# loaded by the role) for WM_MPLIB=SYSTEMOPENMPI to locate the MPI runtime.

%define hpc_prefix /opt/hpc
%define foam_dir %{hpc_prefix}/OpenFOAM-13
%define tp_dir %{hpc_prefix}/ThirdParty-13
%define wm_options linux64GccDPInt32Opt

# OpenFOAM's platforms tree contains many prebuilt .so libraries that link
# each other, plus the OpenMPI runtime (a source install under /opt, not an
# RPM) and the /opt/hpc partitioning libraries. Filter the auto-generated
# Requires that nothing can/should satisfy:
#  - the OpenMPI and /opt/hpc partitioning libraries (resolved at run time via
#    the module environment);
#  - /usr/bin/csh and /usr/bin/tcsh, added because OpenFOAM ships csh config
#    files (etc/cshrc, etc/config.csh/*) that RPM classifies as csh scripts.
#    Users drive OpenFOAM via the (bash/lua) lmod module, not etc/cshrc, so we
#    do not force a csh shell onto every node; the csh files are still shipped
#    for anyone who installs tcsh themselves.
# OpenFOAM's own libraries are BOTH provided and required within this package,
# so they must be left in the auto-Provides (do NOT add a __provides_exclude)
# or the intra-package Requires on libOpenFOAM.so, libfiniteVolume.so, etc.
# become unsatisfiable at install time.
%global __requires_exclude ^(libmpi\\.so.*|libscotch.*|libptscotch.*|libmetis.*|libparmetis.*|libzoltan.*|/usr/bin/t?csh)$

# The build is already optimised by wmake; skip rpm's own post-build steps that
# do not apply to an in-tree OpenFOAM install.
%global debug_package %{nil}
%global __brp_check_rpaths %{nil}

# Run the scriptlets under bash: OpenFOAM's etc/bashrc requires bash (it uses
# $BASH_SOURCE to locate itself) and its config scripts are not sh-compatible.
%global _build_shell /bin/bash

Name:           hpc-openfoam-13
Version:        13
Release:        1%{?dist}
Summary:        OpenFOAM-13 CFD toolbox (HPC build)

License:        GPL-3.0-or-later
URL:            https://openfoam.org

%global srcdir %{?srcdir}%{!?srcdir:%{_sourcedir}/OpenFOAM-13}
%global tpsrcdir %{?tpsrcdir}%{!?tpsrcdir:%{_sourcedir}/ThirdParty-13}

BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make
BuildRequires:  flex
BuildRequires:  bison
BuildRequires:  zlib-devel
BuildRequires:  bzip2-devel
# Partitioning libraries and headers, from our own RPMs.
BuildRequires:  hpc-scotch-devel
BuildRequires:  hpc-metis-devel
BuildRequires:  hpc-parmetis-devel
BuildRequires:  hpc-zoltan

# Runtime needs the partitioning libraries present.
Requires:       hpc-scotch
Requires:       hpc-metis
Requires:       hpc-parmetis
Requires:       hpc-zoltan

%description
OpenFOAM is a free, open-source CFD (computational fluid dynamics) toolbox
from the OpenFOAM Foundation (openfoam.org). This package provides the
OpenFOAM-13 runtime -- the compiled solvers, utilities and libraries plus the
tutorials -- installed under %{foam_dir}, built against the openmpi-5.0.8-cuda
MPI and the HPC partitioning libraries (scotch, METIS, ParMETIS, Zoltan) under
%{hpc_prefix}. Load the openfoam/openfoam-13 environment module to use it.

%package devel
Summary:        OpenFOAM-13 source tree and development files
Requires:       %{name}%{?_isa} = %{version}-%{release}

%description devel
The OpenFOAM-13 source tree (src, applications, wmake) for building custom
solvers and utilities against the HPC OpenFOAM-13 install.

%prep
# Copy the caller-supplied source trees into the build directory. OpenFOAM
# expects ThirdParty-13 to sit next to OpenFOAM-13 under the same parent.
rm -rf %{_builddir}/OpenFOAM-13 %{_builddir}/ThirdParty-13
cp -a "%{srcdir}" %{_builddir}/OpenFOAM-13
cp -a "%{tpsrcdir}" %{_builddir}/ThirdParty-13

%build
cd %{_builddir}/OpenFOAM-13

# --- Point OpenFOAM at the HPC partitioning libraries under /opt/hpc ---
#
# etc/bashrc hard-codes the default decomposition-library selection
# (SCOTCH_TYPE=ThirdParty, METIS_TYPE=none, PARMETIS_TYPE=none,
# ZOLTAN_TYPE=ThirdParty) AFTER any pre-exported values, so exporting
# SCOTCH_TYPE=system beforehand does not stick. The intended override hook is a
# prefs.sh, which bashrc sources via foamEtcFile; foamEtcFile searches
# $WM_PROJECT_DIR/etc/prefs.sh (among others). So write the selection there --
# it takes effect during this build (before Allwmake), ships in the runtime
# package (etc/ is part of it), and applies at run time and for rebuilds.
#
# Likewise etc/config.sh/{scotch,metis,parMetis,zoltan} hard-code
# <LIB>_ARCH_PATH=/usr in their system) branch. Rather than sed a literal
# /opt/hpc, make the system path a controllable variable, FOAM_SYSTEM_ARCH_PATH
# (defaulting to /usr when unset so upstream behaviour is preserved), and set it
# in the same prefs.sh.
cat > etc/prefs.sh << 'EOF'
# HPC system role: use the partitioning libraries installed under /opt/hpc
# instead of building them from ThirdParty or looking under /usr. Written into
# the OpenFOAM tree so it is picked up by etc/bashrc via foamEtcFile, at build
# time and whenever a user sources etc/bashrc to rebuild a solver.
export SCOTCH_TYPE=system
export METIS_TYPE=system
export PARMETIS_TYPE=system
export ZOLTAN_TYPE=system
export FOAM_SYSTEM_ARCH_PATH=/opt/hpc
# So the compiler finds the /opt/hpc headers and libraries (at build time this
# also satisfies ThirdParty's checkSystemLibrary probes).
export CPATH=/opt/hpc/include${CPATH:+:$CPATH}
export LIBRARY_PATH=/opt/hpc/lib${LIBRARY_PATH:+:$LIBRARY_PATH}
EOF

sed -i 's#^\( *export [A-Z]*_ARCH_PATH=\)/usr *$#\1${FOAM_SYSTEM_ARCH_PATH:-/usr}#' \
    etc/config.sh/scotch \
    etc/config.sh/metis \
    etc/config.sh/parMetis \
    etc/config.sh/zoltan

# ThirdParty's Allwmake gates each system library through checkSystemLibrary,
# which link-tests with a bare -l<lib> and preprocesses <hdr>.h using the
# compiler's default search paths. Put /opt/hpc on those paths so the checks
# (and the OpenFOAM compile's fallback) find our libraries and headers.
export CPATH=%{hpc_prefix}/include${CPATH:+:$CPATH}
export LIBRARY_PATH=%{hpc_prefix}/lib${LIBRARY_PATH:+:$LIBRARY_PATH}
export LD_LIBRARY_PATH=%{hpc_prefix}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

# WM_MPLIB=SYSTEMOPENMPI is the default and locates MPI from mpicc on PATH.
# The decomposition-library selection comes from etc/prefs.sh (above), sourced
# by etc/bashrc.

# Source the OpenFOAM environment and build. etc/bashrc and OpenFOAM's config
# scripts and Allwmake legitimately return non-zero in benign places (e.g.
# probing for optional aliases/functions), so errexit and nounset -- which rpm
# turns on for %build -- must be disabled around them, or the first such return
# aborts the build. Allwmake's own exit status is checked explicitly below so a
# genuine build failure still fails the RPM.
set +eu
source etc/bashrc

# In-tree parallel build. wmake handles -j internally.
./Allwmake -j %{?_smp_build_ncpus:%{_smp_build_ncpus}}%{!?_smp_build_ncpus:1}
Allwmake_status=$?
set -eu
[ "$Allwmake_status" -eq 0 ] || {
    echo "OpenFOAM Allwmake failed with status $Allwmake_status" >&2
    exit "$Allwmake_status"
}

%install
# The built tree IS the install; copy it (and the ThirdParty tree, which is
# empty of builds under our system-library configuration but is the expected
# adjacent directory) into the buildroot under /opt/hpc.
mkdir -p %{buildroot}%{hpc_prefix}
cp -a %{_builddir}/OpenFOAM-13 %{buildroot}%{foam_dir}
cp -a %{_builddir}/ThirdParty-13 %{buildroot}%{tp_dir}

# cp -a preserved whatever permissions the in-tree wmake build produced, which
# can include owner-only directories/files. Normalise the installed tree so it
# is world-readable and directories/executables are traversable/runnable by
# ordinary users (a+rX adds execute only where it already exists, i.e. dirs and
# programs), while keeping owner write.
chmod -R u+rwX,go+rX-w %{buildroot}%{foam_dir} %{buildroot}%{tp_dir}

# Drop VCS metadata carried in the source tarballs so it is not packaged
# (it would otherwise be an unpackaged-files error).
find %{buildroot}%{foam_dir} %{buildroot}%{tp_dir} \
    -name .gitignore -o -name .gitattributes | xargs -r rm -f

# The decomposition-library selection lives in etc/prefs.sh (written in %build
# and part of the copied tree), so no separate site prefs.sh is needed.

%files
# Runtime: the built platforms tree, runtime config and scripts, tutorials and
# docs. The development-only directories are carried by the -devel package.
%dir %{foam_dir}
%{foam_dir}/platforms
%{foam_dir}/etc
%{foam_dir}/bin
%{foam_dir}/tutorials
%{foam_dir}/doc
%{foam_dir}/COPYING
%{foam_dir}/README.org
# ThirdParty tree (present, adjacent; no builds under system-library config).
%{tp_dir}

%files devel
%{foam_dir}/src
%{foam_dir}/applications
%{foam_dir}/wmake
%{foam_dir}/test
%{foam_dir}/Allwmake

%changelog
* Tue Aug 25 2026 HPC System Role <hpc@example.com> - 13-1
- Initial hpc-openfoam-13 package for the HPC system role.
