---
layout: single
title:  "Cranberry renderer"
date:   2024-09-07
excerpt: "Notes on how the world renderer works and built on top of GAL"
mermaid: true
categories: 
    - cranberry
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
