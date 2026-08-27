// src/pages/Dashboard.jsx

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";

// ============================================================
// CONFIG
// ============================================================

const API_URL =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// ============================================================
// API CLIENT
// ============================================================

const api = axios.create({
    baseURL: API_URL,
    timeout: 15000,
    headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
    },
});

// ============================================================
// AUTH HELPERS
// ============================================================

const getToken = () => {
    return (
        localStorage.getItem("token") ||
        sessionStorage.getItem("token") ||
        ""
    );
};

const getStoredUser = () => {
    try {
        const raw =
            localStorage.getItem("user") ||
            sessionStorage.getItem("user");

        if (!raw) {
            return null;
        }

        return JSON.parse(raw);
    } catch (error) {
        console.error("Unable to parse stored user:", error);
        return null;
    }
};

const getAuthHeaders = () => {
    const token = getToken();

    if (!token) {
        return {};
    }

    return {
        Authorization: `Bearer ${token}`,
    };
};

// ============================================================
// RESPONSE HELPERS
// ============================================================

const getArrayFromResponse = (data, possibleKeys = []) => {
    if (Array.isArray(data)) {
        return data;
    }

    if (!data || typeof data !== "object") {
        return [];
    }

    for (const key of possibleKeys) {
        if (Array.isArray(data[key])) {
            return data[key];
        }
    }

    return [];
};

const getNewsCount = (data) => {
    if (!data || typeof data !== "object") {
        return 0;
    }

    if (typeof data.total === "number") {
        return data.total;
    }

    if (typeof data.returned_results === "number") {
        return data.returned_results;
    }

    if (typeof data.count === "number") {
        return data.count;
    }

    if (Array.isArray(data.articles)) {
        return data.articles.length;
    }

    if (Array.isArray(data.results)) {
        return data.results.length;
    }

    if (Array.isArray(data.data)) {
        return data.data.length;
    }

    return 0;
};

const getMcqCount = (data) => {
    if (Array.isArray(data)) {
        return data.length;
    }

    if (!data || typeof data !== "object") {
        return 0;
    }

    if (typeof data.total === "number") {
        return data.total;
    }

    if (typeof data.count === "number") {
        return data.count;
    }

    const items = getArrayFromResponse(data, [
        "questions",
        "mcqs",
        "results",
        "data",
    ]);

    return items.length;
};

// ============================================================
// COMPONENT
// ============================================================

