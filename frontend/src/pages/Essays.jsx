import React, { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API_URL =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const getToken = () => {
    return (
        localStorage.getItem("token") ||
        sessionStorage.getItem("token")
    );
};

function Essays() {
    const [exam, setExam] = useState("UPSC");
    const [language, setLanguage] = useState("hi");

    const [essay, setEssay] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const generateEssay = async () => {
        setLoading(true);
        setError("");
        setEssay(null);

        try {
            const token = getToken();

            if (!token) {
                setError("Please login first.");
                return;
            }

            const response = await axios.post(
                `${API_URL}/writing/essays/generate`,
                {
                    exam,
                    language,
                },
                {
                    timeout: 30000,
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            setEssay(response.data);
        } catch (err) {
            console.error("Essay generation error:", err);

            if (err.response?.status === 401) {
                setError("Session expired. Please login again.");
            } else if (err.response?.data?.detail) {
                setError(
                    typeof err.response.data.detail === "string"
                        ? err.response.data.detail
                        : "Unable to generate essay."
                );
            } else if (err.request) {
                setError(
                    "Unable to connect to the Muni48 backend."
                );
            } else {
                setError(
                    err.message || "Something went wrong."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    const getEssayTitle = () => {
        return (
            essay?.title ||
            essay?.question ||
            essay?.topic ||
            essay?.essay_question ||
            "Essay Practice"
        );
    };

    return (
        <main style={styles.page}>
            <div style={styles.container}>

                {/* Header */}
                <div style={styles.topBar}>
                    <div>
                        <Link to="/dashboard" style={styles.backLink}>
                            ← Dashboard
                        </Link>

                        <h1 style={styles.title}>
                            📚 Essay Practice
                        </h1>

                        <p style={styles.subtitle}>
                            Improve your UPSC & BPSC essay writing skills.
                        </p>
                    </div>

                    <div style={styles.badge}>
                        Muni48
                    </div>
                </div>

                {/* Generator */}
                <section style={styles.card}>
                    <h2 style={styles.cardTitle}>
                        Generate Essay
                    </h2>

                    <p style={styles.cardDescription}>
                        Generate a practice essay topic according to
                        your examination.
                    </p>

                    <div style={styles.formGrid}>

                        {/* Exam */}
                        <div>
                            <label style={styles.label}>
                                Examination
                            </label>

                            <select
                                value={exam}
                                onChange={(e) =>
                                    setExam(e.target.value)
                                }
                                style={styles.input}
                                disabled={loading}
                            >
                                <option value="UPSC">
                                    UPSC
                                </option>

                                <option value="BPSC">
                                    BPSC
                                </option>
                            </select>
                        </div>

                        {/* Language */}
                        <div>
                            <label style={styles.label}>
                                Language
                            </label>

                            <select
                                value={language}
                                onChange={(e) =>
                                    setLanguage(e.target.value)
                                }
                                style={styles.input}
                                disabled={loading}
                            >
                                <option value="hi">
                                    Hindi
                                </option>

                                <option value="en">
                                    English
                                </option>
                            </select>
                        </div>

                    </div>

                    {error && (
                        <div style={styles.error}>
                            ⚠️ {error}
                        </div>
                    )}

                    <button
                        type="button"
                        onClick={generateEssay}
                        disabled={loading}
                        style={{
                            ...styles.button,
                            ...(loading
                                ? styles.buttonDisabled
                                : {}),
                        }}
                    >
                        {loading
                            ? "Generating..."
                            : "🚀 Generate Essay"}
                    </button>
                </section>

                {/* Result */}
                {essay && (
                    <section style={styles.resultCard}>
                        <div style={styles.resultHeader}>
                            <span style={styles.resultBadge}>
                                {exam}
                            </span>

                            <span style={styles.languageBadge}>
                                {language === "hi"
                                    ? "Hindi"
                                    : "English"}
                            </span>
                        </div>

                        <h2 style={styles.essayTitle}>
                            {getEssayTitle()}
                        </h2>

                        {essay.content && (
                            <div style={styles.content}>
                                {essay.content}
                            </div>
                        )}

                        {essay.topic && !essay.content && (
                            <div style={styles.content}>
                                {essay.topic}
                            </div>
                        )}

                        {essay.instructions && (
                            <div style={styles.instructions}>
                                <h3>
                                    Instructions
                                </h3>

                                <p>
                                    {essay.instructions}
                                </p>
                            </div>
                        )}

                        <div style={styles.practiceBox}>
                            <strong>
                                ✍️ Practice
                            </strong>

                            <p>
                                Write your essay and focus on
                                introduction, arguments, examples,
                                analysis and conclusion.
                            </p>
                        </div>
                    </section>
                )}

                {/* Empty state */}
                {!essay && !loading && !error && (
                    <section style={styles.emptyCard}>
                        <div style={styles.emptyIcon}>
                            📚
                        </div>

                        <h2>
                            Ready to practice?
                        </h2>

                        <p>
                            Select your exam and language, then
                            generate an essay topic.
                        </p>
                    </section>
                )}

            </div>
        </main>
    );
}

const styles = {
    page: {
        minHeight: "100vh",
        background:
            "linear-gradient(135deg, #eff6ff 0%, #f8fafc 50%, #eef2ff 100%)",
        padding: "32px 20px",
        boxSizing: "border-box",
    },

    container: {
        width: "100%",
        maxWidth: "1000px",
        margin: "0 auto",
    },

    topBar: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: "28px",
        gap: "20px",
    },

    backLink: {
        color: "#2563eb",
        textDecoration: "none",
        fontSize: "14px",
        fontWeight: "600",
    },

    title: {
        margin: "10px 0 6px",
        fontSize: "32px",
        fontWeight: "800",
        color: "#111827",
    },

    subtitle: {
        margin: 0,
        color: "#64748b",
        fontSize: "15px",
    },

    badge: {
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        padding: "9px 14px",
        borderRadius: "10px",
        fontWeight: "800",
        color: "#2563eb",
    },

    card: {
        background: "#ffffff",
        borderRadius: "16px",
        padding: "28px",
        boxShadow:
            "0 10px 30px rgba(15, 23, 42, 0.08)",
        border: "1px solid #e2e8f0",
        marginBottom: "24px",
    },

    cardTitle: {
        margin: 0,
        fontSize: "22px",
        color: "#111827",
    },

    cardDescription: {
        marginTop: "8px",
        marginBottom: "24px",
        color: "#64748b",
        fontSize: "14px",
    },

    formGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "18px",
        marginBottom: "22px",
    },

    label: {
        display: "block",
        marginBottom: "7px",
        fontSize: "14px",
        fontWeight: "600",
        color: "#334155",
    },

    input: {
        width: "100%",
        height: "46px",
        padding: "0 12px",
        border: "1px solid #cbd5e1",
        borderRadius: "9px",
        background: "#ffffff",
        color: "#0f172a",
        fontSize: "14px",
        boxSizing: "border-box",
        outline: "none",
    },

    button: {
        width: "100%",
        height: "48px",
        border: "none",
        borderRadius: "10px",
        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",
        color: "#ffffff",
        fontSize: "15px",
        fontWeight: "700",
        cursor: "pointer",
    },

    buttonDisabled: {
        opacity: 0.65,
        cursor: "not-allowed",
    },

    error: {
        background: "#fef2f2",
        color: "#b91c1c",
        border: "1px solid #fecaca",
        padding: "12px 14px",
        borderRadius: "9px",
        marginBottom: "18px",
        fontSize: "14px",
    },

    resultCard: {
        background: "#ffffff",
        borderRadius: "16px",
        padding: "30px",
        boxShadow:
            "0 10px 30px rgba(15, 23, 42, 0.08)",
        border: "1px solid #e2e8f0",
    },

    resultHeader: {
        display: "flex",
        gap: "8px",
        marginBottom: "18px",
    },

    resultBadge: {
        background: "#dbeafe",
        color: "#1d4ed8",
        padding: "5px 10px",
        borderRadius: "20px",
        fontSize: "12px",
        fontWeight: "700",
    },

    languageBadge: {
        background: "#ede9fe",
        color: "#6d28d9",
        padding: "5px 10px",
        borderRadius: "20px",
        fontSize: "12px",
        fontWeight: "700",
    },

    essayTitle: {
        margin: "0 0 20px",
        fontSize: "24px",
        lineHeight: "1.4",
        color: "#111827",
    },

    content: {
        whiteSpace: "pre-wrap",
        color: "#334155",
        fontSize: "16px",
        lineHeight: "1.8",
        padding: "20px",
        background: "#f8fafc",
        borderRadius: "10px",
    },

    instructions: {
        marginTop: "20px",
        padding: "18px",
        background: "#eff6ff",
        borderRadius: "10px",
        color: "#334155",
    },

    practiceBox: {
        marginTop: "22px",
        padding: "18px",
        background: "#f0fdf4",
        border: "1px solid #bbf7d0",
        borderRadius: "10px",
        color: "#166534",
    },

    emptyCard: {
        background: "#ffffff",
        borderRadius: "16px",
        padding: "50px 30px",
        textAlign: "center",
        border: "1px solid #e2e8f0",
        boxShadow:
            "0 10px 30px rgba(15, 23, 42, 0.06)",
    },

    emptyIcon: {
        fontSize: "45px",
        marginBottom: "10px",
    },
};

export default Essays;