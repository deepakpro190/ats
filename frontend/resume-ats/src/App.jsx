// App.jsx
import React, { useState } from "react";
import UploadForm from "./UploadForm.jsx";

function App() {
  // scores & derived state
 

  // LLM outputs / UI content
  const [overview, setOverview] = useState("");
  const [detailedChanges, setDetailedChanges] = useState([]);
  const [enhancedPreview, setEnhancedPreview] = useState("");
  const [enhancedPdfUrl, setEnhancedPdfUrl] = useState(null);

  // UI state
  const [loading, setLoading] = useState(false);

  return (
    <div style={{ maxWidth: 1000, margin: "24px auto", padding: 20 }}>
      <h1>Intelligent Resume Enhancement</h1>

      <UploadForm
       
        setOverview={setOverview}
        setDetailedChanges={setDetailedChanges}
        setEnhancedPreview={setEnhancedPreview}
        setEnhancedPdfUrl={setEnhancedPdfUrl}
        setLoading={setLoading}
      />

      {loading && <div style={{ marginTop: 12 }}>Processing…</div>}

      

      <div style={{ marginTop: 18 }}>
        <h3>Overview</h3>
        <div style={{ background: "#fafafa", padding: 12, borderRadius: 6, whiteSpace: "pre-wrap" }}>
          {overview || "No overview yet. Click Analyze."}
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <h3>Detailed Changes Suggested</h3>
        {detailedChanges.length === 0 ? (
          <div style={{ color: "#777" }}>No suggestions yet. Click Analyze.</div>
        ) : (
          <ol>
            {detailedChanges.map((c, idx) => (
              <li key={idx} style={{ marginBottom: 8 }}>
                <div style={{ fontWeight: "600" }}>{c.change}</div>
                {c.reason && <div style={{ color: "#444", marginTop: 4 }}>{c.reason}</div>}
                {c.ats_impact && <div style={{ marginTop: 4, fontSize: 13, color: "#0066cc" }}>ATS impact: {c.ats_impact}</div>}
              </li>
            ))}
          </ol>
        )}
      </div>

      <div style={{ marginTop: 18 }}>
        <h3>Enhanced Resume Preview</h3>
        <pre style={{ whiteSpace: "pre-wrap", background: "#fff", padding: 12, borderRadius: 6, border: "1px solid #eee" }}>
          {enhancedPreview || "Preview will appear here after Analyze."}
        </pre>
      </div>

      {enhancedPdfUrl && (
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => {
              const a = document.createElement("a");
              a.href = enhancedPdfUrl;
              a.download = "enhanced_resume.pdf";
              a.click();
            }}
          >
            📄 Download Enhanced Resume (PDF)
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
