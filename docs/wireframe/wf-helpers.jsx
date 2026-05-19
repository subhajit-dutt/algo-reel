// Shared wireframe primitives for the engineer's-notebook aesthetic.
// Every piece is intentionally literal JSX so each label / scribble is
// directly text-editable in the design tool.

const W = 1240;
const H = 780;

// ── App chrome shared by every artboard ───────────────────────────────
function AppChrome({ crumb, title, sub, rightAnnot, children, tone = "default" }) {
  return (
    <div style={{ position: "absolute", inset: 0, fontFamily: "var(--hand)" }}>
      <div className={"paper paper-margin"}></div>
      <div className="frame">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 24, flexWrap: "nowrap" }}>
          <div className="col" style={{ gap: 2, flex: 1, minWidth: 0 }}>
            <div className="crumb" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{crumb}</div>
            <div className="h-title">{title}</div>
            {sub && <div className="h-sub" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{sub}</div>}
          </div>
          <div className="col" style={{ alignItems: "flex-end", gap: 6, flex: "0 0 auto" }}>
            <Logo />
            {rightAnnot && <div className="h-sub" style={{ fontStyle: "italic", whiteSpace: "nowrap" }}>{rightAnnot}</div>}
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

function Logo() {
  return (
    <div className="row" style={{ gap: 8 }}>
      <svg width="28" height="28" viewBox="0 0 28 28">
        <rect x="2" y="2" width="24" height="24" rx="4" fill="none" stroke="var(--ink)" strokeWidth="2"/>
        <path d="M10 8 L10 20 L20 14 Z" fill="var(--ink)" />
        <path d="M22 6 L25 6 M22 9 L25 9" stroke="var(--red)" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
      <div style={{ fontFamily: "var(--serif)", fontSize: 26, fontWeight: 700 }}>AlgoReel</div>
    </div>
  );
}

// Top nav strip — present on every screen
function TopNav({ active = "create" }) {
  const items = [
    ["create", "Create"],
    ["library", "Library"],
    ["jobs",    "Jobs"],
    ["settings","Settings"],
  ];
  return (
    <div className="row" style={{ gap: 8, marginTop: 4 }}>
      {items.map(([k, label]) => (
        <div key={k} className={"chip"} style={{
          background: k === active ? "var(--ink)" : "rgba(255,252,240,0.7)",
          color:      k === active ? "var(--paper-tint)" : "var(--ink)",
          borderColor: "var(--ink)",
          fontWeight: k === active ? 700 : 400,
        }}>{label}</div>
      ))}
      <div className="grow"></div>
      <div className="row" style={{ gap: 6 }}>
        <div style={{ width: 26, height: 26, borderRadius: 999, border: "1.5px solid var(--ink)", background: "var(--paper-warm)", display: "grid", placeItems: "center", fontFamily: "var(--serif)", fontSize: 16 }}>S</div>
      </div>
    </div>
  );
}

// ── Annotation: red ink note + arrow ──────────────────────────────────
function Annot({ style, children, color = "red", arrow = "none", thick = 1.4 }) {
  const c = color === "red" ? "var(--red)" : color === "blue" ? "var(--blue)" : "var(--ink)";
  return (
    <div className={"annot " + (color === "ink" ? "ink" : color === "blue" ? "blue" : "")} style={style}>
      {arrow === "left" && (
        <svg width="36" height="20" viewBox="0 0 36 20" style={{ position: "absolute", right: "100%", top: 6, marginRight: 4 }}>
          <path d="M34 10 Q 18 4, 4 12" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
          <path d="M4 12 L 10 8 M4 12 L 9 14" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
        </svg>
      )}
      {arrow === "right" && (
        <svg width="40" height="22" viewBox="0 0 40 22" style={{ position: "absolute", left: "100%", top: 6, marginLeft: 4 }}>
          <path d="M2 12 Q 18 4, 36 12" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
          <path d="M36 12 L 30 8 M36 12 L 30 16" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
        </svg>
      )}
      {arrow === "down" && (
        <svg width="22" height="40" viewBox="0 0 22 40" style={{ position: "absolute", left: 6, top: "100%", marginTop: 2 }}>
          <path d="M10 2 Q 6 18, 12 36" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
          <path d="M12 36 L 7 32 M12 36 L 16 31" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
        </svg>
      )}
      {arrow === "up" && (
        <svg width="22" height="40" viewBox="0 0 22 40" style={{ position: "absolute", left: 6, bottom: "100%", marginBottom: 2 }}>
          <path d="M12 38 Q 6 22, 10 4" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
          <path d="M10 4 L 6 9 M10 4 L 15 8" stroke={c} strokeWidth={thick} fill="none" strokeLinecap="round"/>
        </svg>
      )}
      {children}
    </div>
  );
}

