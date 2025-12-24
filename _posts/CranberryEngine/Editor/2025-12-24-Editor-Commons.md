---
layout: single
title: "Editor common features and systems"
date: 2025-12-24
excerpt: "Documenting editor common features I have worked on in this page. Archive notes"
categories:
  - cranberry
sidebar:
  nav: "Cranberry"
---


## Deferred Async Tasks

The editor must support asynchronous operations that span multiple frames. The required capabilities are:

1. **Task Enqueueing** – Arbitrary tasks can be queued with an expected completion horizon measured in frames.
2. **Progress Reporting** – Each task maintains an atomic progress counter that is updated as the task advances. The UI can subscribe to these updates to display progress bars or spinners.
3. **Step Count Management** – Tasks are initialized with a known step count. This count is decremented as each step completes, and when it reaches zero an event is broadcast to notify dependent systems.
4. **Non‑Execution Interface** – The deferred‑async interface does not manage execution; it merely reads the progress counter and notifies the UI. Actual step logic resides in separate systems that periodically update the progress.

This design isolates long‑running work from the main rendering thread while still providing real‑time feedback to the user.

## Custom Component Immediate Drawing

Immediate drawing is essential for visualizing custom components (e.g., Spline controllers) and for creating interactive viewport gizmos.

### Assumptions

* Each component class can expose one or more `ViewportDrawInterface` implementations inherited from its base class.
* A `ViewportDrawInterface` is shared across component instances; each instance creates its own drawing context from the interface.
* A `PerObjectDrawer` class can be instantiated per component to cache transient draw state, similar to object‑detail caching.
* The `ViewportDrawInterface` provides a draw API that, when combined with the viewport’s custom ImDraw drawer and the component’s context, satisfies unique rendering requirements.

### Interaction Restrictions

1. **Actors‑Only Selection** – When only actors are selected and no components are selected, all component ImDraw calls are rendered. This enables visualizations such as gizmos in the world editor; the behavior can be toggled via UI options.
2. **Component Selection** – When components are selected, only the ImDraw for those components is rendered. This sub‑selection must be initiated from the owning asset editor; if the editor does not push a sub‑selection, the first rule applies.
3. **Proxy Selection** – Additional handling is required for proxies:
   * **`tf`‑Gizmo Controllable Proxies** – Must implement a specific interface exposing `set`/`get` methods for translation, rotation, and scale in local or global space. These proxies are driven directly by the gizmo.
   * **Internal Proxies** – Managed directly by a `ViewportDrawInterface`; they handle interaction themselves.
   * **Editor‑Selected Proxies** – If a proxy is selected via the asset editor, any `tf`‑gizmo controllable proxy is selected and driven by the gizmo; otherwise, custom proxies are routed through the selection logic of the `ViewportDrawInterface`.

### Required Supporting Components

* **Viewport Draw Interface** – Renders ImDraw per component `ViewportDrawInterface`.
* **Viewport ImDraw Draw Collector** – Wraps the world ImDraw collector, enabling upload of common editor meshes and providing additional drawing helpers.
* **Viewport ImDraw Drawer** – Collects transient draw data per component (`PerObjectDrawer`) to aid rendering.
* **`tf`‑Gizmo Controllable Proxy Interface** – Allows the gizmo to query and set transformed values.
* **Additional Selection Data & Reference Values** – Supplies the necessary context for the gizmo to control components or proxies.
* **`SelectSubObjects` Function** – Enables the asset editor to push selections into the viewport layer.
* **Final Rendering Step** – Uses the `ViewportDrawInterface` and `PerObjectDrawer` to produce the final visual output.
