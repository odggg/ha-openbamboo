#!/bin/sh
# Run inside Alpine 3.22 on the target architecture. Output is self-contained.
set -eu
repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
commit=7822614fc7d24b4e41b2f394ae067aa88ef4b05a
arch="${1:?Pass amd64 or aarch64}"
case "$arch:$(uname -m)" in amd64:x86_64|aarch64:aarch64) ;; *) exit 2 ;; esac
apk add --no-cache build-base cmake ninja pkgconf git curl-dev openssl-dev \
  zlib-dev uthash-dev nlohmann-json pax-utils lddtreepax python3 ca-certificates
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
git init "$work/obn"
git -C "$work/obn" fetch --depth 1 https://github.com/ClusterM/open-bamboo-networking.git "$commit"
git -C "$work/obn" checkout --detach FETCH_HEAD
test "$(git -C "$work/obn" rev-parse HEAD)" = "$commit"
cmake -S "$repo_root/native" -B "$work/build" -G Ninja \
  -DOBN_SOURCE_DIR="$work/obn" -DOBN_COMMIT="$commit" -DCMAKE_BUILD_TYPE=Release
cmake --build "$work/build" --target obn-ha-worker -j 2
out="$repo_root/custom_components/bambu_open_network/bin/$arch"
mkdir -p "$out/lib"
cp "$work/build/obn-ha-worker" "$out/obn-ha-worker"
# Resolve all transitive dependencies, including OBN, OpenSSL, curl and libc.
python3 /usr/bin/lddtreepax -l "$work/build/obn-ha-worker" > "$work/deps.txt"
while IFS= read -r dependency; do
  case "$dependency" in
    */obn-ha-worker) ;;
    */ld-musl-*.so.1) cp -L "$dependency" "$out/loader" ;;
    /*) cp -L "$dependency" "$out/lib/$(basename "$dependency")" ;;
  esac
done < "$work/deps.txt"
test -f "$out/loader"
test -f "$out/lib/libbambu_networking.so"
cp /etc/ssl/cert.pem "$out/ca-bundle.pem"
chmod 755 "$out/loader" "$out/obn-ha-worker"
"$out/loader" --library-path "$out/lib" "$out/obn-ha-worker" --self-test
python3 "$repo_root/scripts/runtime_manifest.py" "$out" "$arch"
mkdir -p "$repo_root/vendor/open-bamboo-networking"
# Exact corresponding source and build recipes accompany binary releases.
git -C "$work/obn" archive HEAD | tar -x -C "$repo_root/vendor/open-bamboo-networking"
cp "$work/obn/LICENSE" "$repo_root/LICENSES/open-bamboo-networking.txt"

mkdir -p "$repo_root/LICENSES/alpine-$arch"
apk info -v > "$repo_root/LICENSES/alpine-$arch/packages.txt"
apk info -a > "$repo_root/LICENSES/alpine-$arch/package-metadata.txt"
if [ -d /usr/share/licenses ]; then
  cp -R /usr/share/licenses/. "$repo_root/LICENSES/alpine-$arch/"
fi
