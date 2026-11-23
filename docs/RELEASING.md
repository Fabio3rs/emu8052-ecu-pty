# Building and distributing the Lab

The `Build and package` workflow produces a Linux x86_64 distribution on
Ubuntu 24.04. It builds the graphical Lab, the PTY emulator, the plant dyno,
and the CAD validator. The distribution always excludes ECU firmware.
Supply a ROM file when starting the emulator or Lab.

## Published files

| File | Contents |
| --- | --- |
| `emu8052-ecu-pty-<version>-linux-x86_64.tar.gz` | Four executables, SDL3 shared library, all selected runtime assets, documentation, and license notices. |
| `emu8052-ecu-pty-<version>-assets.tar.gz` | Runtime assets and license notices, without executables. Contains CAD when a CAD input was selected. |
| `release-manifest.json` | Source commit, version, CAD revision when present, firmware exclusion, and file checksums. |
| `SHA256SUMS` | SHA-256 checksums for the delivered files. |

The application archive already includes the assets. The separate assets
archive uses the same top-level directory, so it can also be extracted next
to a matching application archive. Its data does not depend on CPU
architecture. Use assets from the matching version; CAD compatibility also
depends on the manifest schema, datum, and animation rig.

Extract the application archive into a writable directory and keep its
`bin`, `bin/assets`, and `share` directories together:

```sh
sha256sum --check SHA256SUMS
tar -xzf emu8052-ecu-pty-v0.1.0-linux-x86_64.tar.gz
./emu8052-ecu-pty-v0.1.0-linux-x86_64/bin/sevel-ma17-lab /absolute/path/to/your-rom.bin
```

The version above is an example. The other installed programs are
`emu8051-tty`, `sevel-dyno`, and `sevel-cad-check`. A missing CAD registry
selects the existing classic mechanical view. `--no-cad` selects that view
explicitly even when CAD is available.

### Linux requirements

The build targets Ubuntu 24.04 x86_64 and compatible systems. It is a tar
distribution, with SDL3 bundled beside the executable and an `$ORIGIN`
runtime path. It still uses the host's C/C++ runtime, FreeType, zlib, PNG,
OpenSSL, and desktop/audio/graphics drivers. On Ubuntu 24.04 the core
runtime packages include `libfreetype6`, `zlib1g`, `libpng16-16t64`,
`libssl3t64`, and `libstdc++6`; inspect `ldd bin/sevel-ma17-lab` and
`ldd bin/sevel-cad-check` on the destination system for the exact linked
dependencies. The graphical CAD view additionally needs a working SDL GPU
backend. Software rendering is exercised for the classic view in CI.

The current source also relies on Linux/POSIX facilities for PTY and
subprocess handling. This workflow does not build Windows or macOS packages.

## Workflow behavior

- Pull requests, pushes to `main`, and manual runs build, validate, and upload
  packages as Actions artifacts, retained for 14 days.
- Pushing a tag beginning with `v` also attaches the successful packages to
  a GitHub Release and publishes it automatically.
- An existing Release is left intact. Use a new version tag for new packages.
- Only the Release job has `contents: write`; build jobs use read access.
- The actions are pinned to commit SHAs. Submodules are checked out at the
  commits recorded by this repository.

Tag names must contain only letters, digits, dots, underscores, or hyphens.
For example, after merging the workflow and choosing a version:

```sh
git tag v0.1.0
git push origin v0.1.0
```

No Release is created by an ordinary branch push or PR. A manual run on a
version tag follows the same publication rule as a tag push.

## Bringing the existing FreeCAD models into CI

The scripts in `cad/sevel16` are tracked. Their FCStd/STEP outputs, the real
parameter/datum files, and the active runtime registry currently live in
the ignored `build/sevel-cad` directory. They cannot be reconstructed from
a fresh Git clone alone. Keep the authoritative editable CAD files and
export them on the machine that has the FreeCAD checkpoint.

The CI input is the existing validated runtime registry:

```text
runtime-assets/
  current.json
  <SHA-256 of parts_manifest.json>/
    parts_manifest.json
    <meshes listed in the manifest>.obj
```

Use the existing `export_lab_assets.py` / `runtime_package.py` process to
produce this registry after a new CAD export. The runtime manifest must
include `runtime.schema_version = 1` and its animation `rig`. The
`sevel-cad-check` executable validates the manifest, geometry, and hashes;
the archive builder includes only the active revision.

### 1. Prepare the first CAD archive locally

From the checkout containing the exported runtime registry:

```sh
cmake -S . -B .work/cad-check-build \
  -DENABLE_TESTS=OFF -DENABLE_SEVEL_MA17_LAB=ON \
  -DENABLE_SEVEL_MA17_LAB_GUI=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build .work/cad-check-build --target sevel-cad-check --parallel 2
python3 tools/package_release.py cad \
  --registry build/sevel-cad/runtime-assets \
  --checker .work/cad-check-build/sevel-cad-check \
  --output .work/cad-release/sevel-cad-runtime.tar.gz
sha256sum .work/cad-release/sevel-cad-runtime.tar.gz
```

This command does not invoke FreeCAD or re-export the models. It validates
and packages the already exported revision. The archive includes its CAD
license notice and provenance. Other registry revisions, caches, ROMs,
screenshots, and unrelated local files are excluded.

Publish that archive as an asset of a separate Release, for example
`cad-2026-11-23-r1`. A `cad-...` tag does not trigger the program's `v*`
Release rule. This can be done through the Releases UI or with the GitHub
CLI after inspecting the archive:

