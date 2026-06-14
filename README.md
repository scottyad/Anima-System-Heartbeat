# Anima-System-Heartbeat 🫀

A lightweight biometric hardware monitor layout that maps your local hardware's physical strain into an organic, real-time visual and auditory pulse. 

This repository includes both a borderless desktop widget version and a local web dashboard version.

## Features
- **Anima Desktop Widget (`kimi_desktop_pulse.py`):** Lives directly on your Linux desktop as a floating asset. Click and drag to place it anywhere; **Right-Click** anywhere on the heart to exit cleanly.
- **Web Dashboard (`kimi_heartbeat.py`):** A lightweight Flask-based web layout with a stylized CSS pulse and full metric breakdowns.
- **Unified Stress Tracking:** Samples both CPU usage and NVIDIA GPU utilization, using the dominant load factor (`max(cpu, gpu)`) to drive the pulse engine.
- **Heart Rate Variability (HRV):** Incorporates Gaussian distribution variance to create natural microscopic interval fluctuations, avoiding robotic metronome timing.
- **Thermal Color Shifting:** Dynamically shifts gradients across a live color space based on load intensity: **Cyan (Idle)** ➔ **Amber (Active)** ➔ **Crimson (Peak Stress)**.
- **Native Audio Streams:** Pipes raw 16-bit signed PCM thumps straight into `aplay` asynchronously, eliminating external audio server deadlocks.

## Prerequisites
This project requires Python 3 along with package bindings for system monitoring and NVIDIA management libraries:

```bash
pip install flask psutil nvidia-ml-py
