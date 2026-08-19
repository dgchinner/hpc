# OpenFOAM-13 Build Process

## Overview

The HPC system role provides OpenFOAM-13 (Foundation, openfoam.org) as a
pre-built application for Slurm cluster users. OpenFOAM is a widely-used
open-source CFD toolbox that requires several third-party libraries for mesh
decomposition and renumbering. RHEL 9.6 does not ship most of these libraries,
so they are all built from source as RPM packages, and then OpenFOAM is built
on top of them. All builds use the openmpi-5.0.8-cuda MPI environment provided
by the HPC system role.

## Dependencies

### Libraries built from source (RHEL 9.6 does not provide these)

| Library | Version | Purpose | MPI required | Build system |
|---------|---------|---------|--------------|--------------|
| scotch | 6.0.9 | Mesh decomposition (serial) | No | Make |
| PT-Scotch | 6.0.9 | Mesh decomposition (parallel) | Yes | Make |
| METIS | 5.2.1 | Graph partitioning | No | CMake |
| ParMETIS | 4.0.3 | Parallel graph partitioning | Yes | CMake |
| Zoltan | 3.90 | Partitioning toolkit (hypergraph, geometric) | Yes | Autotools |

### System libraries from RHEL 9.6 AppStream/BaseOS

| Package | Version | Purpose |
|---------|---------|---------|
| GCC | 11.5 | System compiler |
| flex | 2.6.4 | Lexer generator (OpenFOAM STL parser) |
| cmake | 3.26.5 | Build system for METIS/ParMETIS |
| boost-devel | 1.75.0 | SloanRenumber bandwidth-reducing reordering |
| zlib-devel | — | Compression support |
| bzip2-devel | — | Compression support |

### Not required

- **CGAL** — OpenFOAM-13 Foundation does not use CGAL
- **FFTW** — OpenFOAM-13 Foundation does not use FFTW

## Install Layout

All libraries install into a shared FHS-like prefix under `/opt/hpc/`:

```
/opt/hpc/bin/        — executables
/opt/hpc/lib/        — shared libraries
/opt/hpc/lib64/      — 64-bit shared libraries (if needed)
/opt/hpc/include/    — header files
/opt/hpc/share/      — architecture-independent data
/opt/hpc/share/man/  — man pages
```

This mirrors how system packages install under `/usr/` and allows multiple HPC
applications to share the same library installations.

OpenFOAM itself installs to `/opt/hpc/OpenFOAM-13/` as it has its own
directory structure that does not follow FHS conventions.

## RPM Packages

Each library is packaged as a separate RPM for independent versioning.
All RPMs use the `hpc-` prefix.

| RPM name | Contents |
|----------|----------|
| `hpc-scotch` | libscotch.so, libptscotch.so, headers, scotch tools |
| `hpc-metis` | libmetis.so, headers, gpmetis/ndmetis/mpmetis tools |
| `hpc-parmetis` | libparmetis.so, headers |
| `hpc-zoltan` | libzoltan.a, headers |
| `hpc-openfoam-13` | OpenFOAM-13 complete installation |

## Source Packages

| Package | URL | SHA256 |
|---------|-----|--------|
| scotch 6.0.9 | https://gitlab.inria.fr/scotch/scotch/-/archive/v6.0.9/scotch-v6.0.9.tar.gz | `b9bc86c50b65781eb416663e938d57555373c2517ea8b9acf680fd3acde0cb0c` |
| METIS 5.2.1 | https://github.com/KarypisLab/METIS/archive/refs/tags/v5.2.1.tar.gz | `1a4665b2cd07edc2f734e30d7460afb19c1217c2547c2ac7bf6e1848d50aff7a` |
| ParMETIS 4.0.3 | https://github.com/KarypisLab/ParMETIS/archive/refs/tags/v4.0.3.tar.gz | `d5558cd419c8d46bdc958064cb97f963d1ea793866414c025906ec15033512ed` |
| Zoltan 3.90 | https://github.com/sandialabs/Zoltan/archive/refs/tags/v3.90.tar.gz | `30a470af4d97cf03aa5434eb0a095f627a3a8096ecdb17f4f6b9ce58e832d28b` |
| OpenFOAM-13 | https://github.com/OpenFOAM/OpenFOAM-13/archive/version-13.tar.gz | `9969d7f09411d72450855f855f2f37760ff147e3f137fd7063ce6bc26d629632` |
| ThirdParty-13 | https://github.com/OpenFOAM/ThirdParty-13/archive/version-13.tar.gz | `05c91a450113d0f728fa37677147a30fc19f1c04ebf8d70e478db2664f2e6fd9` |

