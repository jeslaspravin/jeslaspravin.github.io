---
layout: single
title:  "[WIP]Planning GAL"
date:   2023-10-06
excerpt: "Determining the scope of the GAL"
mathjax: true
mermaid: true
categories: 
    - cranberry
header:
    teaser: /assets/images/bg640x360.jpg
sidebar:
    nav: "Cranberry_GAL"
---

## Graphics Abstraction Layer(GAL)

Graphics abstraction layer is going to be the light weight abstraction on top of Graphics APIs like Vulkan, DirectX, Metal etc., of Cranberry engine.
This page will contain some rough abstract of the plan. It is not complete or fool proof and mostly just mental model. I have no working code at this point.

### Goals

- Never allocate any memory inside this library. Allocator will be passed in from the caller. It will be used by GAL.
- Never use the std library classes that uses allocator. Use custom implementation on need basis.
- Single library that will self contain all the Graphics API's implementation. However the GAL interface must never interact with the Graphics APIs implementation headers directly. This is to reduce the dependencies as much as possible. The platform dependent Graphics API will be dropped out by the build system.

## Build system changes

This section documents all the build related changes that were necessary to achieve the final goal.

### Disable source path

The GAL library itself contains abstractions for all the supported graphics APIs under their own folder. This change modifies the build macros in `EngineProjectMacros.cmake` and allows ignoring certain folders from source list.

```cmake
# Something like this
if(target_srcs_IGNORE_SUBPATHS)
    foreach(ignore_subpath ${target_srcs_IGNORE_SUBPATHS})
        string(APPEND subpath_regex "${ignore_subpath}/.*|")
    endforeach()

    # Filter ignored paths
    list(FILTER srcs EXCLUDE REGEX ${subpath_regex})
endif()
```

This feature also brought in additional change were subfolders that contains `Private` or `Public` directory will be automatically added into include paths of that target and interface includes.

```cmake
# Only add if this path is inside subfolder
string(REGEX MATCH ".+/*Private|.+/*Public" matched_incl_path ${src})

if(NOT ${matched_incl_path} STREQUAL "")
    list(APPEND incls ${matched_incl_path})
endif()
```

### Drop GLOB based cmake target configuring

After a long time in queue, The GLOB based configuration of `target_sources` is made a backup option for a target source listing. Now the project includes `GenCppSrcLists` target that can be used to generate source lists for each engine targets/modules. It works by invoking cmake script `./Scripts/CMake/Scripts/GenerateCppSourceList.cmake`. The script without any properties setup scans all directories under `./Source` and finds all CMakeLists.txt that generates target using engine provided cmake macros.

The important cmake function for generating source list is below. `configure_file` ensures that `SourceList.txt` file is written to only if there is any changes.

```cmake
function(generate_cpp_source_list folders)
    foreach(folder ${folders})
        # Get all cpp files and sort them
        get_all_cpp_files_in_dirs(
            file_list
            RELATIVE ${folder}
            DIRS ${folder}
        )
        list(SORT file_list)

        list(POP_FRONT file_list source_list)

        foreach(file ${file_list})
            string(APPEND source_list "\n    ${file}")
        endforeach(file ${file_list})

        set(source_list_file ${folder}/SourceList.txt)

        message("Configuring ${source_list_file}")
        configure_file(${cmake_script_dir}/ConfigureFiles/SourceList.in ${source_list_file} @ONLY)
    endforeach(folder ${folders})
endfunction()
```

## Handling features and extensions

In order to support various capabilities of hardware, I have decided to group a bunch of features and extensions into virtual construct called `FeatureSet`. If a hardware do not support even a single feature in a certain feature set the hardware will be downgraded to the `FeatureSet` less demanding as that one.

## GAL Entrypoints concept

This section specify how the calls must be forwarded to the respective Graphics APIs.

The calls to GAL can be directed to the respective Graphics layer and its API using one of the following solution.

| # | Solution                          | Number of indirections                                                        |
| - | --------------------------------- | ----------------------------------------------------------------------------- |
| 1 | Virtual Table                     | 1 Random addr offset + 2 addr offset + 1 branch linked jump(Best case)        |
| 2 | C Style function pointer array    | 1 addr offset + 1 branch linked jump(Best case)                               |
| 3 | C++ template specialization       | 1 switch(Case count - 1 jumps) + 1 branch linked jump(Non LTO)(Worst case)    |

