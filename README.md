# Kotlin OBD2 App

An Android OBD-II diagnostics application built with Kotlin. This project combines real-time vehicle telemetry collection, structured local diagnostic logic, and LLM-assisted analysis to explore how AI can support practical automotive diagnostics workflows.

## Project positioning

This is not just a dashboard app and not just an AI demo.

It is a real-world application prototype built around four layers:

1. **Data acquisition** — collect live vehicle telemetry from Bluetooth OBD2 adapters
2. **Data engineering** — structure, store, and visualize diagnostic data on-device
3. **Deterministic reasoning** — provide a rule-based diagnostic baseline
4. **AI enhancement** — integrate remote LLM diagnosis with prompt construction and guardrails

That combination makes the project relevant to **Applied AI**, especially in the context of intelligent decision-support systems rather than standalone model demos.

## Why this project matters

- Built around a realistic diagnostic scenario instead of a toy AI example
- Connects domain data, software engineering, and AI-assisted reasoning in one end-to-end workflow
- Explores how structured telemetry and controllable baselines can improve the usefulness of LLM output
- Reflects an application-oriented approach to AI systems: collect data, organize it, reason over it, then augment it with model-based interpretation

## What it does

- Connects to paired Bluetooth OBD2 adapters
- Streams live vehicle telemetry to a real-time dashboard
- Stores sessions and samples locally with Room
- Supports a no-hardware demo mode with simulated data
- Tracks trip/session history and supports CSV export
- Runs rule-based diagnosis on saved sessions
- Supports remote LLM-assisted diagnosis through a configurable OpenAI-compatible endpoint

## Applied AI related components

### 1. Structured telemetry ingestion
The app reads OBD2 vehicle parameters through a Bluetooth adapter and organizes them into a usable application-level data flow.

Implemented diagnostic coverage includes **21 OBD2 PIDs**, such as:
- RPM
- Coolant temperature
- Intake temperature
- Throttle position
- Battery voltage
- Engine load
- MAP / MAF
- Fuel trims
- Lambda / equivalence ratio
- Timing advance

### 2. Rule-based diagnostic baseline
Before involving any language model, the project includes a deterministic diagnostic layer. This is important because practical AI systems benefit from a stable baseline that can:
- provide interpretable fallback behavior
- constrain noisy outputs
- create a comparison point for model-assisted reasoning

### 3. LLM-assisted diagnosis
The app supports remote LLM diagnosis by:
- building structured diagnostic inputs from session data
- generating prompt-ready summaries
- sending requests to a configurable remote endpoint
- turning responses into readable diagnostic reports

### 4. Guardrails and validation
LLM output is not treated as blindly trustworthy. The project includes validation and fallback logic so malformed or weak remote output can be constrained and backed off to safer summaries and recommendations.

## Core features

### Live monitoring
- Real-time dashboard for RPM, speed, coolant temperature, intake temperature, throttle position, battery voltage, load, MAP, and more
- Gauge-style widgets and RPM trend chart
- Session statistics such as average RPM, max RPM, and duration

### Diagnostics
- 21 OBD2 PIDs implemented
- Rule-based diagnostic engine for saved sessions
- LLM input preview and remote LLM diagnosis flow with guarded parsing

### Demo mode
- Built-in simulated OBD2 data stream for testing, debugging, and presentation
- Useful when no ELM327-compatible hardware is available

### History and export
- Local persistence with Room
- Trip/session history UI
- CSV export via Android FileProvider

## Tech stack

- Kotlin
- Android Views + ViewBinding
- Room
- Kotlin Coroutines
- MPAndroidChart
- OkHttp
- KSP

## Project structure

```text
app/src/main/java/com/example/myapplication/
├── data/
│   ├── bluetooth/      # OBD2 Bluetooth connection layer
│   ├── local/          # Room entities, DAO, database
│   ├── model/          # OBD command definitions
│   └── repository/     # Data streaming, sessions, diagnostics, LLM integration
├── ui/
│   ├── connection/     # Bluetooth device selection
│   ├── dashboard/      # Live dashboard and charts
│   └── history/        # Session history and reports
├── utils/              # Decoders, exporters, simulation helpers
├── MainActivity.kt
└── MyApplication.kt
```

## Requirements

- Android Studio recent version
- Android SDK 36 / min SDK 24
- Bluetooth-capable Android device
- Optional: ELM327-compatible OBD2 adapter for real vehicle data

## Getting started

1. Clone the repository
2. Open the project in Android Studio
3. Sync Gradle dependencies
4. Run the app on a physical Android device
5. Grant Bluetooth and location permissions when prompted

## Demo mode

If you do not have an OBD2 adapter, you can still use the app:

- From the home screen, open **Demo Mode**
- Or long-press the refresh button in the dashboard to toggle simulation

See [`SIMULATION_MODE.md`](SIMULATION_MODE.md) for details.

## Remote LLM diagnosis setup

The app supports remote LLM diagnosis through Gradle properties.

Example configuration:

```properties
REMOTE_LLM_ENABLED=true
REMOTE_LLM_PROVIDER=openai-compatible
REMOTE_LLM_BASE_URL=https://your-endpoint/v1/chat/completions
REMOTE_LLM_API_KEY=sk-...
REMOTE_LLM_MODEL=gpt-4o-mini
REMOTE_LLM_TIMEOUT_SECONDS=45
```

You can copy the example from [`REMOTE_LLM.example.properties`](REMOTE_LLM.example.properties) into your local `~/.gradle/gradle.properties` or project `gradle.properties`.

## Permissions used

- `BLUETOOTH`
- `BLUETOOTH_ADMIN`
- `BLUETOOTH_SCAN`
- `BLUETOOTH_CONNECT`
- `ACCESS_FINE_LOCATION`
- `ACCESS_COARSE_LOCATION`

## Helpful project docs

- [`PIDS_REFERENCE.md`](PIDS_REFERENCE.md) — implemented OBD2 PID coverage
- [`SIMULATION_MODE.md`](SIMULATION_MODE.md) — demo/simulated data mode
- [`DEBUG_GUIDE.md`](DEBUG_GUIDE.md) — crash/debug notes
- [`DATABASE_FIX.md`](DATABASE_FIX.md) — database-related notes
- [`DATABASE_TEST_REPORT.md`](DATABASE_TEST_REPORT.md) — database testing notes

## Notes

- This project is designed around Bluetooth OBD2 adapters such as ELM327-compatible devices.
- The remote LLM flow is guardrailed, but diagnostic output should still be treated as decision support rather than authoritative repair advice.
- For the best experience, test on a real Android device rather than an emulator.
- From an academic or application perspective, the project is best understood as an **AI-enhanced diagnostic application** rather than a pure machine learning research project.
