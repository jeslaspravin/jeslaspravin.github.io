---
layout: single
title:  "Cranberry renderer"
date:   2024-09-07
excerpt: "Notes on how the world renderer works and built on top of GAL"
mermaid: true
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/WorldRenderer(03-11-2024).png
sidebar:
    nav: "Cranberry_GAL"
---

## Cranberry world renderer

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

<div class="mermaid">
---
title: Static Mesh GPU Data relations
---
erDiagram
    SmVertsBuf ||--|{ SmVertS0 : "contains"
    SmVertsBuf ||--|{ SmVertS1 : "contains"
    SmIdxsBuf ||--|{ Indices : "contains"
    GpBindlessData ||--|{ MID : "contains"
    GpBindlessData ||--|{ SmBatch : "contains"
    GpBindlessData ||--|{ BatchMaterialIndex : "contains"
    SmBuf ||--|{ Sm : "contains"
    SmInstBuf ||--|{ SmInst : "contains"
    MIBuf || -- |{ MI : "contains"
    SmBatch || -- || SmIdxsBuf : "points to"
    MI || -- || MID : "points to"
    BatchMaterialIndex || -- || MI : "points to"
    Sm || -- |{ SmBatch : "points to"
    Sm || -- |{ SmVertsBuf : "points to"
    SmInst || -- || Sm : "points to"
    SmInst }| -- |{ BatchMaterialIndex : "points to"
    MID }| -- |{ RoTextures : "points to"
    GpBindlessData[GeneralPurposeBindlessData] {
        AnyType1 Data1
        AnyType2 Data2
        AnyType1 Data3
        AnyTypesN DataN "And continues"
    }
    MID[MaterialInstanceData] {
        uint MaterialIdx
        FieldTypes Fields "One or more of material fields"
        uint TextureIdx "One or more of texture indices, Sampler types are hardcoded into shader"
    }
    MI[MaterialInstance] {
        uint MaterialIdx
        uint bufferIdx
        uint bufferOffset
    }
    RoTextures[ReadOnlyBindlessTextures]{
        Texture textures[]
    }
    SmBatch[StaticMeshBatch]{
        uint startIdx
        uint idxCount
    }
    Sm[StaticMesh]{
        uint vertS0Offset
        uint vertS1Offset
        uint vertCount
        uint idxOffset
        uint idxCount
        uint batchBufferIdx "Buffer index in GP descriptor"
        uint batchBufferOffset "Bytes offset in GP Buffer"
        uint batchCount
    }
    SmInst[StaticMeshInstance]{
        AABB bound
        float4x3 m2w
        float4x3 w2m
        uint meshIdx
        uint batchMatIdx "Buffer index in GP descriptor"
        uint batchMatOffset "Bytes offset in GP Buffer"
        uint batchCount
    }
    SmVertS0[StaticMeshVertStream0]{
        float3 position
    }
    SmVertS1[StaticMeshVertStream1]{
        float3 normal
        float3 tangent
        float2 uv
    }
    %% Buffers
    SmIdxsBuf[StaticMeshIdxsBuffer]{
        uint idxsMesh1[]
        uint idxsMeshN[]
    }
    SmVertsBuf[StaticMeshVertsBuffer]{
        StaticMeshVertStream0 vertsS0Mesh1[]
        StaticMeshVertStream0 vertsS0MeshN[]
        StaticMeshVertStream1 vertsS1Mesh2[]
        StaticMeshVertStream1 vertsS1MeshN[]
    }
    SmBuf[StaticMeshesBuffer]{
        StaticMesh meshes[]
    }
    SmInstBuf[StaticMeshInstanceBuffer]{
        StaticMeshInstance insts[]
    }
    MIBuf[MaterialInstanceBuffer]{
        MaterialInstance insts[]
    }
</div>

### Transfer buffers from CPU to GPU

For transferring resources from CPU to GPU my initial design was flawed. I have re-architected the transfer jobs better after reading below.
In Vulkan, if you're synchronizing resource access across queues using `vkQueueSubmit` and semaphores, you typically do not need an additional barrier to acquire and release resources explicitly for the transfer queue.

1. **Semaphore Usage for Synchronization Across Queues**:

    - Semaphores in Vulkan are designed to synchronize work between different queues, and they are capable of handling memory visibility across queue families.
    By signaling a semaphore in one queue and waiting on it in another,
    Vulkan ensures that the resources written by the signaling queue (like a transfer queue) are available to the waiting queue (like a graphics or compute queue) without the need for extra barriers.

2. **Pipeline Barriers within Command Buffers**:

    - Within the command buffer of a single queue (like the transfer queue),
    you still need to use pipeline barriers to order operations if there are dependencies within that queue. But when you are dealing with synchronization between different queues,
    the semaphore handles both ordering and memory visibility for the resources shared between them.

3. **Image Layout Transitions**:

    - If the resource being transferred is an image and requires a layout transition before it can be used on a different queue (e.g., from `VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL` in the transfer queue to `VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL` in the graphics queue),
    you can include the layout transition in the command buffer of the second queue.
    the semaphore will ensure the transition only happens after the transfer finishes.

4. **When Additional Barriers Might Be Needed**

    - The only case where you might need additional barriers is if you have complex dependencies that the semaphore alone can't cover like intra-queue dependencies or cases where finer control over memory visibility within a queue is required.
    But for typical inter-queue resource transfers, semaphores handle the synchronization well on their own.

#### Initial implementation

The initial implementation was to do following

- Whenever transfer data comes in I aggregate them in a list with data being uploaded to copied directly to CPU mapped GPU visible memory.
The code that inserts the transfer also inserts the resource usage information before and after transfer.
This is fine for basic use case with 1 to 1 mapping of resource usage in queue.
- During frame start
    1. Acquire all the resources from Other Queues to Transfer Queues.
    2. Perform the GPU to GPU copies.
    3. Insert Write to ReadWrite memory barrier.
    4. Perform the CPU to GPU copies.
    5. Release all the resources from Transfer Queue to Other Queues.
- Then in corresponding Queue's first command, semaphore wait for transfers.

<div class="mermaid">
---
title: Transfer Flow
---
flowchart LR
acqComp["Acquire resources barrier
(*Compute*)"]
relComp["Release resources barrier
(*Compute*)"]
acqGrap["Acquire resources barrier
(*Graphics*)"]
relGrap["Release resources barrier
(*Graphics*)"]
useComp["Use resource *Compute*"]
useGrap["Use resource *Graphics*"]
qTranStart["Start Transfer"]
qTranEnd["End Transfer"]
g2g["Transfer GPU to GPU"]
memBar["Transfer memory barrier"]
c2g["Transfer CPU to GPU"]

acqComp --> qTranStart
acqGrap --> qTranStart
qTranStart --> g2g
g2g --> memBar
memBar --> c2g
c2g --> qTranEnd
qTranEnd --> relComp --> useComp
qTranEnd --> relGrap --> useGrap

</div>

This approach had several issues with GPU.

1. The drivers are general slow when doing so many memory region Q transfer and barriers. As it might have to aggregate everything into execution and memory dependency.
Then handle cache flushes to all those granular memory regions.
    **Solution** is to do transfer as part of main queue which in my case is Graphics queue and do just memory barrier to handle previous frame synchronization.
    Then handle huge transfers and transfers without previous frame dependencies as part of async transfers there by needing no additional resource barriers.
    Once async transfer is done the resources will be available for actual use by renderer.
2. There are several untouched territory in both Validation layer and GPU driver for the way I do things(Maybe I am just doing it wrong).
I had no Validation error and had random driver crashes when doing release build with out RenderDoc recording.
3. Frame drops are huge as actual frame draw had to wait for larger transfers.
    **Solution** is to only do small update transfers as part of frame like transform updates, view updates. Handle as much as possible with async transfer.

#### New implementation

**Goals** for the implementation

1. Large transfers like mesh data upload, new texture upload, other scene data, ... that can be skipped from frame renderer must not block frame rendering.
2. Reduce explicit cache flushes and barriers due to transfer as much as possible. Cannot be avoided to avoid Read-Write synchronization issue so need at least one memory barrier.
3. If data is not ready skip drawing it for frame and start drawing after upload to GPU is done.

**Implementation** plan
There will two type of push data interface for `WorldRenderer`

1. Large/New upload path. The entry points will be a coroutine that needs to be waited on by caller to receive response.
This entry points uses async transfer queue and might take **`several frames`** to complete. These entry point must not block render frame `theoretically`(There is possibility for frame drop due to GPU bandwidth limitation).
2. Small upload path. The entry points will be regular function and caller can immediately assume operation will be reflected immediately in next frame.

#### Large/New upload path

In this path the data gets copied to Async transfer arena memory and entries with offset details gets inserted into list.
The list gets consumed when transfer command buffer becomes available.
> There can only be one transfer happening at a time so only one `CommandBuffer`(One per transfer worker thread?) is necessary.

The entry point coroutine gets resumed after the transfer it is part of gets completed.

#### Small upload path

This path will be similar to old implementation, except with following changes.

- Same as before transfer gets accumulated per frame in per frame arena memory.
- The fine granular barriers and resource transfers will be `removed`.
- Only global memory barrier/cache flush will be issued in `main Queue` and main Queue will be responsible to wait until all previously issued other Queue commands to be completed using semaphores.
- Once transfer is done a `release memory barrier` will be inserted to `all` available Queues and first command submission in respective Queue will just wait for the flush using semaphore.

### Immediate mode drawing

The immediate mode 3D drawing enables drawing shapes in the world in various layers. Currently world and overlay layers are supported.

Due to the immediate nature of the drawing the draw instances lists are generated each frame and gets uploaded to GPU. Apart from this frustum culling and drawing are similar to mesh/component instances with few data layout differences. One important difference is draw list is generated per layer and not per material like done for components.

Also separate depth overlay attachment is used to support overlay layer without losing world depth.

### Screen space selection buffer

I want to support the screen space selection using IDs written to color attachment buffer. This feature might require major rework in how immediate mode and components are rendered in world.

The conditions/steps I want to draw screen space IDs buffer

- The render pass attachments are limited so add new render pass to just draw IDs.
- Drawn IDs must be copied to a CPU accessible buffer after rendering in Transfer Queue.
- Separate render pass means components shard materials must need another permuted variant that accepts color output to IDs attachment.
- Separate render pass means the immediate mode drawing must be deferred to IDs pass. This won't be an issue as depth buffer from previous render pass can be reused.
- The immediate mode shaders needs to be modified to also write to IDs output attachment.

After the IDs are rendered the data gets copied to CPU data buffer at Frame sync step between main thread and render thread. This means a new virtual function call must be introduced that gets called in render frame sync code in window rendering. At this sync point we can be sure the rendering is done and copy the IDs buffer.

Another important point to consider is what to write as IDs into the IDs buffer. I would like to keep these ID number as `WorldRenderer` internal details. This means external code must associate some data to each component or intermediate instances it draws.

Following are the choices I decided go with

- The data that gets associated with each draw instance will be a reference counted class data type.
The type id will be used as simplest form of RTTI.

```cpp
class SelectionHitProxy
{
private:
    uint32 typeId = 0;

public:
    SelectionHitProxy(uint32 inTypeId) : typeId(inTypeId) {}
    NON_MOVE_COPY(SelectionHitProxy)
    virtual ~SelectionHitProxy() = default;

    virtual void addRef() = 0;
    virtual void removeRef() = 0;
    virtual uint32 refCount() const = 0
};
```

- The component has virtual interface to provide the hit proxy data. The data returned from that is wrapped inside the proxy data created by `WorldRendererBridge` to support selection to component mapping. If the inner wrapped data is valid it could be forward to gameplay system in future.
- The immediate draw instances however works differently. Due to immediate nature states cannot be persisted for this reason. All the hit proxy data must be pushed and popped by the code that pushes immediate draws. The persistence of hit proxy data will there by managed by the immediate draw context user.
- Since immediate draw instances list gets replaced every frame the indices for `SelectionHitProxy` data is managed in two vectors. For components the indices are obtained from a sparse vector. For immediate instances indices are obtained from a frame data unique std::vector.
The indices assigned to IDs buffer will be encoded so that it can be differentiated. In my case the MSB will be set for immediate instances and not set for every other persistent instances.
