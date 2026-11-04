#!/usr/bin/env bash
# Builds the toolchain layout that scripts/check/check_cpp_examples.py discovers. Needs Ubuntu 24.04, sudo and roughly 8 GB of disk.
#
#   GCC 9 to 14   apt g++-N (each with its own libstdc++)
#   Clang 14 to 20  apt clang-N, with the libc++ headers of each version unpacked into /opt/libcxx/N, because the libc++-N-dev packages
#                   conflict when installed together
#   GCC 15, 16    conda-forge environments /opt/gcc15 and /opt/gcc16
#   Clang 21 to 23  conda-forge environments /opt/clang21 to /opt/clang23 (compiler, libc++ headers and a glibc sysroot)
#
# It mirrors how the configurations were first set up by hand; it has not been run on a GitHub-hosted runner yet.
set -euo pipefail

echo "Freeing disk space"
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL || true

echo "Installing GCC 9-14 and Clang 14-20 from apt"
sudo apt-get update
sudo apt-get install -y --no-install-recommends g++-9 g++-10 g++-11 g++-12 g++-13 g++-14 \
  clang-14 clang-15 clang-16 clang-17 clang-18 clang-19 clang-20

echo "Unpacking libc++ 14-20 headers into /opt/libcxx/N"
tmp="$(mktemp -d)"
( cd "$tmp" && for v in 14 15 16 17 18 19 20; do apt-get download "libc++-$v-dev"; done )
for v in 14 15 16 17 18 19 20; do
  sudo mkdir -p "/opt/libcxx/$v"
  sudo dpkg -x "$tmp"/libc++-"$v"-dev_*.deb "/opt/libcxx/$v"
done

echo "Installing micromamba"
mkdir -p "$tmp/mm" && ( cd "$tmp/mm" && curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj bin/micromamba )
export MAMBA_ROOT_PREFIX="$tmp/mamba-root"
mm="$tmp/mm/bin/micromamba"
sudo mkdir -p /opt && sudo chown "$USER" /opt

echo "Creating the conda-forge environments"
for v in 15 16; do "$mm" create -y -q -p "/opt/gcc$v" -c conda-forge --override-channels "gxx_linux-64=$v"; done
for v in 21 22 23; do
  "$mm" create -y -q -p "/opt/clang$v" -c conda-forge --override-channels "clangxx=$v" "libcxx-devel=$v" sysroot_linux-64 "gcc_impl_linux-64=14"
  "$mm" clean -a -y -q || true
done
echo "Toolchains ready"
