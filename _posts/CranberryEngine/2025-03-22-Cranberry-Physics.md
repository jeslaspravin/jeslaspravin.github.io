---
layout: single
title:  "Cranberry physics"
date:   2025-03-22
excerpt: "Notes on adding and wrapping physics engines to cranberry"
mermaid: true
mathjax: true
categories: 
    - cranberry
sidebar:
    nav: "Cranberry"
---

## Cranberry physics intro

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

I want physics, ability to query the scene for purposes like audio occlusion and of course for game play queries.
I took a look at Bullet and Jolt, decided to go with Jolt due to following reasons.

- Open source MIT
- Multithreaded
- Probably good enough for most of the use case I will ever have
- JobSystem integration is supported and simple
- Customizable filters are good enough to support my use cases

## Jolt physics engine notes

### Integrate Jolt JobSystem

Jolt's JobSystem is just an interface with few simple rules.

- Jobs are created and destroyed with this interface.
- Each job can be included in only one barrier this makes things so much simpler.
- JobSystem, Barrier, Jobs has to be overridden to support custom behavior.
- Jobs are reference counted and lifetime is managed by that.

The goal here is to integrate the Jolt job system interface to use engine's global JobSystem. Since our JobSystem supports single threaded mode we need two of job system and other interface implementations. One for full multithreaded mode with at least 1 worker thread and another for single threaded mode where each job on enqueue gets executed immediately.

Before we can start looking at JobSystem itself we have to provide a custom implementation for Barriers.

#### Barriers

Barriers are just a collection of Jobs that can be waited on for completion.
It has two function `AddJob` and `OnJobFinished` exposed as interface.

In our case

- `AddJob` just adds job handle or reference to a thread safe linked list. Adding a Job to barrier must add a reference to reference counter.
  Destroying barrier will wait for all tasks to complete.
- `OnJobFinished` does not have to do anything as Job enqueueing happens at either Job construction if no dependencies or when number of dependencies drops to 0.

Barrier can use same implementation for both Single and Multithreaded mode. Exception is when waiting.

`Wait` function flow

- In single threaded mode, Go through each job in the list
  - Execute the ones that can be executed. Executing is not needed as enqueueing must execute the whole tree however it is okay to execute here as well.
  - Remove the jobs that are done.
  - Do this until there is until there is no more Jobs.
  - Assert the list is empty to make sure there is no missing dependencies.
  - Clear the rest of the jobs.
- In multithreaded mode the steps are bit different. We can also assume that barrier never gets waited from a worker thread as Jolt never uses barrier as a way to manage dependencies between jobs. This assumption or fact makes dead lock related issues to not happen when worker threads uses different queues. If inter job dependencies are handled using Barrier then we have problem if barrier wait is queued before queueing the dependent job in the same queue. In this case barrier waits for job queued in thread's same queue which has no chance to dequeue, there by creating dead lock.
  - CAS get the linked list head with `nullptr`. This is to prevent further adding of jobs to same linked list.
  - Count the number of jobs that are already enqueued or waiting for dependencies using some custom data structure.
  - Collect those enqueued jobs in another container to be used with `copat::awaitAllTasks`.
  - Now wait for jobs using `copat::waitOnAwaitable`
  - Remove the done jobs from the linked list.
  - Repeat the steps 2 to 5 until there is no more done jobs cleared from linked list.
  - Assert the list is empty to make sure there is no missing dependencies.
  - Clear the rest of the jobs.

#### Job

Each Job must hold some custom data to track coroutine and the job enqueued into the CoPaT JobSystem. Even though the Jolt's Job has a done status check it cannot alone be relied of if going to destroy a coroutine. As coroutine might still be in progress even after the Jolt job is done.

Instead of overriding the Job I decided to contain the Job inside a JobPacket in cranberry engine.

```cpp
namespace cbe::physics
{
struct JobPacket
{
    JPH::Job joltJob;
    /* Inline chain to next entry in Barrier's Job list, Do not need atomic here as head in Barrier will be atomic */
    JobPacket *barrierNext;

    struct MultiThreadData
    {
        CopatTask task;
        /* For tracking if job is already enqueued, This is necessary since Barrier works outside the coroutine framework of CoPaT JobSystem */
        std::atomic_bool bEnqueued;
    };
    struct SingleThreadData
    {
        JobPacket *next;
    };
    /* MultiThreadData task data is not needed for single threading */
    union
    {
        MultiThreadData mt;
        SingleThreadData st;
    } taskData;
};
}
```

This way we can easily interop between JobPacket and Job.

#### JobSystem

There will be two implementation of JobSystem and one selected based on the multithreading constraints in CoPaT's JobSystem.

In single threaded mode

- `GetMaxConcurrency` always returns 1
- `CreateJob` will create jobs from a preallocated pool until it gets exhausted.
- `FreeJob` returns the Job to preallocated pool or free the dynamically allocated memory.
- `CreateBarrier` will create from a preallocated pool until it gets exhausted.
- `DestroyBarrier` returns the barrier to preallocated pool or free the dynamically allocated memory.
- `WaitForJobs` will call the single threaded variant of wait in Barrier implementation.
- `QueueJob` and `QueueJobs` immediately executes based on reentrant condition. Enqueueing while reentering will add the Job to `JobPacket::taskData.st.next` in JobSystem's queue list.

In multithreaded mode

- `GetMaxConcurrency` returns number of worker threads in `copat::JobSystem`.
- `CreateJob` will reuse already allocated job from a thread safe ring buffer pool. If no free jobs exists new job gets allocated and used.
- `FreeJob` returns the Job to ring buffer. If ring buffer is full frees the allocation.
- `CreateBarrier` Barriers are sparsely created so now it will be pool allocated. New barrier gets allocated from this thread unsafe pool allocator inside a lock.
- `DestroyBarrier` returns the barrier to the thread unsafe pool allocator inside lock.
- `WaitForJobs` will call the multi threaded variant of wait in Barrier implementation.
- `QueueJob` and `QueueJobs` Queues the Job for execution wrapped inside a coroutine. Fills the `JobPacket::taskData.mt` with task details.

### Filter interfaces

The physics engine's collision or queries system can be controlled to provide customized behavior required for engine using several filter or table interfaces.
This is where the collision profiles of engine can be integrated.

Each of the collision or query starts from the `BroadPhaseQuery` then to `NarrowPhaseQuery` using body and shape. Each body has an `ObjectLayer` associated with it which is very important for filtering efficiently.
In order to filter at Broad Phase the `BroadPhaseLayer` will be used. Each ObjectLayer must be associated with a `BroadPhaseLayer` and keeping number of broad phase layer as low as possible is important. Each broad phase layer has its own unique quad tree of AABBs where all the Bodies with mapped ObjectLayer gets added to.

#### BroadPhaseLayerInterface and ObjectVsBroadPhaseLayerFilter

This mapping of ObjectLayer to BroadPhaseLayer is provided by `BroadPhaseLayerInterface`. For now I have decided to have only three BroadPhaseLayers

1. Moveable - For all ObjectLayer that can be moved and cannot be made moveable later. Like static level objects that has no interaction possible other than block collision and world queries.
2. NonMoveable - For all ObjectLayer that can be moved even if created as static body and later moved using `SetPosition`.
3. Triggers - For all ObjectLayer that can be used as triggers or sensors.

The `ObjectVsBroadPhaseLayerFilter` interface is what is used to determine if an ObjectLayer can collide with a BroadPhaseLayer. The ObjectLayer comes from body being tested. The BroadPhaseLayer comes from the BroadPhase tree that is being tested in.

#### ObjectLayerPairFilter

Once BroadPhase filter is successful for each Body's AABB in tree `ObjectLayerPairFilter` is invoke to decide whether to consider the Object layer each body belongs to. This check is done once for all the continuous bodies with same ObjectLayer, keep this in mind when deciding on what data to encode into ObjectLayer.

#### GroupFilter

GroupFilter is described to be used to filter simulation collisions at the global common level. The groups and subgroups can be assigned to each body to control the collisions. This GroupFilter is a way to simplify for an instance sub body collisions without expensive logics.

Some example use case will be

- Disable collisions between each adjacent elements in chain to keep the stability of the chain.
- Disable inter body smi collision between small moving parts in vehicles.

Right now I do not need GroupFilters for my use case but as soon as I have one I will update here on what and how to approach the case.

#### BodyFilter

This filter is used for queries and must be passed in with queries. So depending upon what is requested in a query we can issue different filter to support wider use case.

However the most important part I have in my mind right now is if we use a collider for both querying and simulation then we need to do additional look ups here to eliminate sim results.
The way we do this checks and elimination depends on how we encode the ObjectLayer date into body and body user data.

#### ShapeFilter

This filter is used for queries and must be passed in with queries. So depending upon what is requested in a query we can issue different filter to support wider use case.
However right now I do not see a point to have this implemented. As shapes alone might not be enough to check advanced filtering.

One use case I can think of is filter out complex shapes like mesh shape to reduce query complexity.

#### SimShapeFilter

`SimShapeFilter` is used for sim to filter out shapes for each body here we can filter bodies based on data from userdata.

Example use cases

- Simple LOD between mesh shape and simple shape.
- Filter out ObjectLayer mask if the body is used for querying too.

