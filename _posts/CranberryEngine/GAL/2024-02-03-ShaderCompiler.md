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

I need a shader compiler to parse the shader files and generate the shader byte code necessary for appropriate graphics API being used. The compiler must also be able to generate necessary reflection files.
I am going to use [DXC] to compile shaders. For Vulkan api [DXC] will be able to cross compile and generate SPIRV bytecodes. `SPIRV-Cross` can be used to generate reflection out of SPIRV bytecode. I hope the reflections from DXC and SPIRV can be used together to generate as much reflection information as possible.

Shader compiler will provide an unified interface for my engine to compile and reflect shaders using various tools.
In order to support additional features the shaders written for this compiler must use certain custom pragmas like `sc_hint()` or `sc_config()` to provide hints to compiler inside the shader itself.
There is also few custom syntax to define nodes and configs which will be used to compile permuted shaders.

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

## Custom pragmas

Since unknown pragma can be ignored when compiling the actual shader, Custom pragma are introduced.

### `sc_hint`

Used to provide some hints to shader compiler while determining type and entrypoints of the shader.

#### Usage

```hlsl
#pragma sc_hint(...)
```

## Determining the type of a shader

Shader types are shader compiler custom types provided by enum `EShaderSrcType::type`. Each shader source file aggregates all the possible shader stages it supports separated by different entrypoints.
The shader type can be determined either from file's second extension or using `sc_hint`.
Following table provide overview of how a shader type is determined. The shader compiler first tries to determine type from extension. Then tries to lookup `#pragma sc_hint(-t type)` and uses `type` as shader type.

| Shader type   | Extension  | sc_hint      |
| ------------- | ---------- | ------------ |
| Include       | `.hlsli`   | `include`    |
| MaterialShard | `.ms.hlsl` | `material`   |
| MaterialBase  | `.bs.hlsl` | `base`       |
| Compute       | `.cs.hlsl` | `compute`    |
| Graphics      | `.gs.hlsl` | `graphics`   |
| RayTracing    | `.rs.hlsl` | `raytracing` |

## Determining the per stage entrypoint

Stage entrypoints are determined using pragma `sc_hint`. Shader compiler looks for pragma `#pragma sc_hint(-E shader_stage entrypoint_name)` and uses `shader_stage`, `entrypoint_name` for compiling a shader stage.

| Shader stage          | Stage name |
| --------------------- | ---------- |
| Compute               | `cs`       |
| Vertex                | `vs`       |
| TessellationControl   | `hs`       |
| TessellatonEvaluate   | `ds`       |
| Geometry              | `gs`       |
| Task                  | `as`       |
| Mesh                  | `ms`       |
| Fragment              | `ps`       |
| RayGen                | `rgs`      |
| Intersection          | `ris`      |
| AnyHit                | `rahs`     |
| ClosestHit            | `rchs`     |
| MissHit               | `rmhs`     |
| Callable              | `rcs`      |

## Reading config for a shader

Shader config by default will be read from file with same name as shader but with extension `cfg` for shader types `MaterialBase`, `Compute`, `Graphics` and `RayTracing`. Additional config for each shader can also be provided using pragma `#pragma sc_config(config_path)`. Each `config_path` will be read and appended into current config. The path could be either relative to any directory provided or relative to shader source file's directory.

In case of `MaterialShard` shader type. The syntax is quite different. Instead of using pragma or config with same file name. The config will be written inline inside a `config` block.

```config
config
{
    a=123
    c=34
    t="hello"
}
```

There can be several such config block, They all gets merged together.

## Materials and permutations

The material undergoes permutation based on the input vertex layout, output attachments, and feature sets. For each feature set, the input vertex layout may change, as well as the output attachments. While feature sets do not alter the structure layouts, they do impact the source inclusion. The struct layouts can be generated consistently.

Each `MaterialShard` can be compiled against a set of generated structs, including vertex processing (`MaterialBase`) and color write (`MaterialBase`). These includes can be overridden by feature sets or adjusted using preprocessor defines.

The `MaterialBase` includes a set of nodes, vertex struct layouts, and uniform struct layouts. These specifications are defined in the corresponding configuration. You might wonder why we specify this information in `MaterialBase` while using defines in C++. The reason is that the layouts and node requirements remain constant within the `MaterialBase`. However, other behaviors can be adjusted using defines based on specific requirements. For instance, you can use the same `MaterialBase` for different feature sets.

1. The shader compiler receives a list of **vertex struct layouts** and **uniform struct layouts**, then generates the HLSL struct equivalents for them before beginning the permutation and compilation process.

    ```cpp
    struct VertexLayout
    {
        /* Used for indexing */ 
        NameString name;
        /* To be declared */ 
        ...
    };

    struct UniformLayout
    {
        /* Used for indexing */ 
        NameString name;
        /* To be declared */ 
        ...
    };

    ArrayView<VertexLayout> allVertexLayouts;
    ArrayView<UniformLayout> allUniformLayouts;
    ```

2. The shader compiler also receives a list of vertex processing, color write includes(`MaterialBase`), along with corresponding defines per feature set.

    ```cpp
    struct MaterialBaseDesc
    {
        /* Name to index the MaterialBase with */
        NameString baseName;
        ArrayView<StringView> defines;
    };

    struct FeatureSetPermutations
    {
        ArrayView<MaterialBaseDesc> vertexProcessing;
        ArrayView<MaterialBaseDesc> colorWrites;
        ArrayView<StringView> commonDefines;
    };

    struct MaterialModelDesc
    {
        NameString modelName;    
        ArrayView<FeatureSetPermutations> perFsPermutation;
    };

    ArrayView<MaterialModelDesc> materialModels;
    ```

3. The `MaterialBase`'s config will be used to determine the required nodes in `MaterialShard` and required vertex and uniform layouts.
Nodes can be declared and defined using following syntax in `MaterialShard`.

    ```c
    /* name_of_node will be used for indexing the node */
    node name_of_node
    {
        /* Function code goes here */
        ...
    }
    ```

4. The `MaterialBase`'s config can be written like

    ```config
    verts+={
        struct="VertexStruct1"
        bPerInstance=false
    }
    verts+={
        struct="VertexStruct2"
        bPerInstance=false
    }
    structs+="UniformStruct1"
    structs+="UniformStruct2"
    nodes+={
        name="Node1"
        sig="float invokeNode1(SomeStruct input)"
    }
    nodes+={
        name="Node2"
        sig="float3 invokeNode2(SomeStruct input)"
    }
    ```

5. Once all the required data is available. Shader compiler assembles the final shader in following order
    1. Generate the common always necessary code from `MaterialShard` and includes them.
    2. Generates the necessary nodes.
    3. Includes the generated vertex and uniform struct
    4. Includes the `MaterialBase`s
    5. Includes the generated node codes.
    6. Do the regular shader compilation and reflecting route from here.

[//]: # (Below are link reference definitions)

[DXC]: https://github.com/microsoft/DirectXShaderCompiler
[DXC reference]: https://simoncoenen.com/blog/programming/graphics/DxcCompiling
[Vulkan and DXC]: https://docs.vulkan.org/guide/latest/hlsl.html
