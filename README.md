# Kotlin OBD2 App

Android OBD-II diagnostics app built with Kotlin. It connects to Bluetooth OBD2 adapters, streams live vehicle telemetry, stores drive sessions locally, supports demo/simulation mode, and can generate diagnostic reports from rule-based or LLM-assisted analysis.

## What it does

- Connects to paired Bluetooth OBD2 adapters
- Displays live dashboard metrics and RPM trends
- Supports a no-hardware demo mode with simulated vehicle data
- Stores sessions and samples locally with Room
- Shows trip/session history and exports CSV data
- Runs rule-based diagnosis on saved sessions
- Supports remote LLM diagnosis through a configurable OpenAI-compatible endpoint

## Core features

### Live monitoring
- Real-time dashboard for RPM, speed, coolant temperature, intake temperature, throttle position, battery voltage, load, MAP, and more
- RPM line chart and gauge-style widgets
- Session statistics such as average RPM, max RPM, and duration

### Diagnostics
- 21 OBD2 PIDs implemented
- Rule-based diagnostic engine for saved sessions
- LLM input preview and remote LLM diagnosis flow with guardrails

### Demo mode
- Built-in simulated OBD2 data stream for testing and presentations
- Useful when no ELM327/OBD2 hardware is available

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
- The remote LLM flow is guardrailed, but diagnostic output should still be treated as assistance rather than authoritative repair advice.
- For the best experience, test on a real Android device rather than an emulator.
