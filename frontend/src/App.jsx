import { useState, useRef } from 'react';
import './App.css';

function App() {
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('IDLE'); // IDLE, LOADING, STREAMING, COMPLETED, ERROR
  const [clauses, setClauses] = useState([]);
  const [summary, setSummary] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  // Handle Pasted / Inputted text change
  const handleTextChange = (e) => {
    setText(e.target.value);
  };

  // Handle Drag & Drop
  const [isDragActive, setIsDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const processSelectedFile = (selectedFile) => {
    if (!selectedFile) return;

    const extension = selectedFile.name.split('.').pop().toLowerCase();
    
    if (extension === 'txt') {
      // Read plain text locally using FileReader
      const reader = new FileReader();
      reader.onload = (e) => {
        setText(e.target.result);
        setFile(null); // Clear file since we loaded its text
      };
      reader.readAsText(selectedFile);
    } else if (extension === 'pdf') {
      // Set PDF for backend upload
      setFile(selectedFile);
      setText(''); // Clear textarea to avoid mixing or confusion
    } else {
      alert("Unsupported file type. Please upload a PDF or plain text (.txt) file.");
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
    }
  };

  // Clear inputs and reset state
  const handleReset = () => {
    setText('');
    setFile(null);
    setStatus('IDLE');
    setClauses([]);
    setSummary(null);
    setErrorMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // SSE streaming client logic
  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!text.trim() && !file) return;

    setStatus('LOADING');
    setClauses([]);
    setSummary(null);
    setErrorMessage('');

    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const url = `${apiBase}/api/analyze`;

    const formData = new FormData();
    if (file) {
      formData.append('file', file);
    } else {
      formData.append('text', text);
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errText = `HTTP Error ${response.status}`;
        try {
          const errData = await response.json();
          errText = errData.detail || errText;
        } catch {
          // not JSON
        }
        throw new Error(errText);
      }

      if (!response.body) {
        throw new Error("No response body received from analysis server.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE chunks are delimited by double newlines (\n\n)
        let boundary = buffer.indexOf('\n\n');
        while (boundary !== -1) {
          const chunk = buffer.slice(0, boundary).trim();
          buffer = buffer.slice(boundary + 2);

          if (chunk.startsWith('data:')) {
            const dataStr = chunk.replace(/^data:\s*/, '').trim();

            if (dataStr) {
              try {
                const parsed = JSON.parse(dataStr);
                
                if (parsed.type === 'clause') {
                  setStatus('STREAMING');
                  setClauses((prev) => {
                    const existsIdx = prev.findIndex((c) => c.index === parsed.index);
                    if (existsIdx !== -1) {
                      const updated = [...prev];
                      updated[existsIdx] = parsed;
                      return updated;
                    }
                    return [...prev, parsed].sort((a, b) => a.index - b.index);
                  });
                } else if (parsed.type === 'summary') {
                  setSummary(parsed);
                  setStatus('COMPLETED');
                } else if (parsed.type === 'error') {
                  setErrorMessage(parsed.message || "An error occurred during analysis.");
                  setStatus('ERROR');
                  reader.cancel();
                  break;
                }
              } catch (parseError) {
                console.error("SSE parse error: ", parseError, " on raw chunk: ", dataStr);
                
                if (dataStr !== '===SUMMARY===' && !dataStr.includes('"type":"summary"')) {
                  setStatus('STREAMING');
                  setClauses((prev) => {
                    const fallbackIndex = prev.length;
                    const fallback = {
                      index: fallbackIndex,
                      clause_text: dataStr.length > 300 ? dataStr.slice(0, 300) + '...' : dataStr,
                      explanation: "This clause response was malformed and could not be simplified automatically.",
                      risk_level: "MEDIUM",
                      reasoning: "The analysis system returned a raw or unparseable format for this section.",
                      isFallback: true,
                      rawOutput: dataStr
                    };
                    return [...prev, fallback];
                  });
                }
              }
            }
          }
          boundary = buffer.indexOf('\n\n');
        }
      }

      setStatus((currentStatus) => {
        if (currentStatus === 'STREAMING') {
          return 'COMPLETED';
        }
        return currentStatus;
      });

    } catch (error) {
      console.error("Analysis streaming failed:", error);
      setErrorMessage(error.message || "Failed to communicate with the analysis server. Please check that the server is running and try again.");
      setStatus('ERROR');
    }
  };

  // Simulated Demo Mode for easy evaluation/testing
  const handleDemoAnalyze = () => {
    setStatus('LOADING');
    setClauses([]);
    setSummary(null);
    setErrorMessage('');

    const demoText = `1. The tenant shall pay rent of $1,200 on the first of each month.
2. The landlord may enter the premises with 24-hour notice for repairs or inspections.
3. The tenant agrees to indemnify and hold the landlord harmless from any and all liabilities, damages, or claims arising from the use of the premises, without limit.`;

    setText(demoText);
    setFile(null);

    const demoChunks = [
      {
        type: 'clause',
        index: 0,
        clause_text: "The tenant shall pay rent of $1,200 on the first of each month.",
        explanation: "You must pay $1,200 rent every month on the 1st.",
        risk_level: "LOW",
        reasoning: "Standard rent obligation with clear terms."
      },
      {
        type: 'clause',
        index: 1,
        clause_text: "The landlord may enter the premises with 24-hour notice for repairs or inspections.",
        explanation: "The landlord can enter your home with 24 hours warning for repairs.",
        risk_level: "MEDIUM",
        reasoning: "Limits tenant privacy slightly, but standard for inspections."
      },
      {
        type: 'clause',
        index: 2,
        clause_text: "The tenant agrees to indemnify and hold the landlord harmless from any and all liabilities, damages, or claims arising from the use of the premises, without limit.",
        explanation: "You agree to take full legal and financial responsibility for any issues or accidents on the property, even if they aren't your fault.",
        risk_level: "HIGH",
        reasoning: "Imposes unlimited, highly unbalanced liability on the tenant."
      },
      {
        type: 'summary',
        verdict: "This contract is mostly standard but contains a high-risk liability clause. The tenant is recommended to request a cap on indemnification before signing.",
        overall_risk: "HIGH"
      }
    ];

    let currentStep = 0;
    
    setTimeout(() => {
      setStatus('STREAMING');
      
      const interval = setInterval(() => {
        if (currentStep < demoChunks.length) {
          const chunk = demoChunks[currentStep];
          if (chunk.type === 'clause') {
            setClauses(prev => [...prev, chunk]);
          } else if (chunk.type === 'summary') {
            setSummary(chunk);
            setStatus('COMPLETED');
            clearInterval(interval);
          }
          currentStep++;
        }
      }, 1000);
    }, 1500);
  };

  // Derive Top 3 Concerns from high/medium risk clauses
  const getTopConcerns = () => {
    const criticalClauses = clauses.filter(c => c.risk_level === 'HIGH' || c.risk_level === 'MEDIUM');
    const sorted = [...criticalClauses].sort((a, b) => {
      if (a.risk_level === 'HIGH' && b.risk_level !== 'HIGH') return -1;
      if (a.risk_level !== 'HIGH' && b.risk_level === 'HIGH') return 1;
      return a.index - b.index;
    });
    return sorted.slice(0, 3);
  };

  const topConcerns = getTopConcerns();

  return (
    <div className="app-container">
      {/* Header section */}
      <header className="app-header">
        <div className="logo-section">
          <div className="pulse-dot"></div>
          <h1>ContractSimplifier</h1>
        </div>
        <p className="app-subtitle">
          De-risk your legal agreements instantly. Paste or upload clauses to receive plain-English explanations and smart risk ratings.
        </p>
      </header>

      {/* Main Workspace */}
      <main className="app-main">
        {status === 'IDLE' && (
          <section className="input-section glass-card">
            <form onSubmit={handleAnalyze} className="contract-form">
              <div className="input-group">
                <label htmlFor="contract-textarea">Paste Contract Clauses</label>
                <textarea
                  id="contract-textarea"
                  placeholder="e.g., 1. The tenant shall pay rent of $1,200 on the first of each month.
2. Late payments incur a penalty of 10% per day..."
                  value={text}
                  onChange={handleTextChange}
                  disabled={!!file}
                />
              </div>

              <div className="divider-or">
                <span>OR</span>
              </div>

              <div 
                className={`file-upload-zone ${isDragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.txt"
                  style={{ display: 'none' }}
                />
                <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                </svg>
                {file ? (
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                    <button 
                      type="button" 
                      className="remove-file" 
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <div className="upload-instructions">
                    <p className="main-instruction">Drag & drop your contract file here</p>
                    <p className="sub-instruction">Supports PDF (analysed by AI) or TXT (read instantly)</p>
                    <span className="browse-btn">Browse files</span>
                  </div>
                )}
              </div>

              <div className="form-actions">
                <button 
                  type="button"
                  className="btn-secondary"
                  onClick={handleDemoAnalyze}
                  style={{ marginRight: '12px' }}
                >
                  Try Demo Mode
                </button>
                <button 
                  type="submit" 
                  className="btn-primary"
                  disabled={!text.trim() && !file}
                >
                  Analyze Contract
                </button>
              </div>
            </form>
          </section>
        )}

        {/* Loading and Analysis State */}
        {status !== 'IDLE' && (
          <section className="analysis-results">
            <div className="results-header glass-card">
              <div className="status-indicator">
                {status === 'LOADING' && (
                  <>
                    <div className="spinner"></div>
                    <span>Initializing AI analysis pipeline...</span>
                  </>
                )}
                {status === 'STREAMING' && (
                  <>
                    <div className="pulse-indicator"></div>
                    <span>Streaming live analysis...</span>
                  </>
                )}
                {status === 'COMPLETED' && (
                  <span className="status-success">✓ Analysis complete</span>
                )}
                {status === 'ERROR' && (
                  <span className="status-error">✕ Analysis failed</span>
                )}
              </div>

              <div className="header-actions">
                <button onClick={handleReset} className="btn-secondary">
                  ← New Analysis
                </button>
              </div>
            </div>

            {/* Error Banner */}
            {status === 'ERROR' && (
              <div className="error-banner glass-card">
                <h3>Analysis Interrupted</h3>
                <p>{errorMessage}</p>
                <button onClick={handleAnalyze} className="btn-retry">Try Again</button>
              </div>
            )}

            {/* Initial Loading Skeleton */}
            {status === 'LOADING' && (
              <div className="skeleton-container">
                <div className="skeleton-card glass-card">
                  <div className="skeleton-badge"></div>
                  <div className="skeleton-title"></div>
                  <div className="skeleton-text"></div>
                  <div className="skeleton-text short"></div>
                </div>
                <div className="skeleton-card glass-card">
                  <div className="skeleton-badge"></div>
                  <div className="skeleton-title"></div>
                  <div className="skeleton-text"></div>
                </div>
              </div>
            )}

            {/* Clause Grid */}
            {clauses.length > 0 && (
              <div className="clauses-grid">
                {clauses.map((clause) => (
                  <div 
                    key={clause.index} 
                    className={`clause-card glass-card risk-${clause.risk_level.toLowerCase()} ${clause.isFallback ? 'fallback-card' : ''}`}
                  >
                    <div className="clause-card-header">
                      <span className="clause-index">Clause #{clause.index + 1}</span>
                      <span className={`risk-badge risk-${clause.risk_level.toLowerCase()}`}>
                        {clause.risk_level} RISK
                      </span>
                    </div>

                    <div className="clause-body">
                      <div className="clause-text-box">
                        <h4>Original Clause</h4>
                        <p className="original-text">
                          {clause.clause_text}
                        </p>
                      </div>

                      <div className="clause-explanation-box">
                        <h4>Simplified Explanation</h4>
                        <p className="explanation-text">
                          {clause.explanation}
                        </p>
                      </div>

                      {clause.reasoning && (
                        <div className="clause-reasoning-box">
                          <strong>Reasoning:</strong> {clause.reasoning}
                        </div>
                      )}

                      {clause.isFallback && (
                        <div className="fallback-details">
                          <strong>Raw Server Output:</strong>
                          <pre className="raw-output"><code>{clause.rawOutput}</code></pre>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Overall Verdict & Summary */}
            {summary && (
              <div className="summary-section glass-card">
                <div className="summary-header">
                  <h2>Contract Verdict</h2>
                  <span className={`risk-badge risk-${summary.overall_risk.toLowerCase()} large`}>
                    OVERALL RISK: {summary.overall_risk}
                  </span>
                </div>
                
                <div className="summary-body">
                  <div className="verdict-box">
                    <h3>Summary Assessment</h3>
                    <p className="verdict-text">{summary.verdict}</p>
                  </div>

                  <div className="concerns-box">
                    <h3>Top Concerns</h3>
                    {topConcerns.length > 0 ? (
                      <ul className="concerns-list">
                        {topConcerns.map((concern) => (
                          <li key={concern.index} className={`concern-item border-${concern.risk_level.toLowerCase()}`}>
                            <div className="concern-title">
                              <span className="concern-index-label">Clause #{concern.index + 1}</span>
                              <span className={`risk-text-${concern.risk_level.toLowerCase()}`}>
                                {concern.risk_level} Risk
                              </span>
                            </div>
                            <p className="concern-explanation">{concern.explanation}</p>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="no-concerns-text">
                        No significant high or medium risk concerns detected. The agreement terms appear standard.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p className="legal-disclaimer">
          <strong>Disclaimer:</strong> This tool provides general information only and is not a substitute for professional legal advice.
        </p>
        <p className="copyright">ContractSimplifier © 2026. Made with ❤️ for Pair Programming.</p>
      </footer>
    </div>
  );
}

export default App;
