---
layout: single
title:  "Shader compiler"
date:   2024-02-03
excerpt: "Designing the shader compiler to work with engine shaders both offline and runtime"
mathjax: true
mermaid: true
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/GAL-RP-Pipe-FB-DescSet.svg   
sidebar:
    nav: "Cranberry_GAL"
---

## Introduction

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

I need a shader compiler to parse the shader files and generate the shader byte code necessary for appropriate graphics API being used. The compiler must also be able to generate necessary reflection files.
I am going to use [DXC] to compile shaders. For Vulkan api [DXC] will be able to cross compile and generate SPIRV bytecodes. `SPIRV-Cross` can be used to generate reflection out of SPIRV bytecode. I hope the reflections from DXC and SPIRV can be used together to generate as much reflection information as possible.

## DXC to My shader compiler

DXC is an open source shader compiler to compile and reflect `HLSL` shaders. For more information refer [DXC reference] or [Vulkan and DXC].

The instances created by dxc's `DxcCreateInstance()` are not thread safe. I have to wrap this around my own compiler instance to support multithreading.
Along with thread safety I must also include additional features to support my use case

- API to read all shader files from provided directories and generate a shader code blob. This blob could be used by the shader compile at runtime to dynamically generate permutations. This blob will be stored with the compiler instance throughout its lifetime.
  - Function to create the blob from directories
  - Function to append to the previously created/loaded blob
- API to copy the blob to external memory.
- API to compile both utility rasterization shaders, compute shader ,and etc.
- API to compile several permutations of material shaders shards into final shaders.
- API to validate previously compiled shaders with shaders in directories/disk. This is required at development time only.
- Provide Async equivalent version of the function where ever possible.
- Support specialization constant in DXIL. For supporting specialization constant in D3D I should probably also look into Mesa's `NIR` and `Godot`'s source to understand the scope of that task.

{: .hidden}

## Task logs

{: .hidden}

- Created DxcCompiler instance and creation functions.
- Added JobSystem as multithreading backend.
- Improve the copat to support single threaded dispatch, diverge
- Add HLSL source scanning, blob serialization.

[//]: # (Below are link reference definitions)

[DXC]: https://github.com/microsoft/DirectXShaderCompiler
[DXC reference]: https://simoncoenen.com/blog/programming/graphics/DxcCompiling
[Vulkan and DXC]: https://docs.vulkan.org/guide/latest/hlsl.html
