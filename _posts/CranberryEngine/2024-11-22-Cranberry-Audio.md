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
    sound ||--|| dat_src : uses
    engine ||--|| dev_frames : generates
    dev_frames ||--|| dev : "copied to"
    enc_audio ||--|| decoder : "decoded by"
    decoder ||--|| raw_pcm : "outputs"
    dat_src ||--|| raw_pcm : "encapsulates"

    ctx["Context"]
    dev["Device"]
    engine["Engine"]
    listener["Directional Listener"]
    sound["Sound(Equivalent to audio play instance)"]
    dat_src["Data Source"]
    dev_frames["Device frames"]
    node["Node"]
    eng_node["Engine Node"]
    node_graph["Node Graph"]
    enc_audio["Encoded Audio"]
    decoder["Decoder"]
    raw_pcm["Raw PCM frames"]
</div>

### Device

- The device can be created with device default sampling rate, format, channel count. The `ma_device_init` method takes care of filling these information into device.
- Specify the an unit time period in milliseconds or specify frames count per period directly. This will be used together with sample rate to calculate the buffer count and size in bytes per callback required.

### Engine

- The engine must be created for each unique combination of device config. So if changing device config or device, the engine and all its related object must be recreated.
- The listeners are basically for directional sounds and there can be maximum of four. Listener configs must be set after engine is created.
- The engine generates frames for a device using the sounds, data sources and listeners.
- Allocation callbacks will be used for dynamically allocating engine nodes for sound and other sub nodes. So this must not be arena with engine lifetime.
- Engine will be exposed as engine but instead of one to one. There will be only one audio engine for a world. A miniaudio engine per audio device will be encapsulated inside the one audio engine to accommodate multiple local players with separate audio devices.

### Sound

- A sound node can be attached as input to another node.
- A data source sub range can be used when playing in sound.
- Data source sub range is different from looping range so I assume a single data source and sound is enough to play 3 section audio(Start-Loop-End).
- The flags can be used to specify if want to decode at play. However it is best to decode the audio before using decoder and then use it as data in data source.
- Sounds will be exposed as audio player or controller.

### Data Source

- MiniAudio works with custom data source using virtual interface with C-Style virtual table.
- Uses C-Style template with type being casted to `ma_data_source_base *`. So whatever type pointer is passed into `ma_data_source_*` functions it must have `ma_data_source_base` as base data/at zero offset.
- Best to have raw data without encoding.
- Data source will be exposed as audio resource interface and will be created by engine assets.

### Decoders

- Supported formats
  - MP3
  - WAV
  - FLAC
  - VORBIS(If including stb VORBIS source)
- Each decoder is created for a unique audio. So decoders must be created for each audio data separately.
- In our case this means just decode from memory.
- These decoders will be exposed as functions rather than as object in engine as part of `ICbeAudioModule` interface.

### Node graph

- Engine is the node graph into which all the other node graph and sounds plug into as the endpoint.
- Only difference about node graph from regular graph is each input bus index of node graph can accept several inputs. Each inputs gets mixed together. That is how several sounds or sound graphs can be plugged into the engine end point input.

## Designing the engine interface

Notes on points to consider when designing the engine interface.

- In order to reduce the resampling of the audio frames and recreating data sources. The sample rate of each data source must match that of each engine. The format and channel count could differ though.
- The devices must be created with sampling rate the engine targets instead of device default. This ensures we can use the same data source for all devices and engines.
- Engine and all the sound sources must be recreated after changing the device. However there will be only one cranberry audio engine and remains the same, similar setup works for the sounds as well.
- There will be only `MAX_LOCAL_PLAYERS` count of engines, So for each cranberry engine sound player there could be `MAX_LOCAL_PLAYERS` number of sounds.
- In case of sound graphs I want to keep the graphs independent of the engine. Since input sound nodes are the only variable across engines and devices, custom miniaudio sound nodes must be created that fetches PCM frames from different sound based on which mini audio engine is reading the frames.
- Sound graphs must be created from some high level graph structure(Created from UI) the total number of nodes, their types and memory requirements can be precalculated. This makes it possible to not have separate node resources in Audio module interface.
- Inputs of sound graph will be the data sources/Audio resources. The audio resources themselves will contain the link to sound resource created from data source in the engine.
- Following resources must be independent of the engine/devices
  - Data sources/Audio resources
  - Sound graphs
- Following resources are unique to engine and must retain the create configuration.
  - Sound/Audio player