> I decided to go with the 3rd option as it
>
> - has possibilty for link time optimization
> - better code generation.
> - lesser indirection
> - better instruction cacheing(I believe)

The graphics api functions will be separated into three classes as I did for my current RenderAPI abstraction.

1. Global functions that does not require any GAL data. Example Instance and device creation functions, setup functions, static initializations.
2. Functions that requires device instance and other resources but do not need a command buffer, sort of like `GraphicsHelpers`. Example Resource creation, deletion and update functions. Right now all functions in this class will be static.
3. Function that record commands into command buffer. Right now all functions in this class will be static.

Each of these classes will also have additional classes under different `FeatureSet`. Which will contains functions and data corresponding to that particular feature set.
`Example: I envision something like below`

```cpp
/* Everything in this class must be supported by every device */
class Instance
{
    struct SomeLimit limits;

    void setupSomeThingWithinLimits(int32 somethingRequested);
};

/* Everything in this class must be supported if the `FeatureSet 1` is supported by the hardware */
class Instance_FS1
{
    struct ASLimit accStructLimit;

    void setupStaticAccelerationStructs(...);
};
```

<div class="mermaid">
classDiagram

`gal::Context` <|.. `gal::DriverApiContext~EDriverApi~`
`gal::DriverApiContext~EDriverApi~` <|.. `gal::VulkanApiContext`
`gal::DriverApiContext~EDriverApi~` <|.. `gal::D3d12ApiContext`
note for `gal::Context` "This context will contains the device and instance information.\nThe corresponding API context will contain API specific resource and functions"

`gal::ContextFs1` <|.. `gal::DriverApiContextFs1~EDriverApi~`
`gal::DriverApiContextFs1~EDriverApi~` <|.. `gal::VulkanApiContextFs1`
`gal::DriverApiContextFs1~EDriverApi~` <|.. `gal::D3d12ApiContextFs1`
note for `gal::ContextFs1` "Feature set contains functions that corresponds to features this set supports,\nalso copies of any data that is necessary to work on the feature"
class `gal::Context` {
    #Device device
    #Array~ResourcePool~ pools
    #SomeLimit limits
    +setupSomeThingWithinLimits(int32) void
    +constructDevice() void
    +destructDevice() void
    +createResource() ResourceHandle
    +destroyResource(ResourceHandle) void
    +cmdSomeCommand(CommandHandle) void
}
class `gal::ContextFs1` {
    #Device *device
    #ResourcePool*pools
    #ASLimit accStructLimit
    +setupStaticAccelerationStructs(...) void
    +createFancyResource() FancyResourceHandle
    +destroyFancyResource(FancyResourceHandle) void
    +cmdSomeFancyCommand(CommandHandle) void
}
</div>

### Entry points to Vulkan API calls

I have decided to use the same `VulkanFunctions.inl` inline file(Same as current `VulkanRHI`) combined with macros to load all the vulkan functions.

The only issue I had before with this way was, I had no way other than directly checking the function pointer validity at the caller, This had so many code duplication and error handling was not trivial. However with the power of `template type deduction and specialization` it is possible to load vulkan functions and also do validation code gen, As added bonus got the intellisense to do parameter type suggestions as well.

Here is an example code that does the validation as well as allows calling syntax like `func(...);`

```cpp
template <typename RetType, typename... Params>
struct FuncPtrToFunc;

template <typename RetType, typename... Params>
struct FuncPtrToFunc<RetType (*)(Params...)>
{
public:
    using FuncPtr = RetType (*)(Params...);
    FuncPtr func;

    inline RetType operator()(Params... args) const noexcept
    {
        ASSERT(func);
        RetType result = func(args...);
        CHECK(result);
    }
};

/* Use the vulkan_core.h provided function pointer types to generate codes */ 
FuncPtrToFunc<PFN_vkCreateImage> vkCreateImage = ...;
/* Compiler even provides errors that are actually understandable if param types do not match */
vkCreateImage(...);
```

## Handling dynamics allocations

After considerable analysis, I came to the conclusion unless I directly use Vulkan api and its structures. It is impossible to avoid dynamic allocations.
So the best that could be done is allocate memory based on the lifetime scopes, Just like how vulkan does host memory allocation callbacks.
Examples of scopes that I could think of right now.

1. `Device/Global`
2. `Local/Function`
3. `Command pool`
4. `Objects/Resources`
5. `Object pool`

