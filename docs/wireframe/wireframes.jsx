// Wireframe canvas — assembles all flow artboards into DesignCanvas sections.
// Each artboard is a fixed-size desktop frame (W × H). Variants A and B sit
// side-by-side; user can drag-reorder, delete, or focus any one.

function WireframeApp() {
  const [tweaks, setTweak] = useTweaks(/*EDITMODE-BEGIN*/{
    "showAnnotations": true,
    "showResponsiveNotes": true,
    "showStickies": true,
    "paperTone": "cream"
  }/*EDITMODE-END*/);

  // Toggle annotations on/off via CSS rather than re-rendering trees
  React.useEffect(() => {
    document.documentElement.dataset.annotations = tweaks.showAnnotations ? "on" : "off";
    document.documentElement.dataset.responsive  = tweaks.showResponsiveNotes ? "on" : "off";
    document.documentElement.dataset.stickies    = tweaks.showStickies ? "on" : "off";
    document.documentElement.dataset.paper       = tweaks.paperTone;
  }, [tweaks]);

  return (
    <>
      <DesignCanvas>
        <DCSection id="prompt" title="1 · Prompt entry" subtitle="Single-textarea, ChatGPT-style">
          <DCArtboard id="prompt-a" label="Hero textarea" width={W} height={H}><PromptA/></DCArtboard>
        </DCSection>

        <DCSection id="rendering" title="2 · Rendering progress" subtitle="SSE stream · linear stepper · per-scene grid">
          <DCArtboard id="render-a" label="Storyboard fill-in" width={W} height={H}><RenderA/></DCArtboard>
        </DCSection>

        <DCSection id="done" title="3 · Done state" subtitle="Job complete · video + metadata">
          <DCArtboard id="done-a" label="Hero player" width={W} height={H}><DoneA/></DCArtboard>
        </DCSection>

        <DCSection id="failure" title="4 · Failure state" subtitle="Manual retry · partial-result preservation">
          <DCArtboard id="fail-a" label="Diagnose & retry" width={W} height={H}><FailA/></DCArtboard>
        </DCSection>

        <DCSection id="library" title="5 · Library" subtitle="Past renders · grid of cards">
          <DCArtboard id="library-a" label="Grid of cards" width={W} height={H}><LibraryA/></DCArtboard>
        </DCSection>
      </DesignCanvas>

      <TweaksPanel title="Tweaks · notebook">
        <TweakSection label="Wireframe overlays">
          <TweakToggle label="Ink annotations"  value={tweaks.showAnnotations}      onChange={(v)=>setTweak("showAnnotations", v)}/>
          <TweakToggle label="Responsive notes" value={tweaks.showResponsiveNotes} onChange={(v)=>setTweak("showResponsiveNotes", v)}/>
          <TweakToggle label="Sticky notes"     value={tweaks.showStickies}         onChange={(v)=>setTweak("showStickies", v)}/>
        </TweakSection>
        <TweakSection label="Paper">
          <TweakRadio
            label="Tone"
            value={tweaks.paperTone}
            options={["cream", "warm", "cool"]}
            onChange={(v)=>setTweak("paperTone", v)}
          />
        </TweakSection>
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<WireframeApp/>);
