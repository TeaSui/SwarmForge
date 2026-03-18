import { useState, useEffect, useRef, useMemo, useCallback } from "react";

// ── Theme ──
const C = {
  bg: "#0a0c10", bgSoft: "#0f1117", card: "#161922", cardHover: "#1c2030",
  border: "#21263a", borderHi: "#2d3350",
  text: "#e2e5f0", dim: "#6b7194", dimHi: "#8b90b0",
  accent: "#7c5cfc", accentDim: "rgba(124,92,252,0.12)",
  green: "#22c55e", greenDim: "rgba(34,197,94,0.1)",
  orange: "#f59e0b", orangeDim: "rgba(245,158,11,0.1)",
  red: "#ef4444", redDim: "rgba(239,68,68,0.1)",
  blue: "#3b82f6", blueDim: "rgba(59,130,246,0.1)",
  cyan: "#06b6d4", cyanDim: "rgba(6,182,212,0.1)",
  pink: "#ec4899", yellow: "#eab308",
};

const LEVEL_STYLE = {
  DEBUG: { color: C.dim, bg: "transparent", icon: "●" },
  INFO: { color: C.blue, bg: C.blueDim, icon: "ℹ" },
  WARNING: { color: C.orange, bg: C.orangeDim, icon: "⚠" },
  ERROR: { color: C.red, bg: C.redDim, icon: "✕" },
  CRITICAL: { color: C.red, bg: C.redDim, icon: "⛔" },
};

const COMPONENTS = ["api", "worker", "orchestrator", "crew_runner", "llm_client", "budget", "quality_gate", "approval", "sqs", "agents"];
const COMP_COLORS = {
  api: C.blue, worker: C.cyan, orchestrator: C.accent, crew_runner: C.green,
  llm_client: C.pink, budget: C.orange, quality_gate: C.yellow, approval: C.pink,
  sqs: C.cyan, agents: C.green,
};

const STAGES = [
  "intent-analysis", "solution-plan", "code-generation", "code-review",
  "test-verification", "security-check", "documentation", "quality-gates",
];
const STAGE_STATUS = { pending: C.dim, running: C.accent, completed: C.green, failed: C.red, skipped: C.dim };

// ── Realistic SwarmForge log generator ──
function generateCorrelationId() {
  return `sf-${Math.random().toString(36).slice(2, 10)}`;
}

const TASK_IDS = ["SF-142", "SF-143", "SF-144", "SF-145", "SF-146"];
const TASK_SUMMARIES = [
  "Optimize database query performance for user dashboard",
  "Add rate limiting to public API endpoints",
  "Fix memory leak in WebSocket connection handler",
  "Implement JWT refresh token rotation",
  "Refactor payment service error handling",
];

