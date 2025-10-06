// UploadForm.jsx
import React, { useState } from "react";

function UploadForm({
  setOverview,
  setDetailedChanges,
  setEnhancedPreview,
  setEnhancedPdfUrl,
  setLoading,
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [keywords, setKeywords] = useState("");

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!selectedFile) return alert("Upload a resume file first.");
    setLoading(true);

    try {
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("job_description", jobDescription);
      form.append(
        "keywords",
        JSON.stringify(
          keywords.split(",").map((k) => k.trim()).filter(Boolean)
        )
      );

      const resp = await fetch("http://127.0.0.1:8000/analyze", {
        method: "POST",
        body: form,
      });
      const data = await resp.json();

      setOverview(data.overview || "");
      setDetailedChanges(data.detailed_changes || []);
      setEnhancedPreview(data.enhanced_text_preview || "");
    } catch (err) {
      alert("Analyze failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEnhance = async () => {
    if (!selectedFile) return alert("Upload a resume file first.");
    setLoading(true);

    try {
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("job_description", jobDescription);
      form.append(
        "keywords",
        JSON.stringify(
          keywords.split(",").map((k) => k.trim()).filter(Boolean)
        )
      );

      const resp = await fetch("http://127.0.0.1:8000/enhance", {
        method: "POST",
        body: form,
      });
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      setEnhancedPdfUrl(url);
    } catch (err) {
      alert("Enhance failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={handleAnalyze}
      style={{ display: "flex", flexDirection: "column", gap: 8 }}
    >
      <input
        type="file"
        accept=".pdf,.docx,.png,.jpg,.jpeg"
        onChange={(e) => setSelectedFile(e.target.files[0])}
      />
      <input
        type="text"
        placeholder="Job description"
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
      />
      <input
        type="text"
        placeholder="Keywords (comma separated)"
        value={keywords}
        onChange={(e) => setKeywords(e.target.value)}
      />

      <div style={{ display: "flex", gap: 10 }}>
        <button type="submit">Analyze</button>
        <button type="button" onClick={handleEnhance}>
          Enhance & Download
        </button>
      </div>
    </form>
  );
}

export default UploadForm;
