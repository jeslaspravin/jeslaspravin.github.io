---
layout: single
title:  "GAL resource and memory"
date:   2024-01-14
excerpt: "How the resource creation and memory binding API might look like"
mathjax: true
categories: 
    - cranberry
sidebar:
    nav: "Cranberry_GAL"
---

## GAL Resources

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

This post will cover how I am going to abstract the graphics layer for any resources(Images, Buffers) that require memory.
The main point of interest/question I have right now is, How do I abstract the resource creation, memory allocation, and memory binding?
Then there is sparse memory binding backed by hardware features. Which albeit slow right now, but worth considering.

Summarizing the points/questions below

- Should the abstraction layer allow creating resource and binding memory separately?
- Should the abstraction layer allow the creation of resources with memory bound?
- Should I start with sparse memory support from the start? If I do how does it work across different APIs?
- Should the memory allocations be managed in the GAL layer? If yes should the memory management be implemented at the per-driver API level or GAL level inside GAL?

### References

- [Memory management difference between vulkan and direct3D 12]
- [Sparse virtual shadow maps]

## Separate resource and memory

This is the simplest case when it comes to implementation in GAL. Allows GAL user to create resource first and then allocate, and bind a memory region to this resource.
The issue is some APIs like webGPU(As far as my understanding of that API) do not support separate resource and memory management.
In these special cases, It is better to have a flag in `gal::Context` to check whether the API in use supports such a management.

The conclusion is to allow separate resource and memory management except for a few APIs checked at runtime.

## Resource with bound memory

These are the resources that have the requested type of memory allocated and bound when creating. Vulkan does not have any entry points to support this kind of resource creation. In order to support this in Vulkan I must incorporate a generic GPU memory allocator inside GAL for Vulkan only. It takes some work to get it running.

The conclusion is to not allow resources with bound memory creation at the start but add it eventually.

## Hardware backed sparse memory

I have no idea how to do this at the moment. For now I will go with software route when implementing the sparse textures.

## Memory allocation managed in GAL layer

Managing another layer of memory allocation in the GAL layer has its benefits like users not needing to worry about frequent resource allocation and deletion.
On top of user-managed memory, I could have a GPU memory management layer in GAL. Which also could help better abstract APIs that do not support explicit memory management.
However, writing an efficient memory allocator to cover a wide range of usage at this layer is harder than writing on at Engine render layer.

The conclusion is to not have memory management in GAL at least until creating a resource with bound memory is not supported.
As far as the memory management residing level in GAL, I do not have enough information to make a choice.

[//]: # (Below are link reference definitions)
[Memory management difference between vulkan and direct3D 12]: https://www.asawicki.info/articles/memory_management_vulkan_direct3d_12.php5
[Sparse virtual shadow maps]: https://ktstephano.github.io/rendering/stratusgfx/svsm