function createLogTemplates() {
  return [
    // API layer
    { component: "api", level: "INFO", msg: (t) => `POST /webhook/jira 200 — task_id=${t.taskId} event=jira:issue_updated`, phase: "ingress" },
    { component: "api", level: "INFO", msg: () => `HMAC-SHA256 signature validated`, phase: "ingress" },
    { component: "api", level: "DEBUG", msg: () => `Rate limiter: 23/60 requests this window`, phase: "ingress" },
    { component: "api", level: "INFO", msg: (t) => `Labels matched: ["ai-task"] — publishing to SQS`, phase: "ingress" },

    // SQS
    { component: "sqs", level: "INFO", msg: (t) => `Published message to SQS queue — MessageId=${Math.random().toString(36).slice(2, 14)}`, phase: "queue" },
    { component: "sqs", level: "INFO", msg: (t) => `Consumer received message — task_id=${t.taskId}`, phase: "queue" },
    { component: "sqs", level: "DEBUG", msg: () => `Idempotency check passed — first occurrence`, phase: "queue" },

    // Orchestrator
    { component: "orchestrator", level: "INFO", msg: (t) => `Task ${t.taskId} -> PENDING`, phase: "orchestrate" },
    { component: "orchestrator", level: "INFO", msg: (t) => `Parsing intent for: "${t.summary}"`, phase: "orchestrate" },
    { component: "orchestrator", level: "INFO", msg: (t) => `Task ${t.taskId} -> INTENT_PARSED`, phase: "orchestrate" },
    { component: "orchestrator", level: "INFO", msg: (t) => `Plan built: ${6 + Math.floor(Math.random() * 3)} stages, estimated ${(12000 + Math.floor(Math.random() * 8000)).toLocaleString()} tokens`, phase: "orchestrate" },
    { component: "orchestrator", level: "INFO", msg: (t) => `Task ${t.taskId} -> IN_PROGRESS`, phase: "orchestrate" },

    // Budget
    { component: "budget", level: "DEBUG", msg: () => `Budget reset for new task`, phase: "orchestrate" },
    { component: "budget", level: "DEBUG", msg: () => {
      const t = 1200 + Math.floor(Math.random() * 3000);
      const u = (t * 0.000015).toFixed(4);
      return `Usage update -> Tokens: ${t.toLocaleString()}, USD: $${u}`;
    }, phase: "execute" },

    // CrewAI stages
    { component: "crew_runner", level: "INFO", msg: (t) => `Stage intent-analysis STARTED — timeout=300s`, phase: "execute", stage: "intent-analysis" },
    { component: "agents", level: "INFO", msg: () => `ResearchAgent initialized — model=claude-sonnet-4-6`, phase: "execute", stage: "intent-analysis" },
    { component: "llm_client", level: "INFO", msg: () => {
      const lat = 800 + Math.floor(Math.random() * 2500);
      return `Claude API response — ${lat}ms, ${(800 + Math.floor(Math.random() * 1200)).toLocaleString()} tokens`;
    }, phase: "execute" },
    { component: "crew_runner", level: "INFO", msg: () => `Stage intent-analysis COMPLETED — 4.2s`, phase: "execute", stage: "intent-analysis" },

    { component: "crew_runner", level: "INFO", msg: () => `Stage solution-plan STARTED — timeout=300s`, phase: "execute", stage: "solution-plan" },
    { component: "agents", level: "INFO", msg: () => `CoderAgent initialized — model=claude-sonnet-4-6`, phase: "execute", stage: "solution-plan" },
    { component: "llm_client", level: "INFO", msg: () => {
      const lat = 1200 + Math.floor(Math.random() * 4000);
      return `Claude API response — ${lat}ms, ${(1500 + Math.floor(Math.random() * 2000)).toLocaleString()} tokens`;
    }, phase: "execute" },
    { component: "crew_runner", level: "INFO", msg: () => `Stage solution-plan COMPLETED — 6.8s`, phase: "execute", stage: "solution-plan" },

    { component: "crew_runner", level: "INFO", msg: () => `Stage code-generation STARTED — timeout=900s (critical)`, phase: "execute", stage: "code-generation" },
    { component: "agents", level: "INFO", msg: () => `CoderAgent executing with 3 tools: [shell, file_ops, github_api]`, phase: "execute", stage: "code-generation" },
    { component: "llm_client", level: "INFO", msg: () => {
      const lat = 3000 + Math.floor(Math.random() * 8000);
      return `Claude API response — ${lat}ms, ${(3000 + Math.floor(Math.random() * 5000)).toLocaleString()} tokens`;
    }, phase: "execute" },
    { component: "budget", level: "DEBUG", msg: () => {
      const t = 15000 + Math.floor(Math.random() * 20000);
      const u = (t * 0.000015).toFixed(4);
      return `Usage update -> Tokens: ${t.toLocaleString()}, USD: $${u}`;
    }, phase: "execute" },
    { component: "crew_runner", level: "INFO", msg: () => `Stage code-generation COMPLETED — 18.4s`, phase: "execute", stage: "code-generation" },

    { component: "crew_runner", level: "INFO", msg: () => `Stage code-review STARTED — timeout=300s`, phase: "execute", stage: "code-review" },
    { component: "agents", level: "INFO", msg: () => `ReviewerAgent initialized — model=claude-sonnet-4-6`, phase: "execute", stage: "code-review" },
    { component: "crew_runner", level: "INFO", msg: () => `Stage code-review COMPLETED — 8.1s`, phase: "execute", stage: "code-review" },

    { component: "crew_runner", level: "INFO", msg: () => `Stage test-verification STARTED — timeout=300s`, phase: "execute", stage: "test-verification" },
    { component: "agents", level: "INFO", msg: () => `SREAgent initialized — running pytest suite`, phase: "execute", stage: "test-verification" },
    { component: "crew_runner", level: "INFO", msg: () => `Stage test-verification COMPLETED — 12.6s`, phase: "execute", stage: "test-verification" },

    { component: "crew_runner", level: "INFO", msg: () => `Stage security-check STARTED — timeout=300s`, phase: "execute", stage: "security-check" },
    { component: "crew_runner", level: "INFO", msg: () => `Stage security-check COMPLETED — 5.3s`, phase: "execute", stage: "security-check" },

    // Quality gates
    { component: "quality_gate", level: "INFO", msg: () => `Evaluating quality gates — scope: [standard]`, phase: "quality" },
    { component: "quality_gate", level: "INFO", msg: () => `✓ artifacts-complete`, phase: "quality" },
    { component: "quality_gate", level: "INFO", msg: () => `✓ tests-pass`, phase: "quality" },
    { component: "quality_gate", level: "INFO", msg: () => `✓ security-pass`, phase: "quality" },
    { component: "quality_gate", level: "INFO", msg: () => `✓ delivery-pr`, phase: "quality" },
    { component: "quality_gate", level: "INFO", msg: () => `All quality gates PASSED (4/4)`, phase: "quality" },

    // Approval
    { component: "approval", level: "INFO", msg: (t) => `Approval requested — Jira comment posted on ${t.taskId}`, phase: "approval" },
    { component: "approval", level: "INFO", msg: () => `Polling for approval... (attempt 1, interval=15s)`, phase: "approval" },
    { component: "approval", level: "INFO", msg: () => `Approval GRANTED by user@domain.com`, phase: "approval" },

    // Completion
    { component: "orchestrator", level: "INFO", msg: (t) => `Task ${t.taskId} -> COMPLETED`, phase: "complete" },
    { component: "budget", level: "INFO", msg: (t) => {
      const tokens = 35000 + Math.floor(Math.random() * 30000);
      const usd = (tokens * 0.000015).toFixed(2);
      return `Persisting usage for task ${t.taskId}: ${tokens.toLocaleString()} tokens, $${usd}`;
    }, phase: "complete" },
    { component: "orchestrator", level: "INFO", msg: (t) => `Jira comment posted: [SwarmForge] Task ${t.taskId} completed successfully`, phase: "complete" },

    // Error scenarios (occasional)
    { component: "llm_client", level: "WARNING", msg: () => `Claude API rate limited (429) — retrying with backoff 2.0s`, phase: "execute", chance: 0.15 },
    { component: "llm_client", level: "INFO", msg: () => `Falling back to Bedrock: global.anthropic.claude-sonnet-4-6`, phase: "execute", chance: 0.1 },
    { component: "budget", level: "WARNING", msg: () => `Token soft limit reached: ${(100000 + Math.floor(Math.random() * 5000)).toLocaleString()}`, phase: "execute", chance: 0.08 },
    { component: "crew_runner", level: "ERROR", msg: () => `Stage code-generation TIMEOUT after 900s — switching to fallback model`, phase: "execute", chance: 0.05 },
    { component: "quality_gate", level: "ERROR", msg: () => `✗ tests-pass — 2 test failures detected`, phase: "quality", chance: 0.06 },
    { component: "sqs", level: "WARNING", msg: () => `Message visibility timeout approaching — extending by 300s`, phase: "queue", chance: 0.1 },
    { component: "api", level: "WARNING", msg: () => `Rate limit exceeded for IP 10.0.3.42 — 429 returned`, phase: "ingress", chance: 0.07 },
  ];
}

