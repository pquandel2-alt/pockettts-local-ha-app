# PocketTTS Local INT8

High-performance offline German Text-to-Speech for Home Assistant using PocketTTS C++, ONNX Runtime INT8 and Wyoming streaming.

- Native C++ engine ([PocketTTS.cpp](https://github.com/netai369/PocketTTS.cpp-multilingual), commit `3ed176a`) with ONNX Runtime 1.23.2, CPU only. Main model in FP32 (clear speech, < 1 % dropped words), other models INT8.
- **Real streaming:** audio chunks go out while the sentence is still being generated (first audible chunk after ~0.55 s, measured).
- Eleven German voices (default `juergen`), German number/time/unit normalization, fully offline after a one-time model import.
- Announces itself to Home Assistant via Wyoming discovery.

**Wichtig / Important:** The model weights are access-restricted (Kyutai) and are **not** part of this app. Import your own
model pack once, see the *Documentation* tab (`DOCS.md`).

Nur amd64 · only amd64.
