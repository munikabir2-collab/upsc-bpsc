import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API_URL =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Essays() {
    const [essays, setEssays] = useState([]);
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState("");

    const [form, setForm] = useState({
        exam: "UPSC",
        language: "en",
    });

    const getToken = () => {
        return (
            localStorage.getItem("token") ||
            sessionStorage.getItem("token")
        );
    };

    const authHeaders = () => {
        const token = getToken();

        return token
            ? {
                  Authorization: `Bearer ${token}`,
                  "Content-Type": "application/json",
              }
            : {
                  "Content-Type": "application/json",
              };
    };

    // --------------------------------------------------
    // Load existing essays
    // --------------------------------------------------

    const loadEssays = async () => {
        setLoading(true);
        setError("");

        try {
            const response = await axios.get(
                `${API_URL}/writing/questions`,
                {
                    params: {
                        exam: form.exam,
                    },
                    headers: authHeaders(),
                    timeout: 10000,
                }
            );

            const data = response.data;

            if (Array.isArray(data)) {
                setEssays(data);
            } else if (Array.isArray(data?.items)) {
                setEssays(data.items);
            } else if (Array.isArray(data?.questions)) {
                setEssays(data.questions);
            } else {
                setEssays([]);
            }
        } catch (err) {
            console.error("Essay loading error:", err);

            if (err.response?.status === 401) {
                setError("Please login to continue.");
            } else if (err.response?.data?.detail) {
                setError(
                    typeof err.response.data.detail === "string"
                        ? err.response.data.detail
                        : "Unable to load essay data."
                );
            } else {
                setError(
                    "Unable to connect to the Muni48 backend."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadEssays();
    }, [form.exam]);

    // --------------------------------------------------
    // Generate Essay
    // --------------------------------------------------

    const generateEssay = async () => {
        setGenerating(true);
        setError("");

        try {
            const response = await axios.post(
                `${API_URL}/writing/essays/generate`,
                {
                    exam: form.exam,
                    language: form.language,
                },
                {
                    headers: authHeaders(),
                    timeout: 30000,
                }
            );

            const generated = response.data;

            if (generated) {
                setEssays((prev) => [
                    generated,
                    ...prev,
                ]);
            }
        } catch (err) {
            console.error(
                "Essay generation error:",
                err
            );

            if (err.response?.status === 401) {
                setError("Please login to generate an essay.");
            } else if (err.response?.data?.detail) {
                setError(
                    typeof err.response.data.detail === "string"
                        ? err.response.data.detail
                        : "Unable to generate essay."
                );
            } else {
                setError(
                    "Essay generation failed. Please try again."
                );
            }
        } finally {
            setGenerating(false);
        }
    };

    // --------------------------------------------------
    // Render
    // --------------------------------------------------

    return (
        <main style={styles.page}>
            <div style={styles.container}>

                {/* Header */}
                <header style={styles.header}>
                    <div>
                        <div style={styles.breadcrumb}>
                            <Link
                                to="/dashboard"
                                style={styles.breadcrumbLink}
                            >
                                Dashboard
                            </Link>

                            <span> / </span>

                            <span>Essays</span>
                        </div>

                        <h1 style={styles.title}>
                            Essay Practice
                        </h1>

                        <p style={styles.subtitle}>
                            Improve your UPSC & BPSC essay
                            writing skills.
                        </p>
                    </div>

                    <Link
                        to="/dashboard"
                        style={styles.backButton}
                    >
                        ← Dashboard
                    </Link>
                </header>

                {/* Controls */}
                <section style={styles.controlCard}>
                    <div style={styles.controlGroup}>
                        <label style={styles.label}>
                            Exam
                        </label>

                        <select
                            value={form.exam}
                            onChange={(e) =>
                                setForm((prev) => ({
                                    ...prev,
                                    exam: e.target.value,
                                }))
                            }
                            style={styles.select}
                            disabled={loading || generating}
                        >
                            <option value="UPSC">
                                UPSC
                            </option>

                            <option value="BPSC">
                                BPSC
                            </option>
                        </select>
                    </div>

                    <div style={styles.controlGroup}>
                        <label style={styles.label}>
                            Language
                        </label>

                        <select
                            value={form.language}
                            onChange={(e) =>
                                setForm((prev) => ({
                                    ...prev,
                                    language: e.target.value,
                                }))
                            }
                            style={styles.select}
                            disabled={loading || generating}
                        >
                            <option value="en">
                                English
                            </option>

                            <option value="hi">
                                Hindi
                            </option>
                        </select>
                    </div>

                    <button
                        type="button"
                        onClick={generateEssay}
                        disabled={generating}
                        style={{
                            ...styles.generateButton,
                            ...(generating
                                ? styles.disabledButton
                                : {}),
                        }}
                    >
                        {generating
                            ? "Generating..."
                            : "✨ Generate Essay"}
                    </button>
                </section>

                {/* Error */}
                {error && (
                    <div style={styles.error}>
                        ⚠️ {error}
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div style={styles.loading}>
                        Loading essays...
                    </div>
                )}

                {/* Empty */}
                {!loading && essays.length === 0 && !error && (
                    <section style={styles.emptyCard}>
                        <div style={styles.emptyIcon}>
                            📚
                        </div>

                        <h2 style={styles.emptyTitle}>
                            No essays available
                        </h2>

                        <p style={styles.emptyText}>
                            Generate your first essay to
                            start practicing.
                        </p>

                        <button
                            type="button"
                            onClick={generateEssay}
                            disabled={generating}
                            style={styles.generateButton}
                        >
                            {generating
                                ? "Generating..."
                                : "Generate First Essay"}
                        </button>
                    </section>
                )}

                {/* Essay List */}
                {!loading && essays.length > 0 && (
                    <section style={styles.list}>
                        {essays.map((essay, index) => {
                            const id =
                                essay.id ??
                                essay.question_id ??
                                index;

                            const title =
                                essay.title ||
                                essay.question ||
                                essay.topic ||
                                `Essay ${index + 1}`;

                            const description =
                                essay.description ||
                                essay.instructions ||
                                essay.prompt ||
                                "Practice this essay topic and improve your answer writing.";

                            return (
                                <article
                                    key={id}
                                    style={styles.essayCard}
                                >
                                    <div style={styles.number}>
                                        {index + 1}
                                    </div>

                                    <div style={styles.essayContent}>
                                        <div style={styles.badges}>
                                            <span
                                                style={
                                                    styles.examBadge
                                                }
                                            >
                                                {essay.exam ||
                                                    form.exam}
                                            </span>

                                            <span
                                                style={
                                                    styles.essayBadge
                                                }
                                            >
                                                Essay
                                            </span>
                                        </div>

                                        <h2
                                            style={
                                                styles.essayTitle
                                            }
                                        >
                                            {title}
                                        </h2>

                                        <p
                                            style={
                                                styles.essayDescription
                                            }
                                        >
                                            {description}
                                        </p>

                                        {essay.max_words && (
                                            <div
                                                style={
                                                    styles.meta
                                                }
                                            >
                                                Maximum words:{" "}
                                                {
                                                    essay.max_words
                                                }
                                            </div>
                                        )}

                                        {essay.created_at && (
                                            <div
                                                style={
                                                    styles.meta
                                                }
                                            >
                                                Created:{" "}
                                                {String(
                                                    essay.created_at
                                                ).slice(
                                                    0,
                                                    10
                                                )}
                                            </div>
                                        )}
                                    </div>

                                    <Link
                                        to={
                                            id
                                                ? `/essays/${id}`
                                                : "/essays"
                                        }
                                        state={{
                                            essay,
                                        }}
                                        style={
                                            styles.practiceButton
                                        }
                                    >
                                        Practice →
                                    </Link>
                                </article>
                            );
                        })}
                    </section>
                )}
            </div>
        </main>
    );
}

// ======================================================
// Styles
// ======================================================

const styles = {
    page: {
        minHeight: "100vh",
        background:
            "linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%)",
        padding: "32px 20px",
        boxSizing: "border-box",
    },

    container: {
        width: "100%",
        maxWidth: "1100px",
        margin: "0 auto",
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "20px",
        marginBottom: "28px",
    },

    breadcrumb: {
        fontSize: "13px",
        color: "#64748b",
        marginBottom: "10px",
    },

    breadcrumbLink: {
        color: "#2563eb",
        textDecoration: "none",
        fontWeight: "600",
    },

    title: {
        margin: 0,
        color: "#0f172a",
        fontSize: "32px",
        fontWeight: "800",
    },

    subtitle: {
        margin: "8px 0 0",
        color: "#64748b",
        fontSize: "15px",
    },

    backButton: {
        textDecoration: "none",
        background: "#ffffff",
        color: "#334155",
        border: "1px solid #e2e8f0",
        borderRadius: "10px",
        padding: "10px 16px",
        fontSize: "14px",
        fontWeight: "600",
    },

    controlCard: {
        display: "flex",
        alignItems: "flex-end",
        gap: "16px",
        flexWrap: "wrap",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "20px",
        marginBottom: "22px",
        boxShadow:
            "0 8px 25px rgba(15, 23, 42, 0.05)",
    },

    controlGroup: {
        minWidth: "180px",
    },

    label: {
        display: "block",
        marginBottom: "7px",
        fontSize: "13px",
        fontWeight: "700",
        color: "#334155",
    },

    select: {
        width: "100%",
        height: "44px",
        padding: "0 12px",
        border: "1px solid #cbd5e1",
        borderRadius: "9px",
        background: "#ffffff",
        color: "#0f172a",
        fontSize: "14px",
        outline: "none",
    },

    generateButton: {
        height: "44px",
        border: "none",
        borderRadius: "9px",
        padding: "0 20px",
        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",
        color: "#ffffff",
        fontSize: "14px",
        fontWeight: "700",
        cursor: "pointer",
        whiteSpace: "nowrap",
    },

    disabledButton: {
        opacity: 0.65,
        cursor: "not-allowed",
    },

    error: {
        background: "#fef2f2",
        border: "1px solid #fecaca",
        color: "#b91c1c",
        padding: "13px 16px",
        borderRadius: "10px",
        marginBottom: "20px",
        fontSize: "14px",
    },

    loading: {
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "14px",
        padding: "40px",
        textAlign: "center",
        color: "#64748b",
    },

    emptyCard: {
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "60px 30px",
        textAlign: "center",
        boxShadow:
            "0 8px 25px rgba(15, 23, 42, 0.05)",
    },

    emptyIcon: {
        fontSize: "42px",
        marginBottom: "12px",
    },

    emptyTitle: {
        margin: 0,
        color: "#0f172a",
        fontSize: "21px",
    },

    emptyText: {
        color: "#64748b",
        fontSize: "14px",
        margin: "8px 0 20px",
    },

    list: {
        display: "flex",
        flexDirection: "column",
        gap: "16px",
    },

    essayCard: {
        display: "flex",
        alignItems: "flex-start",
        gap: "18px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
        padding: "22px",
        boxShadow:
            "0 6px 20px rgba(15, 23, 42, 0.04)",
    },

    number: {
        width: "38px",
        height: "38px",
        minWidth: "38px",
        borderRadius: "10px",
        background: "#eff6ff",
        color: "#2563eb",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: "800",
        fontSize: "14px",
    },

    essayContent: {
        flex: 1,
        minWidth: 0,
    },

    badges: {
        display: "flex",
        gap: "8px",
        marginBottom: "9px",
    },

    examBadge: {
        background: "#eff6ff",
        color: "#1d4ed8",
        padding: "4px 8px",
        borderRadius: "6px",
        fontSize: "11px",
        fontWeight: "700",
    },

    essayBadge: {
        background: "#f1f5f9",
        color: "#475569",
        padding: "4px 8px",
        borderRadius: "6px",
        fontSize: "11px",
        fontWeight: "700",
    },

    essayTitle: {
        margin: 0,
        color: "#0f172a",
        fontSize: "18px",
        lineHeight: "1.45",
    },

    essayDescription: {
        margin: "8px 0 0",
        color: "#64748b",
        fontSize: "14px",
        lineHeight: "1.6",
    },

    meta: {
        display: "inline-block",
        marginTop: "10px",
        marginRight: "14px",
        color: "#94a3b8",
        fontSize: "12px",
    },

    practiceButton: {
        alignSelf: "center",
        textDecoration: "none",
        background: "#f8fafc",
        border: "1px solid #cbd5e1",
        color: "#2563eb",
        borderRadius: "9px",
        padding: "9px 13px",
        fontSize: "13px",
        fontWeight: "700",
        whiteSpace: "nowrap",
    },
};

export default Essays;