// ── Helpers ──
function timestamp() {
  return new Date().toISOString();
}

// ── Components ──

function LogLine({ log, isNew }) {
  const ls = LEVEL_STYLE[log.level] || LEVEL_STYLE.INFO;
  const cc = COMP_COLORS[log.component] || C.dim;

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "160px 22px 100px 62px 1fr",
      gap: 8,
      alignItems: "start",
      padding: "6px 14px",
      fontSize: 12.5,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
      borderBottom: `1px solid ${C.border}`,
      background: isNew ? `${C.accent}08` : "transparent",
      transition: "background 1.5s ease",
      lineHeight: 1.5,
    }}>
      <span style={{ color: C.dim, fontSize: 11, whiteSpace: "nowrap" }}>{log.ts.slice(11, 23)}</span>
      <span style={{ color: ls.color, fontSize: 11, textAlign: "center" }}>{ls.icon}</span>
      <span style={{
        color: cc, fontSize: 10, fontWeight: 600,
        padding: "1px 6px", borderRadius: 4, background: `${cc}15`,
        textAlign: "center", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
      }}>{log.component}</span>
      <span style={{
        color: ls.color, fontSize: 10, fontWeight: 600,
        padding: "1px 6px", borderRadius: 4, background: ls.bg,
        textAlign: "center",
      }}>{log.level}</span>
      <span style={{ color: C.text, wordBreak: "break-word" }}>
        {log.correlation_id !== "-" && (
          <span style={{ color: C.dim, fontSize: 10, marginRight: 6 }}>[{log.correlation_id}]</span>
        )}
        {log.event}
      </span>
    </div>
  );
}

