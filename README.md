# jetsetter

Interactive TUI for setting up NVIDIA components on Jetson — via apt, no NVIDIA account needed.

## Install

```bash
sudo pip3 install jetsetter
# or from source:
git clone https://github.com/anandishgupta-source/jetsetter
cd jetsetter
cd jetsetter
sudo pip3 install .
```

## Run

```bash
sudo jetsetter
```

## Components

| Group | Component |
|---|---|
| JetPack | Full meta-package (CUDA + cuDNN + TensorRT + VPI + Multimedia) |
| CUDA | Runtime, Toolkit (nvcc), Samples |
| cuDNN | Runtime, Dev headers |
| TensorRT | Runtime, Dev headers |
| VPI | Vision Programming Interface |
| DeepStream | Streaming analytics SDK |
| ONNX Runtime | GPU inference with TensorRT EP |
| OpenCV | CUDA-accelerated build |
| Multimedia | L4T Multimedia API, GStreamer NVMM plugins |
| Triton | Triton Inference Server client |
| Developer Tools | Nsight Systems, Nsight Compute |

## How it works

1. Auto-detects your board and L4T version
2. Disables components incompatible with your L4T version
3. Review screen shows all packages before anything is touched
4. Sets up NVIDIA apt repo if not already configured
5. Parallel apt installs per component group
6. Post-install dpkg verification

## Override worker count

```bash
JETSETTER_JOBS=8 sudo jetsetter
```
