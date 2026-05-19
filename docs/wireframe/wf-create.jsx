// Wireframe components for all AlgoReel screens.
// Each is a fixed-size desktop frame (1600 × 900 px) with notebook styling.

const W = 1600;
const H = 900;

// ════════════════════════════════════════════════════════════════════════
//  1. PROMPT ENTRY — two layout variants
// ════════════════════════════════════════════════════════════════════════

function PromptA() {
  return (
    <AppChrome
      crumb="POST /api/videos · new (variant A)"
      title="Describe your video."
      sub="single textarea · LLM expands into a script plan before render"
      rightAnnot="v1 · happy path"
    >
      <TopNav active="create" />

      <div className="col" style={{ flex: 1, gap: 14 }}>
        {/* main textarea */}
        <div className="ink-box" style={{ flex: 1, padding: 0, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div className="row" style={{ padding: "10px 14px", borderBottom: "1.5px dashed var(--ink-soft)" }}>
            <div className="h-tag">prompt</div>
            <div className="grow"></div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-soft)" }}>148 ch</div>
          </div>
          <div style={{ flex: 1, padding: "16px 18px", fontFamily: "var(--hand)", fontSize: 16, lineHeight: 1.5, overflow: "auto" }}>
            Explain how Bloom filters work. Start with the false-positive problem, then show set membership naively (O(n) lookup). Introduce a bit array + hash function. Show two more inserts so collisions are visible. Walk through a lookup (hash → check bits → return). End with the sizing rule: m = -n·ln(p) / (ln(2))².
          </div>
        </div>

        {/* options row */}
        <div className="row" style={{ gap: 14, alignItems: "stretch" }}>
          {/* renderer */}
          <div className="ink-box" style={{ flex: 1, padding: 14, position: "relative", minWidth: 0 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>renderer</div>
            <div className="row" style={{ gap: 8 }}>
              <div className="ink-box mint" style={{ flex: 1, minWidth: 0, padding: "10px 12px", boxShadow: "2px 2px 0 var(--ink)" }}>
                <div className="row" style={{ gap: 8, justifyContent: "space-between" }}>
                  <div className="row" style={{ gap: 6, minWidth: 0 }}>
                    <InkIcon kind="code" size={20}/>
                    <div style={{ fontFamily: "var(--serif)", fontSize: 20, fontWeight: 700, whiteSpace: "nowrap" }}>Manim</div>
                  </div>
                  <div className="pill" style={{ background: "var(--ink)", color: "var(--paper-tint)", fontSize: 9, flex: "0 0 auto" }}>v1</div>
                </div>
                <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)", marginTop: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>code-driven · 3b1b style</div>
              </div>
              <div className="ink-box ghost" style={{ flex: 1, minWidth: 0, padding: "10px 12px" }}>
                <div className="row" style={{ gap: 8, justifyContent: "space-between" }}>
                  <div className="row" style={{ gap: 6, minWidth: 0 }}>
                    <InkIcon kind="image" size={20} color="var(--ink-soft)"/>
                    <div style={{ fontFamily: "var(--serif)", fontSize: 20, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>AI-image</div>
                  </div>
                  <div className="pill" style={{ fontSize: 9, color: "var(--ink-soft)", flex: "0 0 auto" }}>v1.1</div>
                </div>
                <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--pencil)", marginTop: 4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>Flux stills + ken-burns</div>
              </div>
            </div>
          </div>

          {/* voice */}
          <div className="ink-box" style={{ width: 280, padding: 14 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>voice (tts)</div>
            <div className="ink-box mint" style={{ padding: "10px 12px", boxShadow: "2px 2px 0 var(--ink)" }}>
              <div className="row" style={{ gap: 8 }}>
                <InkIcon kind="mic" size={18}/>
                <div style={{ fontFamily: "var(--serif)", fontSize: 18, fontWeight: 700 }}>Shimmer</div>
                <div className="pill" style={{ background: "var(--ink)", color: "var(--paper-tint)", fontSize: 9 }}>default</div>
              </div>
              <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)", marginTop: 4 }}>neutral · fast</div>
            </div>
          </div>

          {/* duration cap */}
          <div className="ink-box" style={{ width: 200, padding: 14 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>duration cap</div>
            <div className="row" style={{ gap: 10, alignItems: "baseline" }}>
              <div style={{ fontFamily: "var(--serif)", fontSize: 32, lineHeight: 1, fontWeight: 700 }}>3</div>
              <div style={{ fontFamily: "var(--hand)", fontSize: 14, color: "var(--ink-soft)" }}>minutes max</div>
            </div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)", marginTop: 4 }}>llm will target ~2:30</div>
          </div>
        </div>

        {/* bottom row */}
        <div className="row" style={{ justifyContent: "space-between", marginTop: 6, gap: 12, flexWrap: "nowrap" }}>
          <div className="row" style={{ gap: 10, minWidth: 0, flexWrap: "nowrap" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-soft)", whiteSpace: "nowrap" }}>
              EST · 6 scenes · ~7 min
            </div>
          </div>
          <div className="row" style={{ gap: 8, flex: "0 0 auto" }}>
            <div className="ink-btn ghost">save draft</div>
            <div className="ink-btn primary">
              <InkIcon kind="play" size={14} color="var(--paper-tint)"/>
              generate
            </div>
          </div>
        </div>
      </div>

      <Sticky rot={3} style={{ position: "absolute", left: 110, bottom: 22, width: 220 }}>
        <b>why no template gallery?</b><br/>
        users said the single textarea is faster. revisit in v1.1 if drop-off shows otherwise.
      </Sticky>

      <ResponsiveNote style={{ right: 32, bottom: 22 }}>≥ 1024px · stacks below 720</ResponsiveNote>
    </AppChrome>
  );
}

function RenderA() {
  return (
    <AppChrome
      crumb="status: rendering · job 9f3a · variant A"
      title="How Bloom filters work"
      sub="stepper + storyboard · scene cards fill in as renders complete"
      rightAnnot="visual progress"
    >
      <TopNav active="create" />

      <div className="row" style={{ gap: 14, flex: 1, minHeight: 0 }}>
        {/* left: storyboard + linear stepper */}
        <div className="col" style={{ flex: 1, gap: 12, minHeight: 0 }}>
          {/* stepper */}
          <div className="ink-box" style={{ padding: 14 }}>
            <div className="col" style={{ gap: 7, fontFamily: "var(--hand)", fontSize: 14 }}>
              <div className="row"><span className="cbox on"></span>script ready · 6 scenes · 92.4s</div>
              <div className="row"><span className="cbox on"></span>fan-out to render pool</div>
              <div className="row"><span className="cbox on"></span>tts for all scenes (~18s)</div>
              <div className="row"><span className="cbox pulse"></span>rendering scenes in parallel</div>
              <div className="row"><span className="cbox"></span>compose final video</div>
            </div>
          </div>

          {/* scene grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, flex: 1, alignContent: "start" }}>
            {[
              [1, "done", "Cold-open: the false-positive question"],
              [2, "done", "Set membership, naively"],
              [3, "done", "Enter the bit array + hash function"],
              [4, "running", "Two more inserts — collisions are fine"],
              [5, "pending", "Lookup: hash → check bits → return"],
              [6, "pending", "Sizing rule: m = -n·ln(p) / (ln 2)²"],
            ].map(([i, state, t]) => {
              const bg = state === "done" ? "linear-gradient(135deg, #2e3a55, #20283a)" : "transparent";
              const hasThumbnail = state === "done";
              return (
                <div key={i} className="ink-box" style={{ padding: 8, background: state === "pending" ? "rgba(255,252,240,0.4)" : "rgba(255,252,240,0.7)" }}>
                  <div style={{
                    height: 80, borderRadius: 3, position: "relative",
                    background: bg,
                    border: state === "running" ? "2px solid var(--hl)" : "1.5px solid var(--ink)",
                  }}>
                    {hasThumbnail && (
                      <svg viewBox="0 0 200 80" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
                        {i === 1 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                          <text x="100" y="45" fontSize="14" textAnchor="middle" fill="#f3ecd8">alice?</text>
                          <rect x="60" y="50" width="80" height="18"/>
                        </g>}
                        {i === 2 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                          <circle cx="40" cy="40" r="8"/><circle cx="70" cy="40" r="8"/><circle cx="100" cy="40" r="8"/>
                          <path d="M48 40 L62 40 M78 40 L92 40"/>
                        </g>}
                        {i === 3 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                          {Array.from({ length: 8 }).map((_, k) => <rect key={k} x={40 + k * 15} y={30} width={12} height={20}/>)}
                        </g>}
                      </svg>
                    )}
                    {state === "running" && (
                      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
                        <div className="pill hl" style={{ fontSize: 9 }}>▶ rendering</div>
                      </div>
                    )}
                    {state === "pending" && (
                      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-soft)" }}>
                        queued
                      </div>
                    )}
                  </div>
                  <div style={{ fontFamily: "var(--mono)", fontSize: 10, marginTop: 4, color: state === "done" ? "var(--ink)" : "var(--ink-soft)" }}>scene {String(i).padStart(2, "0")}</div>
                  <div style={{ fontFamily: "var(--hand)", fontSize: 12, lineHeight: 1.2, marginTop: 2, height: 32, overflow: "hidden", color: state === "pending" ? "var(--ink-soft)" : "var(--ink)" }}>{t}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* right: meta + live stats */}
        <div className="col" style={{ width: 270, gap: 12 }}>
          <div className="ink-box mint" style={{ padding: 14 }}>
            <div className="h-tag">time estimate</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 42, lineHeight: 1, fontWeight: 700, marginTop: 4 }}>~6 min</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 13 }}>6 scenes · 92 sec video</div>
          </div>

          <div className="ink-box warm" style={{ padding: 12 }}>
            <div className="h-tag" style={{ marginBottom: 6 }}>time elapsed</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 30, lineHeight: 1, fontWeight: 700 }}>14s</div>
            <div className="scrib" style={{ marginTop: 8 }}></div>
            <div className="h-tag" style={{ marginTop: 10 }}>est. remaining</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 30, lineHeight: 1, fontWeight: 700, color: "var(--ink-2)" }}>~6 min</div>
          </div>

          <div className="ink-box" style={{ padding: 12 }}>
            <div className="h-tag" style={{ marginBottom: 6 }}>status</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)" }}>script ready · awaiting approval</div>
            <div className="pill mint" style={{ fontSize: 9, marginTop: 6 }}>✓ ready for fan-out</div>
          </div>

          <div className="ink-box" style={{ padding: 12 }}>
            <div className="h-tag" style={{ marginBottom: 6 }}>renderer</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 18, fontWeight: 700 }}>Manim</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)" }}>code-driven · 3b1b</div>
          </div>

          <div className="ink-btn ghost" style={{ width: "100%" }}>view logs</div>
          <div className="ink-btn sm" style={{ width: "100%" }}>cancel job</div>

          <Annot style={{ top: -16, left: -180, width: 160 }} arrow="right">
            storyboard layout —<br/>cards fill in as<br/>scenes complete
          </Annot>
        </div>
      </div>
    </AppChrome>
  );
}

