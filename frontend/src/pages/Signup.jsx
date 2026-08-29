import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";

const API_URL = "https://upsc-bpsc.onrender.com";

function Signup() {
    const navigate = useNavigate();

    const [form, setForm] = useState({
        name: "",
        email: "",
        password: "",
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const handleChange = (e) => {
        setForm((prev) => ({
            ...prev,
            [e.target.name]: e.target.value,
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        setError("");
        setSuccess("");

        const name = form.name.trim();
        const email = form.email.trim().toLowerCase();
        const password = form.password;

        if (!name) {
            setError("Please enter your name.");
            return;
        }

        if (!email) {
            setError("Please enter your email.");
            return;
        }

        if (password.length < 6) {
            setError("Password must be at least 6 characters.");
            return;
        }

        setLoading(true);

        try {
            console.log("Signup API:", `${API_URL}/auth/signup`);

            const response = await axios.post(
                `${API_URL}/auth/signup`,
                {
                    name,
                    email,
                    password,
                },
                {
                    headers: {
                        "Content-Type": "application/json",
                        Accept: "application/json",
                    },
                    timeout: 20000,
                }
            );

            console.log("Signup response:", response.data);

            setSuccess(
                response.data?.message ||
                "Registration successful!"
            );

            setForm({
                name: "",
                email: "",
                password: "",
            });

            setTimeout(() => {
                navigate("/login", { replace: true });
            }, 1000);

        } catch (err) {
            console.error("Signup error:", err);

            if (err.response) {
                const status = err.response.status;
                const detail = err.response.data?.detail;

                if (Array.isArray(detail)) {
                    setError(
                        detail
                            .map((item) => item.msg || "Invalid input")
                            .join(", ")
                    );
                } else if (typeof detail === "string") {
                    setError(detail);
                } else {
                    setError(
                        err.response.data?.message ||
                        `Registration failed (${status}).`
                    );
                }

            } else if (err.request) {
                setError(
                    "Server से connection नहीं हो रहा। Please check your internet connection and try again."
                );

            } else {
                setError(
                    err.message || "Registration failed."
                );
            }

        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "#f5f7fb",
                padding: "20px",
            }}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: "420px",
                    background: "#ffffff",
                    padding: "32px",
                    borderRadius: "14px",
                    boxShadow: "0 10px 30px rgba(0,0,0,0.08)",
                }}
            >
                <h1
                    style={{
                        textAlign: "center",
                        marginBottom: "8px",
                    }}
                >
                    Muni48
                </h1>

                <p
                    style={{
                        textAlign: "center",
                        color: "#666",
                        marginBottom: "25px",
                    }}
                >
                    UPSC & BPSC Preparation Platform
                </p>

                <h2
                    style={{
                        textAlign: "center",
                        marginBottom: "20px",
                    }}
                >
                    Create Account
                </h2>

                {error && (
                    <div
                        style={{
                            background: "#fee2e2",
                            color: "#b91c1c",
                            padding: "12px",
                            borderRadius: "8px",
                            marginBottom: "15px",
                            fontSize: "14px",
                        }}
                    >
                        {error}
                    </div>
                )}

                {success && (
                    <div
                        style={{
                            background: "#dcfce7",
                            color: "#166534",
                            padding: "12px",
                            borderRadius: "8px",
                            marginBottom: "15px",
                            fontSize: "14px",
                        }}
                    >
                        {success}
                    </div>
                )}

                <form onSubmit={handleSubmit}>

                    <label>Name</label>

                    <input
                        type="text"
                        name="name"
                        value={form.name}
                        onChange={handleChange}
                        placeholder="Enter your name"
                        autoComplete="name"
                        required
                        style={inputStyle}
                    />

                    <label>Email</label>

                    <input
                        type="email"
                        name="email"
                        value={form.email}
                        onChange={handleChange}
                        placeholder="Enter your email"
                        autoComplete="email"
                        required
                        style={inputStyle}
                    />

                    <label>Password</label>

                    <input
                        type="password"
                        name="password"
                        value={form.password}
                        onChange={handleChange}
                        placeholder="Create password"
                        autoComplete="new-password"
                        required
                        minLength={6}
                        style={inputStyle}
                    />

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: "100%",
                            marginTop: "20px",
                            padding: "13px",
                            border: "none",
                            borderRadius: "8px",
                            background: loading
                                ? "#9ca3af"
                                : "#2563eb",
                            color: "#ffffff",
                            fontSize: "16px",
                            fontWeight: "600",
                            cursor: loading
                                ? "not-allowed"
                                : "pointer",
                        }}
                    >
                        {loading
                            ? "Creating Account..."
                            : "Create Account"}
                    </button>

                </form>

                <p
                    style={{
                        textAlign: "center",
                        marginTop: "20px",
                    }}
                >
                    Already have an account?{" "}

                    <Link
                        to="/login"
                        style={{
                            color: "#2563eb",
                            fontWeight: "600",
                            textDecoration: "none",
                        }}
                    >
                        Login
                    </Link>
                </p>

            </div>
        </div>
    );
}

const inputStyle = {
    width: "100%",
    boxSizing: "border-box",
    padding: "12px",
    marginTop: "6px",
    marginBottom: "15px",
    border: "1px solid #d1d5db",
    borderRadius: "8px",
    fontSize: "15px",
    outline: "none",
};

export default Signup;