function StageTracker({ stages }) {
  return (
    <div style={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
      {stages.map((s, i) => (
        <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 2 }}>
          <div style={{
            padding: "3px 10px", borderRadius: 6, fontSize: 10, fontWeight: 600,
            background: `${STAGE_STATUS[s.status]}18`,
            color: STAGE_STATUS[s.status],
            border: `1px solid ${STAGE_STATUS[s.status]}33`,
            whiteSpace: "nowrap",
            animation: s.status === "running" ? "pulse 1.5s ease-in-out infinite" : "none",
          }}>
            {s.status === "running" && "▶ "}
            {s.status === "completed" && "✓ "}
            {s.status === "failed" && "✗ "}
            {s.name}
          </div>
          {i < stages.length - 1 && <span style={{ color: C.dim, fontSize: 10 }}>→</span>}
        </div>
      ))}
    </div>
  );
}

function BudgetGauge({ label, current, soft, hard, unit, color }) {
  const pct = Math.min((current / hard) * 100, 100);
  const softPct = (soft / hard) * 100;
  const isWarn = current >= soft;
  const isDanger = current >= hard * 0.9;
  const barColor = isDanger ? C.red : isWarn ? C.orange : color;

  return (
    <div style={{ flex: "1 1 200px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: C.dim }}>{label}</span>
        <span style={{ fontSize: 11, color: barColor, fontWeight: 600, fontFamily: "monospace" }}>
          {unit === "$" ? `$${current.toFixed(2)}` : current.toLocaleString()} / {unit === "$" ? `$${hard.toFixed(2)}` : hard.toLocaleString()}
        </span>
      </div>
      <div style={{ height: 6, borderRadius: 3, background: C.border, position: "relative", overflow: "hidden" }}>
        <div style={{
          height: "100%", borderRadius: 3,
          width: `${pct}%`,
          background: `linear-gradient(90deg, ${barColor}, ${barColor}cc)`,
          transition: "width 0.5s ease",
        }} />
        <div style={{
          position: "absolute", left: `${softPct}%`, top: 0, bottom: 0,
          width: 1, background: C.orange, opacity: 0.6,
        }} />
      </div>
    </div>
  );
}

function FilterChip({ label, active, color, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: "4px 10px", borderRadius: 999, border: `1px solid ${active ? (color || C.accent) : C.border}`,
      background: active ? `${color || C.accent}18` : "transparent",
      color: active ? (color || C.accent) : C.dim,
      fontSize: 11, fontWeight: 500, cursor: "pointer", transition: "all 0.15s",
      whiteSpace: "nowrap",
    }}>{label}</button>
  );
}