```sh
gh release create cad-2026-11-23-r1 \
  .work/cad-release/sevel-cad-runtime.tar.gz \
  --target "$(git rev-parse HEAD)" --title 'SEVEL CAD 2026-11-23 r1' \
  --notes 'Validated runtime export; editable checkpoint retained separately.'
```

Use a new CAD tag for a new revision. Keep the SHA-256 emitted locally;
the CI verifies that exact digest before extracting anything.

### 2. Select the CAD input

Set these repository **Actions variables** for subsequent builds:

| Variable | Example |
| --- | --- |
| `SEVEL_CAD_RELEASE` | `cad-2026-11-23-r1` |
| `SEVEL_CAD_ASSET` | `sevel-cad-runtime.tar.gz` |
| `SEVEL_CAD_SHA256` | The full 64-character SHA-256 of that archive. |

Alternatively, provide `cad_release`, `cad_asset`, and `cad_sha256` in a
manual `Build and package` run. Manual values override their corresponding
repository variables. Supply all three when selecting a different CAD
archive. Downloads are from this same repository's Releases.

When all three are absent, the workflow intentionally builds without CAD.
When any is configured, all three are required. A missing download, wrong
digest, unsafe archive, damaged mesh, or invalid runtime manifest fails the
build. CMake receives `SEVEL_REQUIRE_CAD_ASSETS=ON`, so requested CAD cannot
silently disappear from the installed distribution.

The archive's outer checksum and the internal manifest/mesh checksums are
both verified. The compiled C++ checker runs again during installation
and on the extracted application bundle.

### Editable CAD sources

FCStd, STEP, parameter snapshots, datum files, and export evidence belong
in a separate CAD source asset. They are unnecessary for running the Lab.
The existing `cad/sevel16/portable_delivery.py` is a starting point for a
local source delivery, but it needs local checkpoint/proof/specification
files that are not in Git. Include the applicable license notices for the
CAD and any copied Open Engine Sim sources with that delivery. The runtime
workflow deliberately does not manufacture or claim to rebuild these
missing editable files.

## Building the same distribution locally

Install the development dependencies listed in
`.github/workflows/packages.yml`, including the emu8051 submodule. SDL3 is
found locally or fetched at the source version pinned by `CMakeLists.txt`.
For a first build without CAD:

```sh
git submodule update --init --recursive
cmake -S . -B .work/release-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTS=ON \
  -DENABLE_SEVEL_MA17_LAB=ON -DENABLE_SEVEL_MA17_LAB_GUI=ON \
  -DSEVEL_CAD_ASSET_DIR="$PWD/.work/cad-input/sevel-cad" \
  -DSEVEL_REQUIRE_CAD_ASSETS=OFF \
  -DSDL_SHARED=ON -DSDL_STATIC=OFF \
  -DSDL_TESTS=OFF -DSDL_TEST_LIBRARY=OFF -DSDL_EXAMPLES=OFF
cmake --build .work/release-build --parallel 2 --target \
  emu8051-tty sevel-dyno sevel-ma17-lab sevel-cad-check
cmake --install .work/release-build --prefix "$PWD/.work/install" --component Runtime
python3 tools/package_release.py bundle --prefix .work/install \
  --output-dir .work/dist --version local --commit "$(git rev-parse HEAD)"
```

To use a CAD archive, run `extract-cad` before configuring and set
`SEVEL_REQUIRE_CAD_ASSETS=ON`:

```sh
python3 tools/package_release.py extract-cad \
  --archive /path/to/sevel-cad-runtime.tar.gz \
  --sha256 THE_FULL_ARCHIVE_SHA256 --destination .work/cad-input
```

The extraction destination must be new, preventing accidental mixing of
two input bundles. For local iteration, use a fresh installation prefix
as well; a CMake install does not remove files from an older installation.
The packager rejects unexpected files rather than sweeping up a whole
build directory.

Verify the actual archive after moving it away from the checkout:

```sh
mkdir -p /tmp/sevel-package-check
tar -xzf .work/dist/emu8052-ecu-pty-local-linux-x86_64.tar.gz -C /tmp/sevel-package-check
python3 tools/smoke_release.py \
  --prefix /tmp/sevel-package-check/emu8052-ecu-pty-local-linux-x86_64
```

Add `--require-cad` to `bundle` and `smoke_release.py` when testing a
distribution intended to include the CAD.

## What CI validates

The selected tests cover donor meshes, fonts, layout, audio generation,
CAD validation/picking, archive checksums, and the package file allowlist.
The extracted distribution is started from an unrelated working directory
with developer library overrides removed. It exercises the CLI, a dyno
point, a headless SVG, and an SDL software PNG. Missing runtime libraries,
assets, notices, or requested CAD fail the run.

The only firmware created by the package smoke test is a temporary 8051
`SJMP $` loop, outside the distribution directory. It is deleted afterward.
These checks verify packaging and startup; they do not assert physical
engine behavior or ECU firmware correctness. Existing tests that require
the real ROM remain available for local validation and are not included
in this workflow's ROM-free selection.

Packaging normalizes archive ordering, permissions, owners, and gzip/tar
timestamps. Identical staged inputs produce identical archives. Compilers
and system dependencies are not a fully hermetic toolchain, so this is not
a claim of reproducible executable bytes across different build hosts.

## Firmware distribution policy

The workflow has no firmware download, secret, or include-ROM switch.
The packager only accepts the installed runtime's expected files and
records `rom_included: false`. CAD and executable releases are independent
of any future decision about redistributing the ECU dump. If that policy
changes, implement and review a separate explicit firmware artifact.
