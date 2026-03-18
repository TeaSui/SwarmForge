import { useState, useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend, Treemap } from "recharts";

const COLORS = {
  bg: "#0f1117",
  card: "#1a1d27",
  cardHover: "#232736",
  border: "#2a2e3d",
  text: "#e1e4ed",
  textDim: "#8b8fa3",
  accent: "#7c5cfc",
  accentGlow: "rgba(124,92,252,0.15)",
  green: "#22c55e",
  greenDim: "rgba(34,197,94,0.15)",
  orange: "#f59e0b",
  orangeDim: "rgba(245,158,11,0.15)",
  red: "#ef4444",
  redDim: "rgba(239,68,68,0.15)",
  blue: "#3b82f6",
  blueDim: "rgba(59,130,246,0.15)",
  cyan: "#06b6d4",
  cyanDim: "rgba(6,182,212,0.15)",
  pink: "#ec4899",
  pinkDim: "rgba(236,72,153,0.15)",
};

const TABS = ["Overview", "Pipeline", "Services", "Dependencies"];

// ── Data ──
const serviceFiles = [
  { name: "stage_dispatcher", lines: 500, layer: "executor", risk: "high" },
  { name: "orchestrator", lines: 465, layer: "core", risk: "high" },
  { name: "code_sandbox", lines: 343, layer: "executor", risk: "medium" },
  { name: "github_delivery", lines: 283, layer: "executor", risk: "medium" },
  { name: "quality_gate", lines: 260, layer: "core", risk: "high" },
  { name: "llm_stages", lines: 225, layer: "executor", risk: "medium" },
  { name: "llm_codegen", lines: 176, layer: "executor", risk: "medium" },
  { name: "jira_client", lines: 164, layer: "integration", risk: "low" },
  { name: "flutter_codegen", lines: 158, layer: "executor", risk: "medium" },
  { name: "crew_stage_runner", lines: 145, layer: "core", risk: "high" },
  { name: "llm_client", lines: 139, layer: "core", risk: "high" },
  { name: "agent_base", lines: 135, layer: "core", risk: "medium" },
  { name: "mcp_tools", lines: 133, layer: "integration", risk: "low" },
  { name: "approval_gate", lines: 133, layer: "core", risk: "high" },
  { name: "agents", lines: 129, layer: "core", risk: "medium" },
  { name: "mcp_bridge_server", lines: 124, layer: "integration", risk: "low" },
  { name: "sqs_consumer", lines: 95, layer: "infra", risk: "medium" },
  { name: "git_ops", lines: 92, layer: "executor", risk: "low" },
  { name: "agent_contract", lines: 90, layer: "core", risk: "low" },
  { name: "budget_manager", lines: 88, layer: "core", risk: "high" },
  { name: "task_notifications", lines: 84, layer: "integration", risk: "low" },
  { name: "notifications", lines: 75, layer: "integration", risk: "low" },
  { name: "sla_monitor", lines: 69, layer: "infra", risk: "low" },
  { name: "rate_limiter", lines: 65, layer: "infra", risk: "medium" },
  { name: "deduplication", lines: 55, layer: "infra", risk: "medium" },
  { name: "idempotency", lines: 50, layer: "infra", risk: "medium" },
  { name: "logging_setup", lines: 45, layer: "infra", risk: "low" },
  { name: "sqs_producer", lines: 40, layer: "infra", risk: "low" },
  { name: "log_streamer", lines: 38, layer: "infra", risk: "low" },
  { name: "aws_session", lines: 35, layer: "infra", risk: "low" },
  { name: "autonomous_executor", lines: 30, layer: "executor", risk: "medium" },
  { name: "mcp_client", lines: 28, layer: "integration", risk: "low" },
];

