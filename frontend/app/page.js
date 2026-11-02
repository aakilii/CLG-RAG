"use client";

import { useState, useEffect, useRef } from "react";
import katex from "katex";

const API_BASE = "http://localhost:8000";

export default function Home() {
  // Theme state
  const [theme, setTheme] = useState("light");

  // Workspaces & Notes state
  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState(null);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [newProjectInput, setNewProjectInput] = useState("");
  const [docFilter, setDocFilter] = useState("");
  const [showSyllabusTree, setShowSyllabusTree] = useState(true);

  // Scoped chat messages per project: { [projectId]: [...] }
  const [projectChats, setProjectChats] = useState({});
  const [inputValue, setInputValue] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [isGeneratingFlashcards, setIsGeneratingFlashcards] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Excerpt verification drawer state: { [messageId]: boolean }
  const [openExcerpts, setOpenExcerpts] = useState({});

  // Active recall flip states: { [cardKey]: boolean }
  const [flippedCards, setFlippedCards] = useState({});

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Initialize theme from localStorage or default
  useEffect(() => {
    const savedTheme = localStorage.getItem("rag_theme") || "light";
    setTheme(savedTheme);
    document.documentElement.setAttribute("data-theme", savedTheme);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    localStorage.setItem("rag_theme", nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
  };

  // Show temporary toast notification
  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Fetch all projects on mount
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
        setActiveProjectId((current) => {
          if (current && data.some((p) => p.id === current)) return current;
          return data.length > 0 ? data[0].id : null;
        });
      }
    } catch (err) {
      console.error("Error fetching projects:", err);
    }
  };

  // Active project data
  const currentProject = projects.find((p) => p.id === activeProjectId) || null;
  const currentDocs = currentProject?.documents || [];
  const readyDocs = currentDocs.filter((d) => d.status === "ready");
  const hasReadyDocs = readyDocs.length > 0;
  const readyDocIds = readyDocs.map((d) => d.id || d.note_id);

  // Filtered documents list for sidebar
  const filteredDocs = currentDocs.filter((doc) => {
    if (!docFilter.trim()) return true;
    const term = docFilter.toLowerCase();
    const matchName = doc.filename?.toLowerCase().includes(term);
    const matchTopics = doc.topics?.some((t) => t.toLowerCase().includes(term));
    return matchName || matchTopics;
  });

  // Collect unique topics across ready documents for starter chips
  const activeTopics = Array.from(
    new Set(readyDocs.flatMap((d) => d.topics || []))
  ).slice(0, 3);

  // Active chat thread for the current project
  const currentMessages = (currentProject && projectChats[currentProject.id]) || [];

  const updateCurrentProjectMessages = (updater) => {
    if (!currentProject) return;
    setProjectChats((prev) => {
      const currentList = prev[currentProject.id] || [];
      const updatedList = typeof updater === "function" ? updater(currentList) : updater;
      return { ...prev, [currentProject.id]: updatedList };
    });
  };

  // Auto scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentMessages, isAsking, isGeneratingQuiz, isGeneratingFlashcards]);

  // Polling for processing documents in active project
  useEffect(() => {
    const processingDocs = currentDocs.filter((d) => d.status === "processing");
    if (processingDocs.length === 0) return;

    const interval = setInterval(async () => {
      let anyChanged = false;
      await Promise.all(
        processingDocs.map(async (doc) => {
          try {
            const docId = doc.id || doc.note_id;
            const res = await fetch(`${API_BASE}/notes/${docId}/status`);
            if (res.ok) {
              const statusData = await res.json();
              if (statusData.status !== "processing") {
                anyChanged = true;
              }
            }
          } catch (e) {
            console.error("Polling error for doc:", doc.id, e);
          }
        })
      );
      if (anyChanged) {
        fetchProjects();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentDocs]);

  // Create a new Project
  const handleCreateProject = async (e) => {
    e.preventDefault();
    const name = newProjectInput.trim();
    if (!name) return;

    try {
      const res = await fetch(`${API_BASE}/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        const newProj = await res.json();
        setNewProjectInput("");
        setIsCreatingProject(false);
        await fetchProjects();
        setActiveProjectId(newProj.id);
        showToast(`Created project "${newProj.name}"`);
      }
    } catch (err) {
      console.error("Error creating project:", err);
    }
  };

  // Delete a Project (Permanent in DB!)
  const handleDeleteProject = async (e, projId, projName) => {
    e.stopPropagation();
    if (!confirm(`Delete project "${projName}"? (All knowledge remains preserved in memory)`)) return;

    try {
      const res = await fetch(`${API_BASE}/projects/${projId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await fetchProjects();
        showToast(`Deleted project "${projName}"`);
      }
    } catch (err) {
      console.error("Error deleting project:", err);
    }
  };

  // Upload handler supporting single or multiple files into active project
  const handleFileUpload = async (files) => {
    const fileList = Array.from(files).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf")
    );

    if (fileList.length === 0) {
      alert("Please upload valid PDF files.");
      return;
    }

    if (!currentProject) {
      alert("Please create or select a project first.");
      return;
    }

    setIsUploading(true);

    try {
      const uploadPromises = fileList.map(async (file) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("project_id", currentProject.id);

        const res = await fetch(`${API_BASE}/upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`Upload failed for ${file.name}`);
        return await res.json();
      });

      await Promise.all(uploadPromises);
      await fetchProjects();
      showToast(`${fileList.length} document(s) uploaded to ${currentProject.name}`);
    } catch (err) {
      console.error("Error uploading documents:", err);
      alert("Failed to upload document(s). Ensure backend is running.");
    } finally {
      setIsUploading(false);
    }
  };

  // Drag & drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  // Soft-remove document from active project (Permanent in DB!)
  const handleRemoveDocFromProject = async (e, noteId, filename) => {
    e.stopPropagation();
    if (!currentProject) return;

    try {
      const res = await fetch(`${API_BASE}/projects/${currentProject.id}/docs/${noteId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await fetchProjects();
        showToast(`Removed from ${currentProject.name}`);
      }
    } catch (err) {
      console.error("Error removing doc from project:", err);
    }
  };

  // Send Question across documents in the active project
  const executeQuery = async (queryText) => {
    if (!queryText.trim() || isAsking || !hasReadyDocs || !currentProject) return;

    const question = queryText.trim();
    setInputValue("");

    const userMsg = { id: Date.now(), sender: "user", text: question };
    updateCurrentProjectMessages((prev) => [...prev, userMsg]);
    setIsAsking(true);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: currentProject.id,
          note_ids: readyDocIds,
          query: question,
        }),
      });

      if (!res.ok) throw new Error("Failed to get answer");

      const data = await res.json();
      const assistantMsg = {
        id: Date.now() + 1,
        sender: "assistant",
        type: "answer",
        text: data.answer,
        source: data.source,
        citation: data.citation,
        similarity: data.similarity,
        excerpts: data.excerpts || [],
      };
      updateCurrentProjectMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Error asking question:", err);
      updateCurrentProjectMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: "assistant",
          type: "answer",
          text: "An error occurred while answering your question. Please ensure the backend server is running.",
          source: "notes",
          citation: "",
          excerpts: [],
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  const handleSendMessage = (e) => {
    e.preventDefault();
    executeQuery(inputValue);
  };

  // Generate Multi-Document Quiz
  const handleGenerateQuiz = async () => {
    if (!hasReadyDocs || isGeneratingQuiz || !currentProject) return;

    setIsGeneratingQuiz(true);
    try {
      const res = await fetch(`${API_BASE}/quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: currentProject.id,
          note_ids: readyDocIds,
          count: 3,
        }),
      });

      if (!res.ok) throw new Error("Failed to generate quiz");

      const data = await res.json();
      const quizMsg = {
        id: Date.now(),
        sender: "assistant",
        type: "quiz",
        quizItems: data.quiz,
        userAnswers: {},
      };
      updateCurrentProjectMessages((prev) => [...prev, quizMsg]);
    } catch (err) {
      console.error("Error generating quiz:", err);
      alert("Could not generate quiz. Ensure documents have finished indexing.");
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  // Generate Active Recall Flashcards
  const handleGenerateFlashcards = async () => {
    if (!hasReadyDocs || isGeneratingFlashcards || !currentProject) return;

    setIsGeneratingFlashcards(true);
    try {
      const res = await fetch(`${API_BASE}/flashcards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: currentProject.id,
          note_ids: readyDocIds,
          count: 4,
        }),
      });

      if (!res.ok) throw new Error("Failed to generate flashcards");

      const data = await res.json();
      const flashcardsMsg = {
        id: Date.now(),
        sender: "assistant",
        type: "flashcards",
        cards: data.flashcards,
        currentCardIdx: 0,
      };
      updateCurrentProjectMessages((prev) => [...prev, flashcardsMsg]);
    } catch (err) {
      console.error("Error generating flashcards:", err);
      alert("Could not generate flashcards. Ensure documents have finished indexing.");
    } finally {
      setIsGeneratingFlashcards(false);
    }
  };

  const handleSelectQuizOption = (messageId, questionIdx, optionIdx) => {
    updateCurrentProjectMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === messageId) {
          const userAnswers = { ...msg.userAnswers, [questionIdx]: optionIdx };
          return { ...msg, userAnswers };
        }
        return msg;
      })
    );
  };

  // Flashcard Navigation
  const handleNavFlashcard = (msgId, delta, total) => {
    updateCurrentProjectMessages((prev) =>
      prev.map((msg) => {
        if (msg.id === msgId) {
          const nextIdx = Math.max(0, Math.min(total - 1, (msg.currentCardIdx || 0) + delta));
          return { ...msg, currentCardIdx: nextIdx };
        }
        return msg;
      })
    );
  };

  const toggleFlipCard = (cardKey) => {
    setFlippedCards((prev) => ({ ...prev, [cardKey]: !prev[cardKey] }));
  };

  // Toggle Excerpt Verification Drawer
  const toggleExcerptDrawer = (msgId) => {
    setOpenExcerpts((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  // Export Study Guide to Markdown (.md)
  const handleExportStudyGuide = () => {
    if (!currentProject || currentMessages.length === 0) {
      showToast("No study notes in this workspace yet.");
      return;
    }

    let markdown = `# ${currentProject.name} — Study Guide\n`;
    markdown += `Generated on ${new Date().toLocaleDateString()} | Indexed Documents: ${readyDocs.map((d) => d.filename).join(", ")}\n\n---\n\n`;

    currentMessages.forEach((msg, idx) => {
      if (msg.sender === "user") {
        markdown += `### Question: ${msg.text}\n\n`;
      } else if (msg.type === "answer") {
        markdown += `${msg.text}\n\n`;
        if (msg.citation) {
          markdown += `> **Source**: ${msg.citation}\n\n`;
        }
        markdown += `---\n\n`;
      } else if (msg.type === "quiz") {
        markdown += `### Self-Assessment Quiz\n\n`;
        msg.quizItems.forEach((q, qIdx) => {
          markdown += `**Q${qIdx + 1}: ${q.question}**\n`;
          q.options.forEach((opt, optIdx) => {
            const isCorrect = optIdx === q.correct_index;
            markdown += `- [${isCorrect ? "x" : " "}] ${opt}\n`;
          });
          markdown += `*Explanation: ${q.explanation}*\n\n`;
        });
        markdown += `---\n\n`;
      } else if (msg.type === "flashcards") {
        markdown += `### Active Recall Flashcards\n\n`;
        msg.cards.forEach((c, cIdx) => {
          markdown += `**Card ${cIdx + 1}: ${c.key_term}**\n`;
          markdown += `- **Front**: ${c.front}\n`;
          markdown += `- **Back**: ${c.back}\n\n`;
        });
        markdown += `---\n\n`;
      }
    });

    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `study-guide-${currentProject.name.toLowerCase().replace(/\s+/g, "-")}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast("Exported study guide (.md)");
  };

  // Copy helper
  const handleCopyText = (text) => {
    navigator.clipboard.writeText(text);
    showToast("Copied to clipboard");
  };

  // Safe KaTeX renderer for LaTeX mathematical formulas
  const renderLatexFormula = (tex, displayMode = false) => {
    try {
      const html = katex.renderToString(tex, {
        displayMode,
        throwOnError: false,
      });
      return <span dangerouslySetInnerHTML={{ __html: html }} />;
    } catch (e) {
      return <span>{tex}</span>;
    }
  };

  // Parse inline elements (KaTeX math $...$, bold **...**, code `...`)
  const parseInlineElements = (str) => {
    if (!str) return null;

    // Pattern for math ($...$), bold (**...**), and inline code (`...`)
    const regex = /(\$\$[\s\S]*?\$\$|\$[^$\n]+?\$|\*\*.*?\*\*|`[^`]+?`)/g;
    const parts = str.split(regex);

    return parts.map((part, idx) => {
      if (!part) return null;

      // Block math $$ ... $$
      if (part.startsWith("$$") && part.endsWith("$$")) {
        const mathExpr = part.slice(2, -2).trim();
        return (
          <div key={idx} style={styles.blockMathWrapper}>
            {renderLatexFormula(mathExpr, true)}
          </div>
        );
      }

      // Inline math $ ... $
      if (part.startsWith("$") && part.endsWith("$") && part.length > 2) {
        const mathExpr = part.slice(1, -1).trim();
        return (
          <span key={idx} style={styles.inlineMath}>
            {renderLatexFormula(mathExpr, false)}
          </span>
        );
      }

      // Bold ** ... **
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={idx} style={styles.boldText}>
            {part.slice(2, -2)}
          </strong>
        );
      }

      // Inline code ` ... `
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code key={idx} style={styles.inlineCode}>
            {part.slice(1, -1)}
          </code>
        );
      }

      return part;
    });
  };

  // Render Markdown Table cleanly
  const renderMarkdownTable = (tableLines, key) => {
    const rows = tableLines.map((line) =>
      line
        .split("|")
        .map((cell) => cell.trim())
        .filter((cell, idx, arr) => idx > 0 && idx < arr.length - 1)
    );

    if (rows.length < 2) return null;

    const headers = rows[0];
    const dataRows = rows.slice(2); // Skip separator row (---|---|---)

    return (
      <div key={key} style={styles.tableWrapper}>
        <table style={styles.markdownTable}>
          <thead>
            <tr>
              {headers.map((h, idx) => (
                <th key={idx} style={styles.tableHeaderCell}>
                  {parseInlineElements(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, rIdx) => (
              <tr key={rIdx} style={styles.tableRow}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} style={styles.tableCell}>
                    {parseInlineElements(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Structured Content Formatter (Code Blocks, KaTeX Math, Markdown Tables, Lists)
  const renderFormattedAnswer = (text) => {
    if (!text) return null;

    // Split code blocks ```lang ... ```
    const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(text)) !== null) {
      const precedingText = text.substring(lastIndex, match.index);
      if (precedingText) {
        parts.push({ type: "text", content: precedingText });
      }
      parts.push({
        type: "code",
        language: match[1] || "code",
        code: match[2].trim(),
      });
      lastIndex = match.index + match[0].length;
    }

    const remainingText = text.substring(lastIndex);
    if (remainingText) {
      parts.push({ type: "text", content: remainingText });
    }

    if (parts.length === 0) {
      parts.push({ type: "text", content: text });
    }

    return (
      <div style={styles.formattedAnswerContainer}>
        {parts.map((part, pIdx) => {
          if (part.type === "code") {
            return (
              <div key={pIdx} style={styles.codeBlockWrapper}>
                <div style={styles.codeBlockHeader}>
                  <span style={styles.codeBlockLang}>{part.language}</span>
                  <button
                    onClick={() => handleCopyText(part.code)}
                    style={styles.copyCodeBtn}
                    title="Copy code"
                  >
                    Copy
                  </button>
                </div>
                <pre style={styles.codeBlockPre}>
                  <code>{part.code}</code>
                </pre>
              </div>
            );
          }

          // Parse text sections for Markdown tables, headings, block math, lists
          const rawLines = part.content.split("\n");
          const elements = [];
          let currentTableLines = [];
          let insideTable = false;

          rawLines.forEach((line, lIdx) => {
            const trimmed = line.trim();

            // Table detection
            if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
              insideTable = true;
              currentTableLines.push(trimmed);
              return;
            } else if (insideTable) {
              insideTable = false;
              elements.push(renderMarkdownTable(currentTableLines, `tbl-${lIdx}`));
              currentTableLines = [];
            }

            if (!trimmed) {
              elements.push(<div key={`sp-${lIdx}`} style={{ height: "6px" }} />);
              return;
            }

            // Headings
            if (trimmed.startsWith("### ")) {
              elements.push(
                <h4 key={`h3-${lIdx}`} style={styles.answerHeading3}>
                  {parseInlineElements(trimmed.replace(/^###\s+/, ""))}
                </h4>
              );
              return;
            }
            if (trimmed.startsWith("## ")) {
              elements.push(
                <h3 key={`h2-${lIdx}`} style={styles.answerHeading2}>
                  {parseInlineElements(trimmed.replace(/^##\s+/, ""))}
                </h3>
              );
              return;
            }
            if (trimmed.startsWith("# ")) {
              elements.push(
                <h2 key={`h1-${lIdx}`} style={styles.answerHeading1}>
                  {parseInlineElements(trimmed.replace(/^#\s+/, ""))}
                </h2>
              );
              return;
            }

            // Bullets
            if (trimmed.startsWith("- ") || trimmed.startsWith("• ") || trimmed.startsWith("* ")) {
              const bulletContent = trimmed.replace(/^[-•*]\s+/, "");
              elements.push(
                <div key={`b-${lIdx}`} style={styles.answerBulletRow}>
                  <span style={styles.bulletDash}>—</span>
                  <span style={styles.bulletText}>{parseInlineElements(bulletContent)}</span>
                </div>
              );
              return;
            }

            // Standard paragraph with KaTeX & bold
            elements.push(
              <p key={`p-${lIdx}`} style={styles.answerParagraph}>
                {parseInlineElements(line)}
              </p>
            );
          });

          // Flush any trailing table
          if (insideTable && currentTableLines.length >= 2) {
            elements.push(renderMarkdownTable(currentTableLines, `tbl-end`));
          }

          return (
            <div key={pIdx} style={styles.textSection}>
              {elements}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={styles.container}>
      {/* Toast Notification (Pure Text, No Green Dot) */}
      {toastMessage && (
        <div style={styles.toast}>
          {toastMessage}
        </div>
      )}

      {/* LEFT PANEL: VERTICAL WORKSPACES, SYLLABUS TREE & DOCUMENT REPOSITORY */}
      <aside style={styles.leftPanel}>
        {/* App Title & Top Header */}
        <div style={styles.sidebarHeader}>
          <div style={styles.headerRow}>
            <div>
              <h1 style={styles.sidebarTitle}>Class Notes</h1>
              <span style={styles.sidebarSubtitle}>Study Assistant</span>
            </div>
            {/* Theme Toggle Button (Pure Monochrome) */}
            <button
              onClick={toggleTheme}
              style={styles.themeToggleBtn}
              title={`Switch to ${theme === "light" ? "Dark" : "Light"} Mode`}
            >
              {theme === "light" ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Vertical Workspaces Section */}
        <div style={styles.projectSection}>
          <div style={styles.projectSectionHeader}>
            <span style={styles.sectionMiniLabel}>Workspaces</span>
            <button
              onClick={() => setIsCreatingProject(!isCreatingProject)}
              style={styles.addProjectBtn}
              title="Create New Project"
            >
              + New Project
            </button>
          </div>

          {/* New Project Inline Input */}
          {isCreatingProject && (
            <form onSubmit={handleCreateProject} style={styles.newProjectForm}>
              <input
                type="text"
                autoFocus
                placeholder="Workspace name..."
                value={newProjectInput}
                onChange={(e) => setNewProjectInput(e.target.value)}
                style={styles.newProjectInput}
              />
              <button type="submit" style={styles.saveProjectBtn}>Create</button>
              <button
                type="button"
                onClick={() => { setIsCreatingProject(false); setNewProjectInput(""); }}
                style={styles.cancelProjectBtn}
              >
                &times;
              </button>
            </form>
          )}

          {/* Vertical Project List */}
          <div style={styles.projectListVertical}>
            {projects.length === 0 ? (
              <div style={styles.emptyWorkspaces}>
                No workspaces created.<br />Click &ldquo;+ New Project&rdquo; above.
              </div>
            ) : (
              projects.map((proj) => {
                const isActive = proj.id === activeProjectId;
                return (
                  <div
                    key={proj.id}
                    onClick={() => setActiveProjectId(proj.id)}
                    style={{
                      ...styles.projectRowItem,
                      backgroundColor: isActive ? "var(--tab-active-bg)" : "var(--tab-inactive-bg)",
                      color: isActive ? "var(--tab-active-text)" : "var(--tab-inactive-text)",
                    }}
                  >
                    <div style={styles.projectRowInfo}>
                      <span style={styles.projectRowName}>{proj.name}</span>
                      <span
                        style={{
                          ...styles.projectDocCount,
                          color: isActive ? "var(--tab-active-text)" : "var(--text-tertiary)",
                        }}
                      >
                        {proj.doc_count || 0} {proj.doc_count === 1 ? "doc" : "docs"}
                      </span>
                    </div>

                    <button
                      onClick={(e) => handleDeleteProject(e, proj.id, proj.name)}
                      style={{
                        ...styles.projectDeleteBtn,
                        color: isActive ? "var(--tab-active-text)" : "var(--text-tertiary)",
                      }}
                      title="Delete project workspace"
                    >
                      &times;
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Drag & Drop Zone for Active Project */}
        {currentProject && (
          <div
            style={{
              ...styles.dropZone,
              borderColor: dragActive ? "var(--border-focus)" : "var(--border-hairline)",
              backgroundColor: dragActive ? "var(--accent-subtle)" : "var(--bg-card)",
            }}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              multiple
              style={{ display: "none" }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileUpload(e.target.files);
                }
              }}
            />
            <svg
              style={styles.uploadIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p style={styles.dropText}>
              {isUploading
                ? `Indexing into ${currentProject.name}...`
                : `Upload PDF(s) to ${currentProject.name}`}
            </p>
          </div>
        )}

        {/* Documents in Active Project + Search Filter */}
        {currentProject && (
          <div style={styles.filesSection}>
            <div style={styles.sectionHeader}>
              <span style={styles.sectionTitle}>{currentProject.name} Documents</span>
              <span style={styles.fileCount}>{currentDocs.length}</span>
            </div>

            {/* Quick Document Search Filter */}
            {currentDocs.length > 1 && (
              <input
                type="text"
                placeholder="Filter documents by topic or name..."
                value={docFilter}
                onChange={(e) => setDocFilter(e.target.value)}
                style={styles.docFilterInput}
              />
            )}

            <div style={styles.fileList}>
              {filteredDocs.length === 0 ? (
                <div style={styles.emptyFiles}>
                  {docFilter ? "No matching documents found." : "No documents in this workspace yet."}
                </div>
              ) : (
                filteredDocs.map((doc) => {
                  const docId = doc.id || doc.note_id;
                  const isReady = doc.status === "ready";
                  const isProcessing = doc.status === "processing";

                  return (
                    <div key={docId} style={styles.fileCard}>
                      <div style={styles.fileCardHeader}>
                        <span style={styles.fileName} title={doc.filename}>{doc.filename}</span>
                        <div style={styles.badgeActionsRow}>
                          <span style={styles.statusBadge}>
                            {isReady ? "Ready" : isProcessing ? "Indexing..." : doc.status}
                          </span>
                          <button
                            onClick={(e) => handleRemoveDocFromProject(e, docId, doc.filename)}
                            style={styles.deleteBtn}
                            title="Remove document from workspace"
                          >
                            &times;
                          </button>
                        </div>
                      </div>

                      {/* Detected Topics Tags (Pure Monochrome) */}
                      {doc.topics && doc.topics.length > 0 && (
                        <div style={styles.topicTags}>
                          {doc.topics.slice(0, 4).map((t, idx) => (
                            <span key={idx} style={styles.topicPill}>
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Interactive Syllabus Tree / Topic Map (Item 4) */}
        {readyDocs.length > 0 && (
          <div style={styles.syllabusSection}>
            <div
              onClick={() => setShowSyllabusTree(!showSyllabusTree)}
              style={styles.syllabusHeaderToggle}
              title="Click to toggle syllabus hierarchy"
            >
              <span style={styles.sectionMiniLabel}>Interactive Syllabus Map</span>
              <span style={styles.syllabusToggleArrow}>
                {showSyllabusTree ? "▲" : "▼"}
              </span>
            </div>

            {showSyllabusTree && (
              <div style={styles.syllabusTreeBody}>
                {readyDocs.map((doc) => {
                  const docId = doc.id || doc.note_id;
                  const topics = doc.topics || [];
                  const cleanDocName = doc.filename.replace(".pdf", "");

                  return (
                    <div key={docId} style={styles.syllabusDocNode}>
                      <div style={styles.syllabusDocHeader}>
                        <span style={styles.treeBranchPrefix}>├─</span>
                        <span style={styles.treeDocName} title={doc.filename}>{cleanDocName}</span>
                      </div>
                      <div style={styles.syllabusTopicsList}>
                        {topics.map((t, tIdx) => {
                          const isLast = tIdx === topics.length - 1;
                          return (
                            <div
                              key={tIdx}
                              onClick={() => executeQuery(`Explain the core mechanics and exam principles of ${t}`)}
                              style={styles.syllabusTopicNode}
                              title={`Click to explore ${t}`}
                            >
                              <span style={styles.treeSubBranchPrefix}>{isLast ? "└──" : "├──"}</span>
                              <span style={styles.treeTopicText}>{t}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Dual Study Buttons: Quiz & Flashcards */}
        {currentProject && (
          <div style={styles.sidebarFooter}>
            <div style={styles.studyButtonsGrid}>
              <button
                style={{
                  ...styles.studyButtonPrimary,
                  opacity: hasReadyDocs && !isGeneratingQuiz ? 1 : 0.35,
                  cursor: hasReadyDocs && !isGeneratingQuiz ? "pointer" : "not-allowed",
                }}
                disabled={!hasReadyDocs || isGeneratingQuiz}
                onClick={handleGenerateQuiz}
              >
                {isGeneratingQuiz ? "Generating..." : "Generate Quiz"}
              </button>

              <button
                style={{
                  ...styles.studyButtonSecondary,
                  opacity: hasReadyDocs && !isGeneratingFlashcards ? 1 : 0.35,
                  cursor: hasReadyDocs && !isGeneratingFlashcards ? "pointer" : "not-allowed",
                }}
                disabled={!hasReadyDocs || isGeneratingFlashcards}
                onClick={handleGenerateFlashcards}
              >
                {isGeneratingFlashcards ? "Generating..." : "Flashcards"}
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* RIGHT PANEL: CHAT, VERIFICATION DRAWER & ACTIVE WORKSPACE */}
      <main style={styles.rightPanel}>
        {/* Right Top Header Bar */}
        <div style={styles.chatTopBar}>
          <div style={styles.activeProjectIndicator}>
            <span style={styles.activeProjectLabel}>
              {currentProject ? currentProject.name : "Select a Workspace"}
            </span>
            {currentProject && (
              <span style={styles.docCountPill}>
                {readyDocs.length} {readyDocs.length === 1 ? "document" : "documents"} ready
              </span>
            )}
          </div>

          {/* Export Study Guide Button */}
          {currentProject && currentMessages.length > 0 && (
            <button
              onClick={handleExportStudyGuide}
              style={styles.exportGuideBtn}
              title="Export complete session as Markdown file"
            >
              Export Study Guide
            </button>
          )}
        </div>

        <div style={styles.chatScrollArea}>
          {!currentProject ? (
            <div style={styles.emptyChatContainer}>
              <h2 style={styles.emptyHeader}>No Workspace Selected</h2>
              <p style={styles.emptySubheader}>
                Create or select a workspace on the left panel to begin.
              </p>
            </div>
          ) : currentDocs.length === 0 ? (
            <div style={styles.emptyChatContainer}>
              <h2 style={styles.emptyHeader}>{currentProject.name} is Empty</h2>
              <p style={styles.emptySubheader}>
                Upload one or multiple PDF documents on the left panel to begin querying across your notes, taking quizzes, and studying flashcards.
              </p>
            </div>
          ) : currentMessages.length === 0 ? (
            <div style={styles.emptyChatContainer}>
              <h2 style={styles.emptyHeader}>
                {readyDocs.length} Document(s) Ready in {currentProject.name}
              </h2>
              <p style={styles.emptySubheader}>
                Ask any question grounded across your notes, or click &ldquo;Generate Quiz&rdquo; / &ldquo;Flashcards&rdquo; to test your understanding.
              </p>

              {/* High-Yield Starter & Comparative Chips (Items 3 & 4) */}
              <div style={styles.starterChipsContainer}>
                <span style={styles.starterChipsLabel}>Suggested Prompts & Comparative Synthesis:</span>
                <div style={styles.starterChipsList}>
                  {/* Item 3: Cross-Document Comparative Synthesis Chip */}
                  <button
                    onClick={() => executeQuery("Compare and contrast the primary paradigms, tradeoffs, and architectural differences across my uploaded course notes into a comparison matrix table.")}
                    style={styles.comparativeChip}
                  >
                    Compare &amp; Contrast Notes Matrix &rarr;
                  </button>

                  {activeTopics.map((topic, tIdx) => (
                    <button
                      key={tIdx}
                      onClick={() => executeQuery(`Explain the core mechanics and formula derivation for ${topic}`)}
                      style={styles.starterChip}
                    >
                      Explain {topic} &rarr;
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div style={styles.messageThread}>
              {currentMessages.map((msg) => (
                <div
                  key={msg.id}
                  style={
                    msg.sender === "user"
                      ? styles.userMessageRow
                      : styles.assistantMessageRow
                  }
                >
                  {msg.sender === "user" ? (
                    <div style={styles.userBubble}>{msg.text}</div>
                  ) : msg.type === "quiz" ? (
                    <div style={styles.quizCardContainer}>
                      <div style={styles.quizHeader}>
                        <span style={styles.quizTag}>Knowledge Check</span>
                        <span style={styles.quizCount}>
                          {msg.quizItems.length} Questions
                        </span>
                      </div>

                      {msg.quizItems.map((item, qIdx) => {
                        const selectedOption = msg.userAnswers[qIdx];
                        const hasAnswered = selectedOption !== undefined;

                        return (
                          <div key={qIdx} style={styles.questionBlock}>
                            <p style={styles.questionText}>
                              <span style={styles.questionNum}>Q{qIdx + 1}.</span> {item.question}
                            </p>

                            <div style={styles.optionsGrid}>
                              {item.options.map((opt, optIdx) => {
                                const isSelected = selectedOption === optIdx;
                                const isCorrect = optIdx === item.correct_index;

                                let optBg = "var(--bg-card)";
                                let optBorder = "var(--border-hairline)";
                                let optColor = "var(--text-primary)";

                                if (hasAnswered) {
                                  if (isCorrect) {
                                    optBg = "var(--quiz-correct-bg)";
                                    optBorder = "var(--quiz-correct-border)";
                                  } else if (isSelected && !isCorrect) {
                                    optBg = "var(--quiz-wrong-bg)";
                                    optBorder = "var(--quiz-wrong-border)";
                                  }
                                }

                                return (
                                  <button
                                    key={optIdx}
                                    style={{
                                      ...styles.optionCard,
                                      backgroundColor: optBg,
                                      borderColor: optBorder,
                                      color: optColor,
                                      cursor: hasAnswered ? "default" : "pointer",
                                    }}
                                    disabled={hasAnswered}
                                    onClick={() => handleSelectQuizOption(msg.id, qIdx, optIdx)}
                                  >
                                    <span style={styles.optionLetter}>
                                      {String.fromCharCode(65 + optIdx)}
                                    </span>
                                    <span style={styles.optionContent}>{opt}</span>
                                  </button>
                                );
                              })}
                            </div>

                            {hasAnswered && (
                              <div style={styles.explanationBox}>
                                <span style={styles.explanationLabel}>Explanation:</span>{" "}
                                {item.explanation}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : msg.type === "flashcards" ? (
                    /* Active Recall Flashcard Deck */
                    <div style={styles.flashcardsContainer}>
                      <div style={styles.quizHeader}>
                        <span style={styles.quizTag}>Active Recall Deck</span>
                        <span style={styles.quizCount}>
                          Card {(msg.currentCardIdx || 0) + 1} of {msg.cards.length}
                        </span>
                      </div>

                      {(() => {
                        const currentIdx = msg.currentCardIdx || 0;
                        const card = msg.cards[currentIdx];
                        const cardKey = `${msg.id}-${currentIdx}`;
                        const isFlipped = !!flippedCards[cardKey];

                        return (
                          <div style={styles.flashcardWrapper}>
                            <div
                              onClick={() => toggleFlipCard(cardKey)}
                              style={{
                                ...styles.flashcardBody,
                                border: isFlipped ? "1px solid var(--border-focus)" : "1px solid var(--border-hairline)",
                              }}
                            >
                              <div style={styles.flashcardTopBar}>
                                <span style={styles.flashcardKeyTerm}>{card.key_term}</span>
                                <span style={styles.flashcardSideHint}>
                                  {isFlipped ? "Answer (Click to flip)" : "Prompt (Click to flip)"}
                                </span>
                              </div>

                              <div style={styles.flashcardContentArea}>
                                {isFlipped ? (
                                  <div style={styles.flashcardAnswerText}>
                                    {card.back}
                                  </div>
                                ) : (
                                  <div style={styles.flashcardQuestionText}>
                                    {card.front}
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Flashcard Controls */}
                            <div style={styles.flashcardControls}>
                              <button
                                onClick={() => handleNavFlashcard(msg.id, -1, msg.cards.length)}
                                disabled={currentIdx === 0}
                                style={{
                                  ...styles.flashcardNavBtn,
                                  opacity: currentIdx === 0 ? 0.3 : 1,
                                }}
                              >
                                &larr; Previous
                              </button>

                              <button
                                onClick={() => toggleFlipCard(cardKey)}
                                style={styles.flashcardFlipBtn}
                              >
                                {isFlipped ? "Show Prompt" : "Reveal Answer"}
                              </button>

                              <button
                                onClick={() => handleNavFlashcard(msg.id, 1, msg.cards.length)}
                                disabled={currentIdx === msg.cards.length - 1}
                                style={{
                                  ...styles.flashcardNavBtn,
                                  opacity: currentIdx === msg.cards.length - 1 ? 0.3 : 1,
                                }}
                              >
                                Next &rarr;
                              </button>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  ) : (
                    <div style={styles.assistantMessageContent}>
                      {/* Discreet citation badge (NEVER shows 'from web') */}
                      {msg.source === "notes" && (
                        <div style={styles.assistantHeader}>
                          <span style={styles.sourceTagNotes}>
                            Study Material
                          </span>
                        </div>
                      )}

                      {/* Structured Formatted Answer (KaTeX Math + Tables + Code Blocks) */}
                      {renderFormattedAnswer(msg.text)}

                      {/* Source Citation Footnote */}
                      {msg.citation && (
                        <div style={styles.citationFootnote}>
                          <span style={styles.citationLabel}>Source:</span>{" "}
                          {msg.citation}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {isAsking && (
                <div style={styles.assistantMessageRow}>
                  <div style={styles.thinkingBubble}>
                    <span style={styles.thinkingDot}></span>
                    <span style={styles.thinkingDot}></span>
                    <span style={styles.thinkingDot}></span>
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>
          )}
        </div>

        {/* Fixed Bottom Input Bar */}
        <div style={styles.inputBarContainer}>
          <form onSubmit={handleSendMessage} style={styles.inputForm}>
            <input
              type="text"
              placeholder={
                hasReadyDocs
                  ? `Ask across ${currentProject?.name || "your notes"} (e.g. Compare concepts, formulas)...`
                  : "Upload notes to start asking..."
              }
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={!hasReadyDocs || isAsking}
              style={styles.chatInput}
            />

            <button
              type="submit"
              disabled={!inputValue.trim() || !hasReadyDocs || isAsking}
              style={{
                ...styles.sendButton,
                opacity: inputValue.trim() && hasReadyDocs && !isAsking ? 1 : 0.3,
                cursor: inputValue.trim() && hasReadyDocs && !isAsking ? "pointer" : "default",
              }}
            >
              <svg
                style={styles.sendIcon}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

// ----------------- Pure Black and White Swiss / Minimalist Styles -----------------

const styles = {
  container: {
    display: "flex",
    height: "100vh",
    width: "100vw",
    overflow: "hidden",
    backgroundColor: "var(--bg-main)",
  },

  toast: {
    position: "fixed",
    top: "18px",
    right: "22px",
    backgroundColor: "var(--bg-card)",
    border: "1px solid var(--border-hairline)",
    borderRadius: "6px",
    padding: "8px 14px",
    fontSize: "12.5px",
    fontWeight: "500",
    color: "var(--text-primary)",
    zIndex: 1000,
    animation: "fadeIn 0.15s ease",
  },

  /* Left Panel */
  leftPanel: {
    width: "330px",
    minWidth: "290px",
    maxWidth: "380px",
    height: "100%",
    backgroundColor: "var(--bg-sidebar)",
    borderRight: "1px solid var(--border-hairline)",
    display: "flex",
    flexDirection: "column",
    padding: "16px 14px",
    gap: "14px",
  },
  sidebarHeader: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sidebarTitle: {
    fontSize: "16px",
    fontWeight: "600",
    letterSpacing: "-0.02em",
    color: "var(--text-primary)",
  },
  sidebarSubtitle: {
    fontSize: "11.5px",
    color: "var(--text-tertiary)",
  },
  themeToggleBtn: {
    width: "28px",
    height: "28px",
    borderRadius: "4px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-card)",
    color: "var(--text-primary)",
    cursor: "pointer",
  },

  /* Workspaces Vertical Section */
  projectSection: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  projectSectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0 2px",
  },
  sectionMiniLabel: {
    fontSize: "10.5px",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "var(--text-tertiary)",
  },
  addProjectBtn: {
    fontSize: "11px",
    fontWeight: "500",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "2px 4px",
  },
  newProjectForm: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    marginTop: "2px",
  },
  newProjectInput: {
    flex: 1,
    padding: "6px 8px",
    borderRadius: "4px",
    fontSize: "12px",
    border: "1px solid var(--border-focus)",
    backgroundColor: "var(--bg-card)",
    color: "var(--text-primary)",
  },
  saveProjectBtn: {
    padding: "6px 8px",
    backgroundColor: "var(--accent)",
    color: "var(--tab-active-text)",
    fontSize: "11px",
    fontWeight: "600",
    borderRadius: "4px",
  },
  cancelProjectBtn: {
    fontSize: "15px",
    color: "var(--text-tertiary)",
    padding: "0 2px",
    cursor: "pointer",
  },
  projectListVertical: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    maxHeight: "140px",
    overflowY: "auto",
  },
  emptyWorkspaces: {
    fontSize: "11.5px",
    color: "var(--text-tertiary)",
    padding: "6px 2px",
    lineHeight: "1.4",
  },
  projectRowItem: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "7px 10px",
    borderRadius: "5px",
    border: "1px solid var(--border-hairline)",
    cursor: "pointer",
    transition: "background-color 0.12s ease",
  },
  projectRowInfo: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    overflow: "hidden",
    flex: 1,
  },
  projectRowName: {
    fontSize: "12px",
    fontWeight: "500",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  projectDocCount: {
    fontSize: "10.5px",
    flexShrink: 0,
  },
  projectDeleteBtn: {
    fontSize: "14px",
    lineHeight: "1",
    padding: "0 2px",
    cursor: "pointer",
    opacity: 0.6,
  },

  /* Drag & Drop */
  dropZone: {
    border: "1px dashed var(--border-hairline)",
    borderRadius: "6px",
    padding: "14px 10px",
    textAlign: "center",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "4px",
  },
  uploadIcon: {
    width: "16px",
    height: "16px",
    color: "var(--text-secondary)",
  },
  dropText: {
    fontSize: "11.5px",
    color: "var(--text-primary)",
    fontWeight: "500",
  },

  /* Document Library */
  filesSection: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minHeight: 0,
    gap: "6px",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0 2px",
  },
  sectionTitle: {
    fontSize: "10.5px",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "var(--text-tertiary)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  fileCount: {
    fontSize: "10.5px",
    color: "var(--text-tertiary)",
    flexShrink: 0,
  },
  docFilterInput: {
    width: "100%",
    padding: "4px 8px",
    borderRadius: "4px",
    fontSize: "11px",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-input)",
    color: "var(--text-primary)",
  },
  fileList: {
    flex: 1,
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "5px",
  },
  emptyFiles: {
    fontSize: "11.5px",
    color: "var(--text-tertiary)",
    textAlign: "center",
    marginTop: "16px",
  },
  fileCard: {
    border: "1px solid var(--border-hairline)",
    borderRadius: "5px",
    padding: "7px 9px",
    backgroundColor: "var(--bg-card)",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  fileCardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "6px",
  },
  fileName: {
    fontSize: "11.5px",
    fontWeight: "500",
    color: "var(--text-primary)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    flex: 1,
  },
  badgeActionsRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  deleteBtn: {
    fontSize: "13px",
    color: "var(--text-tertiary)",
    lineHeight: "1",
    padding: "0 2px",
    cursor: "pointer",
  },
  statusBadge: {
    fontSize: "10px",
    fontWeight: "400",
    color: "var(--text-tertiary)",
    flexShrink: 0,
  },
  topicTags: {
    display: "flex",
    flexWrap: "wrap",
    gap: "3px",
  },
  topicPill: {
    fontSize: "9.5px",
    padding: "1px 5px",
    borderRadius: "3px",
    backgroundColor: "var(--tag-ref-bg)",
    color: "var(--tag-ref-text)",
  },

  /* Interactive Syllabus Tree / Topic Map (Item 4) */
  syllabusSection: {
    border: "1px solid var(--border-hairline)",
    borderRadius: "6px",
    backgroundColor: "var(--bg-card)",
    padding: "8px 10px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    maxHeight: "180px",
  },
  syllabusHeaderToggle: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
  },
  syllabusToggleArrow: {
    fontSize: "9px",
    color: "var(--text-tertiary)",
  },
  syllabusTreeBody: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    overflowY: "auto",
    paddingTop: "2px",
  },
  syllabusDocNode: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
  },
  syllabusDocHeader: {
    display: "flex",
    alignItems: "center",
    gap: "5px",
    fontSize: "11px",
    fontWeight: "600",
    color: "var(--text-primary)",
  },
  treeBranchPrefix: {
    color: "var(--text-tertiary)",
    fontFamily: "monospace",
  },
  treeDocName: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  syllabusTopicsList: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    marginLeft: "12px",
  },
  syllabusTopicNode: {
    display: "flex",
    alignItems: "center",
    gap: "5px",
    fontSize: "10.5px",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "2px 0",
    transition: "color 0.1s ease",
  },
  treeSubBranchPrefix: {
    color: "var(--text-tertiary)",
    fontFamily: "monospace",
  },
  treeTopicText: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },

  /* Sidebar Footer Study Buttons */
  sidebarFooter: {
    paddingTop: "2px",
  },
  studyButtonsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "6px",
  },
  studyButtonPrimary: {
    padding: "8px 10px",
    borderRadius: "5px",
    backgroundColor: "var(--accent)",
    color: "var(--tab-active-text)",
    fontSize: "11.5px",
    fontWeight: "600",
    textAlign: "center",
  },
  studyButtonSecondary: {
    padding: "8px 10px",
    borderRadius: "5px",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-card)",
    color: "var(--text-primary)",
    fontSize: "11.5px",
    fontWeight: "500",
    textAlign: "center",
  },

  /* Right Panel */
  rightPanel: {
    flex: 1,
    height: "100%",
    display: "flex",
    flexDirection: "column",
    backgroundColor: "var(--bg-main)",
  },
  chatTopBar: {
    padding: "12px 40px",
    borderBottom: "1px solid var(--border-hairline)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  activeProjectIndicator: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  activeProjectLabel: {
    fontSize: "13px",
    fontWeight: "600",
    color: "var(--text-primary)",
  },
  docCountPill: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
    backgroundColor: "var(--tag-ref-bg)",
    padding: "2px 6px",
    borderRadius: "4px",
  },
  exportGuideBtn: {
    fontSize: "11.5px",
    fontWeight: "500",
    padding: "4px 10px",
    borderRadius: "4px",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-card)",
    color: "var(--text-primary)",
    cursor: "pointer",
  },
  chatScrollArea: {
    flex: 1,
    overflowY: "auto",
    padding: "26px 40px",
    display: "flex",
    flexDirection: "column",
  },
  emptyChatContainer: {
    margin: "auto",
    textAlign: "center",
    maxWidth: "500px",
  },
  emptyHeader: {
    fontSize: "18px",
    fontWeight: "600",
    letterSpacing: "-0.01em",
    color: "var(--text-primary)",
    marginBottom: "6px",
  },
  emptySubheader: {
    fontSize: "13px",
    color: "var(--text-secondary)",
    lineHeight: "1.55",
  },
  starterChipsContainer: {
    marginTop: "20px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "8px",
  },
  starterChipsLabel: {
    fontSize: "10.5px",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "var(--text-tertiary)",
    fontWeight: "600",
  },
  starterChipsList: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: "6px",
  },
  starterChip: {
    fontSize: "11px",
    padding: "5px 12px",
    borderRadius: "14px",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-card)",
    color: "var(--text-primary)",
    cursor: "pointer",
    transition: "border-color 0.12s ease",
  },
  comparativeChip: {
    fontSize: "11px",
    padding: "5px 12px",
    borderRadius: "14px",
    border: "1px solid var(--border-focus)",
    backgroundColor: "var(--accent)",
    color: "var(--tab-active-text)",
    fontWeight: "600",
    cursor: "pointer",
  },
  messageThread: {
    display: "flex",
    flexDirection: "column",
    gap: "24px",
    maxWidth: "780px",
    width: "100%",
    margin: "0 auto",
  },
  userMessageRow: {
    display: "flex",
    justifyContent: "flex-end",
  },
  userBubble: {
    maxWidth: "80%",
    backgroundColor: "var(--bg-sidebar)",
    border: "1px solid var(--border-hairline)",
    padding: "10px 16px",
    borderRadius: "12px",
    fontSize: "13.5px",
    color: "var(--text-primary)",
    lineHeight: "1.5",
  },
  assistantMessageRow: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
  },
  assistantMessageContent: {
    width: "100%",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  assistantHeader: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  },
  sourceTagNotes: {
    fontSize: "10.5px",
    fontWeight: "500",
    padding: "1px 6px",
    borderRadius: "3px",
    backgroundColor: "var(--tag-notes-bg)",
    color: "var(--tag-notes-text)",
  },
  citationFootnote: {
    fontSize: "11.5px",
    color: "var(--text-tertiary)",
    borderTop: "1px solid var(--border-hairline)",
    paddingTop: "6px",
    marginTop: "4px",
    lineHeight: "1.4",
  },
  citationLabel: {
    fontWeight: "500",
    color: "var(--text-secondary)",
  },

  /* Verification Drawer */
  verificationDrawerSection: {
    marginTop: "6px",
  },
  toggleExcerptsBtn: {
    fontSize: "11px",
    fontWeight: "500",
    color: "var(--text-secondary)",
    border: "1px solid var(--border-hairline)",
    borderRadius: "4px",
    padding: "3px 8px",
    backgroundColor: "var(--bg-sidebar)",
    cursor: "pointer",
  },
  excerptsList: {
    marginTop: "8px",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  excerptCard: {
    padding: "10px 12px",
    borderRadius: "6px",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-card)",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  excerptHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  excerptDocName: {
    fontSize: "11px",
    fontWeight: "600",
    color: "var(--text-primary)",
  },
  excerptScore: {
    fontSize: "10.5px",
    color: "var(--text-tertiary)",
  },
  excerptContent: {
    fontSize: "12px",
    color: "var(--text-secondary)",
    lineHeight: "1.45",
    fontStyle: "italic",
    margin: "2px 0 0",
  },

  /* Active Recall Flashcards */
  flashcardsContainer: {
    width: "100%",
    border: "1px solid var(--border-hairline)",
    borderRadius: "8px",
    padding: "16px",
    backgroundColor: "var(--bg-sidebar)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  flashcardWrapper: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  flashcardBody: {
    padding: "20px 24px",
    borderRadius: "8px",
    backgroundColor: "var(--bg-card)",
    minHeight: "140px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    cursor: "pointer",
    transition: "border-color 0.15s ease",
  },
  flashcardTopBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  flashcardKeyTerm: {
    fontSize: "11.5px",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "var(--text-primary)",
  },
  flashcardSideHint: {
    fontSize: "10.5px",
    color: "var(--text-tertiary)",
  },
  flashcardContentArea: {
    flex: 1,
    display: "flex",
    alignItems: "center",
  },
  flashcardQuestionText: {
    fontSize: "14px",
    fontWeight: "500",
    color: "var(--text-primary)",
    lineHeight: "1.5",
  },
  flashcardAnswerText: {
    fontSize: "13.5px",
    color: "var(--text-primary)",
    lineHeight: "1.6",
  },
  flashcardControls: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "8px",
  },
  flashcardNavBtn: {
    fontSize: "11.5px",
    fontWeight: "500",
    padding: "6px 12px",
    borderRadius: "4px",
    border: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-card)",
    color: "var(--text-primary)",
    cursor: "pointer",
  },
  flashcardFlipBtn: {
    fontSize: "11.5px",
    fontWeight: "600",
    padding: "6px 14px",
    borderRadius: "4px",
    backgroundColor: "var(--accent)",
    color: "var(--tab-active-text)",
    cursor: "pointer",
  },

  /* Formatted Markdown Content */
  formattedAnswerContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  textSection: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  answerParagraph: {
    fontSize: "13.5px",
    lineHeight: "1.6",
    color: "var(--text-primary)",
  },
  answerHeading1: {
    fontSize: "16px",
    fontWeight: "600",
    color: "var(--text-primary)",
    marginTop: "8px",
    marginBottom: "4px",
  },
  answerHeading2: {
    fontSize: "14.5px",
    fontWeight: "600",
    color: "var(--text-primary)",
    marginTop: "6px",
    marginBottom: "3px",
  },
  answerHeading3: {
    fontSize: "13.5px",
    fontWeight: "600",
    color: "var(--text-primary)",
    marginTop: "4px",
  },
  answerBulletRow: {
    display: "flex",
    alignItems: "baseline",
    gap: "8px",
    fontSize: "13.5px",
    lineHeight: "1.55",
    color: "var(--text-primary)",
  },
  bulletDash: {
    color: "var(--text-tertiary)",
  },
  bulletText: {
    flex: 1,
  },
  boldText: {
    fontWeight: "600",
  },
  inlineCode: {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: "12px",
    padding: "1px 4px",
    borderRadius: "3px",
    backgroundColor: "var(--bg-sidebar)",
    border: "1px solid var(--border-hairline)",
  },
  inlineMath: {
    padding: "0 2px",
  },
  blockMathWrapper: {
    margin: "8px 0",
    padding: "10px",
    borderRadius: "6px",
    backgroundColor: "var(--bg-card)",
    border: "1px solid var(--border-hairline)",
    overflowX: "auto",
    textAlign: "center",
  },

  /* Markdown Tables (Item 3: Comparison Tables) */
  tableWrapper: {
    margin: "10px 0",
    overflowX: "auto",
    borderRadius: "6px",
    border: "1px solid var(--border-hairline)",
  },
  markdownTable: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "12.5px",
    textAlign: "left",
  },
  tableHeaderCell: {
    padding: "8px 12px",
    backgroundColor: "var(--bg-sidebar)",
    borderBottom: "1px solid var(--border-hairline)",
    fontWeight: "600",
    color: "var(--text-primary)",
    whiteSpace: "nowrap",
  },
  tableRow: {
    borderBottom: "1px solid var(--border-hairline)",
  },
  tableCell: {
    padding: "8px 12px",
    color: "var(--text-primary)",
    lineHeight: "1.4",
  },

  /* Code Blocks */
  codeBlockWrapper: {
    border: "1px solid var(--border-hairline)",
    borderRadius: "6px",
    backgroundColor: "var(--bg-card)",
    overflow: "hidden",
    margin: "4px 0",
  },
  codeBlockHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "4px 10px",
    borderBottom: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-sidebar)",
  },
  codeBlockLang: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    fontWeight: "500",
  },
  copyCodeBtn: {
    fontSize: "11px",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "2px 4px",
  },
  codeBlockPre: {
    padding: "10px 12px",
    fontSize: "12.5px",
    lineHeight: "1.5",
    overflowX: "auto",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    color: "var(--text-primary)",
  },

  /* Inline Quiz Card */
  quizCardContainer: {
    width: "100%",
    border: "1px solid var(--border-hairline)",
    borderRadius: "8px",
    padding: "16px",
    backgroundColor: "var(--bg-sidebar)",
    display: "flex",
    flexDirection: "column",
    gap: "16px",
  },
  quizHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid var(--border-hairline)",
    paddingBottom: "8px",
  },
  quizTag: {
    fontSize: "11px",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    color: "var(--text-primary)",
  },
  quizCount: {
    fontSize: "11px",
    color: "var(--text-tertiary)",
  },
  questionBlock: {
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  questionText: {
    fontSize: "13.5px",
    fontWeight: "500",
    color: "var(--text-primary)",
    lineHeight: "1.5",
  },
  questionNum: {
    fontWeight: "600",
  },
  optionsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "6px",
  },
  optionCard: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid",
    textAlign: "left",
    fontSize: "12.5px",
  },
  optionLetter: {
    width: "20px",
    height: "20px",
    borderRadius: "50%",
    backgroundColor: "var(--bg-sidebar)",
    border: "1px solid var(--border-hairline)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "10.5px",
    fontWeight: "600",
    flexShrink: 0,
  },
  optionContent: {
    flex: 1,
    lineHeight: "1.4",
  },
  explanationBox: {
    fontSize: "12px",
    color: "var(--text-secondary)",
    backgroundColor: "var(--bg-card)",
    border: "1px solid var(--border-hairline)",
    borderRadius: "4px",
    padding: "6px 10px",
    lineHeight: "1.4",
  },
  explanationLabel: {
    fontWeight: "600",
    color: "var(--text-primary)",
  },

  /* Thinking Indicator */
  thinkingBubble: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    padding: "8px 14px",
    backgroundColor: "var(--bg-sidebar)",
    border: "1px solid var(--border-hairline)",
    borderRadius: "10px",
  },
  thinkingDot: {
    width: "4px",
    height: "4px",
    borderRadius: "50%",
    backgroundColor: "var(--text-tertiary)",
    opacity: 0.6,
  },

  /* Fixed Input Bar */
  inputBarContainer: {
    padding: "14px 40px 18px",
    borderTop: "1px solid var(--border-hairline)",
    backgroundColor: "var(--bg-main)",
  },
  inputForm: {
    maxWidth: "760px",
    margin: "0 auto",
    display: "flex",
    alignItems: "center",
    border: "1px solid var(--border-hairline)",
    borderRadius: "8px",
    padding: "5px 6px 5px 14px",
    backgroundColor: "var(--bg-input)",
  },
  chatInput: {
    flex: 1,
    fontSize: "13.5px",
    color: "var(--text-primary)",
    backgroundColor: "transparent",
  },
  sendButton: {
    width: "28px",
    height: "28px",
    borderRadius: "4px",
    backgroundColor: "var(--accent)",
    color: "var(--tab-active-text)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  sendIcon: {
    width: "14px",
    height: "14px",
  },
};