function Dashboard() {
    const navigate = useNavigate();

    // --------------------------------------------------------
    // USER
    // --------------------------------------------------------

    const storedUser = useMemo(() => getStoredUser(), []);

    const [user, setUser] = useState(storedUser);

    // --------------------------------------------------------
    // DASHBOARD STATE
    // --------------------------------------------------------

    const [backendOnline, setBackendOnline] = useState(false);

    const [loading, setLoading] = useState(true);

    const [error, setError] = useState("");

    const [newsCount, setNewsCount] = useState(0);

    const [mcqCount, setMcqCount] = useState(0);

    const [writingCount, setWritingCount] = useState(0);

    // Essay endpoint is not available in the supplied docs.
    // Therefore we don't invent an API call.
    const [essayCount] = useState(0);

    // --------------------------------------------------------
    // USER NAME
    // --------------------------------------------------------

    const displayName =
        user?.name ||
        user?.full_name ||
        user?.username ||
        user?.email?.split("@")[0] ||
        "Student";

    // --------------------------------------------------------
    // EXAM
    // --------------------------------------------------------

    const exam =
        user?.exam ||
        user?.target_exam ||
        localStorage.getItem("exam") ||
        sessionStorage.getItem("exam") ||
        "UPSC";

    // --------------------------------------------------------
    // GREETING
    // --------------------------------------------------------

    const greeting = useMemo(() => {
        const hour = new Date().getHours();

        if (hour < 12) {
            return "Good morning";
        }

        if (hour < 18) {
            return "Good afternoon";
        }

        return "Good evening";
    }, []);

    // ========================================================
    // HEALTH CHECK
    // ========================================================

    const checkHealth = useCallback(async () => {
        try {
            const response = await api.get("/health");

            if (response.status >= 200 && response.status < 300) {
                setBackendOnline(true);
                return true;
            }

            setBackendOnline(false);
            return false;
        } catch (err) {
            console.error("Health check failed:", err);
            setBackendOnline(false);
            return false;
        }
    }, []);

    // ========================================================
    // LOAD DASHBOARD DATA
    // ========================================================

    const loadDashboard = useCallback(async () => {
        setLoading(true);
        setError("");

        const token = getToken();

        // ----------------------------------------------------
        // Health
        // ----------------------------------------------------

        let healthOK = false;

        try {
            const healthResponse = await api.get("/health");

            healthOK =
                healthResponse.status >= 200 &&
                healthResponse.status < 300;

            setBackendOnline(healthOK);
        } catch (err) {
            console.error("Health error:", err);
            setBackendOnline(false);
        }

        // ----------------------------------------------------
        // News
        // ----------------------------------------------------

        try {
            const newsResponse = await api.get("/news/search", {
                params: {
                    q: "India",
                    page: 1,
                    page_size: 20,
                    language: "en",
                    exam,
                    category: "General",
                    bihar_only: false,
                },
                headers: {
                    ...getAuthHeaders(),
                },
            });

            setNewsCount(getNewsCount(newsResponse.data));
        } catch (err) {
            console.error("News API error:", err);

            // Do not overwrite dashboard if other APIs work.
            setNewsCount(0);

            if (err.response?.status === 401) {
                console.warn(
                    "News API returned 401. Check login token."
                );
            }
        }

        // ----------------------------------------------------
        // MCQ Practice
        // ----------------------------------------------------

        try {
            const mcqResponse = await api.get(
                "/news/mcqs/practice",
                {
                    params: {
                        exam,
                        language: "hi",
                        limit: 50,
                    },
                    headers: {
                        ...getAuthHeaders(),
                    },
                }
            );

            setMcqCount(getMcqCount(mcqResponse.data));
        } catch (err) {
            console.error("MCQ API error:", err);
            setMcqCount(0);
        }

        // ----------------------------------------------------
        // Writing Questions
        // ----------------------------------------------------

        try {
            const writingResponse = await api.get(
                "/writing/questions",
                {
                    params: {
                        exam,
                        category: "General",
                    },
                    headers: {
                        ...getAuthHeaders(),
                    },
                }
            );

            const writingQuestions =
                getArrayFromResponse(
                    writingResponse.data,
                    [
                        "questions",
                        "results",
                        "data",
                    ]
                );

            setWritingCount(
                writingQuestions.length
            );
        } catch (err) {
            console.error(
                "Writing API error:",
                err
            );

            setWritingCount(0);
        }

        // ----------------------------------------------------
        // General error
        // ----------------------------------------------------

        if (!healthOK) {
            setError(
                "Backend is offline. Please make sure the FastAPI server is running."
            );
        } else if (!token) {
            setError(
                "Please login to continue."
            );
        }

        setLoading(false);
    }, [exam]);

    // ========================================================
    // INITIAL LOAD
    // ========================================================

    useEffect(() => {
        const currentUser = getStoredUser();

        if (currentUser) {
            setUser(currentUser);
        }

        loadDashboard();
    }, [loadDashboard]);

    // ========================================================
    // LOGOUT
    // ========================================================

    const handleLogout = () => {
        localStorage.removeItem("token");
        localStorage.removeItem("user");

        sessionStorage.removeItem("token");
        sessionStorage.removeItem("user");

        navigate("/login", {
            replace: true,
        });
    };

    // ========================================================
    // RETRY
    // ========================================================

    const handleRetry = () => {
        loadDashboard();
    };

    // ========================================================
    // DASHBOARD STATS
    // ========================================================

    const stats = [
        {
            icon: "📰",
            title: "Current Affairs",
            value: newsCount,
            description: "Articles available",
            path: "/news",
        },
        {
            icon: "🎯",
            title: "MCQ Practice",
            value: mcqCount,
            description: "Questions available",
            path: "/mcqs",
        },
        {
            icon: "✍️",
            title: "Answer Writing",
            value: writingCount,
            description: "Writing questions",
            path: "/writing",
        },
        {
            icon: "📚",
            title: "Essays",
            value: essayCount,
            description: "Essay practice",
            path: "/essays",
        },
    ];

    // ========================================================
    // QUICK PRACTICE
    // ========================================================

    const quickPractice = [
        {
            icon: "📰",
            title: "Current Affairs",
            description:
                "Read important UPSC & BPSC news",
            path: "/news",
        },
        {
            icon: "📝",
            title: "Practice MCQs",
            description:
                "Test your knowledge",
            path: "/mcqs",
        },
        {
            icon: "✍️",
            title: "Answer Writing",
            description:
                "Practice mains answers",
            path: "/writing",
        },
        {
            icon: "📚",
            title: "Essay Practice",
            description:
                "Improve your essay writing",
            path: "/essays",
        },
    ];

    // ========================================================
    // TODAY'S PLAN
    // ========================================================

    const todayPlan = [
        {
            icon: "📰",
            title: "Read Current Affairs",
            description: `${newsCount} articles available`,
            path: "/news",
        },
        {
            icon: "📝",
            title: "Practice MCQs",
            description: `${mcqCount} questions available`,
            path: "/mcqs",
        },
        {
            icon: "✍️",
            title: "Write an Answer",
            description: `${writingCount} writing questions`,
            path: "/writing",
        },
        {
            icon: "📚",
            title: "Practice Essay",
            description: "Continue your essay preparation",
            path: "/essays",
        },
    ];

    // ========================================================
    // PREPARATION PROGRESS
    // ========================================================

    const totalTasks = todayPlan.length;

    const completedTasks = [
        newsCount > 0,
        mcqCount > 0,
        writingCount > 0,
        essayCount > 0,
    ].filter(Boolean).length;

    const progress = Math.round(
        (completedTasks / totalTasks) * 100
    );

    // ========================================================
    // RENDER
    // ========================================================

    return (
        <div style={styles.app}>
            {/* =================================================
                SIDEBAR
            ================================================= */}

            <aside style={styles.sidebar}>
                {/* Brand */}

                <div style={styles.brand}>
                    <div style={styles.logo}>
                        M
                    </div>

                    <div>
                        <div style={styles.brandName}>
                            Muni48
                        </div>

                        <div style={styles.brandSubtitle}>
                            Civil Services
                        </div>
                    </div>
                </div>

                {/* Navigation */}

                <nav style={styles.nav}>
                    <Link
                        to="/dashboard"
                        style={{
                            ...styles.navItem,
                            ...styles.navItemActive,
                        }}
                    >
                        <span>🏠</span>
                        <span>Dashboard</span>
                    </Link>

                    <Link
                        to="/news"
                        style={styles.navItem}
                    >
                        <span>📰</span>
                        <span>Current Affairs</span>
                    </Link>

                    <Link
                        to="/mcqs"
                        style={styles.navItem}
                    >
                        <span>📝</span>
                        <span>MCQ Practice</span>
                    </Link>

                    <Link
                        to="/writing"
                        style={styles.navItem}
                    >
                        <span>✍️</span>
                        <span>Answer Writing</span>
                    </Link>

                    <Link
                        to="/essays"
                        style={styles.navItem}
                    >
                        <span>📚</span>
                        <span>Essay Practice</span>
                    </Link>

                    <Link
                        to="/profile"
                        style={styles.navItem}
                    >
                        <span>👤</span>
                        <span>Profile</span>
                    </Link>
                </nav>

                {/* Pro Card */}

                <div style={styles.proCard}>
                    <div style={styles.proIcon}>
                        ⭐
                    </div>

                    <div style={styles.proTitle}>
                        Upgrade to Pro
                    </div>

                    <div style={styles.proText}>
                        Unlock premium features
                    </div>

                    <Link
                        to="/subscription"
                        style={styles.proButton}
                    >
                        Upgrade
                        <span>→</span>
                    </Link>
                </div>

                {/* Logout */}

                <button
                    type="button"
                    onClick={handleLogout}
                    style={styles.logoutButton}
                >
                    <span>🚪</span>
                    <span>Logout</span>
                </button>
            </aside>

            {/* =================================================
                MAIN
            ================================================= */}

            <main style={styles.main}>
                {/* Top Header */}

                <header style={styles.topbar}>
                    <div>
                        <div style={styles.smallHeading}>
                            STUDENT DASHBOARD
                        </div>

                        <h1 style={styles.pageTitle}>
                            {greeting},{" "}
                            {displayName} 👋
                        </h1>

                        <p style={styles.pageSubtitle}>
                            Continue your {exam} preparation.
                        </p>
                    </div>

                    <div style={styles.topbarRight}>
                        <div
                            style={{
                                ...styles.statusBadge,
                                ...(backendOnline
                                    ? styles.statusOnline
                                    : styles.statusOffline),
                            }}
                        >
                            <span
                                style={
                                    styles.statusDot
                                }
                            />
                            {backendOnline
                                ? "Backend Online"
                                : "Backend Offline"}
                        </div>

                        <button
                            type="button"
                            style={styles.iconButton}
                            onClick={handleRetry}
                            title="Refresh dashboard"
                        >
                            ↻
                        </button>

                        <button
                            type="button"
                            style={styles.iconButton}
                            title="Notifications"
                        >
                            🔔
                        </button>

                        <div style={styles.avatar}>
                            {String(displayName)
                                .charAt(0)
                                .toUpperCase()}
                        </div>
                    </div>
                </header>

                {/* =================================================
                    ERROR
                ================================================= */}

                {error && (
                    <div style={styles.errorBox}>
                        <div>
                            <strong>
                                Some data could not be loaded.
                            </strong>

                            <div style={styles.errorText}>
                                {error}
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={handleRetry}
                            style={styles.retryButton}
                        >
                            Retry
                        </button>
                    </div>
                )}

                {/* =================================================
                    STATS
                ================================================= */}

                <section style={styles.statsGrid}>
                    {stats.map((item) => (
                        <Link
                            key={item.title}
                            to={item.path}
                            style={styles.statCard}
                        >
                            <div style={styles.statIcon}>
                                {item.icon}
                            </div>

                            <div style={styles.statContent}>
                                <div style={styles.statTitle}>
                                    {item.title}
                                </div>

                                <div style={styles.statValue}>
                                    {loading
                                        ? "—"
                                        : item.value}
                                </div>

                                <div style={styles.statDescription}>
                                    {item.description}
                                </div>
                            </div>
                        </Link>
                    ))}
                </section>

                {/* =================================================
                    QUICK PRACTICE
                ================================================= */}

                <section style={styles.section}>
                    <div style={styles.sectionHeader}>
                        <div>
                            <h2 style={styles.sectionTitle}>
                                Quick Practice
                            </h2>

                            <p style={styles.sectionSubtitle}>
                                Start your preparation
                            </p>
                        </div>

                        <div style={styles.rocket}>
                            🚀
                        </div>
                    </div>

                    <div style={styles.quickGrid}>
                        {quickPractice.map((item) => (
                            <Link
                                key={item.title}
                                to={item.path}
                                style={styles.quickCard}
                            >
                                <div style={styles.quickIcon}>
                                    {item.icon}
                                </div>

                                <div style={styles.quickContent}>
                                    <h3 style={styles.quickTitle}>
                                        {item.title}
                                    </h3>

                                    <p style={styles.quickDescription}>
                                        {item.description}
                                    </p>
                                </div>

                                <div style={styles.arrow}>
                                    →
                                </div>
                            </Link>
                        ))}
                    </div>
                </section>

                {/* =================================================
                    TODAY'S PLAN
                ================================================= */}

                <section style={styles.planSection}>
                    <div style={styles.planHeader}>
                        <div>
                            <h2 style={styles.sectionTitle}>
                                Today's Plan
                            </h2>

                            <p style={styles.sectionSubtitle}>
                                Your preparation checklist
                            </p>
                        </div>

                        <div style={styles.progressBox}>
                            <div style={styles.progressValue}>
                                {progress}%
                            </div>

                            <div style={styles.progressBar}>
                                <div
                                    style={{
                                        ...styles.progressFill,
                                        width: `${progress}%`,
                                    }}
                                />
                            </div>
                        </div>
                    </div>

                    <div style={styles.planList}>
                        {todayPlan.map((item) => (
                            <Link
                                key={item.title}
                                to={item.path}
                                style={styles.planItem}
                            >
                                <div style={styles.planIcon}>
                                    {item.icon}
                                </div>

                                <div style={styles.planContent}>
                                    <div style={styles.planTitle}>
                                        {item.title}
                                    </div>

                                    <div style={styles.planDescription}>
                                        {item.description}
                                    </div>
                                </div>

                                <div style={styles.planArrow}>
                                    →
                                </div>
                            </Link>
                        ))}
                    </div>
                </section>

                {/* =================================================
                    PREPARATION OVERVIEW
                ================================================= */}

                <section style={styles.section}>
                    <div style={styles.sectionHeader}>
                        <div>
                            <h2 style={styles.sectionTitle}>
                                Preparation Overview
                            </h2>

                            <p style={styles.sectionSubtitle}>
                                Live data from your preparation APIs
                            </p>
                        </div>

                        <Link
                            to="/profile"
                            style={styles.profileLink}
                        >
                            View Profile →
                        </Link>
                    </div>

                    <div style={styles.overviewGrid}>
                        {stats.map((item) => (
                            <Link
                                key={`overview-${item.title}`}
                                to={item.path}
                                style={styles.overviewCard}
                            >
                                <div style={styles.overviewTop}>
                                    <span style={styles.overviewIcon}>
                                        {item.icon}
                                    </span>

                                    <span style={styles.overviewArrow}>
                                        →
                                    </span>
                                </div>

                                <div style={styles.overviewTitle}>
                                    {item.title}
                                </div>

                                <div style={styles.overviewValue}>
                                    {loading
                                        ? "—"
                                        : item.value}
                                </div>

                                <div style={styles.overviewDescription}>
                                    {item.description}
                                </div>
                            </Link>
                        ))}
                    </div>
                </section>

                {/* =================================================
                    FOOTER
                ================================================= */}

                <footer style={styles.footer}>
                    © 2026 Muni48 · UPSC & BPSC Preparation Platform
                </footer>
            </main>
        </div>
    );
}

