package com.example.myapplication.data.repository

object VehicleQaKnowledgeCatalog {

    val sources: List<VehicleQaKnowledgeSource> = listOf(
        VehicleQaKnowledgeSource(
            id = "obd2_pids_wiki",
            title = "OBD-II PID reference",
            url = "https://en.wikipedia.org/wiki/OBD-II_PIDs",
            keywords = listOf("pid", "obd", "rpm", "coolant", "maf", "map", "throttle", "lambda", "fuel trim", "battery"),
            summary = "General OBD-II PID meaning, formulas, and interpretation."
        ),
        VehicleQaKnowledgeSource(
            id = "fuel_trim_diagnostics",
            title = "Fuel trim diagnostics guide",
            url = "https://www.underhoodservice.com/understanding-short-term-and-long-term-fuel-trims/",
            keywords = listOf("fuel trim", "stft", "ltft", "lean", "rich", "mixture", "injector", "vacuum"),
            summary = "How to read short-term and long-term fuel trims in drivability diagnostics."
        ),
        VehicleQaKnowledgeSource(
            id = "coolant_overheat_basics",
            title = "Engine overheating basics",
            url = "https://www.firestonecompleteautocare.com/blog/maintenance/engine-overheating-causes/",
            keywords = listOf("coolant", "temperature", "overheat", "thermostat", "radiator", "fan"),
            summary = "Common causes and checks for overheating symptoms."
        ),
        VehicleQaKnowledgeSource(
            id = "battery_voltage_basics",
            title = "Battery and charging voltage basics",
            url = "https://www.jdpower.com/cars/shopping-guides/what-should-a-car-battery-voltage-be-while-running",
            keywords = listOf("battery", "voltage", "charging", "alternator", "electrical"),
            summary = "Normal battery and charging system voltage ranges."
        ),
        VehicleQaKnowledgeSource(
            id = "oxygen_sensor_basics",
            title = "Oxygen sensor and lambda basics",
            url = "https://www.walkerproducts.com/oxygen-sensor-training-guide/",
            keywords = listOf("oxygen sensor", "o2", "lambda", "air fuel", "equivalence ratio", "exhaust"),
            summary = "How oxygen sensor and lambda data are used in diagnostics."
        ),
        VehicleQaKnowledgeSource(
            id = "maf_sensor_basics",
            title = "MAF sensor basics",
            url = "https://www.hella.com/techworld/ae/technical/sensors-and-actuators/mass-air-flow-sensor/",
            keywords = listOf("maf", "mass air flow", "air flow", "intake", "sensor"),
            summary = "MAF sensor failure symptoms and interpretation."
        ),
        VehicleQaKnowledgeSource(
            id = "map_sensor_basics",
            title = "MAP sensor basics",
            url = "https://www.hella.com/techworld/ae/technical/sensors-and-actuators/map-sensor/",
            keywords = listOf("map", "manifold pressure", "intake manifold", "vacuum", "boost"),
            summary = "MAP sensor use and manifold pressure interpretation."
        )
    )

    fun matchSources(question: String, input: LlmDiagnosticInput, maxSources: Int = 3): List<VehicleQaKnowledgeSource> {
        val normalized = (question + " " + input.ruleSummary.summary + " " + input.ruleSummary.findings.joinToString(" ") { it.title + " " + it.detail })
            .lowercase()

        val scored = sources.map { source ->
            val keywordHits = source.keywords.sumOf { keyword ->
                if (normalized.contains(keyword.lowercase())) 3 else 0
            }
            val titleHit = if (normalized.contains(source.title.lowercase())) 2 else 0
            val summaryHit = source.summary.lowercase().split(" ").count { token ->
                token.length > 3 && normalized.contains(token)
            }
            source to (keywordHits + titleHit + summaryHit)
        }
            .filter { it.second > 0 }
            .sortedByDescending { it.second }
            .map { it.first }

        return when {
            scored.isNotEmpty() -> scored.distinctBy { it.id }.take(maxSources)
            else -> sources.take(maxSources)
        }
    }
}
