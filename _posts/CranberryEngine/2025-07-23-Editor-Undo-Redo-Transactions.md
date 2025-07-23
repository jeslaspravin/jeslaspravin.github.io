---
layout: single
title:  "Editor Undo/Redo"
date:   2025-07-23
excerpt: "Initial design plans for Undo/Redo system in engine editor"
mermaid: true
mathjax: false
categories: 
    - cranberry
header:
    teaser: /assets/images/CranberryEngine/PropertiesEditor.png
sidebar:
    nav: "Cranberry"
---

## Undo/Redo introduction

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

Generally the Undo/Redo system can be implemented using following techniques

- Action based transactions where after an action is performed an undo action gets created and pushed into the transaction list of changes.
- State based where a snapshot before editing an object is taken and after subsequent edits the corresponding diff gets recorded. Upon undo the difference gets reset into snapshot. Upon redo the difference gets applied on snapshot.

## Undo/Redo in my engine

Since I have reflection data and reflected properties, doing state based differencing in a general purpose way is possible.
For other cases that does not come under the state based differencing method must use Action based undoing.

Following are list of components needed for any Undo/Redo system

1. A Transaction that can be rolled back/applied.
2. One or several nested TransactionsLedger to keep track of list of Transactions.
3. Editor system that can begin or end a transaction in sensible way.

### Transaction

Transaction is an object that holds a whole single unit of undo able work.
It may contain several snapshots of several objects and differences of several properties.
It may contain several Undo/Redo actions.

However each of this state/action records must be a separate unit in order to preserve the ordering. This record is called Transaction Record.

Right now I do not have plans to persist transactions or undo/redo buffers across sessions. So I do not even have to worry about linking pointers. That means I can use `ObjectSerializationHelpers::serializeAllFields` or `ObjectSerializationHelpers::serializeOnlyFields` with custom ObjectArchive. Even If I want to persist transactions across session I can include a simple solution to link pointers after load that are not as robust as `PackageSaver` and `PackageLoader`.

Each transaction must expose following APIs

- `beginTransaction` this could just be part of constructor. Here the necessary data structures can be setup.
- `captureObjectBaseline` accepts an Object. Stores a reference to the object and takes the baseline snapshot of the object by serializing all relevant fields. The fields will be serialized with tags that provide the bytes range in which each fields will be stored. The data generated will be put into records lists which will at later point gets processed and trimmed at commit/end transaction.
- `captureMapBaseline` accepts an Object, Map property path from the root object to the property(This is to retrieve the map's pointer even when data gets changed due to parent path changes), Map property itself for quick data retriever interface, Operation to be performed(Add, Modify, Remove), Element key value pair object being edited if operation being performed is not add/create.
- `captureArrayBaseline` accepts an Object, Array property path from the root object to the property(This is to retrieve the Array's pointer even when data gets changed due to parent path changes), Array property itself for quick data retriever interface, Operation to be performed(Add, Modify, Remove), Element object being edited if operation being performed is not add/create, Element index.
- `captureSetBaseline` accepts an Object, Set property path from the root object to the property(This is to retrieve the Set's pointer even when data gets changed due to parent path changes), Set property itself for quick data retriever interface, Operation to be performed(Add, Modify, Remove), Element object being edited if operation being performed is not add/create.
- `addAction` custom action that must be applied by a record.
- `endTransaction` Which goes through each record and does the post processing like memory trimming of captured properties.

In all the above capture cases each call creates a new record at the end of list. Exception to this is when doing `captureObjectBaseline` where the subsequent captures gets merged into the first captured snapshot of the object. This is to keep the differences unified to a single entry.

### TransactionsLedger

This ledger create a new Transaction for each begin and end of named transactions. Whenever an undo/redo request happens a single transaction is undone or redone.

I am planning to have only one ledger for my entire engine.
This might not make things clear when undo/redo is triggered as they are global and might affect any asset from any window. However If I feel like adding more ledger in a stack is easier to get it working I will do that.
One issue I see right now with having separate ledger per tab is objects are shared between three tabs when editing. So the only solution even when I enable multiple ledger is to have a ledger per window attached to main tab. Since this will most likely be a separate editor window. Global ledger will be used only by the main world viewport residing window.

Whenever things gets undone the transaction must be transferred to redo queue. Whenever new transaction gets added all the transactions in redo queue must be cleared.

## Changes required for property editor

Since ImGui is immediate mode GUI and I do not want to take baseline snapshots more than necessary, I have to update the field contexts to retain the values and commit them to object only when it gets committed.
This means when generating the context the initial values must be retained.
