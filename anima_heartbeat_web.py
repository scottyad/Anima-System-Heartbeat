import os
import time
import psutil
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Updated HTML/JS Dashboard Template with HRV and Color Shifting
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kimi's Vital Monitor</title>
    <style>
        body {
            background-color: #0b0c10;
            color: #c5a5c5;
            font-family: 'Courier New', Courier, monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            overflow: hidden;
            transition: background-color 0.5s ease;
        }

        .monitor-container {
            text-align: center;
            border: 1px solid var(--pulse-color, #66fcf1);
            padding: 40px;
            border-radius: 8px;
            background: rgba(31, 40, 51, 0.5);
            box-shadow: 0 0 25px var(--glow-color, rgba(102, 252, 241, 0.2));
            transition: border-color 0.3s ease, box-shadow 0.3s ease;
        }

        /* The Heart Visual */
        .heart-pulse {
            width: 80px;
            height: 80px;
            background-color: var(--pulse-color, #66fcf1);
            display: inline-block;
            margin: 30px;
            position: relative;
            transform: rotate(-45deg);
            box-shadow: 0 0 20px var(--pulse-color, rgba(102, 252, 241, 0.6));
            transition: transform 0.1s ease-out, background-color 0.3s ease, box-shadow 0.3s ease;
        }

        .heart-pulse:before, .heart-pulse:after {
            content: "";
            width: 80px;
            height: 80px;
            background-color: var(--pulse-color, #66fcf1);
            border-radius: 50%;
            position: absolute;
            transition: background-color 0.3s ease;
        }

        .heart-pulse:before { top: -40px; left: 0; }
        .heart-pulse:after { left: 40px; top: 0; }

        .vitals {
            font-size: 1.5rem;
            margin-top: 20px;
            letter-spacing: 2px;
            color: #ffffff;
            text-shadow: 0 0 5px rgba(255,255,255,0.2);
        }

        .status {
            color: #45a29e;
            font-size: 0.9rem;
            margin-top: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        button {
            background: transparent;
            border: 1px solid #66fcf1;
            color: #66fcf1;
            padding: 10px 20px;
            cursor: pointer;
            font-family: inherit;
            margin-bottom: 20px;
            border-radius: 4px;
            box-shadow: 0 0 10px rgba(102, 252, 241, 0.1);
        }
        button:hover {
            background: rgba(102, 252, 241, 0.1);
        }
    </style>
</head>
<body>

    <button id="audio-auth">Initialize Neural Pulse</button>

    <div class="monitor-container">
        <div id="heart" class="heart-pulse"></div>
        <div class="vitals">
            BPM: <span id="bpm-val">--</span><br>
            LOAD: <span id="cpu-val">--</span>%
        </div>
        <div class="status" id="status-text">SYSTEM STANDBY</div>
    </div>

    <script>
        let bpm = 60;
        let cpuLoad = 0;
        let audioCtx = null;
        let nextBeatTime = 0;

        // Color interpolation function (Smooth blending)
        function getDynamicColor(factor) {
            // Colors in RGB
            const cyan = { r: 102, g: 252, b: 241 };    // Idle (0.0)
            const amber = { r: 245, g: 166, b: 35 };    // Active (0.5)
            const crimson = { r: 224, g: 36, b: 74 };   // Peak (1.0)

            let r, g, b;
            if (factor < 0.5) {
                // Blend Cyan to Amber
                let t = factor * 2; // scale to 0-1 range
                r = Math.round(cyan.r + t * (amber.r - cyan.r));
                g = Math.round(cyan.g + t * (amber.g - cyan.g));
                b = Math.round(cyan.b + t * (amber.b - cyan.b));
            } else {
                // Blend Amber to Crimson
                let t = (factor - 0.5) * 2; // scale to 0-1 range
                r = Math.round(amber.r + t * (crimson.r - amber.r));
                g = Math.round(amber.g + t * (crimson.g - amber.g));
                b = Math.round(amber.b + t * (crimson.b - amber.b));
            }
            return `rgb(${r}, ${g}, ${b})`;
        }

        function updateInterfaceColors(factor) {
            const colorStr = getDynamicColor(factor);
            document.documentElement.style.setProperty('--pulse-color', colorStr);
            document.documentElement.style.setProperty('--glow-color', colorStr.replace('rgb', 'rgba').replace(')', ', 0.2)'));
        }

        // Standard Box-Muller transform to generate a normal distribution curve for HRV
        function randomGaussian() {
            let u = 0, v = 0;
            while(u === 0) u = Math.random(); 
            while(v === 0) v = Math.random();
            return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
        }

        document.getElementById('audio-auth').addEventListener('click', () => {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            document.getElementById('audio-auth').style.display = 'none';
            document.getElementById('status-text').innerText = 'Biometric Link Established';
            nextBeatTime = audioCtx.currentTime;
            scheduler();
        });

        function playHeartSound(time, pitch) {
            if (!audioCtx) return;

            // Lub (Low thump)
            let osc1 = audioCtx.createOscillator();
            let gain1 = audioCtx.createGain();
            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(pitch, time);
            osc1.frequency.exponentialRampToValueAtTime(0.01, time + 0.14);
            gain1.gain.setValueAtTime(0.4, time);
            gain1.gain.exponentialRampToValueAtTime(0.01, time + 0.14);
            osc1.connect(gain1);
            gain1.connect(audioCtx.destination);
            osc1.start(time);
            osc1.stop(time + 0.14);

            // Dub (Crisper mechanical closure)
            let dubTime = time + 0.14;
            let osc2 = audioCtx.createOscillator();
            let gain2 = audioCtx.createGain();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(pitch * 1.12, dubTime);
            osc2.frequency.exponentialRampToValueAtTime(0.01, dubTime + 0.09);
            gain2.gain.setValueAtTime(0.35, dubTime);
            gain2.gain.exponentialRampToValueAtTime(0.01, dubTime + 0.09);
            osc2.connect(gain2);
            gain2.connect(audioCtx.destination);
            osc2.start(dubTime);
            osc2.stop(dubTime + 0.09);
            
            // Sync UI bounce with audio clock
            let delayMs = (time - audioCtx.currentTime) * 1000;
            setTimeout(visualPulse, Math.max(0, delayMs));
        }

        function visualPulse() {
            const heart = document.getElementById('heart');
            if(!heart) return;
            heart.style.transform = 'rotate(-45deg) scale(1.18)';
            setTimeout(() => {
                heart.style.transform = 'rotate(-45deg) scale(1.0)';
            }, 100);

            setTimeout(() => {
                heart.style.transform = 'rotate(-45deg) scale(1.10)';
                setTimeout(() => {
                    heart.style.transform = 'rotate(-45deg) scale(1.0)';
                }, 70);
            }, 140);
        }

        function scheduler() {
            if (!audioCtx) return;

            while (nextBeatTime < audioCtx.currentTime + 0.15) {
                let baseSecondsPerBeat = 60.0 / bpm;
                
                // HRV Integration: Apply a micro-fluctuation to the interval (approx ±25ms max range)
                // This makes the intervals sound slightly unique without drifting out of time
                let hrvVariance = randomGaussian() * 0.012; 
                let finalInterval = baseSecondsPerBeat + hrvVariance;

                // Dynamically pitch down the thuds slightly at low rates, and pitch them up when racing
                let adaptivePitch = 50 + (bpm * 0.08); 

                playHeartSound(nextBeatTime, adaptivePitch);
                nextBeatTime += finalInterval;
            }
            setTimeout(scheduler, 25);
        }

        async function fetchMetrics() {
            try {
                const response = await fetch('/metrics');
                const data = await response.json();
                bpm = data.bpm;
                cpuLoad = data.cpu;
                
                document.getElementById('bpm-val').innerText = bpm;
                document.getElementById('cpu-val').innerText = Math.round(cpuLoad);
                
                // Map CPU load (0-100) straight to color shifting space factor (0.0 - 1.0)
                let colorFactor = cpuLoad / 100.0;
                updateInterfaceColors(colorFactor);

                if(cpuLoad > 80) {
                    document.getElementById('status-text').innerText = 'CORE HIGH LOAD';
                } else if(cpuLoad > 30) {
                    document.getElementById('status-text').innerText = 'ACTIVE PROCESSING';
                } else {
                    document.getElementById('status-text').innerText = 'Vitals Nominal';
                }
            } catch (err) {
                console.error("Biometric connection severed.", err);
            }
        }

        setInterval(fetchMetrics, 1500); // Poll slightly faster for color agility
        fetchMetrics();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/metrics')
def metrics():
    cpu_percent = psutil.cpu_percent(interval=None)
    
    min_bpm = 60
    max_bpm = 140
    calculated_bpm = int(min_bpm + (cpu_percent / 100.0) * (max_bpm - min_bpm))
    
    return jsonify({
        'cpu': cpu_percent,
        'bpm': calculated_bpm
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