## Build Order

Libraries must be built in dependency order:

1. **scotch 6.0.9** (+ PT-Scotch) — no library dependencies, MPI for PT-Scotch
2. **METIS 5.2.1** — no dependencies
3. **ParMETIS 4.0.3** — depends on METIS, requires MPI
4. **Zoltan 3.90** — requires MPI
5. **OpenFOAM-13** — depends on all of the above, MPI, boost

Steps 1 and 2 are independent and could be built in parallel.

## Build Environment

All MPI-dependent builds use the openmpi-5.0.8-cuda environment:

```bash
export PATH=/opt/openmpi-5.0.8/bin:$PATH
export LD_LIBRARY_PATH=/opt/openmpi-5.0.8/lib:$LD_LIBRARY_PATH
```

In Ansible tasks, this is set via the `environment:` directive following the
same pattern used by mpifileutils in `tasks/mpi.yml`.

## OpenFOAM Build Configuration

OpenFOAM-13 is configured via environment variables in its `etc/bashrc`.
Key settings for our build:

```bash
export WM_MPLIB=SYSTEMOPENMPI      # Use our openmpi-5.0.8-cuda
export SCOTCH_TYPE=system           # Find scotch in /opt/hpc/
export METIS_TYPE=system            # Find METIS in /opt/hpc/
export PARMETIS_TYPE=system         # Find ParMETIS in /opt/hpc/
export ZOLTAN_TYPE=system           # Find Zoltan in /opt/hpc/
```

When `*_TYPE=system`, OpenFOAM looks for libraries and headers under `/usr/`.
Since our libraries install under `/opt/hpc/`, the build environment will need
`CPATH`, `LIBRARY_PATH`, and `LD_LIBRARY_PATH` set to include `/opt/hpc/include`
and `/opt/hpc/lib` respectively, or the OpenFOAM config files will need
overrides to set `*_ARCH_PATH=/opt/hpc` instead of `/usr`.

## Ansible Integration

### File Structure

| File | Purpose |
|------|---------|
| `tasks/openfoam.yml` | All OpenFOAM build/install tasks |
| `tasks/main.yml` | `include_tasks: tasks/openfoam.yml` |
| `defaults/main.yml` | `hpc_install_openfoam: true` toggle |
| `vars/apps.yml` | Install paths, build deps, package info |
| `templates/openfoam-13.lua.j2` | Lmod modulefile |
| `files/openfoam/` | RPM spec files |
| `README.md` | User documentation |

### RPM Build Pattern

Each library follows this pattern in the Ansible tasks:

1. Check if RPM already installed (idempotence via `rpm -q`)
2. Download source tarball with checksum verification (via `download_extract_package.yml`)
3. Copy spec file from `files/openfoam/` to build host
4. Set up rpmbuild tree and build with `rpmbuild -ba`
5. Install resulting RPM with `package:` module
6. Clean up build artifacts

### Lmod Modulefile

The OpenFOAM modulefile (`templates/openfoam-13.lua.j2`):

- `conflict("openfoam")` for mutual exclusivity with other OpenFOAM versions
- `depends_on("mpi/openmpi-5.0.8-cuda12-gpu")` to auto-load MPI
- Sets `WM_PROJECT_DIR`, `FOAM_*` environment variables
- Prepends `PATH`, `LD_LIBRARY_PATH` for OpenFOAM and `/opt/hpc/`

## Implementation Phases

This work is implemented as sequential guilt patches:

1. **Scaffold** — toggle variable, empty task file, variable files, README, test updates
2. **scotch RPM** — spec file, download/build/install tasks
3. **METIS RPM** — spec file, download/build/install tasks
4. **ParMETIS RPM** — spec file, download/build/install tasks
5. **Zoltan RPM** — spec file, download/build/install tasks
6. **OpenFOAM-13 RPM** — spec file, environment config, build tasks, modulefile

Each patch is independently testable and reviewable.

## Verification

- Run the role on a RHEL 9.6 test VM with `hpc_install_openfoam: true`
- Verify all RPMs install cleanly: `rpm -qa | grep hpc-`
- Load the module: `module load openfoam/openfoam-13`
- Run a simple OpenFOAM test case (e.g. `$FOAM_TUTORIALS/incompressible/simpleFoam/pitzDaily`)
- Verify `decomposePar` works with scotch, METIS, and Zoltan methods
- Verify PT-Scotch parallel decomposition works with `mpirun`
