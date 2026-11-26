#!/bin/sh
# Build the optional Linux OCCT integration helper used for curved STEP/OBJ solids.
set -eu
source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
output_dir="$source_dir/../../build/sevel-cad"
mkdir -p "$output_dir/volume-libs"
c++ -std=c++17 -O2 -I/usr/include/opencascade "$source_dir/check_brep_volume.cpp" \
    -Wl,--disable-new-dtags,-rpath,'$ORIGIN/volume-libs' -o "$output_dir/check_brep_volume" \
    -lTKTopAlgo -lTKBRep -lTKG3d -lTKMath -lTKernel
# The FreeCAD Flatpak can have a different OCCT ABI than the host compiler.
# Bundle the SONAMEs resolved by the host for this standalone child process.
ldd "$output_dir/check_brep_volume" | awk '/libTK|libtbb/ && $2=="=>" {print $1,$3}' |
while read -r soname library; do
    target="$output_dir/volume-libs/$soname"
    if ! test "$library" -ef "$target"; then
        cp -L "$library" "$target"
    fi
done