function DoneA() {
  return (
    <AppChrome
      crumb="status: done · job 9f3a · variant A"
      title="How Bloom filters work"
      sub="hero player · video complete and stored in R2"
      rightAnnot="share-first layout"
    >
      <TopNav active="create" />

      <div className="row" style={{ gap: 14, flex: 1, minHeight: 0 }}>
        {/* left: player */}
        <div className="col" style={{ flex: 1, gap: 12, minHeight: 0 }}>
          <div className="ink-box" style={{ flex: 1, padding: 0, display: "flex", flexDirection: "column", minHeight: 0, background: "#1c2230" }}>
            <div style={{
              flex: 1, display: "grid", placeItems: "center", position: "relative",
              background: "linear-gradient(135deg, #2e3a55 0%, #20283a 100%)",
            }}>
              <svg viewBox="0 0 400 225" style={{ width: "60%", maxWidth: 400 }}>
                <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                  {Array.from({ length: 16 }).map((_, i) => (
                    <rect key={i} x={40 + i * 20} y={95} width={16} height={35}/>
                  ))}
                  <rect x="100" y="95" width="16" height="35" fill="#f7d36b"/>
                  <rect x="180" y="95" width="16" height="35" fill="#f7d36b"/>
                  <rect x="260" y="95" width="16" height="35" fill="#f7d36b"/>
                  <text x="200" y="70" fontSize="12" textAnchor="middle" fill="#f3ecd8">is 'alice' in here?</text>
                  <path d="M200 75 L200 88" markerEnd="url(#arrow)"/>
                </g>
                <defs>
                  <marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
                    <path d="M0 0 L8 4 L0 8 Z" fill="#f3ecd8"/>
                  </marker>
                </defs>
              </svg>
              <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
                <div style={{ width: 64, height: 64, borderRadius: 999, background: "rgba(243,236,216,0.95)", display: "grid", placeItems: "center" }}>
                  <InkIcon kind="play" size={28}/>
                </div>
              </div>
              <div style={{ position: "absolute", bottom: 12, left: 12, fontFamily: "var(--mono)", fontSize: 11, color: "rgba(243,236,216,0.9)", background: "rgba(0,0,0,0.5)", padding: "2px 6px", borderRadius: 2 }}>1:32</div>
            </div>
            <div style={{ padding: "10px 14px", background: "#1c2230", borderTop: "1.5px solid var(--ink)" }}>
              <div style={{ height: 6, background: "rgba(243,236,216,0.2)", borderRadius: 999, position: "relative", overflow: "hidden" }}>
                <div style={{ position: "absolute", inset: 0, width: "0%", background: "var(--mint)" }}></div>
              </div>
            </div>
          </div>

          <div className="row" style={{ gap: 8 }}>
            <div className="ink-btn primary" style={{ flex: 1, justifyContent: "center" }}>
              <InkIcon kind="download" size={14} color="var(--paper-tint)"/>
              download mp4
            </div>
            <div className="ink-btn" style={{ flex: 1, justifyContent: "center" }}>
              <InkIcon kind="share" size={14}/>
              copy link
            </div>
          </div>
        </div>

        {/* right: meta */}
        <div className="col" style={{ width: 260, gap: 12 }}>
          <div className="ink-box mint" style={{ padding: 14 }}>
            <div className="h-tag">token usage</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 44, lineHeight: 1, fontWeight: 700 }}>12.4k</div>
            <div className="scrib mid" style={{ marginTop: 8, opacity: 0.5 }}></div>
            <div className="col" style={{ gap: 4, marginTop: 8, fontFamily: "var(--mono)", fontSize: 10.5 }}>
              <div className="row"><span>script gen</span><span className="leader"></span><span>2.8k</span></div>
              <div className="row"><span>scene code × 6</span><span className="leader"></span><span>8.4k</span></div>
              <div className="row"><span>retry overhead</span><span className="leader"></span><span>1.2k</span></div>
            </div>
          </div>

          <div className="ink-box" style={{ padding: 12 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>stats</div>
            <div className="col" style={{ gap: 4, fontFamily: "var(--mono)", fontSize: 11 }}>
              <div className="row"><span>elapsed</span><span className="leader"></span><span>8:46</span></div>
              <div className="row"><span>retries</span><span className="leader"></span><span>1 (scene 4)</span></div>
              <div className="row"><span>tokens used</span><span className="leader"></span><span>12,408</span></div>
              <div className="row"><span>R2 path</span><span className="leader"></span><span>9f3a.mp4</span></div>
            </div>
          </div>

          <div className="ink-box" style={{ padding: 12 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>renderer</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 20, fontWeight: 700 }}>Manim</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-2)" }}>code-driven · 3b1b style</div>
          </div>

          <div className="ink-btn sm" style={{ width: "100%" }}>view generated code</div>
          <div className="ink-btn sm ghost" style={{ width: "100%" }}>make another</div>

          <Sticky rot={2} bg="rgba(126,181,154,0.6)">
            🎉 faster than p50 by 1:14
          </Sticky>
        </div>
      </div>
    </AppChrome>
  );
}