// ── Main ──
export default function SwarmForgeLogVisualizer() {
  const [logs, setLogs] = useState([]);
  const [isStreaming, setIsStreaming] = useState(true);
  const [speed, setSpeed] = useState(800);
  const [levelFilter, setLevelFilter] = useState(new Set(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]));
  const [compFilter, setCompFilter] = useState(new Set(COMPONENTS));
  const [searchTerm, setSearchTerm] = useState("");
  const [stageStates, setStageStates] = useState(STAGES.map(s => ({ name: s, status: "pending" })));
  const [budget, setBudget] = useState({ tokens: 0, usd: 0 });
  const [taskIdx, setTaskIdx] = useState(0);
  const [logIdx, setLogIdx] = useState(0);
  const [newLogIds, setNewLogIds] = useState(new Set());

  const logEndRef = useRef(null);
  const templates = useRef(createLogTemplates());
  const correlationId = useRef(generateCorrelationId());
  const autoScroll = useRef(true);

  const currentTask = useMemo(() => ({
    taskId: TASK_IDS[taskIdx % TASK_IDS.length],
    summary: TASK_SUMMARIES[taskIdx % TASK_SUMMARIES.length],
  }), [taskIdx]);

  const addLog = useCallback(() => {
    const allTemplates = templates.current;
    let tmpl;

    // Sequential for main flow, random for error events
    if (logIdx < allTemplates.length) {
      tmpl = allTemplates[logIdx];
      if (tmpl.chance && Math.random() > tmpl.chance) {
        setLogIdx(i => i + 1);
        return;
      }
    } else {
      // Cycle to next task
      correlationId.current = generateCorrelationId();
      setTaskIdx(i => i + 1);
      setLogIdx(0);
      setStageStates(STAGES.map(s => ({ name: s, status: "pending" })));
      setBudget({ tokens: 0, usd: 0 });
      templates.current = createLogTemplates();
      return;
    }

    const id = Date.now() + Math.random();
    const log = {
      id, ts: timestamp(), level: tmpl.level, component: tmpl.component,
      event: tmpl.msg(currentTask), correlation_id: correlationId.current,
    };

    setLogs(prev => [...prev.slice(-500), log]);
    setNewLogIds(prev => { const n = new Set(prev); n.add(id); return n; });
    setTimeout(() => setNewLogIds(prev => { const n = new Set(prev); n.delete(id); return n; }), 1500);
    setLogIdx(i => i + 1);

    // Update stage tracker
    if (tmpl.stage) {
      setStageStates(prev => prev.map(s =>
        s.name === tmpl.stage
          ? { ...s, status: tmpl.level === "ERROR" ? "failed" : (tmpl.msg({}).includes("COMPLETED") ? "completed" : "running") }
          : s
      ));
    }

    // Update budget
    if (tmpl.component === "budget" && tmpl.msg({}).includes("Usage update")) {
      const m = tmpl.msg({}).match(/Tokens: ([\d,]+), USD: \$([\d.]+)/);
      if (m) {
        const tokens = parseInt(m[1].replace(/,/g, ""));
        const usd = parseFloat(m[2]);
        setBudget(prev => ({ tokens: prev.tokens + Math.floor(tokens * 0.3), usd: prev.usd + usd * 0.3 }));
      }
    }

    if (tmpl.component === "budget" && tmpl.msg({}).includes("Persisting")) {
      const m = tmpl.msg({}).match(/([\d,]+) tokens, \$([\d.]+)/);
      if (m) {
        setBudget({ tokens: parseInt(m[1].replace(/,/g, "")), usd: parseFloat(m[2]) });
      }
    }
  }, [logIdx, currentTask]);

  useEffect(() => {
    if (!isStreaming) return;
    const interval = setInterval(addLog, speed);
    return () => clearInterval(interval);
  }, [isStreaming, speed, addLog]);

  useEffect(() => {
    if (autoScroll.current && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const filteredLogs = useMemo(() => {
    return logs.filter(l =>
      levelFilter.has(l.level) &&
      compFilter.has(l.component) &&
      (!searchTerm || l.event.toLowerCase().includes(searchTerm.toLowerCase()) ||
       l.component.includes(searchTerm.toLowerCase()) ||
       l.correlation_id.includes(searchTerm.toLowerCase()))
    );
  }, [logs, levelFilter, compFilter, searchTerm]);

  const stats = useMemo(() => {
    const counts = { DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, CRITICAL: 0 };
    logs.forEach(l => { counts[l.level] = (counts[l.level] || 0) + 1; });
    return counts;
  }, [logs]);

  const toggleLevel = (lvl) => {
    setLevelFilter(prev => {
      const n = new Set(prev);
      n.has(lvl) ? n.delete(lvl) : n.add(lvl);
      return n;
    });
  };
  const toggleComp = (comp) => {
    setCompFilter(prev => {
      const n = new Set(prev);
      n.has(comp) ? n.delete(comp) : n.add(comp);
      return n;
    });
  };

  return (
    <div style={{
      minHeight: "100vh", background: C.bg, color: C.text,
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }}>
      <style>{`
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: ${C.bg}; }
        ::-webkit-scrollbar-thumb { background: ${C.border}; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: ${C.borderHi}; }
      `}</style>

      {/* Header */}
      <div style={{
        padding: "16px 24px", borderBottom: `1px solid ${C.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: C.bgSoft, position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: `linear-gradient(135deg, ${C.accent}, ${C.pink})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 15, fontWeight: 700, color: "#fff",
          }}>S</div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700 }}>SwarmForge Log Visualizer</div>
            <div style={{ fontSize: 11, color: C.dim }}>Real-time pipeline execution logs</div>
          </div>
          <div style={{
            display: "flex", alignItems: "center", gap: 6, marginLeft: 16,
            padding: "4px 12px", borderRadius: 999,
            background: isStreaming ? C.greenDim : C.redDim,
            border: `1px solid ${isStreaming ? C.green : C.red}33`,
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: isStreaming ? C.green : C.red,
              animation: isStreaming ? "pulse 1.5s ease infinite" : "none",
            }} />
            <span style={{ fontSize: 11, color: isStreaming ? C.green : C.red, fontWeight: 600 }}>
              {isStreaming ? "STREAMING" : "PAUSED"}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 11, color: C.dim }}>Speed:</span>
          {[{ label: "0.5×", val: 1600 }, { label: "1×", val: 800 }, { label: "2×", val: 400 }, { label: "4×", val: 200 }].map(s => (
            <button key={s.val} onClick={() => setSpeed(s.val)} style={{
              padding: "4px 10px", borderRadius: 6, fontSize: 11, fontWeight: 500, cursor: "pointer",
              border: `1px solid ${speed === s.val ? C.accent : C.border}`,
              background: speed === s.val ? C.accentDim : "transparent",
              color: speed === s.val ? C.accent : C.dim,
            }}>{s.label}</button>
          ))}
          <div style={{ width: 1, height: 24, background: C.border, margin: "0 4px" }} />
          <button onClick={() => setIsStreaming(!isStreaming)} style={{
            padding: "6px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
            border: `1px solid ${isStreaming ? C.orange : C.green}`,
            background: isStreaming ? C.orangeDim : C.greenDim,
            color: isStreaming ? C.orange : C.green,
          }}>{isStreaming ? "⏸ Pause" : "▶ Resume"}</button>
          <button onClick={() => { setLogs([]); setLogIdx(0); setStageStates(STAGES.map(s => ({ name: s, status: "pending" }))); setBudget({ tokens: 0, usd: 0 }); }} style={{
            padding: "6px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
            border: `1px solid ${C.red}44`, background: C.redDim, color: C.red,
          }}>Clear</button>
        </div>
      </div>

      <div style={{ padding: "16px 24px" }}>
        {/* Task + Budget + Stage row */}
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16,
        }}>
          {/* Task info + Stage tracker */}
          <div style={{
            background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <div>
                <span style={{ fontSize: 11, color: C.dim }}>Current Task</span>
                <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>
                  <span style={{ color: C.accent }}>{currentTask.taskId}</span>
                  <span style={{ color: C.dim, margin: "0 6px" }}>—</span>
                  <span style={{ color: C.text, fontSize: 12 }}>{currentTask.summary.slice(0, 45)}...</span>
                </div>
              </div>
              <span style={{
                fontSize: 10, fontWeight: 600, padding: "3px 10px", borderRadius: 999,
                background: C.accentDim, color: C.accent, border: `1px solid ${C.accent}33`,
              }}>{correlationId.current}</span>
            </div>
            <StageTracker stages={stageStates} />
          </div>

          {/* Budget */}
          <div style={{
            background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 16,
            display: "flex", flexDirection: "column", gap: 12,
          }}>
            <span style={{ fontSize: 11, color: C.dim }}>Budget Tracking</span>
            <BudgetGauge label="Tokens" current={budget.tokens} soft={100000} hard={140000} unit="" color={C.accent} />
            <BudgetGauge label="USD" current={budget.usd} soft={4.0} hard={6.0} unit="$" color={C.green} />
          </div>
        </div>

        {/* Stats bar */}
        <div style={{
          display: "flex", gap: 12, marginBottom: 16, alignItems: "center",
          padding: "10px 16px", background: C.card, border: `1px solid ${C.border}`, borderRadius: 10,
        }}>
          <span style={{ fontSize: 11, color: C.dim, marginRight: 4 }}>Total: {logs.length}</span>
          <div style={{ width: 1, height: 16, background: C.border }} />
          {Object.entries(stats).filter(([, v]) => v > 0).map(([lvl, count]) => (
            <span key={lvl} style={{
              fontSize: 11, color: LEVEL_STYLE[lvl].color, fontWeight: 500,
              fontFamily: "monospace",
            }}>{lvl}: {count}</span>
          ))}
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: C.dim }}>Showing: {filteredLogs.length}</span>
        </div>

        {/* Filters */}
        <div style={{
          display: "flex", gap: 8, marginBottom: 12, alignItems: "center", flexWrap: "wrap",
        }}>
          <span style={{ fontSize: 11, color: C.dim }}>Level:</span>
          {["DEBUG", "INFO", "WARNING", "ERROR"].map(l => (
            <FilterChip key={l} label={l} active={levelFilter.has(l)} color={LEVEL_STYLE[l].color} onClick={() => toggleLevel(l)} />
          ))}
          <div style={{ width: 1, height: 16, background: C.border, margin: "0 4px" }} />
          <span style={{ fontSize: 11, color: C.dim }}>Component:</span>
          {COMPONENTS.map(c => (
            <FilterChip key={c} label={c} active={compFilter.has(c)} color={COMP_COLORS[c]} onClick={() => toggleComp(c)} />
          ))}
        </div>

        {/* Search */}
        <div style={{ marginBottom: 12 }}>
          <input
            type="text" placeholder="Search logs... (task ID, component, message)" value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{
              width: "100%", padding: "8px 14px", borderRadius: 8, fontSize: 12,
              background: C.card, border: `1px solid ${C.border}`, color: C.text,
              outline: "none", fontFamily: "'JetBrains Mono', monospace",
              boxSizing: "border-box",
            }}
          />
        </div>

        {/* Log stream */}
        <div
          style={{
            background: C.bgSoft, border: `1px solid ${C.border}`, borderRadius: 10,
            height: 460, overflowY: "auto", overflowX: "hidden",
          }}
          onScroll={(e) => {
            const el = e.target;
            autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
          }}
        >
          {/* Header row */}
          <div style={{
            display: "grid", gridTemplateColumns: "160px 22px 100px 62px 1fr",
            gap: 8, padding: "8px 14px", borderBottom: `1px solid ${C.border}`,
            background: C.card, position: "sticky", top: 0, zIndex: 2,
            fontSize: 10, fontWeight: 600, color: C.dim, textTransform: "uppercase", letterSpacing: 0.5,
          }}>
            <span>Timestamp</span>
            <span></span>
            <span>Component</span>
            <span>Level</span>
            <span>Message</span>
          </div>

          {filteredLogs.length === 0 ? (
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              height: 200, color: C.dim, fontSize: 13,
            }}>
              {logs.length === 0 ? "Waiting for logs..." : "No logs match filters"}
            </div>
          ) : (
            filteredLogs.map(log => (
              <LogLine key={log.id} log={log} isNew={newLogIds.has(log.id)} />
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
