export default function Home() {
  return (
    <>
      <section id="welcome-screen" className="welcome-screen" aria-label="Welcome">
        <div className="welcome-card">
          <p className="eyebrow">Welcome</p>
          <h1>FactLens</h1>
          <p>Analyze claims, PDFs, and images with evidence-backed verdicts in a focused verification workspace.</p>
          <button id="enter-app-btn" type="button">Start Analysis</button>
        </div>
      </section>

      <div className="bg-grid" aria-hidden="true"></div>
      <div className="bg-orb orb-a"></div>
      <div className="bg-orb orb-b"></div>
      <div className="bg-orb orb-c"></div>

      <main id="app-main" className="page" hidden>
        <section className="hero">
          <p className="eyebrow">Verification Console</p>
          <h1>FactLens</h1>
          <p className="subtitle">Run claim checks, PDF extraction, and image evidence analysis in one high-signal workspace.</p>
          <div className="hero-chips" aria-label="Key capabilities">
            <span>Multilingual analysis</span>
            <span>Document evidence tracing</span>
            <span>Live verdict confidence</span>
          </div>
        </section>

        <section className="workspace">
          <div className="left-stack">
            <section className="panel controls">
              <div className="controls-head">
                <h3>Start A Verification Run</h3>
                <p>Choose an input mode, submit content, then review sourced evidence and final verdict details.</p>
              </div>

              <div className="tabs" role="tablist" aria-label="Analysis type">
                <button className="tab active" data-mode="claim" role="tab">Claim</button>
                <button className="tab" data-mode="pdf" role="tab">PDF</button>
                <button className="tab" data-mode="image" role="tab">Image</button>
                <span className="tab-indicator" aria-hidden="true"></span>
              </div>

              <form id="analyzer-form">
                <div className="field mode-block active" data-mode="claim">
                  <label htmlFor="claim-text">Claim text</label>
                  <textarea id="claim-text" rows={4} placeholder="Example: India's inflation was below 4% in 2024."></textarea>
                </div>

                <div className="field mode-block file mode-block-inline" data-mode="pdf">
                  <label htmlFor="pdf-file">Upload PDF</label>
                  <input id="pdf-file" type="file" accept=".pdf" />
                  <label htmlFor="pdf-page-range">Pages to check</label>
                  <input
                    id="pdf-page-range"
                    className="page-range-input"
                    type="text"
                    inputMode="numeric"
                    placeholder="1 or 1-2"
                    aria-label="PDF pages to check"
                  />
                  <p className="field-note">Check up to the configured PDF max pages. Large PDFs may be capped and warned automatically.</p>
                  <p id="pdf-page-warning" className="field-warning" hidden></p>
                </div>

                <div className="field mode-block file mode-block-inline" data-mode="image">
                  <label htmlFor="image-file">Upload image</label>
                  <input id="image-file" type="file" accept=".png,.jpg,.jpeg" />
                </div>

                <p id="mode-tip" className="mode-hint">
                  Tip: include a concrete subject, timeframe, and measurable fact for better evidence retrieval.
                </p>

                <div className="actions">
                  <button id="run-btn" type="submit">Run Analysis</button>
                  <button id="cancel-btn" type="button" className="danger" hidden>Cancel</button>
                  <span id="status" className="status" aria-live="polite"></span>
                </div>

                <div id="claim-advisory" className="claim-advisory" hidden aria-live="polite"></div>
              </form>
            </section>

            <section id="inline-source-preview" className="panel preview-strip" hidden>
              <h3>Strong Source Preview</h3>
              <div id="inline-source-preview-body"></div>
            </section>
          </div>

          <aside className="panel process-panel" id="process-panel" hidden>
            <h3>Fact-Check Progress</h3>
            <p id="process-preview" className="meta">Submit a claim, PDF, or image to start.</p>
            <ul id="process-steps" className="steps"></ul>
          </aside>
        </section>

        <section id="report-tools" className="report-tools" hidden>
          <label htmlFor="report-lang">Report language</label>
          <select id="report-lang" defaultValue="en">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="ta">Tamil</option>
            <option value="te">Telugu</option>
            <option value="bn">Bengali</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
            <option value="de">German</option>
            <option value="ar">Arabic</option>
          </select>
          <button id="translate-btn" type="button">Translate Report</button>
          <button id="reset-translate-btn" type="button" hidden>Original</button>
          <span id="translate-status" className="status" aria-live="polite"></span>
        </section>

        <section id="results" className="results"></section>
      </main>
    </>
  );
}