function FailA() {
  return (
    <AppChrome
      crumb="status: partially_failed · job 9f3a · variant A"
      title="Scene 4 failed — manual retry"
      sub="show error · user clicks retry button · no auto-retry"
      rightAnnot="simple manual retry"
    >
      <TopNav active="create" />

      <div className="row" style={{ gap: 14, flex: 1, minHeight: 0 }}>
        {/* left: failed scene card */}
        <div className="col" style={{ flex: 1, gap: 12, minWidth: 0 }}>
          <div className="ink-box fail" style={{ padding: 16 }}>
            <div className="row" style={{ gap: 14, alignItems: "flex-start" }}>
              <div style={{ width: 80, flex: "0 0 80px" }}>
                <div style={{ fontFamily: "var(--serif)", fontSize: 48, lineHeight: 1, fontWeight: 700, color: "var(--red)" }}>04</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--ink-soft)", marginTop: 2 }}>46–62s</div>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: "var(--serif)", fontSize: 26, fontWeight: 700, lineHeight: 1.2 }}>
                  Two more inserts — collisions are fine
                </div>
                <div style={{ fontFamily: "var(--hand)", fontSize: 15, color: "var(--ink-2)", marginTop: 6, lineHeight: 1.35 }}>
                  Add 'bob' and 'eve'; bits flip; highlight that some bits are shared.
                </div>
                <div className="row" style={{ gap: 8, marginTop: 10 }}>
                  <div className="pill red" style={{ fontSize: 10 }}>NameError: 'updated_array' not defined</div>
                  <div className="pill" style={{ fontSize: 10 }}>failed 04:48 ago</div>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 16, padding: "12px 14px", background: "rgba(184,65,44,0.08)", borderRadius: 3, border: "1.5px dashed var(--red)" }}>
              <div className="h-tag" style={{ color: "var(--red)", marginBottom: 6 }}>error</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.55, color: "var(--ink-2)", whiteSpace: "pre-wrap" }}>
{`Traceback (most recent call last):
  File "scene_004.py", line 38, in construct
    self.play(Transform(bit_array, `}<span style={{ color: "var(--red)", fontWeight: 700 }}>updated_array</span>{`))
NameError: name 'updated_array' is not defined.`}
              </div>
            </div>

            <div className="row" style={{ gap: 8, marginTop: 14 }}>
              <div className="ink-btn primary">
                <InkIcon kind="retry" size={14} color="var(--paper-tint)"/>
                retry scene 4
              </div>
              <div className="ink-btn sm">edit code manually</div>
              <div className="grow"></div>
              <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-soft)" }}>est. add'l time: ~45s</div>
            </div>
          </div>

          {/* other scenes OK */}
          <div className="ink-box mint" style={{ padding: 14 }}>
            <div className="h-tag">5 of 6 scenes complete</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 14, marginTop: 4, color: "var(--ink-2)" }}>
              Scenes 1, 2, 3, 5, 6 are already rendered and stored in R2. Only scene 4 needs retry.
            </div>
            <div className="row" style={{ gap: 6, marginTop: 10, flexWrap: "wrap" }}>
              {[1, 2, 3, 4, 5, 6].map((i) => {
                const failed = i === 4;
                return (
                  <div key={i} className={failed ? "pill red" : "pill mint"} style={{ fontSize: 10 }}>
                    #{String(i).padStart(2, "0")} {failed ? "failed" : "✓"}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* right: retry notes */}
        <div className="col" style={{ width: 300, gap: 12 }}>
          <div className="ink-box" style={{ padding: 14 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>retry policy (v1)</div>
            <div className="col" style={{ gap: 6, fontFamily: "var(--hand)", fontSize: 14 }}>
              <div>• no automatic retries</div>
              <div>• user clicks to retry failed scene</div>
              <div>• unlimited manual retries</div>
              <div>• can edit code before retry</div>
            </div>
          </div>

          <div className="ink-box" style={{ padding: 14 }}>
            <div className="h-tag" style={{ marginBottom: 8 }}>salvage strategy</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 14, lineHeight: 1.4 }}>
              Completed scenes are stored in R2. When you retry scene 4, only that scene re-renders. The final video will be composed from the cached + new scenes.
            </div>
          </div>

          <div className="ink-box warm" style={{ padding: 12 }}>
            <div className="h-tag" style={{ marginBottom: 6 }}>time spent so far</div>
            <div style={{ fontFamily: "var(--serif)", fontSize: 32, fontWeight: 700, lineHeight: 1 }}>6:20</div>
            <div style={{ fontFamily: "var(--hand)", fontSize: 13, color: "var(--ink-soft)", marginTop: 2 }}>not wasted — 5 scenes cached</div>
          </div>

          <Sticky rot={-3}>
            <b>TRD §4.6:</b> user can also download the partial result (5 scenes) if they want to proceed without scene 4.
            (TRD §4.6, case 2)
          </Sticky>
        </div>

        {/* stderr */}
        <div className="ink-box" style={{ width: 460, padding: 0, display: "flex", flexDirection: "column" }}>
          <div className="row" style={{ padding: "8px 12px", borderBottom: "1.5px dashed var(--ink-soft)", background: "rgba(184,65,44,0.08)" }}>
            <div className="h-tag" style={{ color: "var(--red)" }}>scene 4 · stderr</div>
            <div className="grow"></div>
            <div className="pill red" style={{ fontSize: 9 }}>NameError</div>
          </div>
          <div style={{ flex: 1, padding: "12px 14px", fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.55, color: "var(--ink-2)", whiteSpace: "pre", overflow: "hidden" }}>
{`Traceback (most recent call last):
  File "scene_004.py", line 38, in construct
    self.play(Transform(bit_array, `}<span style={{ color: "var(--red)", fontWeight: 700 }}>updated_array</span>{`))
NameError: name 'updated_array' is not defined.
Did you mean: 'bit_array'?`}
          </div>
          <div className="row" style={{ padding: "8px 12px", borderTop: "1.5px dashed var(--ink-soft)", gap: 6, flexWrap: "wrap" }}>
            <div className="ink-btn sm"><InkIcon kind="code" size={12}/>view generated code</div>
            <div className="ink-btn sm">edit code manually</div>
          </div>
        </div>
      </div>

      <Annot style={{ top: 100, left: 280, width: 200 }} arrow="left">no auto-retry for v1 —<br/>user clicks to retry<br/>failed scenes</Annot>
    </AppChrome>
  );
}

// ════════════════════════════════════════════════════════════════════════
//  5. LIBRARY — past videos
// ════════════════════════════════════════════════════════════════════════

const LIBRARY = [
  { id: "9f3a", title: "How Bloom filters work",        when: "today · 14:22", dur: "1:32", scenes: 6, state: "done",    r: "manim" },
  { id: "8b21", title: "Why the FFT is O(n log n)",      when: "today · 09:11", dur: "2:48", scenes: 11, state: "done",    r: "manim" },
  { id: "7c40", title: "Dijkstra, step by step",         when: "yesterday",     dur: "1:48", scenes: 7, state: "done",    r: "manim" },
  { id: "6e1c", title: "B-trees, drawn by hand",         when: "yesterday",     dur: "1:12", scenes: 5, state: "done",    r: "ai_image" },
  { id: "5a99", title: "What is a hash collision?",      when: "2d ago",        dur: "0:54", scenes: 4, state: "done",    r: "manim" },
  { id: "4d72", title: "Reed–Solomon error correction",  when: "2d ago",        dur: "—",    scenes: 8, state: "failed",  r: "manim" },
  { id: "3f88", title: "How TLS handshakes work",        when: "3d ago",        dur: "2:31", scenes: 9, state: "done",    r: "manim" },
  { id: "2b04", title: "RAFT consensus, visually",       when: "3d ago",        dur: "—",    scenes: 6, state: "running", r: "manim" },
];

function LibraryA() {
  return (
    <AppChrome
      crumb="GET /api/videos · library"
      title="Library"
      sub="grid of past renders · cards · quick-glance state"
      rightAnnot="default view"
    >
      <TopNav active="library" />

      {/* filter bar */}
      <div className="ink-box" style={{ padding: "10px 14px" }}>
        <div className="row" style={{ gap: 10 }}>
          <div className="row" style={{ gap: 6, flex: 1, maxWidth: 360 }}>
            <InkIcon kind="search" size={14}/>
            <div className="field" style={{ flex: 1, padding: "5px 8px", color: "var(--pencil)", fontStyle: "italic" }}>search title or prompt...</div>
          </div>
          <div className="grow"></div>
          <div className="row" style={{ gap: 4 }}>
            <div className="chip" style={{ background: "var(--ink)", color: "var(--paper-tint)", borderColor: "var(--ink)" }}>all 24</div>
            <div className="chip">done 21</div>
            <div className="chip" style={{ borderColor: "var(--red)", color: "var(--red)" }}>failed 2</div>
            <div className="chip">running 1</div>
          </div>
          <div style={{ width: 1, background: "var(--ink-soft)", height: 22, opacity: 0.3 }}></div>
          <div className="chip">manim</div>
          <div className="chip" style={{ color: "var(--ink-soft)" }}>ai-image</div>
          <div style={{ width: 1, background: "var(--ink-soft)", height: 22, opacity: 0.3 }}></div>
          <div className="chip">last 7 days ▾</div>
          <div className="ink-btn primary sm"><InkIcon kind="plus" size={12} color="var(--paper-tint)"/>new</div>
        </div>
      </div>

      {/* grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, flex: 1, minHeight: 0, alignContent: "start" }}>
        {LIBRARY.slice(0, 8).map((v, i) => {
          const tone = v.state === "failed" ? "fail" : v.state === "running" ? "warm" : "";
          return (
            <div key={v.id} className={"ink-box " + tone} style={{ padding: 10, position: "relative" }}>
              {/* thumbnail */}
              <div style={{
                height: 110, borderRadius: 3, position: "relative", overflow: "hidden",
                background: v.state === "failed"
                  ? "repeating-linear-gradient(45deg, rgba(184,65,44,0.12) 0 8px, transparent 8px 16px)"
                  : v.state === "running"
                  ? "linear-gradient(135deg, #2e3a55, #20283a)"
                  : "linear-gradient(135deg, #20283a 0%, #2e3a55 100%)",
                border: "1.5px solid var(--ink)",
              }}>
                {v.state === "done" && (
                  <>
                    <svg viewBox="0 0 200 110" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
                      {/* unique-ish doodle per video */}
                      {i % 4 === 0 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                        {Array.from({ length: 8 }).map((_, k) => <rect key={k} x={20 + k * 20} y={45} width={16} height={28}/>)}
                        <rect x="60" y="45" width="16" height="28" fill="#f7d36b"/>
                        <rect x="120" y="45" width="16" height="28" fill="#f7d36b"/>
                      </g>}
                      {i % 4 === 1 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                        <path d="M10 90 Q 60 30, 110 70 T 190 30"/>
                        <circle cx="60" cy="55" r="3" fill="#f7d36b"/>
                        <circle cx="110" cy="70" r="3" fill="#f7d36b"/>
                        <circle cx="150" cy="48" r="3" fill="#f7d36b"/>
                      </g>}
                      {i % 4 === 2 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                        <circle cx="40" cy="55" r="14"/><circle cx="100" cy="55" r="14"/><circle cx="160" cy="55" r="14"/>
                        <path d="M54 55 L86 55 M114 55 L146 55"/>
                      </g>}
                      {i % 4 === 3 && <g stroke="#f3ecd8" strokeWidth="1.5" fill="none">
                        <rect x="30" y="30" width="50" height="50"/>
                        <rect x="120" y="30" width="50" height="50"/>
                        <path d="M80 55 L120 55"/>
                        <path d="M55 80 L55 95 M145 80 L145 95"/>
                      </g>}
                    </svg>
                    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
                      <div style={{ width: 36, height: 36, borderRadius: 999, background: "rgba(243,236,216,0.92)", display: "grid", placeItems: "center" }}>
                        <InkIcon kind="play" size={16}/>
                      </div>
                    </div>
                  </>
                )}
                {v.state === "failed" && (
                  <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontFamily: "var(--serif)", fontSize: 32, color: "var(--red)" }}>!</div>
                )}
                {v.state === "running" && (
                  <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
                    <div className="pill hl" style={{ fontSize: 10 }}>▶ rendering 3/6</div>
                  </div>
                )}
                <div style={{ position: "absolute", bottom: 4, right: 6, fontFamily: "var(--mono)", fontSize: 9.5, color: "rgba(243,236,216,0.9)", background: "rgba(0,0,0,0.4)", padding: "1px 4px", borderRadius: 2 }}>{v.dur}</div>
              </div>

              {/* meta */}
              <div style={{ fontFamily: "var(--serif)", fontSize: 16, fontWeight: 700, lineHeight: 1.15, marginTop: 8, height: 38, overflow: "hidden" }}>{v.title}</div>
              <div className="row" style={{ gap: 4, marginTop: 6, flexWrap: "wrap" }}>
                <div className="pill" style={{ fontSize: 9 }}>{v.r}</div>
                <div className="pill" style={{ fontSize: 9 }}>{v.scenes} sc</div>
                {v.state === "failed" && <div className="pill red" style={{ fontSize: 9 }}>failed</div>}
                {v.state === "running" && <div className="pill" style={{ fontSize: 9, background: "var(--hl)" }}>running</div>}
              </div>
              <div className="row" style={{ justifyContent: "space-between", marginTop: 6, fontFamily: "var(--mono)", fontSize: 10, color: "var(--ink-soft)" }}>
                <span>{v.when}</span>
              </div>
            </div>
          );
        })}
      </div>

      <ResponsiveNote style={{ left: 70, bottom: 14 }}>4-col → 3 → 2 → 1</ResponsiveNote>
      <Annot style={{ top: 192, right: 38, width: 110 }} arrow="left">color-coded<br/>border for fail/run</Annot>
    </AppChrome>
  );
}

