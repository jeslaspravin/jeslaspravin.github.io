---
layout: single
title:  "GAL render pass, framebuffer, pipelines and descriptors"
date:   2024-01-27
excerpt: "Creating pipelines and descriptors set with compatible render pass and pipeline layouts!"
mathjax: true
mermaid: true
categories: 
    - cranberry
sidebar:
    nav: "Cranberry_GAL"
---

## Why?

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

Managing compatibility between render passes, pipelines, and framebuffers can be challenging. Creating a descriptor layout and using it to create pipelines can also be difficult. Allocating descriptors from the descriptor pool and ensuring that they are fully compatible with the pipeline can be another challenge. Supporting additional features like bindless and buffer memory addressing can further complicate the process.

<div class="mermaid">
---
title: Compatibility Relations
---
erDiagram
    Framebuffer }|--|| RenderPass : "uses"
    RenderPass ||--|{ SubPass : "has"
    GraphicsPipeline }|--|| SubPass : "uses"
    vkCmdBeginRenderPass }|--|| RenderPass : "uses"
    vkCmdBeginRenderPass ||--|| Framebuffer : "uses"
    VkDescriptorSetLayout ||--|{ VkDescriptorSetLayoutBinding : "created using"
    VkDescriptorPoolSize ||--|| VkDescriptorSetLayoutBinding : "subset of"
    VkPipelineLayout }|--o{ VkDescriptorSetLayout : "uses"
    GraphicsPipeline }|--|{ VkPipelineLayout : "uses"
    ComputePipeline }|--|{ VkPipelineLayout : "uses"
    VkDescriptorPool }|--|{ VkDescriptorPoolSize : "created using"
    VkDescriptorSet }|--|| VkDescriptorPool : "allocated from"
    VkDescriptorSet }|--|| VkDescriptorSetLayout : "allocated using"
    vkCmdBindPipeline ||--|| ComputePipeline : "binds"
    vkCmdBindPipeline ||--|| GraphicsPipeline : "binds"
    vkCmdBindDescriptorSets }|--|{ VkDescriptorSet : "binds"
    VkPipelineLayout {
        VkDescriptorSetLayout descriptorLayouts[]
    }
    VkDescriptorPool {
        VkDescriptorPoolSize descriptors[]
    }
    Framebuffer {
        ImgView imageViews[]
    }
    RenderPass {
        Attachment attachments[]
        SubPass subpasses[]
        SubpassDependency subpassDependencies[]
    }
    SubPass {
        AttachmentRef attachmentReferences[]
    }
</div>

From the above diagram, you can clearly see how many elements need to be compatible for everything to work well. That is a lot of upfront information needed even before considering the complexity of the pipeline description.

## Handling

So, how to handle this level of complexity? The answer is shader compiler and permutation, combined with runtime pipeline creation and caching. Of course, all this complexity will be handled by the layer that uses the GAL. What does GAL do then? GAL provides APIs that create renderpass, framebuffer, pipelines, resource descriptors(VkDescriptorSet), and Resource descriptors pool.

Who handles the other resources that are not exposed by the GAL? GAL itself the create info sent to GAL will contain all the data that are necessary for GAL to create those internal resources. This might change If I determine at the implementation stage if it is not feasible.

## RenderPass

This time I have decided to allow render pass to have subpasses and dependencies. So the render pass interface closely mimicks the vulkan [VkRenderPassCreateInfo].
There are few exceptions like

- Made the sample count common to all attachments. So all color and depth attachments will be of that sample count. All `resolveAttachments` will be of sample count 1.
- Attachment information has one additional flag to denote If an attachment will only be used for resolve. The reason I choose flag to separate regular render target attachments and resolve attachment instead of having separate array of attachments for each usage like below code snippet is to avoid having additional data inside each subpass's input and preserve attachment list. The preserve and input attachment list can refer to any attachment even multisampled images. In case of multisampled image each input attachment sample refers to corresponding multisampled point.

    ```cpp
    ArrayView<AttachmentInfo> colorAttachments;
    ArrayView<AttachmentInfo> depthAttachments;
    ArrayView<AttachmentInfo> resolveAttachments;
    ```

## Framebuffer

Framebuffer is just a list of image views. It follows a similar structure as that of [VkFramebufferCreateInfo] and [VkFramebufferAttachmentsCreateInfo]. The image-less frame buffer must be allowed to be created if the driver supports it. The support can be checked from `gal::Context`.

## Resource descriptor pool

The resource descriptor pool is Vulkan's [VkDescriptorPool] equivalent. However The GAL is not going to expose all the parameters from [VkDescriptorPoolCreateInfo]. This is to keep the implementation simple. GAL will have additional parameter or struct fields to support allocating bindless(`VK_EXT_descriptor_indexing`) resource descriptors and whatever necessary for dynamic buffer offsets. It will take in a number of descriptors per descriptor type and total number of descriptor sets per pool to determine total number of descriptors necessary from the pool.

## Pipelines

The pipeline requires more work from the layer above GAL just to keep the interface simple without many assumptions like resource descriptor change frequency, caching, etc.,

The GAL will not assume that the shader is compiled and written in any particular language. All it needs is just a create info struct filled with the necessary information required for this platform and API combination.

In this section, I will try to figure out the necessary field in the create info struct. First, let me go over the common states between compute and graphics pipelines. Both of them have pipeline layout and shader code in common.

### Shader code

The shader code binaries as different between D3D and Vulkan. Vulkan uses SPIR-V binary and D3D12 uses Shader model 6(I believe). So in this case the shader code necessary for the current API must be provided by the layer above GAL. The main reason for this decision is I do not want GAL to be handling several external dependencies like SPIRV, DXC, GLSLang, or any other tools that help with shader toolings. So the layer that uses GAL must speak with these external dependencies and generate all the data necessary for GAL to consume. The GAL must expose some API-specific GAL headers(Not necessarily Vulkan or d3d headers) for such a layer to work with in order to provide API-unique data.

So when it comes to shader the pipeline create info must have fields to receive shader data unique per API. At runtime, it won't be required to populate the shader code for API that is not currently active.

Along with the shader code, the common shader stage-related data such as per stage entry points, shader stage type, and specialization information must be provided. How the common and API-specific data are arranged must be decided when implementing to make it as optimal as possible.

I assume(Not checked) specialization constant([VkSpecializationInfo]) is unique to vulkan and it must be part of vulkan unique data as well? but since the layer above GAL is going to be a api agnostic layer. I am going to use specialization constant anyway and convert the specialization constant to uniforms in D3D when I add D3D support. The issue to track native specialization constant support in hlsl <https://github.com/microsoft/hlsl-specs/issues/16>.

```cpp
/* API Agnostic data and code */ 
struct SpecConstDesc
{
    uint16 offset;
    uint16 size;
};

struct ShaderDesc
{
    EShaderStage::Type type;
    const AChar *entrypoint;
};

struct PipelineDesc
{ 
    ArrayView<ShaderDesc> shaders;
    // Common for this pipeline, do not needed per stage
    ArrayView<SpecConstDesc> specConstEntries;
    ArrayView<uint8> specConstData;
};

/* Vulkan API data */
struct VulkanShaderDesc
{
    ArrayView<uint8> shaderCodes;
};
struct VulkanPipelineDesc
{
    ArrayView<VulkanShaderDesc> shaders;
    // Maps the elements in spec const entries to it's corresponding specialization constant's ID.
    ArrayView<uint32> specConstEntryToConstId;
};
```

### Pipeline layout

The pipeline layout will be created from pipeline create info, to create pipeline data we need resource descriptors set layouts and push constant description.

The push constant description is simply a list of size, offsets ,and shader stage usage per entry. The size and offsets must be 4 byte aligned.

When it comes to resource descriptors set layouts. I choose to not use set index and bind index. Instead use descriptor table id and entry id. This IDs may or may not align with Vulkan's set and bind IDs. In order to map any table ID and entry ID to the respective API's binding format, there will be a remapping table inside API's descriptors description. When it comes to rest of the common data I have none of importance right now, but I am sure additional data will be needed when implementing.

The GAL pipeline object will contain the descriptor layouts which will be used to allocate descriptor sets from descriptors pools. The resource descriptor table ID and entry ID combined can be used when calling GAL to create a specific resource descriptor handle.

```cpp
/* API Agnostic data and code */ 
struct PushConstsDesc
{
    EShaderStage::Flags stagesUsed;
    uint32 size;
    uint32 offset;
};

struct ResourceTableDesc
{
    uint32 entriesCount;  
};

struct PipelineDesc
{
    ArrayView<PushConstsDesc> pushConstDescs;
    ArrayView<ResourceTableDesc> resTableDescs;
};

/* Vulkan API data */

struct VulkanResourceDescriptorDesc
{
    uint32 bindId;
    EResourceDescriptor::Type type;
    uint32 count;
    // Additional data necessary
};
struct VulkanResourceDescriptorsSetDesc
{
    uint32 setId;
    ArrayView<VulkanResourceDescriptorDesc> descriptors;
    EShaderStage::Flags stagesUsed;
    // Additional data necessary
};

struct VulkanPipelineDesc
{
    ArrayView<VulkanResourceDescriptorsSetDesc> resTableDescs;
};
```

## Graphics Pipeline

I choose to have most of the options required when creating a Vulkan graphics pipeline here [VkGraphicsPipelineCreateInfo]. However, I am planning to enable as much of dynamic states as possible to make it easier without sacrificing performance. Since dynamic states will be decided upfront It will all be hardcorded. I am also never going to create the parent pipeline and child in the same creation call. So parent handle must be valid if needs to be inherited. An idea of how all this data will be populated and permuted will be described in [GAL user notes](#gal-user-notes).

{: .hidden}

### Common entries for pipeline creation

{: .hidden}

- `ArrayView<ShaderDesc> shaders;`
- `ArrayView<SpecConstDesc> specConstEntries; ArrayView<uint8> specConstData;`
- `ArrayView<PushConstsDesc> pushConstDescs;`
- `ArrayView<ResourceTableDesc> resTableDescs;`

{: .hidden}

### API entries for pipeline creation

{: .hidden}

- `ArrayView<uint8> shaderCodes[MAX_SUPPORTED_DRIVER_API];` or `ArrayView<VulkanShaderDesc> shaders;`
- `ArrayView<uint32> specConstEntryToConstId;`
- `ArrayView<VulkanResourceDescriptorsSetDesc> resTableDescs;`

## GAL user notes

This section includes some of the points on how the layer above GAL must interface with GAL while designing this API. Also, the plans I have for developing the layers around GAL. The shader compiler tool I am planning on using is `DXC`.

{: .emphasis}
Here are the constraints I have on the GAL user layer

- Never do any major driver API-specific processing for GAL.
- There can be additional libraries developed only with GAL in mind. These libraries will be GAL helper libraries.
- All the driver API-specific data required by GAL will be provided by some GAL helper library or shader compiler.
- GAL will provide the necessary headers and implementations for these helper libraries.

Onward to implementation design. The user layer will have shader objects similar to the ones I had in the previous RHI implementation. The shader objects could be a full-fledged C++ class or data structs, implementation decides. The idea behind the design is to allow engine users to author custom materials which then get compiled and permuted to be useable with the engine's unified rendering path.

{: .emphasis}
Following are shader types(Considered only graphics and compute pipelines so far)

- Draw shader. These get generated from user-authored materials by the shader compiler. It could be generated into graphics or compute pipeline based on need.
- Unique draw shader or Utility fragment shader. These are graphics pipelines with constant vertex layouts, descriptor layouts, push constants, and attachments.
- Compute shader.

The shader compiler library will be developed to work closely with GAL. The shader compiler will use `DXC` as a statically linked library. It will have entry points such that it could be used as a statically linked library and separate offline compiler executable. This tool also will apply patching to generated IR if necessary. It must also generate the necessary driver API data by reflecting the shaders. For Vulkan specific data `SPIR-V cross` will be used for reflection and patching.

{: .emphasis}
The following features are planned to be supported in the shader compiler

- Compile all the permutations for a material shader to the mesh draw shader.
- Patch compiled shader IRs as necessary.
- Reflect shader to generate GAL data and GAL driver API relevant data.
- Possibly generate headers from the material shader to match the resource descriptor uniforms.

{: .emphasis}
What data will be reflected by the shader compiler? Planning to do the following at the start

- Input vertex attributes and bindings(Common GAL data).
- Push constants layout(Common GAL data).
- Specialization constants layout and defaults(Common GAL data).
- Specialization constants ID to Vulkan ID mapping(Vulkan data).
- Resource descriptors table and entries(Common GAL data).
- Resource descriptors usage description(Common GAL data).
- Resource descriptors Vulkan description(Vulkan data).
- Resource descriptors table to descriptor sets mapping(Vulkan data).
- Color attachments and its usages(Common GAL data).
- Possibly precision information for all these data where applicable(Common GAL data).

Once the reflected data is filled It could be used by the user layer to create necessary pipelines from GAL. The reflected data generated by the shader compiler is not enough to create the pipeline. The attachment info is incomplete we could use an attachment with any format that could plug into the shader attachment data type. This is where the user layer creates an initial set of pipeline states with a single pass render pass. This allows the user layer to compile and cache the parent pipeline for each combination of material, feature set, descriptors, and vertex inputs. The user layer must cache shaders and pipelines for each of these combinations and also create new child pipelines for each incompatible render pass. These render passes are known at runtime when render graph or similar logic runs.

When it comes to resource descriptor tables in mesh draw shaders. Each table will contain descriptors separated based on rebinding frequency. An example would be

- All views, feature sets, and global constants can be bound to Table 0.
- All vertex constants(eg, Vertex transform matrices) can be bound to Table 1.
- All material unique constants can be bound to Table 2.
- All shader usage constants(eg, Shader used for depth pre-pass, different types of shadow rendering, GBuffer, forward) can be bound to Table 3.

Each shader might use each of these descriptors the way they see fit. So user layer must ensure each descriptor provides maximum compatiblity when bound as per frequency. What I mean by that is If shader A uses global descriptor in vertex and fragments and shader B uses only in the fragment shader. Then the global descriptor must be created with both vertex and fragment as its usage.

Once all of the above is done I will have a working and extensible GAL, shader compiler, and a renderer user layer for my engine.

[//]: # (Below are link reference definitions)

[VkRenderPassCreateInfo]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkRenderPassCreateInfo.html
[VkFramebufferCreateInfo]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkFramebufferCreateInfo.html
[VkFramebufferAttachmentsCreateInfo]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkFramebufferAttachmentsCreateInfo.html
[VkDescriptorPool]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkDescriptorPool.html
[VkDescriptorPoolCreateInfo]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkDescriptorPoolCreateInfo.html
[VkSpecializationInfo]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkSpecializationInfo.html
[VkGraphicsPipelineCreateInfo]: https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkGraphicsPipelineCreateInfo.html
