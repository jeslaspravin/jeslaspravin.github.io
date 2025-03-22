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