// ============================================================
// STYLES
// ============================================================

const styles = {
    app: {
        minHeight: "100vh",
        display: "flex",
        background: "#f8fafc",
        color: "#0f172a",
        fontFamily:
            "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    },

    // --------------------------------------------------------
    // SIDEBAR
    // --------------------------------------------------------

    sidebar: {
        width: "250px",
        minHeight: "100vh",
        position: "fixed",
        left: 0,
        top: 0,
        bottom: 0,
        display: "flex",
        flexDirection: "column",
        boxSizing: "border-box",
        padding: "24px 16px",
        background: "#ffffff",
        borderRight: "1px solid #e2e8f0",
        zIndex: 20,
    },

    brand: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "0 10px",
        marginBottom: "30px",
    },

    logo: {
        width: "42px",
        height: "42px",
        borderRadius: "12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",
        color: "#ffffff",
        fontSize: "21px",
        fontWeight: "800",
        boxShadow:
            "0 7px 18px rgba(37, 99, 235, 0.20)",
    },

    brandName: {
        fontSize: "18px",
        fontWeight: "800",
        color: "#111827",
        lineHeight: 1.2,
    },

    brandSubtitle: {
        marginTop: "3px",
        fontSize: "11px",
        color: "#64748b",
    },

    nav: {
        display: "flex",
        flexDirection: "column",
        gap: "5px",
    },

    navItem: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "11px 13px",
        borderRadius: "10px",
        color: "#475569",
        textDecoration: "none",
        fontSize: "14px",
        fontWeight: "600",
        transition: "all 0.2s ease",
    },

    navItemActive: {
        background: "#eff6ff",
        color: "#2563eb",
    },

    proCard: {
        marginTop: "auto",
        padding: "16px",
        borderRadius: "14px",
        background:
            "linear-gradient(135deg, #eff6ff, #eef2ff)",
        border: "1px solid #dbeafe",
    },

    proIcon: {
        fontSize: "20px",
        marginBottom: "8px",
    },

    proTitle: {
        fontSize: "14px",
        fontWeight: "800",
        color: "#1e3a8a",
    },

    proText: {
        marginTop: "4px",
        fontSize: "11px",
        color: "#64748b",
        lineHeight: 1.4,
    },

    proButton: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginTop: "12px",
        padding: "9px 11px",
        borderRadius: "8px",
        background: "#2563eb",
        color: "#ffffff",
        textDecoration: "none",
        fontSize: "12px",
        fontWeight: "700",
    },

    logoutButton: {
        marginTop: "14px",
        display: "flex",
        alignItems: "center",
        gap: "11px",
        width: "100%",
        padding: "11px 13px",
        border: "none",
        borderRadius: "10px",
        background: "transparent",
        color: "#64748b",
        fontSize: "14px",
        fontWeight: "600",
        cursor: "pointer",
        textAlign: "left",
    },

    // --------------------------------------------------------
    // MAIN
    // --------------------------------------------------------

    main: {
        width: "calc(100% - 250px)",
        marginLeft: "250px",
        boxSizing: "border-box",
        padding: "32px 40px 24px",
    },

    topbar: {
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "20px",
        marginBottom: "28px",
    },

    smallHeading: {
        fontSize: "11px",
        fontWeight: "800",
        letterSpacing: "1.2px",
        color: "#64748b",
        marginBottom: "7px",
    },

    pageTitle: {
        margin: 0,
        fontSize: "30px",
        lineHeight: 1.2,
        fontWeight: "800",
        color: "#111827",
    },

    pageSubtitle: {
        margin: "8px 0 0",
        fontSize: "14px",
        color: "#64748b",
    },

    topbarRight: {
        display: "flex",
        alignItems: "center",
        gap: "10px",
    },

    statusBadge: {
        display: "flex",
        alignItems: "center",
        gap: "7px",
        padding: "8px 11px",
        borderRadius: "999px",
        fontSize: "12px",
        fontWeight: "700",
        whiteSpace: "nowrap",
    },

    statusOnline: {
        color: "#15803d",
        background: "#f0fdf4",
        border: "1px solid #bbf7d0",
    },

    statusOffline: {
        color: "#b91c1c",
        background: "#fef2f2",
        border: "1px solid #fecaca",
    },

    statusDot: {
        width: "7px",
        height: "7px",
        borderRadius: "50%",
        background: "currentColor",
    },

    iconButton: {
        width: "38px",
        height: "38px",
        borderRadius: "10px",
        border: "1px solid #e2e8f0",
        background: "#ffffff",
        color: "#475569",
        cursor: "pointer",
        fontSize: "16px",
    },

    avatar: {
        width: "38px",
        height: "38px",
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",
        color: "#ffffff",
        fontSize: "14px",
        fontWeight: "800",
    },

    // --------------------------------------------------------
    // ERROR
    // --------------------------------------------------------

    errorBox: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "15px",
        padding: "14px 16px",
        marginBottom: "22px",
        borderRadius: "12px",
        background: "#fff7ed",
        border: "1px solid #fed7aa",
        color: "#9a3412",
        fontSize: "13px",
    },

    errorText: {
        marginTop: "3px",
        color: "#c2410c",
    },

    retryButton: {
        border: "1px solid #fdba74",
        background: "#ffffff",
        color: "#c2410c",
        borderRadius: "8px",
        padding: "8px 13px",
        cursor: "pointer",
        fontWeight: "700",
        whiteSpace: "nowrap",
    },

    // --------------------------------------------------------
    // STATS
    // --------------------------------------------------------

    statsGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
        gap: "16px",
        marginBottom: "34px",
    },

    statCard: {
        display: "flex",
        alignItems: "center",
        gap: "14px",
        padding: "18px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "14px",
        textDecoration: "none",
        color: "inherit",
        boxShadow:
            "0 4px 15px rgba(15, 23, 42, 0.03)",
    },

    statIcon: {
        width: "46px",
        height: "46px",
        minWidth: "46px",
        borderRadius: "12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f8fafc",
        fontSize: "21px",
    },

    statContent: {
        minWidth: 0,
    },

    statTitle: {
        fontSize: "13px",
        fontWeight: "700",
        color: "#475569",
    },

    statValue: {
        marginTop: "3px",
        fontSize: "24px",
        lineHeight: 1,
        fontWeight: "800",
        color: "#111827",
    },

    statDescription: {
        marginTop: "4px",
        fontSize: "11px",
        color: "#94a3b8",
    },

    // --------------------------------------------------------
    // SECTION
    // --------------------------------------------------------

    section: {
        marginBottom: "34px",
    },

    sectionHeader: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "15px",
    },

    sectionTitle: {
        margin: 0,
        fontSize: "19px",
        fontWeight: "800",
        color: "#111827",
    },

    sectionSubtitle: {
        margin: "5px 0 0",
        fontSize: "13px",
        color: "#64748b",
    },

    rocket: {
        fontSize: "22px",
    },

    quickGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
        gap: "15px",
    },

    quickCard: {
        position: "relative",
        display: "block",
        padding: "20px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "14px",
        color: "inherit",
        textDecoration: "none",
        minHeight: "145px",
        boxSizing: "border-box",
    },

    quickIcon: {
        fontSize: "23px",
        marginBottom: "14px",
    },

    quickContent: {
        paddingRight: "20px",
    },

    quickTitle: {
        margin: 0,
        fontSize: "15px",
        fontWeight: "800",
        color: "#111827",
    },

    quickDescription: {
        margin: "6px 0 0",
        fontSize: "12px",
        lineHeight: 1.5,
        color: "#64748b",
    },

    arrow: {
        position: "absolute",
        right: "17px",
        bottom: "16px",
        color: "#2563eb",
        fontSize: "17px",
        fontWeight: "700",
    },

    // --------------------------------------------------------
    // PLAN
    // --------------------------------------------------------

    planSection: {
        marginBottom: "34px",
        padding: "22px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "16px",
    },

    planHeader: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "20px",
        marginBottom: "18px",
    },

    progressBox: {
        width: "150px",
    },

    progressValue: {
        textAlign: "right",
        fontSize: "13px",
        fontWeight: "800",
        color: "#2563eb",
        marginBottom: "6px",
    },

    progressBar: {
        width: "100%",
        height: "7px",
        borderRadius: "999px",
        background: "#e2e8f0",
        overflow: "hidden",
    },

    progressFill: {
        height: "100%",
        borderRadius: "999px",
        background:
            "linear-gradient(90deg, #2563eb, #4f46e5)",
        transition: "width 0.3s ease",
    },

    planList: {
        display: "grid",
        gridTemplateColumns:
            "repeat(2, minmax(0, 1fr))",
        gap: "10px",
    },

    planItem: {
        display: "flex",
        alignItems: "center",
        gap: "13px",
        padding: "13px",
        borderRadius: "11px",
        background: "#f8fafc",
        border: "1px solid #f1f5f9",
        textDecoration: "none",
        color: "inherit",
    },

    planIcon: {
        width: "38px",
        height: "38px",
        minWidth: "38px",
        borderRadius: "9px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#ffffff",
        fontSize: "18px",
    },

    planContent: {
        flex: 1,
        minWidth: 0,
    },

    planTitle: {
        fontSize: "13px",
        fontWeight: "800",
        color: "#1e293b",
    },

    planDescription: {
        marginTop: "3px",
        fontSize: "11px",
        color: "#64748b",
    },

    planArrow: {
        color: "#2563eb",
        fontSize: "16px",
        fontWeight: "700",
    },

    // --------------------------------------------------------
    // OVERVIEW
    // --------------------------------------------------------

    profileLink: {
        color: "#2563eb",
        textDecoration: "none",
        fontSize: "13px",
        fontWeight: "700",
    },

    overviewGrid: {
        display: "grid",
        gridTemplateColumns:
            "repeat(4, minmax(0, 1fr))",
        gap: "15px",
    },

    overviewCard: {
        display: "block",
        padding: "18px",
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "14px",
        textDecoration: "none",
        color: "inherit",
    },

    overviewTop: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "16px",
    },

    overviewIcon: {
        fontSize: "21px",
    },

    overviewArrow: {
        color: "#2563eb",
        fontWeight: "700",
    },

    overviewTitle: {
        fontSize: "13px",
        fontWeight: "700",
        color: "#475569",
    },

    overviewValue: {
        marginTop: "4px",
        fontSize: "25px",
        fontWeight: "800",
        color: "#111827",
    },

    overviewDescription: {
        marginTop: "2px",
        fontSize: "11px",
        color: "#94a3b8",
    },

    // --------------------------------------------------------
    // FOOTER
    // --------------------------------------------------------

    footer: {
        paddingTop: "10px",
        paddingBottom: "10px",
        textAlign: "center",
        color: "#94a3b8",
        fontSize: "11px",
    },
};

export default Dashboard;