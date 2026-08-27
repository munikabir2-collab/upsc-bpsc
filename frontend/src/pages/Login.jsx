import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";

const API_URL =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Login() {
    const navigate = useNavigate();
    const location = useLocation();

    const [form, setForm] = useState({
        email: "",
        password: "",
    });

    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    // =====================================================
    // HANDLE INPUT
    // =====================================================

    const handleChange = (e) => {
        const { name, value } = e.target;

        setForm((prev) => ({
            ...prev,
            [name]: value,
        }));

        if (error) {
            setError("");
        }
    };

    // =====================================================
    // VALIDATE FORM
    // =====================================================

    const validateForm = () => {
        const email = form.email.trim();
        const password = form.password;

        if (!email) {
            setError("Please enter your email address.");
            return false;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailRegex.test(email)) {
            setError("Please enter a valid email address.");
            return false;
        }

        if (!password) {
            setError("Please enter your password.");
            return false;
        }

        if (password.length < 6) {
            setError("Password must be at least 6 characters.");
            return false;
        }

        return true;
    };

    // =====================================================
    // SAVE AUTH DATA
    // =====================================================

    const saveAuthData = (data) => {
        console.log("AUTH RESPONSE:", data);

        const token =
            data?.access_token ||
            data?.accessToken ||
            data?.token;

        if (!token) {
            throw new Error(
                "Login successful, but authentication token was not returned by the server."
            );
        }

        const storage = rememberMe
            ? localStorage
            : sessionStorage;

        const otherStorage = rememberMe
            ? sessionStorage
            : localStorage;

        // Clear old authentication data first
        otherStorage.removeItem("token");
        otherStorage.removeItem("user");

        // Save token
        storage.setItem("token", token);

        // Save user if backend returns it
        if (data?.user) {
            storage.setItem(
                "user",
                JSON.stringify(data.user)
            );
        }

        // Also save auth flag
        storage.setItem("isAuthenticated", "true");

        console.log("TOKEN SAVED:", token);

        return token;
    };

    // =====================================================
    // LOGIN
    // =====================================================

    const handleSubmit = async (e) => {
        e.preventDefault();

        setError("");

        if (!validateForm()) {
            return;
        }

        setLoading(true);

        try {
            const response = await axios.post(
                `${API_URL}/auth/login`,
                {
                    email: form.email.trim(),
                    password: form.password,
                },
                {
                    timeout: 10000,
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                }
            );

            console.log(
                "Login successful:",
                response.data
            );

            // Save token
            saveAuthData(response.data);

            // Determine where user should go
            const from =
                location.state?.from;

            let redirectTo = "/dashboard";

            if (typeof from === "string" && from) {
                redirectTo = from;
            }

            console.log(
                "Redirecting to:",
                redirectTo
            );

            navigate(redirectTo, {
                replace: true,
            });
        } catch (err) {
            console.error(
                "Login error:",
                err
            );

            // =============================================
            // BACKEND RESPONSE
            // =============================================

            if (err.response) {
                const status =
                    err.response.status;

                const data =
                    err.response.data;

                const detail = data?.detail;

                // FastAPI validation error
                if (Array.isArray(detail)) {
                    const messages = detail
                        .map((item) => item?.msg)
                        .filter(Boolean);

                    setError(
                        messages.length
                            ? messages.join(", ")
                            : "Please check your input."
                    );

                    return;
                }

                // Normal FastAPI error
                if (
                    typeof detail === "string"
                ) {
                    setError(detail);
                    return;
                }

                // Custom API message
                if (
                    typeof data?.message === "string"
                ) {
                    setError(data.message);
                    return;
                }

                // Status specific
                if (status === 401) {
                    setError(
                        "Invalid email or password."
                    );
                    return;
                }

                if (status === 403) {
                    setError(
                        "Your account does not have permission to login."
                    );
                    return;
                }

                if (status === 404) {
                    setError(
                        "Login service was not found. Please check the backend API."
                    );
                    return;
                }

                if (status >= 500) {
                    setError(
                        "Server error. Please try again later."
                    );
                    return;
                }

                setError(
                    `Login failed (${status}).`
                );

                return;
            }

            // =============================================
            // NO RESPONSE
            // =============================================

            if (err.request) {
                if (
                    err.code ===
                    "ECONNABORTED"
                ) {
                    setError(
                        "Server request timed out. Please try again."
                    );
                } else {
                    setError(
                        "Unable to connect to the Muni48 server. Make sure the backend is running."
                    );
                }

                return;
            }

            // =============================================
            // CLIENT ERROR
            // =============================================

            setError(
                err.message ||
                    "Something went wrong. Please try again."
            );
        } finally {
            setLoading(false);
        }
    };

    // =====================================================
    // UI
    // =====================================================

    return (
        <main style={styles.page}>
            <section
                style={styles.card}
                aria-labelledby="login-title"
            >
                {/* BRAND */}

                <div style={styles.brand}>
                    <div style={styles.logo}>
                        M
                    </div>

                    <div>
                        <h1 style={styles.brandName}>
                            Muni48
                        </h1>

                        <p style={styles.brandTagline}>
                            Learn. Practice. Succeed.
                        </p>
                    </div>
                </div>

                {/* HEADER */}

                <div style={styles.header}>
                    <h2
                        id="login-title"
                        style={styles.title}
                    >
                        Welcome back
                    </h2>

                    <p style={styles.subtitle}>
                        Sign in to continue your
                        UPSC & BPSC preparation.
                    </p>
                </div>

                {/* ERROR */}

                {error && (
                    <div
                        role="alert"
                        style={styles.errorBox}
                    >
                        <span
                            style={styles.errorIcon}
                            aria-hidden="true"
                        >
                            !
                        </span>

                        <span>{error}</span>
                    </div>
                )}

                {/* FORM */}

                <form
                    onSubmit={handleSubmit}
                    noValidate
                >
                    {/* EMAIL */}

                    <div style={styles.field}>
                        <label
                            htmlFor="email"
                            style={styles.label}
                        >
                            Email address
                        </label>

                        <input
                            id="email"
                            type="email"
                            name="email"
                            value={form.email}
                            onChange={handleChange}
                            placeholder="you@example.com"
                            autoComplete="email"
                            disabled={loading}
                            required
                            style={styles.input}
                        />
                    </div>

                    {/* PASSWORD */}

                    <div style={styles.field}>
                        <div
                            style={
                                styles.passwordHeader
                            }
                        >
                            <label
                                htmlFor="password"
                                style={styles.label}
                            >
                                Password
                            </label>

                            <Link
                                to="/forgot-password"
                                style={
                                    styles.forgotLink
                                }
                            >
                                Forgot password?
                            </Link>
                        </div>

                        <div
                            style={
                                styles.passwordWrapper
                            }
                        >
                            <input
                                id="password"
                                type={
                                    showPassword
                                        ? "text"
                                        : "password"
                                }
                                name="password"
                                value={form.password}
                                onChange={handleChange}
                                placeholder="Enter your password"
                                autoComplete="current-password"
                                disabled={loading}
                                required
                                style={{
                                    ...styles.input,
                                    paddingRight: "60px",
                                }}
                            />

                            <button
                                type="button"
                                onClick={() =>
                                    setShowPassword(
                                        (prev) =>
                                            !prev
                                    )
                                }
                                disabled={loading}
                                style={
                                    styles.passwordToggle
                                }
                                aria-label={
                                    showPassword
                                        ? "Hide password"
                                        : "Show password"
                                }
                            >
                                {showPassword
                                    ? "Hide"
                                    : "Show"}
                            </button>
                        </div>
                    </div>

                    {/* REMEMBER ME */}

                    <label
                        style={
                            styles.rememberContainer
                        }
                    >
                        <input
                            type="checkbox"
                            checked={rememberMe}
                            onChange={(e) =>
                                setRememberMe(
                                    e.target.checked
                                )
                            }
                            disabled={loading}
                        />

                        <span>
                            Remember me
                        </span>
                    </label>

                    {/* SUBMIT */}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            ...styles.submitButton,
                            ...(loading
                                ? styles.submitDisabled
                                : {}),
                        }}
                    >
                        {loading ? (
                            <>
                                <span
                                    style={
                                        styles.spinner
                                    }
                                />
                                Signing in...
                            </>
                        ) : (
                            "Sign in"
                        )}
                    </button>
                </form>

                {/* SIGNUP */}

                <div
                    style={
                        styles.signupContainer
                    }
                >
                    <span>
                        Don't have an account?
                    </span>

                    <Link
                        to="/signup"
                        style={
                            styles.signupLink
                        }
                    >
                        Create account
                    </Link>
                </div>

                {/* FOOTER */}

                <p style={styles.footer}>
                    By continuing, you agree to
                    Muni48's Terms of Service and
                    Privacy Policy.
                </p>
            </section>
        </main>
    );
}