// Scribble placeholder text lines (multiline gray bars)
function Lines({ count = 3, w = "100%", gap = 8 }) {
  return (
    <div className="col" style={{ gap, width: w }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="scrib" style={{
          width: i === count - 1 ? "55%" : (i % 2 === 0 ? "94%" : "82%"),
          opacity: 0.55,
        }}></div>
      ))}
    </div>
  );
}

// Stepper used in render/done screens
function Stepper({ steps, currentIdx, failedIdx = -1 }) {
  return (
    <div className="row" style={{ gap: 0, width: "100%" }}>
      {steps.map((s, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        const failed = i === failedIdx;
        const c = failed ? "var(--red)" : (done || active ? "var(--ink)" : "var(--pencil)");
        return (
          <React.Fragment key={s}>
            <div className="col" style={{ alignItems: "center", gap: 4, minWidth: 0 }}>
              <div style={{
                width: 30, height: 30, borderRadius: 999,
                border: `2px solid ${c}`,
                background: done ? "var(--ink)" : (active ? "var(--paper-tint)" : "transparent"),
                color: done ? "var(--paper-tint)" : c,
                display: "grid", placeItems: "center",
                fontFamily: "var(--serif)", fontSize: 18, fontWeight: 700,
                boxShadow: active ? `2px 2px 0 ${c}` : "none",
              }}>{done ? "✓" : failed ? "!" : i + 1}</div>
              <div style={{
                fontFamily: "var(--hand)", fontSize: 14, color: c,
                fontWeight: active || failed ? 700 : 400,
                whiteSpace: "nowrap",
              }}>{s}</div>
            </div>
            {i < steps.length - 1 && (
              <div style={{
                flex: 1, height: 0, marginTop: 15,
                borderTop: `2px ${i < currentIdx ? "solid" : "dashed"} ${i < currentIdx ? "var(--ink)" : "var(--pencil)"}`,
              }}></div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// Scene placeholder (storyboard tile)
function SceneTile({ idx, state = "queued", w = 150, h = 96, label = "" }) {
  // state: queued, rendering, done, failed
  const palette = {
    queued:    { bg: "transparent",          border: "var(--pencil)",  badge: "queued",    badgeBg: "transparent",      badgeColor: "var(--pencil)" },
    rendering: { bg: "rgba(247,211,107,.35)",border: "var(--ink)",     badge: "rendering", badgeBg: "var(--hl)",        badgeColor: "var(--ink)" },
    done:      { bg: "rgba(126,181,154,.18)",border: "var(--ink)",     badge: "done",      badgeBg: "var(--mint)",      badgeColor: "#fff" },
    failed:    { bg: "rgba(184,65,44,.10)",  border: "var(--red)",     badge: "failed",    badgeBg: "var(--red)",       badgeColor: "#fff" },
  }[state];
  const isQueued = state === "queued";
  return (
    <div style={{ width: w, position: "relative" }}>
      <div style={{
        width: w, height: h,
        border: `1.8px ${isQueued ? "dashed" : "solid"} ${palette.border}`,
        background: palette.bg,
        borderRadius: 4, position: "relative",
        boxShadow: state === "done" || state === "rendering" ? `2px 2px 0 var(--ink)` : "none",
      }}>
        <div style={{ position: "absolute", top: 4, left: 6, fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-soft)" }}>#{String(idx).padStart(2,"0")}</div>
        {state === "rendering" && (
          <div style={{ position: "absolute", inset: "30% 18% 30% 18%", border: "1.5px solid var(--ink)", borderRadius: 3, background: "rgba(255,252,240,0.4)" }}>
            <div style={{ position: "absolute", inset: 0, background: "repeating-linear-gradient(45deg, rgba(28,34,48,0.18) 0 4px, transparent 4px 9px)" }}></div>
          </div>
        )}
        {state === "done" && (
          <svg viewBox="0 0 100 60" style={{ position: "absolute", inset: 12 }}>
            <circle cx="32" cy="34" r="10" fill="none" stroke="var(--ink)" strokeWidth="2"/>
            <path d="M58 22 L 82 22 L 70 46 Z" fill="none" stroke="var(--ink)" strokeWidth="2"/>
            <path d="M14 50 Q 50 38, 88 52" stroke="var(--ink)" strokeWidth="1.5" fill="none" strokeDasharray="3 3"/>
          </svg>
        )}
        {state === "queued" && (
          <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", color: "var(--pencil)", fontFamily: "var(--serif)", fontSize: 32, opacity: 0.45 }}>·  ·  ·</div>
        )}
        {state === "failed" && (
          <svg viewBox="0 0 100 60" style={{ position: "absolute", inset: 8 }}>
            <path d="M12 12 L88 50 M12 50 L88 12" stroke="var(--red)" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        )}
      </div>
      <div className="row" style={{ marginTop: 4, gap: 6, justifyContent: "space-between" }}>
        <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis", maxWidth: w - 70 }}>{label}</div>
        <div className="pill" style={{
          fontSize: 9, padding: "1px 7px",
          background: palette.badgeBg, color: palette.badgeColor,
          borderColor: state === "queued" ? "var(--pencil)" : (state === "failed" ? "var(--red)" : "var(--ink)"),
        }}>{palette.badge}</div>
      </div>
    </div>
  );
}

// Small icon-as-ink helpers used throughout
function InkIcon({ kind, size = 16, color = "var(--ink)" }) {
  const s = size, stroke = 1.6;
  const paths = {
    play:  <path d="M5 4 L19 12 L5 20 Z" fill={color} stroke={color} strokeWidth={stroke} strokeLinejoin="round"/>,
    pause: <g fill={color}><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></g>,
    download: <g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><path d="M12 4 L12 16"/><path d="M7 11 L12 16 L17 11"/><path d="M5 20 L19 20"/></g>,
    share: <g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8 11 L16 7 M8 13 L16 17"/></g>,
    plus: <g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><path d="M12 5 L12 19 M5 12 L19 12"/></g>,
    search: <g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><circle cx="11" cy="11" r="6"/><path d="M16 16 L20 20"/></g>,
    bolt: <path d="M13 3 L5 13 L11 13 L9 21 L19 9 L13 9 Z" fill="none" stroke={color} strokeWidth={stroke} strokeLinejoin="round"/>,
    image: <g fill="none" stroke={color} strokeWidth={stroke}><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="1.5" fill={color}/><path d="M5 17 L10 12 L14 16 L19 11 L21 13"/></g>,
    code:  <g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><path d="M8 7 L3 12 L8 17"/><path d="M16 7 L21 12 L16 17"/><path d="M14 4 L10 20"/></g>,
    retry: <g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><path d="M4 12 A 8 8 0 1 1 7 18"/><path d="M3 17 L7 18 L7 14"/></g>,
    eye:   <g fill="none" stroke={color} strokeWidth={stroke}><path d="M2 12 C 5 6, 19 6, 22 12 C 19 18, 5 18, 2 12 Z"/><circle cx="12" cy="12" r="3" fill={color}/></g>,
    clock: <g fill="none" stroke={color} strokeWidth={stroke}><circle cx="12" cy="12" r="8"/><path d="M12 7 L12 12 L15 14"/></g>,
    folder:<g fill="none" stroke={color} strokeWidth={stroke}><path d="M3 7 L10 7 L12 9 L21 9 L21 19 L3 19 Z"/></g>,
    spark: <g fill={color}><path d="M12 2 L13 9 L20 10 L13 11 L12 18 L11 11 L4 10 L11 9 Z"/></g>,
    cancel:<g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><circle cx="12" cy="12" r="8"/><path d="M8 8 L16 16 M16 8 L8 16"/></g>,
    expand:<g fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"><path d="M4 9 L4 4 L9 4 M20 9 L20 4 L15 4 M4 15 L4 20 L9 20 M20 15 L20 20 L15 20"/></g>,
    sound: <g fill="none" stroke={color} strokeWidth={stroke}><path d="M5 9 L9 9 L13 5 L13 19 L9 15 L5 15 Z" fill={color}/><path d="M16 8 Q 19 12, 16 16" strokeLinecap="round"/></g>,
    film:  <g fill="none" stroke={color} strokeWidth={stroke}><rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 9 L21 9 M3 15 L21 15 M7 5 L7 19 M17 5 L17 19"/></g>,
  };
  return <svg width={s} height={s} viewBox="0 0 24 24">{paths[kind]}</svg>;
}

// Sticky note / post-it
function Sticky({ children, rot = -2, bg = "var(--hl)", style }) {
  return (
    <div data-sticky="1" style={{
      transform: `rotate(${rot}deg)`,
      background: bg, padding: "10px 12px",
      fontFamily: "var(--hand)", fontSize: 14, color: "var(--ink)",
      boxShadow: "2px 4px 8px rgba(0,0,0,0.10)",
      maxWidth: 220, position: "relative", lineHeight: 1.25,
      ...style,
    }}>
      <div className="tape"></div>
      {children}
    </div>
  );
}

// Responsive note pinned to corner
function ResponsiveNote({ children, style }) {
  return (
    <div data-rn="1" style={{
      position: "absolute", display: "inline-flex", alignItems: "center", gap: 6,
      fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-soft)",
      letterSpacing: "0.06em", textTransform: "uppercase",
      padding: "3px 8px", border: "1px dashed var(--ink-soft)", borderRadius: 4,
      background: "rgba(255,252,240,0.7)",
      ...style,
    }}>
      <svg width="12" height="12" viewBox="0 0 12 12"><rect x="1" y="2" width="10" height="6" rx="1" fill="none" stroke="currentColor"/><rect x="4" y="9" width="4" height="1.5" fill="currentColor"/></svg>
      {children}
    </div>
  );
}

Object.assign(window, { W, H, AppChrome, TopNav, Annot, Lines, Stepper, SceneTile, InkIcon, Sticky, ResponsiveNote, Logo });
