---
layout: single
title:  "Cranberry audio"
date:   2024-11-22
excerpt: "Notes on adding and wrapping audio library to cranberry"
mermaid: true
categories: 
    - cranberry
sidebar:
    nav: "Cranberry"
---

## Cranberry audio intro

{: .notice--warning}
**Attention**{: .notice-warn-header} Work in progress

Audio programming is conceptually simple however writing it correctly is not an easy task. So I chose to use existing libraries.
After skimming through few audio library's(`sdl`, `miniaudio`, `wwise` and `fmod`) documentations, I decided to go with `miniaudio`{: .jpblog_emphasized } and base my wrapper on it.
Why `miniaudio`?

- Open source MIT
- Thin platform wrapper
- Freedom to override any system in the library to my satisfactory.

## MiniAudio notes

<div class="mermaid">
---
title: MiniAudio Objects Relations
---
erDiagram
    ctx ||--o{ dev : enumerates
    ctx ||--o{ engine : "linked to"
    node_graph ||--|| node : extends
    eng_node ||--|| node : extends
    engine ||--|| node_graph : extends
    engine ||--|| dev : uses
    engine ||--|{ listener : contains
    engine ||--|{ sound : plays
    sound ||--|| eng_node : extends
    engine ||--|| dev_frames : generates
    dev_frames ||--|| dev : "copied to"
    ctx["Context"]
    dev["Device"]
    engine["Engine"]
    listener["Directional Listener"]
    sound["Sound(Equivalent to audio play instance)"]
    dev_frames["Device frames"]
    node["Node"]
    eng_node["Engine Node"]
    node_graph["Node Graph"]
</div>

### Device

- The device can be created with device default sampling rate, format, channel count. The `ma_device_init` method takes care of filling these information into device.
- Specify the an unit time period in milliseconds or specify frames count per period directly. This will be used together with sample rate to calculate the buffer count and size in bytes per callback required.

### Engine

- The engine must be created for each unique combination of device config. So if changing device config or device, the engine and all its related object must be recreated.
- The listeners are basically for directional sounds and there can be maximum of four. Listener configs must be set after engine is created.
- The engine generates frames for a device using the sounds, data sources and listeners.

### Sound