// ======================================================
// STYLES
// ======================================================

const styles = {
    page: {
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
            "linear-gradient(135deg, #eff6ff 0%, #f8fafc 50%, #eef2ff 100%)",
        padding: "24px",
        boxSizing: "border-box",
    },

    card: {
        width: "100%",
        maxWidth: "440px",
        background: "#ffffff",
        borderRadius: "18px",
        padding: "36px",
        boxSizing: "border-box",
        boxShadow:
            "0 20px 60px rgba(15, 23, 42, 0.10)",
        border:
            "1px solid rgba(226, 232, 240, 0.8)",
    },

    brand: {
        display: "flex",
        alignItems: "center",
        gap: "12px",
        marginBottom: "32px",
    },

    logo: {
        width: "44px",
        height: "44px",
        borderRadius: "12px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",
        color: "#ffffff",
        fontSize: "22px",
        fontWeight: "800",
    },

    brandName: {
        margin: 0,
        fontSize: "21px",
        fontWeight: "800",
        color: "#111827",
    },

    brandTagline: {
        margin: "2px 0 0",
        fontSize: "12px",
        color: "#64748b",
    },

    header: {
        marginBottom: "24px",
    },

    title: {
        margin: 0,
        fontSize: "28px",
        fontWeight: "750",
        color: "#111827",
    },

    subtitle: {
        marginTop: "8px",
        marginBottom: 0,
        color: "#64748b",
        fontSize: "14px",
        lineHeight: "1.6",
    },

    errorBox: {
        display: "flex",
        alignItems: "center",
        gap: "10px",
        background: "#fef2f2",
        color: "#b91c1c",
        border: "1px solid #fecaca",
        padding: "12px 14px",
        borderRadius: "10px",
        marginBottom: "20px",
        fontSize: "14px",
        lineHeight: "1.4",
    },

    errorIcon: {
        width: "20px",
        height: "20px",
        minWidth: "20px",
        borderRadius: "50%",
        background: "#dc2626",
        color: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: "700",
        fontSize: "12px",
    },

    field: {
        marginBottom: "18px",
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
        height: "48px",
        boxSizing: "border-box",
        padding: "0 14px",
        border: "1px solid #cbd5e1",
        borderRadius: "10px",
        outline: "none",
        fontSize: "15px",
        color: "#0f172a",
        background: "#ffffff",
    },

    passwordHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    },

    passwordWrapper: {
        position: "relative",
    },

    passwordToggle: {
        position: "absolute",
        right: "10px",
        top: "50%",
        transform: "translateY(-50%)",
        border: "none",
        background: "transparent",
        color: "#2563eb",
        fontSize: "13px",
        fontWeight: "600",
        cursor: "pointer",
    },

    forgotLink: {
        color: "#2563eb",
        fontSize: "13px",
        fontWeight: "600",
        textDecoration: "none",
    },

    rememberContainer: {
        display: "flex",
        alignItems: "center",
        gap: "8px",
        color: "#475569",
        fontSize: "14px",
        marginBottom: "20px",
        cursor: "pointer",
    },

    submitButton: {
        width: "100%",
        height: "50px",
        border: "none",
        borderRadius: "10px",
        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",
        color: "#ffffff",
        fontSize: "15px",
        fontWeight: "700",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        boxShadow:
            "0 8px 20px rgba(37, 99, 235, 0.20)",
    },

    submitDisabled: {
        opacity: 0.7,
        cursor: "not-allowed",
    },

    spinner: {
        width: "16px",
        height: "16px",
        borderRadius: "50%",
        border:
            "2px solid rgba(255,255,255,0.4)",
        borderTopColor: "#ffffff",
        display: "inline-block",
    },

    signupContainer: {
        display: "flex",
        justifyContent: "center",
        gap: "6px",
        marginTop: "24px",
        fontSize: "14px",
        color: "#64748b",
    },

    signupLink: {
        color: "#2563eb",
        fontWeight: "700",
        textDecoration: "none",
    },

    footer: {
        textAlign: "center",
        color: "#94a3b8",
        fontSize: "11px",
        lineHeight: "1.5",
        marginTop: "24px",
        marginBottom: 0,
    },
};

export default Login;