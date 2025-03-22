---
layout: single
title:  "Cranberry Object Garbage Collector"
date:   2024-12-30
excerpt: "Improving the Garbage Collector of Cranberry Objects"
mermaid: true
mathjax: true
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/GC_AI_Generated.webp
sidebar:
    nav: "Cranberry"
---

## Existing GC and What to improve

The current GC goes through all the fields of each objects to collect references of other objects. Then goes through each objects and replaces the pointer in case the objects gets deleted.
This is brute force collecting and could be improved. Then the GC is single threaded and cannot run in worker threads. Yielding is not very cooperative once GC starts.

So the points I want to improve are

- Multi thread the GC.
- Reduce the overhead at collecting the references.
- Reduce the overhead at replacing/deleting the references.
- Have reference collection for classes that uses Raw pointer as worst case fallback.
- Better thread yielding.

## GC Idea

Since GC in our case only deal with `cbe::Object` which is a class with virtual interface, the availability of `cbe::ObjectAllocator<Class>` and `CoreObjectsDB`. The GC could use some shortcuts to get better performance. The ideas are listed below.

- When I first created the Objects system I did not had a Job system/scheduler. But now I have and will use it to achieve multi threading with cooperative scheduling.
- Objects pointer alone have to be tracked. This reduces need to check and track every pointers.
- I will introduce a new `ObjectPtr<Class>` to use instead of Raw pointers. This allows having reference counting embedded into fields of Objects.
- GC will cache all raw pointer fields per class to allow faster traversal in case of classes with Raw pointers. Such a classes must be minimal.
- `IReferenceCollector` interface will be supported and it must be minimal in count too.
- Always run GC in low priority queue.

### What makes an object valid

The following list will be checked only if none of the object and its parents are marked for delete. So if Object or any of its parent has [object flags] `cbe::EObjectFlagBits::ObjFlag_MarkedForDelete` then Object will always be deleted.

- If an Object is a `cbe::Package` and has at least one [subobject]
- If an Object is referred by one of the instances of `IReferenceCollector`
- If an Object is referred in one of the raw pointers of Objects that are not [subobject] of the Object.
- If an Object is referred in one of the `ObjectPtr` of Objects that are not [subobject] of the Object.
- If an Object has [object flags] `cbe::EObjectFlagBits::ObjFlag_RootObject | cbe::EObjectFlagBits::ObjFlag_Default`

## Improvements and Details

- **Raw pointers** The raw pointer work flow remains the same except the pointer fields will be cached
- **`ObjectPtr`** This add reference to the reference counter that will be part of `CoreObjectsDB`.
  - **Note** Below points are obsolete as objects when referred inside containers will not be possible to reverse retrieve. However storing the list of referrer is still better way to avoid scanning all objects.
  - **Obsolete** The `ObjectPtr *` gets added to referrer list of referred object in `CoreObjectsDB`.
  - **Obsolete** In order to support getting referrer object from `ObjectPtr *` we need help from `cbe::ObjectAllocator<Class>`.
  - **Obsolete** By using `ObjectPtr *` we can skip scanning all object's `ObjectPtr` field when object being deleted.
  - **Obsolete** This address to object look back can be done using `vtable *`

### Scaffolding

- Required to expand `RTTI` to support new property type `Template` that support structure with single template type. This is to support `ObjectPtr` and more.
  - May require rewriting some of ModuleReflect tool.
- **Obsolete** Support retrieval of Object pointer from any address in `cbe::ObjectAllocator<Class>`
- Support tuple of vector of types in `SparseVector` as `SparseVectorTuple` and in `FlatTree`. This is to allow multiple stream independent types of Sparse array but with single tracking data structure.
- Support in `copat::JobSystem` to allow checking if current thread's Job Queue has jobs.

## GC Steps

- GC starts by collecting list of all objects from each `cbe::ObjectAllocator<Class>` in main thread. Now GC knows all the objects it will work with this frame.
- In worker thread GC starts by marking all objects with valid conditions as valid *exception* being if not already marked for delete or condition from reference counting.
- In worker thread mark objects as valid based on `ObjectPtr` references and references from Raw pointer.
- In worker thread collect the list of Objects to delete.
- In main thread mark the Invalid Objects with `cbe::EObjectFlagBits::ObjFlag_MarkedForDelete` [object flags]. Do this few objects per frame.
- In worker thread collect the list of `ObjectPtr` and `raw pointers` to null.
- In main thread null the pointers.
- In worker thread collect the list of Object to destroy. check the reference count of `ObjectPtr` one last time before adding to destroy list.
- In main thread destroy the objects few objects per frame.
- In worker thread clean up the GC and get ready for next GC.

## Terms

- <a id="term-subobject">`subobject`</a> Cranberry Objects might have outer objects except few root objects like package. These objects with outer are subobjects of the outer.
- <a id="term-obj-flags">`Object flags`</a> Cranberry Objects have bit flags to mark important core information.

[//]: # (Below are link reference definitions)
[subobject]: #term-subobject
[object flags]: #term-obj-flags
