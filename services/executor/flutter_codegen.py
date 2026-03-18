from __future__ import annotations

from pathlib import Path


class FlutterCodeGenerator:
    def is_session_dashboard_scope(self, summary: str, labels: list[str]) -> bool:
        haystack = f"{summary} {' '.join(labels)}".lower()
        keywords = (
            "session dashboard",
            "dashboard",
            "timeline",
            "diagnostics",
            "observability",
            "pr/jira",
            "live status",
        )
        return any(k in haystack for k in keywords)

    def write_session_dashboard_ui(self, workdir: Path) -> None:
        theme_dart = workdir / "lib" / "src" / "theme" / "dashboard_theme.dart"
        theme_dart.parent.mkdir(parents=True, exist_ok=True)
        theme_dart.write_text(
            (
                "import 'package:flutter/material.dart';\n\n"
                "class DashboardTheme {\n"
                "  static ThemeData build() {\n"
                "    return ThemeData(\n"
                "      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0F766E)),\n"
                "      scaffoldBackgroundColor: const Color(0xFFF8FAFC),\n"
                "      useMaterial3: true,\n"
                "    );\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        main_dart = workdir / "lib" / "main.dart"
        main_dart.parent.mkdir(parents=True, exist_ok=True)
        main_dart.write_text(
            (
                "import 'package:flutter/material.dart';\n\n"
                "import 'src/theme/dashboard_theme.dart';\n\n"
                "void main() {\n"
                "  runApp(const SessionDashboardApp());\n"
                "}\n\n"
                "class SessionDashboardApp extends StatelessWidget {\n"
                "  const SessionDashboardApp({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return MaterialApp(\n"
                "      debugShowCheckedModeBanner: false,\n"
                "      title: 'SwarmForge Session Dashboard',\n"
                "      theme: DashboardTheme.build(),\n"
                "      home: const SessionDashboardPage(),\n"
                "    );\n"
                "  }\n"
                "}\n\n"
                "class SessionDashboardPage extends StatelessWidget {\n"
                "  const SessionDashboardPage({super.key});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    final sessions = const [\n"
                "      ('SCRUM-55', 'Frontend dashboard shell', 'running'),\n"
                "      ('SCRUM-56', 'Live status and timeline UI', 'running'),\n"
                "      ('SCRUM-61', 'UAT and production readiness', 'queued'),\n"
                "    ];\n"
                "    return Scaffold(\n"
                "      appBar: AppBar(\n"
                "        title: const Text('SwarmForge Session Dashboard'),\n"
                "      ),\n"
                "      body: Padding(\n"
                "        padding: const EdgeInsets.all(16),\n"
                "        child: Column(\n"
                "          crossAxisAlignment: CrossAxisAlignment.start,\n"
                "          children: [\n"
                "            const Wrap(\n"
                "              spacing: 12,\n"
                "              runSpacing: 12,\n"
                "              children: [\n"
                "                _KpiCard(title: 'Active Sessions', value: '3'),\n"
                "                _KpiCard(title: 'Open PRs', value: '0'),\n"
                "                _KpiCard(title: 'Chain Health', value: 'Healthy'),\n"
                "              ],\n"
                "            ),\n"
                "            const SizedBox(height: 16),\n"
                "            const Text('Ticket Flow', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),\n"
                "            const SizedBox(height: 8),\n"
                "            Expanded(\n"
                "              child: ListView.separated(\n"
                "                itemCount: sessions.length,\n"
                "                separatorBuilder: (_, __) => const SizedBox(height: 8),\n"
                "                itemBuilder: (context, index) {\n"
                "                  final item = sessions[index];\n"
                "                  return ListTile(\n"
                "                    tileColor: const Color(0xFFF1F5F9),\n"
                "                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),\n"
                "                    title: Text('${item.$1} - ${item.$2}'),\n"
                "                    subtitle: Text('status: ${item.$3}'),\n"
                "                    trailing: const Icon(Icons.chevron_right),\n"
                "                  );\n"
                "                },\n"
                "              ),\n"
                "            ),\n"
                "          ],\n"
                "        ),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}\n\n"
                "class _KpiCard extends StatelessWidget {\n"
                "  final String title;\n"
                "  final String value;\n\n"
                "  const _KpiCard({required this.title, required this.value});\n\n"
                "  @override\n"
                "  Widget build(BuildContext context) {\n"
                "    return SizedBox(\n"
                "      width: 220,\n"
                "      child: Card(\n"
                "        elevation: 0,\n"
                "        color: const Color(0xFFECFEFF),\n"
                "        child: Padding(\n"
                "          padding: const EdgeInsets.all(12),\n"
                "          child: Column(\n"
                "            crossAxisAlignment: CrossAxisAlignment.start,\n"
                "            children: [\n"
                "              Text(title, style: const TextStyle(fontSize: 13, color: Colors.black54)),\n"
                "              const SizedBox(height: 6),\n"
                "              Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),\n"
                "            ],\n"
                "          ),\n"
                "        ),\n"
                "      ),\n"
                "    );\n"
                "  }\n"
                "}\n"
            ),
            encoding="utf-8",
        )

        widget_test = workdir / "test" / "session_dashboard_widget_test.dart"
        widget_test.parent.mkdir(parents=True, exist_ok=True)
        widget_test.write_text(
            (
                "import 'package:flutter_test/flutter_test.dart';\n"
                "import 'package:repo/main.dart';\n\n"
                "void main() {\n"
                "  testWidgets('renders Session Dashboard shell', (tester) async {\n"
                "    await tester.pumpWidget(const SessionDashboardApp());\n"
                "    expect(find.text('SwarmForge Session Dashboard'), findsOneWidget);\n"
                "    expect(find.text('Active Sessions'), findsOneWidget);\n"
                "    expect(find.text('Ticket Flow'), findsOneWidget);\n"
                "  });\n"
                "}\n"
            ),
            encoding="utf-8",
        )