const pipelineStages = [
  { id: "webhook", label: "Webhook Ingress", desc: "Jira / Slack / Generic", color: COLORS.blue, icon: "🔌" },
  { id: "validate", label: "Validate & Dedup", desc: "HMAC + Idempotency", color: COLORS.cyan, icon: "🔒" },
  { id: "sqs", label: "SQS Queue", desc: "Async dispatch", color: COLORS.orange, icon: "📨" },
  { id: "intent", label: "Intent Analysis", desc: "Parse task scope", color: COLORS.accent, icon: "🧠" },
  { id: "plan", label: "Solution Plan", desc: "Strategy generation", color: COLORS.accent, icon: "📋" },
  { id: "code", label: "Code Generation", desc: "CrewAI agents", color: COLORS.green, icon: "⚡" },
  { id: "review", label: "Code Review", desc: "Reviewer agent", color: COLORS.pink, icon: "🔍" },
  { id: "test", label: "Test Verification", desc: "Tester agent", color: COLORS.green, icon: "✅" },
  { id: "security", label: "Security Check", desc: "Security agent", color: COLORS.red, icon: "🛡️" },
  { id: "quality", label: "Quality Gates", desc: "Fail-closed checks", color: COLORS.orange, icon: "🚧" },
  { id: "approval", label: "Human Approval", desc: "HITL gate", color: COLORS.pink, icon: "👤" },
  { id: "deliver", label: "Delivery", desc: "PR + Jira update", color: COLORS.green, icon: "🚀" },
];

const depMatrix = [
  { from: "main.py", to: ["api/webhooks/*", "config", "rate_limiter", "logging_setup"] },
  { from: "worker.py", to: ["sqs_consumer", "orchestrator", "config", "logging_setup"] },
  { from: "orchestrator", to: ["crew_stage_runner", "quality_gate", "approval_gate", "budget_manager", "idempotency", "jira_client", "task_notifications", "agents"] },
  { from: "crew_stage_runner", to: ["agent_base", "agents", "llm_client", "budget_manager"] },
  { from: "stage_dispatcher", to: ["llm_stages", "llm_codegen", "code_sandbox", "github_delivery", "flutter_codegen", "git_ops"] },
  { from: "quality_gate", to: ["jira_client", "github_delivery"] },
  { from: "approval_gate", to: ["jira_client"] },
  { from: "llm_client", to: ["config", "budget_manager"] },
  { from: "sqs_consumer", to: ["config", "aws_session"] },
  { from: "sqs_producer", to: ["config", "aws_session"] },
];

const projectStats = {
  totalPyLines: 37251,
  serviceLines: 4523,
  testFiles: 24,
  testLines: 2597,
  apiLines: 262,
  serviceModules: 31,
  coverage: "80%+",
  agents: 5,
  stages: 12,
  qualityChecks: 7,
};

const layerColors = {
  core: COLORS.accent,
  executor: COLORS.green,
  integration: COLORS.blue,
  infra: COLORS.orange,
};

const riskColors = { high: COLORS.red, medium: COLORS.orange, low: COLORS.green };

// ── Components ──