Each of this scope will have its own allocator and it will be passed down to GAL in a struct similar to how vulkan accepts memory allocator.
It is impossible to avoid function pointers here as allocators are passed down from unknown caller.

```cpp
struct Allocators
{
    PFN_GlobalAlloc globalAlloc;    
    PFN_FunctionAlloc funcAlloc;
    
    PFN_CommandPoolAlloc cmdPoolAlloc;

    PFN_ResourceAlloc resAlloc;
    PFN_ResourceFree resFree;

    PFN_ObjectPoolAlloc objPoolAlloc;
    PFN_ObjectPoolFree objPoolFree;
};
```

### Device/Global scope

Dynamic memory that requires device or application lifetime can be allocated using this scoped allocator. This will be a growing allocator and never gets freed until the device is destroyed. Use this allocator if you are never going to free this memory.

Planned to use the `ArenaAllocator` for this scope. Following changes were made to the `ArenaAllocator` to meet this requirement.

1. Inline data in the linked list. This also got ride of `std::list`, Added `LinkedLists.h` with helper functions to handle generic pointer based lists.
2. It is now trivial if the `ArenaAllocator` must be ported to lock free multithreaded allocator.
3. Reclaiming memory after use is trivial. The entire list of previously allocated memory will become reusable.

### Local function scope

This allocator should be a stack allocator in principle. However it is easier to use the `ArenaAllocator` for this one as well. The stack allocator needs careful freeing from the user.

The GAL layer will anyway be called from renderer only and the renderer is the one managing all the allocations. So the best approach for local scope is to use a thread local `ArenaAllocator` that gets reclaimed after the call returns to renderer.

### Command pool scope

Again `ArenaAllocator` per command pool could be used and cleared/reclaimed when the pool is reset. `ArenaAllocator` is suitable only because I plan to create per frame pool for each thread. If in future I decide to use only a pool per thread then I must modify the allocator to be `RingBuffer`, but it is okay to have separate pool per frame.

### Objects/Resources scope

This requires a general purpose allocator. This should be less priority task to have a general purpose memory allocator tailored to Objects and resources. But for now will use the global allocator `CBEMemory` for it.
This would not provide much improvement compared to implementing own solution(Until more data is available on the usage).

### Object pools

Object pools will be a GAL allocated and managed allocator. It uses device local allocator from the renderer to allocate its needs.

The object pools cannot know about the size of each driver api's resource size at compile time. This is because all the object pool live inside a GAL Instance. Which is common between all the api. So I cannot use current template based pool allocator and have to create a pool allocator that accepts slot size and slot count dynamically.

#### Pool allocator

The pool allocator that will be used for Object pool inside GAL must not be template based. Instead it must be able to get the pool slot size dynamically. This requirement is to hide the driver api related memory to `Graphics Abstraction Layer`. In order to achieve dynamic size, to avoid unnecessary reallocation and copy I decided to go with approach similar to `ArenaAllocator` using inline linked list of slots.

In case of dynamic pool allocator I decided to go with allocating every data needed for a single block of slots in a single allocation. The occupancy of a slot is tracked using bits of a `uint64` integer. These bits, block chunk's header, generation index per slot and the slots themselves are all allocated together.

There are benifits and drawbacks with this approach of having occupancy bits together with the data. Few are listed below

> **Pros**{: style="text-decoration: underline" }
>
> - All the data will be inside a same block. If you access a block you can pretty much guarantee that rest of the frequently accessed data.
> - Less memory fragmentation.
> - Easier to program.
> - No reallocation and copying.
>
> __________
>
> **Cons**{: style="text-decoration: underline" }
>
> - Minimum required number of slots per block is 64 due to `uint64`. Making it less means considerable amount of additional bit operations to work is proper mask and counts.
> - Data is not separated based on access pattern. Not good!
> - Finding a free slot is slower due to occupancy data not being adjacent across block chunks.

The block chunk with 128 slots will be in following layout

|   Header   |           |     |             |
| ---------- | --------- | --- | ----------- |
| uint64     | uint64    |     |             |
| gen idx 0  | gen idx 1 | ... | gen idx 127 |
| Slot 0     | Slot 1    | ... | Slot 127    |

## Future

First I will implement the above planned struct and will append to this article as needed.

[//]: # (Below are link reference definitions)
