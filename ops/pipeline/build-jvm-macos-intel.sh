#!/bin/bash
## Build libxgboost4j.dylib targeting MacOS (Intel)

set -euox pipefail

source ops/pipeline/enforce-ci.sh

# Display system info
echo "--- Display system information"
set -x
system_profiler SPSoftwareDataType
sysctl -n machdep.cpu.brand_string
uname -m
set +x

brew install ninja libomp

# Build XGBoost4J binary
echo "--- Build libxgboost4j.dylib"
set -x
mkdir build
pushd build
export JAVA_HOME=$(/usr/libexec/java_home)
cmake .. -GNinja -DJVM_BINDINGS=ON -DUSE_OPENMP=ON -DCMAKE_OSX_DEPLOYMENT_TARGET=10.15
ninja -v
popd
rm -rf build
otool -L lib/libxgboost.dylib
set +x

echo "--- Upload libxgboost4j.dylib"
set -x
pushd lib
libname=libxgboost4j_intel_${GITHUB_SHA}.dylib
mv -v libxgboost4j.dylib ${libname}

if [[ ($is_pull_request == 0) && ($is_release_branch == 1) ]]
then
  aws s3 cp ${libname} \
    s3://xgboost-nightly-builds/${BRANCH_NAME}/libxgboost4j/ \
    --acl public-read --no-progress
fi
popd
set +x