function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
      padding: "18px 20px", flex: "1 1 140px", minWidth: 140,
    }}>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || COLORS.text, fontVariantNumeric: "tabular-nums" }}>{value}</div>
      <div style={{ fontSize: 13, color: COLORS.textDim, marginTop: 4 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: COLORS.textDim, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function Badge({ text, color, bg }) {
  return (
    <span style={{
      display: "inline-block", fontSize: 10, fontWeight: 600, padding: "2px 8px",
      borderRadius: 999, color: color, background: bg, textTransform: "uppercase", letterSpacing: 0.5,
    }}>{text}</span>
  );
}

function OverviewTab() {
  const layerData = useMemo(() => {
    const groups = {};
    serviceFiles.forEach(f => {
      groups[f.layer] = (groups[f.layer] || 0) + f.lines;
    });
    return Object.entries(groups).map(([name, value]) => ({ name, value }));
  }, []);

  const riskData = useMemo(() => {
    const groups = {};
    serviceFiles.forEach(f => {
      groups[f.risk] = (groups[f.risk] || 0) + 1;
    });
    return Object.entries(groups).map(([name, value]) => ({ name, value }));
  }, []);

  const pieColors = { core: COLORS.accent, executor: COLORS.green, integration: COLORS.blue, infra: COLORS.orange };
  const riskPieColors = { high: COLORS.red, medium: COLORS.orange, low: COLORS.green };

  return (
    <div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 28 }}>
        <StatCard label="Python LOC" value="37.2K" sub="total codebase" color={COLORS.accent} />
        <StatCard label="Service Modules" value={projectStats.serviceModules} sub="across 4 layers" color={COLORS.green} />
        <StatCard label="Test Files" value={projectStats.testFiles} sub={`${projectStats.testLines} lines`} color={COLORS.blue} />
        <StatCard label="Coverage" value={projectStats.coverage} sub="fail_under=80" color={COLORS.cyan} />
        <StatCard label="AI Agents" value={projectStats.agents} sub="CrewAI swarm" color={COLORS.pink} />
        <StatCard label="Pipeline Stages" value={projectStats.stages} sub="scope-aware" color={COLORS.orange} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 14, color: COLORS.textDim, fontWeight: 500 }}>Code Distribution by Layer</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={layerData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} strokeWidth={2} stroke={COLORS.bg}>
                {layerData.map((e) => <Cell key={e.name} fill={pieColors[e.name] || COLORS.textDim} />)}
              </Pie>
              <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: 20 }}>
          <h3 style={{ margin: "0 0 16px", fontSize: 14, color: COLORS.textDim, fontWeight: 500 }}>Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={riskData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} strokeWidth={2} stroke={COLORS.bg}>
                {riskData.map((e) => <Cell key={e.name} fill={riskPieColors[e.name] || COLORS.textDim} />)}
              </Pie>
              <Tooltip contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: 20 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 14, color: COLORS.textDim, fontWeight: 500 }}>Tech Stack</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {["Python 3.12", "FastAPI", "CrewAI", "Claude API", "AWS Bedrock", "SQS", "DynamoDB", "ECS Fargate", "AWS CDK", "LangChain", "Pydantic v2", "CloudWatch", "LangSmith"].map(t => (
            <span key={t} style={{
              padding: "6px 14px", borderRadius: 999, fontSize: 12, fontWeight: 500,
              background: COLORS.accentGlow, color: COLORS.accent, border: `1px solid ${COLORS.border}`,
            }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function PipelineTab() {
  const [hovered, setHovered] = useState(null);

  return (
    <div>
      <p style={{ color: COLORS.textDim, fontSize: 13, margin: "0 0 24px" }}>
        Webhook → SQS → Orchestrator → Agent Stages → Quality Gates → Delivery
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {pipelineStages.map((stage, i) => {
          const isHov = hovered === stage.id;
          return (
            <div key={stage.id} onMouseEnter={() => setHovered(stage.id)} onMouseLeave={() => setHovered(null)}>
              <div style={{
                display: "flex", alignItems: "center", gap: 16,
                background: isHov ? COLORS.cardHover : COLORS.card,
                border: `1px solid ${isHov ? stage.color : COLORS.border}`,
                borderRadius: 10, padding: "14px 20px",
                transition: "all 0.15s ease",
                transform: isHov ? "scale(1.01)" : "scale(1)",
                boxShadow: isHov ? `0 0 20px ${stage.color}22` : "none",
              }}>
                <span style={{ fontSize: 22, width: 36, textAlign: "center" }}>{stage.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text }}>{stage.label}</div>
                  <div style={{ fontSize: 12, color: COLORS.textDim }}>{stage.desc}</div>
                </div>
                <div style={{
                  width: 28, height: 28, borderRadius: "50%",
                  background: `${stage.color}22`, border: `2px solid ${stage.color}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 12, fontWeight: 700, color: stage.color,
                }}>{i + 1}</div>
              </div>
              {i < pipelineStages.length - 1 && (
                <div style={{ display: "flex", justifyContent: "center", padding: "2px 0" }}>
                  <div style={{ width: 2, height: 12, background: COLORS.border }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ServicesTab() {
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("lines");

  const filtered = useMemo(() => {
    let data = [...serviceFiles];
    if (filter !== "all") data = data.filter(f => f.layer === filter);
    if (sort === "lines") data.sort((a, b) => b.lines - a.lines);
    else if (sort === "name") data.sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === "risk") {
      const riskOrder = { high: 0, medium: 1, low: 2 };
      data.sort((a, b) => riskOrder[a.risk] - riskOrder[b.risk]);
    }
    return data;
  }, [filter, sort]);

  const btnStyle = (active) => ({
    padding: "6px 14px", borderRadius: 999, border: `1px solid ${active ? COLORS.accent : COLORS.border}`,
    background: active ? COLORS.accentGlow : "transparent", color: active ? COLORS.accent : COLORS.textDim,
    fontSize: 12, fontWeight: 500, cursor: "pointer", transition: "all 0.15s",
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: 12, color: COLORS.textDim, marginRight: 4 }}>Layer:</span>
        {["all", "core", "executor", "integration", "infra"].map(l => (
          <button key={l} onClick={() => setFilter(l)} style={btnStyle(filter === l)}>{l}</button>
        ))}
        <span style={{ fontSize: 12, color: COLORS.textDim, marginLeft: 12, marginRight: 4 }}>Sort:</span>
        {["lines", "name", "risk"].map(s => (
          <button key={s} onClick={() => setSort(s)} style={btnStyle(sort === s)}>{s}</button>
        ))}
      </div>

      <div style={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12, padding: 20 }}>
        <ResponsiveContainer width="100%" height={Math.max(400, filtered.length * 28)}>
          <BarChart data={filtered} layout="vertical" margin={{ left: 140, right: 20 }}>
            <XAxis type="number" tick={{ fill: COLORS.textDim, fontSize: 11 }} axisLine={{ stroke: COLORS.border }} />
            <YAxis type="category" dataKey="name" tick={{ fill: COLORS.text, fontSize: 11 }} axisLine={false} tickLine={false} width={130} />
            <Tooltip
              contentStyle={{ background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 8, fontSize: 12 }}
              formatter={(v, n, p) => [`${v} lines`, `Layer: ${p.payload.layer} | Risk: ${p.payload.risk}`]}
            />
            <Bar dataKey="lines" radius={[0, 4, 4, 0]} barSize={18}>
              {filtered.map((f) => <Cell key={f.name} fill={layerColors[f.layer]} fillOpacity={0.8} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: 20, display: "flex", gap: 16, flexWrap: "wrap" }}>
        {Object.entries(layerColors).map(([l, c]) => (
          <div key={l} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: COLORS.textDim }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: c }} />
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}

function DependenciesTab() {
  const [selected, setSelected] = useState(null);

  const selDeps = selected ? depMatrix.find(d => d.from === selected) : null;

  return (
    <div>
      <p style={{ color: COLORS.textDim, fontSize: 13, margin: "0 0 20px" }}>
        Click a module to see its dependencies
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <h3 style={{ fontSize: 13, color: COLORS.textDim, fontWeight: 500, margin: "0 0 12px" }}>Source Modules</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {depMatrix.map(d => {
              const isSel = selected === d.from;
              return (
                <button key={d.from} onClick={() => setSelected(isSel ? null : d.from)} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "10px 16px", borderRadius: 8, border: `1px solid ${isSel ? COLORS.accent : COLORS.border}`,
                  background: isSel ? COLORS.accentGlow : COLORS.card, color: isSel ? COLORS.accent : COLORS.text,
                  fontSize: 13, fontWeight: isSel ? 600 : 400, cursor: "pointer", transition: "all 0.15s",
                  textAlign: "left", width: "100%",
                }}>
                  <span>{d.from}</span>
                  <span style={{ fontSize: 11, color: COLORS.textDim }}>{d.to.length} deps</span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <h3 style={{ fontSize: 13, color: COLORS.textDim, fontWeight: 500, margin: "0 0 12px" }}>
            {selected ? `Dependencies of ${selected}` : "Select a module"}
          </h3>
          {selDeps ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {selDeps.to.map(dep => {
                const sf = serviceFiles.find(f => f.name === dep);
                return (
                  <div key={dep} style={{
                    padding: "10px 16px", borderRadius: 8,
                    border: `1px solid ${COLORS.border}`, background: COLORS.card,
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                  }}>
                    <span style={{ fontSize: 13, color: COLORS.text }}>{dep}</span>
                    {sf && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <Badge text={sf.layer} color={layerColors[sf.layer]} bg={`${layerColors[sf.layer]}22`} />
                        <Badge text={sf.risk} color={riskColors[sf.risk]} bg={`${riskColors[sf.risk]}22`} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{
              padding: 40, borderRadius: 12, border: `1px dashed ${COLORS.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: COLORS.textDim, fontSize: 13,
            }}>
              Click a module on the left
            </div>
          )}
        </div>
      </div>

      <div style={{
        marginTop: 28, padding: 20, borderRadius: 12,
        background: COLORS.card, border: `1px solid ${COLORS.border}`,
      }}>
        <h3 style={{ fontSize: 13, color: COLORS.textDim, fontWeight: 500, margin: "0 0 12px" }}>Dependency Hotspots</h3>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {[
            { name: "orchestrator", deps: 8, note: "God module risk" },
            { name: "config", deps: 0, note: "Imported everywhere" },
            { name: "budget_manager", deps: 0, note: "Cross-cutting concern" },
            { name: "jira_client", deps: 0, note: "3 upstream consumers" },
          ].map(h => (
            <div key={h.name} style={{
              padding: "10px 16px", borderRadius: 8,
              background: COLORS.redDim, border: `1px solid ${COLORS.red}33`,
              flex: "1 1 200px",
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.red }}>{h.name}</div>
              <div style={{ fontSize: 11, color: COLORS.textDim, marginTop: 2 }}>{h.note}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main ──
export default function SwarmForgeVisualizer() {
  const [activeTab, setActiveTab] = useState("Overview");

  return (
    <div style={{
      minHeight: "100vh", background: COLORS.bg, color: COLORS.text,
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      padding: "32px 24px",
    }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: `linear-gradient(135deg, ${COLORS.accent}, ${COLORS.pink})`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, fontWeight: 700, color: "#fff",
            }}>S</div>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>SwarmForge</h1>
            <Badge text="v0.1.0" color={COLORS.accent} bg={COLORS.accentGlow} />
          </div>
          <p style={{ margin: 0, fontSize: 14, color: COLORS.textDim }}>
            AI-driven task automation — CrewAI multi-agent swarm for autonomous code generation
          </p>
        </div>

        {/* Tabs */}
        <div style={{
          display: "flex", gap: 4, marginBottom: 28, padding: 4,
          background: COLORS.card, borderRadius: 10, border: `1px solid ${COLORS.border}`,
          width: "fit-content",
        }}>
          {TABS.map(tab => {
            const isActive = activeTab === tab;
            return (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{
                padding: "8px 20px", borderRadius: 8, border: "none",
                background: isActive ? COLORS.accent : "transparent",
                color: isActive ? "#fff" : COLORS.textDim,
                fontSize: 13, fontWeight: isActive ? 600 : 400,
                cursor: "pointer", transition: "all 0.15s",
              }}>{tab}</button>
            );
          })}
        </div>

        {/* Content */}
        {activeTab === "Overview" && <OverviewTab />}
        {activeTab === "Pipeline" && <PipelineTab />}
        {activeTab === "Services" && <ServicesTab />}
        {activeTab === "Dependencies" && <DependenciesTab />}

        {/* Footer */}
        <div style={{
          marginTop: 40, padding: "16px 0", borderTop: `1px solid ${COLORS.border}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ fontSize: 11, color: COLORS.textDim }}>SwarmForge Visualizer — Generated from codebase analysis</span>
          <span style={{ fontSize: 11, color: COLORS.textDim }}>Python 3.12 • FastAPI • CrewAI • AWS</span>
        </div>
      </div>
    </div>
  );
}
