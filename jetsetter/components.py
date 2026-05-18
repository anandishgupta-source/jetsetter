"""NVIDIA SDK component definitions — installed via apt from NVIDIA repos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Component:
    id: str
    group: str                          # shown as section header in TUI
    name: str
    description: str
    packages: List[str]                 # apt package names
    recommends: List[str] = field(default_factory=list)   # optional extras
    notes: str = ""
    min_l4t: Optional[str] = None       # e.g. "35.0" — shown as warning if older


# ─────────────────────────────────────────────────────────────────────────────
# CUDA
# ─────────────────────────────────────────────────────────────────────────────
COMPONENTS: List[Component] = [
    Component(
        id="cuda_runtime",
        group="CUDA",
        name="CUDA Runtime",
        description="CUDA runtime libraries — required by everything GPU",
        packages=["cuda-runtime-12-6", "cuda-libraries-12-6"],
        recommends=["cuda-documentation-12-6"],
        notes="Installs to /usr/local/cuda. Add to PATH: export PATH=/usr/local/cuda/bin:$PATH",
    ),
    Component(
        id="cuda_toolkit",
        group="CUDA",
        name="CUDA Toolkit (nvcc + headers)",
        description="Compiler, headers, static libs — needed to build CUDA code",
        packages=["cuda-toolkit-12-6"],
        notes="Includes nvcc, cuBLAS, cuFFT, cuSolver, cuSparse headers",
    ),
    Component(
        id="cuda_samples",
        group="CUDA",
        name="CUDA Samples",
        description="Official CUDA sample programs",
        packages=["cuda-samples-12-6"],
        notes="Installed to /usr/local/cuda/samples",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # cuDNN
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="cudnn_runtime",
        group="cuDNN",
        name="cuDNN Runtime",
        description="Deep Neural Network library runtime",
        packages=["libcudnn9-cuda-12"],
        notes="Required by TensorRT and most DNN frameworks",
        min_l4t="35.0",
    ),
    Component(
        id="cudnn_dev",
        group="cuDNN",
        name="cuDNN Dev (headers + static libs)",
        description="cuDNN headers and static libraries for building",
        packages=["libcudnn9-dev-cuda-12"],
        min_l4t="35.0",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # TensorRT
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="tensorrt",
        group="TensorRT",
        name="TensorRT Runtime",
        description="High-performance DNN inference optimizer and runtime",
        packages=["tensorrt"],
        recommends=["python3-libnvinfer", "python3-libnvinfer-dev"],
        notes="Includes trtexec CLI for benchmarking and engine building",
        min_l4t="35.0",
    ),
    Component(
        id="tensorrt_dev",
        group="TensorRT",
        name="TensorRT Dev",
        description="TensorRT headers and libraries for building custom plugins",
        packages=["libnvinfer-dev", "libnvinfer-headers-dev", "libnvonnxparsers-dev"],
        min_l4t="35.0",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # DeepStream
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="deepstream",
        group="DeepStream",
        name="DeepStream SDK",
        description="Streaming analytics pipeline framework — multi-camera AI",
        packages=["deepstream-7.0"],
        recommends=["deepstream-7.0-dev"],
        notes="Requires GStreamer. Pipelines via deepstream-app or Python bindings.",
        min_l4t="35.0",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # VPI
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="vpi",
        group="VPI",
        name="VPI (Vision Programming Interface)",
        description="NVIDIA VPI — accelerated CV primitives on CUDA/PVA/VIC",
        packages=["libnvvpi3", "vpi3-dev"],
        recommends=["python3-vpi3"],
        notes="Stereo disparity, optical flow, background subtraction etc.",
        min_l4t="35.0",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # ONNX Runtime
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="onnxruntime",
        group="ONNX Runtime",
        name="ONNX Runtime (GPU)",
        description="Cross-platform ML inference with CUDA/TensorRT EP",
        packages=["libonnxruntime-dev"],
        recommends=["python3-onnxruntime-gpu"],
        notes="Use with TensorRT EP for best Jetson performance",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # OpenCV
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="opencv_cuda",
        group="OpenCV",
        name="OpenCV (CUDA-accelerated)",
        description="NVIDIA-built OpenCV with CUDA, GStreamer, V4L2 support",
        packages=["libopencv-dev", "libopencv-python"],
        notes="NVIDIA's build enables CUDA modules disabled in the Ubuntu stock package",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Multimedia
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="multimedia_api",
        group="Multimedia",
        name="Multimedia API",
        description="Jetson low-level multimedia APIs — V4L2, NvBuf, Argus camera",
        packages=["nvidia-l4t-multimedia", "nvidia-l4t-multimedia-utils"],
        notes="Required for zero-copy camera → CUDA pipelines",
    ),
    Component(
        id="gstreamer_nvmm",
        group="Multimedia",
        name="GStreamer NVMM plugins",
        description="GStreamer plugins using NVMM memory — nvv4l2decoder, nvvidconv etc.",
        packages=[
            "gstreamer1.0-plugins-base",
            "gstreamer1.0-plugins-good",
            "gstreamer1.0-plugins-bad",
            "nvidia-l4t-gstreamer",
        ],
        notes="Hardware-accelerated decode/encode/ISP via GStreamer",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Triton
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="triton",
        group="Triton",
        name="Triton Inference Server",
        description="Production multi-model inference server with REST/gRPC",
        packages=["tritonclient-http", "tritonclient-grpc"],
        recommends=["nvidia-tritonserver"],
        notes="Run via Docker on Jetson: nvcr.io/nvidia/tritonserver:*-jetpack",
        min_l4t="35.0",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # Nsight
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="nsight_systems",
        group="Developer Tools",
        name="Nsight Systems",
        description="System-wide GPU/CPU profiler and timeline visualizer",
        packages=["nsight-systems-2024.5.1"],
        notes="CLI: nsys profile ./myapp",
    ),
    Component(
        id="nsight_compute",
        group="Developer Tools",
        name="Nsight Compute",
        description="Kernel-level CUDA profiler — roofline, memory analysis",
        packages=["nsight-compute-2024.3.2"],
        notes="CLI: ncu --set full ./myapp",
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # JetPack meta
    # ─────────────────────────────────────────────────────────────────────────
    Component(
        id="jetpack_all",
        group="JetPack",
        name="JetPack (full meta-package)",
        description="Installs everything: CUDA, cuDNN, TensorRT, VPI, Multimedia",
        packages=["nvidia-jetpack"],
        notes="Equivalent to full SDK Manager install. Largest option (~3 GB).",
        min_l4t="35.0",
    ),
]

# Group ordering for display
GROUP_ORDER = [
    "JetPack",
    "CUDA",
    "cuDNN",
    "TensorRT",
    "VPI",
    "DeepStream",
    "ONNX Runtime",
    "OpenCV",
    "Multimedia",
    "Triton",
    "Developer Tools",
]