#### ContactListener

`ContactListener` is event callback to listen to and reject specific contact points. I do not have any use for this now.

#### Summary

Here is a short diagram of what I envision the filter interface will do in my engine now.

<div class="mermaid">
---
title: Flow
---
flowchart LR
subgraph BroadPhase
    subgraph olf_block["Object layer filter"]
        direction BT
        olf["Object
        layer filter"]
        olf_cmt@{ shape: braces, label: "In my engine
        this will be used to filter
        both query and sim filter mask
        encoded in **ObjectLayer**" }
        olf_cmt -.- olf
    end
    bpf["Broad phase
    layer filter"]
    bpf -- "`Select broad
    phase tree`" --> olf_block
end

subgraph cqf["Collision Query Flow"]
    direction LR
    subgraph bf_block["Body Filter"]
        direction BT
        bf["Body filter"]
        bf_cmt@{ shape: braces, label: "This filters out
        sim only filter
        mask from positive
        results of previous stage" }
        bf_cmt -.- bf
    end
    subgraph sf_block["Shape Filter"]
        direction BT
        sf["Shape filter"]
        sf_cmt@{ shape: braces, label: "This can be used for
        additional filters like
        whether to enable
        complex shapes like triangle mesh" }
        sf_cmt -.- sf
    end
    subgraph cc_block["Collision Collector"]
        direction BT
        cc["Collision Collector
        (AddHit)"]
        cc_cmt@{ shape: braces, label: "Custom collector if required can be implemented here." }
        cc_cmt -.- cc
    end
    olf_block -- "`Check AABB
    of bodies`" --> bf_block
    bf_block -- "`Iterate
    shape pairs or
    shapes`" --> sf_block
    sf_block -- "`Detect collisions
    between selected
    shapes or shape pairs`" --> cc_block
end

subgraph scd["Sim collision detection"]
    direction LR
    subgraph gf_block["Group Filter"]
        direction BT
        gf["Group Filter"]
        gf_cmt@{ shape: braces, label: "This can be used to
        filter collisions using
        group and subgroup IDs.
        Example to skip collisions in
        a chain of bodies to immediate
        next body for stability" }
        gf_cmt -.- gf
    end
    subgraph ssf_block["Sim Shape Filter"]
        direction BT
        ssf["Sim Shape filter"]
        ssf_cmt@{ shape: braces, label: "This can be used for
        additional filters like
        whether to enable
        complex shapes like triangle mesh,
        select LOD and
        most importantly
        filter out query only filter
        mask from positive
        results of previous stage" }
        ssf_cmt -.- ssf
    end
    subgraph cl_block["Contact Listener"]
        direction BT
        cl["Contact Listener"]
        cl_cmt@{ shape: braces, label: "Callback to listen to
        and reject specific contact point." }
        cl_cmt -.- cl
    end
    cp["Contact Points"]
    olf_block -- "`Check AABB
    of bodies`" --> gf_block
    gf_block -- "`Iterate
    shape pairs`" --> ssf_block
    ssf_block -- "`Detect collisions
    between shape pairs`" --> cl_block
    cl_block -- "`If not rejected`" --> cp
end

</div>

## Engine physics

For optimizing the collision detection as mush as possible I have decided to make each physics body to have separate mask of `ObjectLayers`.
However for coarse `Object layer filter` these two will be encoded into the `ObjectLayer` of each body.
Since each mask must be tested against another body's Object layer itself we need to store both Object layer and body's Object layer response.
For this to work we need following conditions

- Change Jolt to use 32bit for ObjectLayer, this can be done using `-DOBJECT_LAYER_BITS=32` cmake config
- Limit maximum number of Engine Object Layers to `26(0-25)`. This is to use the higher 26 bits of ObjectLayer as body response mask for both simulation and query combined.
- Use `one bit` for determining whether the mask has simulation response in it. Why simulation instead of query? This can be used to quickly reject simulation request if the there the body is never used for simulation. Where as for query if needs additional checks if sim is enabled to be sure if body needs to respond.
- Use `5bits` for storing the body's Object layer itself
- ObjectLayer filter will filter layers coarsely
- `BodyFilter` or `SimShapeFilter` filters the based on body's sim or query response mask based on the filter used.

```cpp
namespace cbe::physics
{
// same as sizeof(JPH::ObjectLayer) == 32bit
struct ObjectLayer
{
    uint32 bodyLayer : 5;
    uint32 isSimMask : 1;
    uint32 responseMask : 26;
};
}
```

These are the only special and most important case when it comes to filtering need to be handled by physics engine. Rest of the settings can be created 1:1 with Jolt to keep the interface simple.
