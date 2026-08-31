import React, {
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";

/*
|--------------------------------------------------------------------------
| NEWS.JSX
|--------------------------------------------------------------------------
| Features
|--------------------------------------------------------------------------
| 1. News search
| 2. UPSC / BPSC
| 3. Hindi / English
| 4. Category filter
| 5. Bihar only
| 6. 402 => ₹1 Razorpay popup
| 7. Payment verification
| 8. Automatic News reload after payment
| 9. MCQ loading
| 10. 402 on MCQ => payment => automatic retry
|--------------------------------------------------------------------------
*/

const API_URL =
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000";

const RAZORPAY_SCRIPT =
    "https://checkout.razorpay.com/v1/checkout.js";

const PAGE_SIZE = 20;

const EXAMS = [
    "UPSC",
    "BPSC",
];

const LANGUAGES = [
    {
        value: "en",
        label: "English",
    },
    {
        value: "hi",
        label: "हिंदी",
    },
];

const CATEGORIES = [
    "General",
    "Economy",
    "Polity & Governance",
    "International Relations",
    "Environment",
    "Science & Technology",
    "Security",
    "Agriculture",
    "Education",
    "Health",
    "Social Issues",
    "History & Culture",
    "Geography",
    "Disaster Management",
    "Ethics",
];

/*
|--------------------------------------------------------------------------
| Helpers
|--------------------------------------------------------------------------
*/

function getToken() {
    return (
        localStorage.getItem("access_token") ||
        localStorage.getItem("token") ||
        localStorage.getItem("jwt") ||
        ""
    );
}

function getUser() {
    try {
        return JSON.parse(
            localStorage.getItem("user") || "null"
        );
    } catch {
        return null;
    }
}

function extract402Detail(data) {
    if (!data) {
        return null;
    }

    if (typeof data.detail === "object") {
        return data.detail;
    }

    if (
        typeof data.detail === "string"
    ) {
        return {
            message: data.detail,
        };
    }

    return null;
}

function isPaymentRequired(status, data) {
    if (status !== 402) {
        return false;
    }

    const detail =
        extract402Detail(data);

    if (!detail) {
        return true;
    }

    return (
        detail.code ===
            "NEWS_PAYMENT_REQUIRED" ||
        detail.payment_endpoint ||
        detail.amount === 1
    );
}

/*
|--------------------------------------------------------------------------
| Load Razorpay SDK
|--------------------------------------------------------------------------
*/

function loadRazorpayScript() {
    return new Promise(
        (resolve, reject) => {
            if (
                window.Razorpay
            ) {
                resolve(true);
                return;
            }

            const existing =
                document.querySelector(
                    `script[src="${RAZORPAY_SCRIPT}"]`
                );

            if (existing) {
                existing.addEventListener(
                    "load",
                    () => resolve(true)
                );

                existing.addEventListener(
                    "error",
                    () =>
                        reject(
                            new Error(
                                "Razorpay SDK load failed."
                            )
                        )
                );

                return;
            }

            const script =
                document.createElement(
                    "script"
                );

            script.src =
                RAZORPAY_SCRIPT;

            script.async = true;

            script.onload = () =>
                resolve(true);

            script.onerror = () =>
                reject(
                    new Error(
                        "Unable to load Razorpay."
                    )
                );

            document.body.appendChild(
                script
            );
        }
    );
}

/*
|--------------------------------------------------------------------------
| Main Component
|--------------------------------------------------------------------------
*/

export default function News() {
    const [exam, setExam] =
        useState("UPSC");

    const [language, setLanguage] =
        useState("en");

    const [category, setCategory] =
        useState("");

    const [biharOnly, setBiharOnly] =
        useState(false);

    const [query, setQuery] =
        useState("India");

    const [articles, setArticles] =
        useState([]);

    const [loading, setLoading] =
        useState(false);

    const [error, setError] =
        useState("");

    const [page, setPage] =
        useState(1);

    const [total, setTotal] =
        useState(0);

    const [paymentLoading, setPaymentLoading] =
        useState(false);

    const [paymentMessage, setPaymentMessage] =
        useState("");

    const [hasAccess, setHasAccess] =
        useState(false);

    const [selectedArticle, setSelectedArticle] =
        useState(null);

    const [mcqs, setMcqs] =
        useState([]);

    const [mcqLoading, setMcqLoading] =
        useState(false);

    const [mcqError, setMcqError] =
        useState("");

    const [mcqVisible, setMcqVisible] =
        useState(false);

    const paymentInProgress =
        useRef(false);

    const retryAfterPayment =
        useRef(null);

    /*
    |--------------------------------------------------------------------------
    | Auth Headers
    |--------------------------------------------------------------------------
    */

    const getHeaders =
        useCallback(() => {
            const token =
                getToken();

            const headers = {
                "Content-Type":
                    "application/json",
            };

            if (token) {
                headers.Authorization =
                    `Bearer ${token}`;
            }

            return headers;
        }, []);

    /*
    |--------------------------------------------------------------------------
    | Generic API Request
    |--------------------------------------------------------------------------
    */

    const apiRequest =
        useCallback(
            async (
                url,
                options = {}
            ) => {
                const response =
                    await fetch(
                        `${API_URL}${url}`,
                        {
                            ...options,
                            headers: {
                                ...getHeaders(),
                                ...(options.headers ||
                                    {}),
                            },
                        }
                    );

                let data = null;

                try {
                    data =
                        await response.json();
                } catch {
                    data = null;
                }

                return {
                    response,
                    data,
                };
            },
            [getHeaders]
        );

    /*
    |--------------------------------------------------------------------------
    | Create Razorpay Order
    |--------------------------------------------------------------------------
    */

    const createPaymentOrder =
        useCallback(
            async () => {
                const {
                    response,
                    data,
                } =
                    await apiRequest(
                        "/news/payment/create-order",
                        {
                            method: "POST",
                        }
                    );

                if (
                    response.status ===
                    401
                ) {
                    throw new Error(
                        "Please login again."
                    );
                }

                if (!response.ok) {
                    throw new Error(
                        data?.detail ||
                            "Unable to create payment order."
                    );
                }

                return data;
            },
            [apiRequest]
        );

    /*
    |--------------------------------------------------------------------------
    | Verify Payment
    |--------------------------------------------------------------------------
    */

    const verifyPayment =
        useCallback(
            async ({
                razorpay_order_id,
                razorpay_payment_id,
                razorpay_signature,
            }) => {
                const {
                    response,
                    data,
                } =
                    await apiRequest(
                        "/news/payment/verify",
                        {
                            method: "POST",
                            body: JSON.stringify(
                                {
                                    razorpay_order_id,
                                    razorpay_payment_id,
                                    razorpay_signature,
                                }
                            ),
                        }
                    );

                if (!response.ok) {
                    throw new Error(
                        data?.detail ||
                            "Payment verification failed."
                    );
                }

                return data;
            },
            [apiRequest]
        );

    /*
    |--------------------------------------------------------------------------
    | Open Razorpay
    |--------------------------------------------------------------------------
    */

    const openRazorpayPayment =
        useCallback(
            async (
                afterPayment
            ) => {
                if (
                    paymentInProgress.current
                ) {
                    return;
                }

                paymentInProgress.current =
                    true;

                setPaymentLoading(
                    true
                );

                setPaymentMessage(
                    "Payment window preparing..."
                );

                try {
                    /*
                    |--------------------------------------------------------------------------
                    | Load SDK
                    |--------------------------------------------------------------------------
                    */

                    await loadRazorpayScript();

                    if (
                        !window.Razorpay
                    ) {
                        throw new Error(
                            "Razorpay SDK is unavailable."
                        );
                    }

                    /*
                    |--------------------------------------------------------------------------
                    | Create ₹1 Order
                    |--------------------------------------------------------------------------
                    */

                    const order =
                        await createPaymentOrder();

                    /*
                    |--------------------------------------------------------------------------
                    | Already Paid
                    |--------------------------------------------------------------------------
                    */

                    if (
                        order?.has_access ===
                            true ||
                        order?.access_active ===
                            true
                    ) {
                        setHasAccess(
                            true
                        );

                        setPaymentMessage(
                            "Today's News access is already active."
                        );

                        if (
                            typeof afterPayment ===
                            "function"
                        ) {
                            await afterPayment();
                        }

                        return;
                    }

                    const keyId =
                        order?.key_id;

                    const orderId =
                        order?.order_id;

                    const amount =
                        Number(
                            order?.amount ||
                                100
                        );

                    const currency =
                        order?.currency ||
                        "INR";

                    if (!keyId) {
                        throw new Error(
                            "Razorpay Key ID missing from server."
                        );
                    }

                    if (!orderId) {
                        throw new Error(
                            "Razorpay Order ID missing."
                        );
                    }

                    /*
                    |--------------------------------------------------------------------------
                    | Razorpay Options
                    |--------------------------------------------------------------------------
                    */

                    await new Promise(
                        (
                            resolve,
                            reject
                        ) => {
                            let completed =
                                false;

                            const finish =
                                (
                                    callback
                                ) => {
                                    if (
                                        completed
                                    ) {
                                        return;
                                    }

                                    completed =
                                        true;

                                    callback();
                                };

                            const options =
                                {
                                    key: keyId,

                                    amount,

                                    currency,

                                    name:
                                        "Muni48",

                                    description:
                                        "Daily Current Affairs Access",

                                    order_id:
                                        orderId,

                                    prefill:
                                        {
                                            name:
                                                getUser()
                                                    ?.name ||
                                                "",
                                            email:
                                                getUser()
                                                    ?.email ||
                                                "",
                                        },

                                    notes:
                                        {
                                            feature:
                                                "daily_current_affairs",
                                        },

                                    theme:
                                        {
                                            color:
                                                "#2563eb",
                                        },

                                    modal:
                                        {
                                            ondismiss:
                                                () => {
                                                    finish(
                                                        () => {
                                                            setPaymentMessage(
                                                                "Payment cancelled."
                                                            );

                                                            paymentInProgress.current =
                                                                false;

                                                            setPaymentLoading(
                                                                false
                                                            );

                                                            resolve();
                                                        }
                                                    );
                                                },
                                        },

                                    handler:
                                        async (
                                            paymentResponse
                                        ) => {
                                            try {
                                                setPaymentMessage(
                                                    "Payment successful. Verifying..."
                                                );

                                                /*
                                                |--------------------------------------------------------------------------
                                                | Verify on backend
                                                |--------------------------------------------------------------------------
                                                */

                                                const verified =
                                                    await verifyPayment(
                                                        {
                                                            razorpay_order_id:
                                                                paymentResponse.razorpay_order_id,

                                                            razorpay_payment_id:
                                                                paymentResponse.razorpay_payment_id,

                                                            razorpay_signature:
                                                                paymentResponse.razorpay_signature,
                                                        }
                                                    );

                                                if (
                                                    !verified?.has_access &&
                                                    !verified?.access_active
                                                ) {
                                                    throw new Error(
                                                        "Payment verified but access is not active."
                                                    );
                                                }

                                                /*
                                                |--------------------------------------------------------------------------
                                                | Access Active
                                                |--------------------------------------------------------------------------
                                                */

                                                setHasAccess(
                                                    true
                                                );

                                                setPaymentMessage(
                                                    "Payment verified. Loading News..."
                                                );

                                                /*
                                                |--------------------------------------------------------------------------
                                                | Retry Original Request
                                                |--------------------------------------------------------------------------
                                                */

                                                if (
                                                    typeof afterPayment ===
                                                    "function"
                                                ) {
                                                    await afterPayment();
                                                }

                                                finish(
                                                    () =>
                                                        resolve()
                                                );
                                            } catch (
                                                verifyError
                                            ) {
                                                setPaymentMessage(
                                                    verifyError
                                                        ?.message ||
                                                        "Payment verification failed."
                                                );

                                                finish(
                                                    () =>
                                                        reject(
                                                            verifyError
                                                        )
                                                );
                                            }
                                        },
                                };

                            const razorpay =
                                new window.Razorpay(
                                    options
                                );

                            razorpay.on(
                                "payment.failed",
                                (
                                    paymentError
                                ) => {
                                    setPaymentMessage(
                                        paymentError
                                            ?.error
                                            ?.description ||
                                            "Payment failed."
                                    );

                                    finish(
                                        () =>
                                            reject(
                                                new Error(
                                                    paymentError
                                                        ?.error
                                                        ?.description ||
                                                        "Payment failed."
                                                )
                                            )
                                    );
                                }
                            );

                            razorpay.open();
                        }
                    );
                } catch (paymentError) {
                    console.error(
                        "Razorpay error:",
                        paymentError
                    );

                    setPaymentMessage(
                        paymentError
                            ?.message ||
                            "Unable to process payment."
                    );

                    throw paymentError;
                } finally {
                    paymentInProgress.current =
                        false;

                    setPaymentLoading(
                        false
                    );
                }
            },
            [
                createPaymentOrder,
                verifyPayment,
            ]
        );

    /*
    |--------------------------------------------------------------------------
    | Fetch News
    |--------------------------------------------------------------------------
    */

    const fetchNews =
        useCallback(
            async ({
                requestedPage = 1,
                silent = false,
            } = {}) => {
                if (!silent) {
                    setLoading(
                        true
                    );
                }

                setError("");

                const params =
                    new URLSearchParams();

                params.set(
                    "q",
                    query.trim() ||
                        "India"
                );

                params.set(
                    "page",
                    String(
                        requestedPage
                    )
                );

                params.set(
                    "page_size",
                    String(
                        PAGE_SIZE
                    )
                );

                params.set(
                    "language",
                    language
                );

                params.set(
                    "exam",
                    exam
                );

                if (
                    category
                ) {
                    params.set(
                        "category",
                        category
                    );
                }

                if (
                    biharOnly
                ) {
                    params.set(
                        "bihar_only",
                        "true"
                    );
                }

                try {
                    const {
                        response,
                        data,
                    } =
                        await apiRequest(
                            `/news/search?${params.toString()}`
                        );

                    /*
                    |--------------------------------------------------------------------------
                    | 402 PAYMENT REQUIRED
                    |--------------------------------------------------------------------------
                    */

                    if (
                        isPaymentRequired(
                            response.status,
                            data
                        )
                    ) {
                        setLoading(
                            false
                        );

                        setPaymentMessage(
                            "Today's News access requires ₹1 payment."
                        );

                        /*
                        |--------------------------------------------------------------------------
                        | Save request for automatic retry
                        |--------------------------------------------------------------------------
                        */

                        retryAfterPayment.current =
                            async () => {
                                await fetchNews(
                                    {
                                        requestedPage,
                                        silent: false,
                                    }
                                );
                            };

                        await openRazorpayPayment(
                            async () => {
                                const retry =
                                    retryAfterPayment.current;

                                retryAfterPayment.current =
                                    null;

                                if (
                                    retry
                                ) {
                                    await retry();
                                }
                            }
                        );

                        return;
                    }

                    /*
                    |--------------------------------------------------------------------------
                    | Unauthorized
                    |--------------------------------------------------------------------------
                    */

                    if (
                        response.status ===
                        401
                    ) {
                        setError(
                            "Session expired. Please login again."
                        );

                        return;
                    }

                    /*
                    |--------------------------------------------------------------------------
                    | Other errors
                    |--------------------------------------------------------------------------
                    */

                    if (!response.ok) {
                        const detail =
                            data?.detail;

                        let message =
                            "News load failed.";

                        if (
                            typeof detail ===
                            "string"
                        ) {
                            message =
                                detail;
                        } else if (
                            detail?.message
                        ) {
                            message =
                                detail.message;
                        }

                        throw new Error(
                            `Request failed (${response.status}). ${message}`
                        );
                    }

                    /*
                    |--------------------------------------------------------------------------
                    | Success
                    |--------------------------------------------------------------------------
                    */

                    setArticles(
                        Array.isArray(
                            data?.articles
                        )
                            ? data.articles
                            : []
                    );

                    setTotal(
                        Number(
                            data?.total ||
                                data?.filtered_results ||
                                0
                        )
                    );

                    setPage(
                        Number(
                            data?.page ||
                                requestedPage
                        )
                    );

                    setHasAccess(
                        true
                    );

                    setPaymentMessage(
                        ""
                    );
                } catch (fetchError) {
                    console.error(
                        "News fetch error:",
                        fetchError
                    );

                    if (
                        fetchError
                            ?.message
                            ?.includes(
                                "cancelled"
                            )
                    ) {
                        return;
                    }

                    setError(
                        fetchError
                            ?.message ||
                            "News load failed."
                    );
                } finally {
                    if (!silent) {
                        setLoading(
                            false
                        );
                    }
                }
            },
            [
                apiRequest,
                query,
                language,
                exam,
                category,
                biharOnly,
                openRazorpayPayment,
            ]
        );

    /*
    |--------------------------------------------------------------------------
    | Load Article MCQs
    |--------------------------------------------------------------------------
    */

    const loadArticleMCQs =
        useCallback(
            async (
                articleId
            ) => {
                if (!articleId) {
                    return;
                }

                setMcqLoading(
                    true
                );

                setMcqError(
                    ""
                );

                try {
                    const params =
                        new URLSearchParams();

                    params.set(
                        "exam",
                        exam
                    );

                    params.set(
                        "language",
                        language
                    );

                    const {
                        response,
                        data,
                    } =
                        await apiRequest(
                            `/news/${articleId}/mcqs?${params.toString()}`
                        );

                    /*
                    |--------------------------------------------------------------------------
                    | 402 => Payment
                    |--------------------------------------------------------------------------
                    */

                    if (
                        isPaymentRequired(
                            response.status,
                            data
                        )
                    ) {
                        setMcqLoading(
                            false
                        );

                        setPaymentMessage(
                            "Today's News/MCQ access requires ₹1 payment."
                        );

                        await openRazorpayPayment(
                            async () => {
                                await loadArticleMCQs(
                                    articleId
                                );
                            }
                        );

                        return;
                    }

                    if (
                        response.status ===
                        401
                    ) {
                        throw new Error(
                            "Session expired. Please login again."
                        );
                    }

                    if (!response.ok) {
                        throw new Error(
                            data?.detail ||
                                "MCQs could not be loaded."
                        );
                    }

                    setMcqs(
                        Array.isArray(
                            data?.mcqs
                        )
                            ? data.mcqs
                            : []
                    );

                    setMcqVisible(
                        true
                    );
                } catch (mcqFetchError) {
                    console.error(
                        "MCQ error:",
                        mcqFetchError
                    );

                    setMcqError(
                        mcqFetchError
                            ?.message ||
                            "MCQs could not be loaded."
                    );
                } finally {
                    setMcqLoading(
                        false
                    );
                }
            },
            [
                apiRequest,
                exam,
                language,
                openRazorpayPayment,
            ]
        );

    /*
    |--------------------------------------------------------------------------
    | Initial Load
    |--------------------------------------------------------------------------
    */

    useEffect(() => {
        fetchNews({
            requestedPage: 1,
        });
    }, [
        exam,
        language,
        category,
        biharOnly,
    ]);

    /*
    |--------------------------------------------------------------------------
    | Search
    |--------------------------------------------------------------------------
    */

    const handleSearch =
        async (
            event
        ) => {
            event?.preventDefault();

            await fetchNews({
                requestedPage: 1,
            });
        };

    /*
    |--------------------------------------------------------------------------
    | Page Change
    |--------------------------------------------------------------------------
    */

    const changePage =
        async (
            nextPage
        ) => {
            if (
                nextPage < 1
            ) {
                return;
            }

            const totalPages =
                Math.max(
                    1,
                    Math.ceil(
                        total /
                            PAGE_SIZE
                    )
                );

            if (
                nextPage >
                totalPages
            ) {
                return;
            }

            await fetchNews({
                requestedPage:
                    nextPage,
            });

            window.scrollTo({
                top: 0,
                behavior:
                    "smooth",
            });
        };

    /*
    |--------------------------------------------------------------------------
    | Open Article
    |--------------------------------------------------------------------------
    */

    const openArticle =
        (article) => {
            setSelectedArticle(
                article
            );

            setMcqs([]);

            setMcqError("");

            setMcqVisible(
                false
            );
        };

    /*
    |--------------------------------------------------------------------------
    | Close Article
    |--------------------------------------------------------------------------
    */

    const closeArticle =
        () => {
            setSelectedArticle(
                null
            );

            setMcqs([]);

            setMcqVisible(
                false
            );

            setMcqError("");
        };

    /*
    |--------------------------------------------------------------------------
    | Format Date
    |--------------------------------------------------------------------------
    */

    const formatDate =
        (value) => {
            if (!value) {
                return "";
            }

            try {
                return new Date(
                    value
                ).toLocaleDateString(
                    language ===
                        "hi"
                        ? "hi-IN"
                        : "en-IN",
                    {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                    }
                );
            } catch {
                return "";
            }
        };

    /*
    |--------------------------------------------------------------------------
    | UI
    |--------------------------------------------------------------------------
    */

    const totalPages =
        Math.max(
            1,
            Math.ceil(
                total /
                    PAGE_SIZE
            )
        );

    const user =
        getUser();

    return (
        <div
            style={{
                minHeight:
                    "100vh",
                background:
                    "#f8fafc",
                color:
                    "#0f172a",
                paddingBottom:
                    50,
            }}
        >
            {/* ======================================================
                HEADER
            ====================================================== */}

            <header
                style={{
                    background:
                        "#ffffff",
                    borderBottom:
                        "1px solid #e2e8f0",
                    position:
                        "sticky",
                    top: 0,
                    zIndex: 20,
                }}
            >
                <div
                    style={{
                        maxWidth:
                            1200,
                        margin:
                            "0 auto",
                        padding:
                            "16px 20px",
                        display:
                            "flex",
                        alignItems:
                            "center",
                        justifyContent:
                            "space-between",
                        gap: 20,
                    }}
                >
                    <div>
                        <h1
                            style={{
                                margin: 0,
                                fontSize:
                                    24,
                                fontWeight:
                                    800,
                            }}
                        >
                            Muni48
                        </h1>

                        <div
                            style={{
                                fontSize:
                                    13,
                                color:
                                    "#64748b",
                                marginTop:
                                    2,
                            }}
                        >
                            UPSC & BPSC
                            Current
                            Affairs
                        </div>
                    </div>

                    <div
                        style={{
                            display:
                                "flex",
                            alignItems:
                                "center",
                            gap: 10,
                        }}
                    >
                        <span
                            style={{
                                fontSize:
                                    13,
                                color:
                                    "#64748b",
                            }}
                        >
                            {user?.name ||
                                "Student"}
                        </span>

                        {hasAccess && (
                            <span
                                style={{
                                    background:
                                        "#dcfce7",
                                    color:
                                        "#166534",
                                    borderRadius:
                                        999,
                                    padding:
                                        "6px 10px",
                                    fontSize:
                                        12,
                                    fontWeight:
                                        700,
                                }}
                            >
                                ✓ Access
                            </span>
                        )}
                    </div>
                </div>
            </header>

            {/* ======================================================
                MAIN
            ====================================================== */}

            <main
                style={{
                    maxWidth:
                        1200,
                    margin:
                        "0 auto",
                    padding:
                        "24px 20px",
                }}
            >
                {/* ==================================================
                    FILTER CARD
                ================================================== */}

                <section
                    style={{
                        background:
                            "#ffffff",
                        border:
                            "1px solid #e2e8f0",
                        borderRadius:
                            16,
                        padding:
                            20,
                        marginBottom:
                            20,
                    }}
                >
                    <form
                        onSubmit={
                            handleSearch
                        }
                    >
                        <div
                            style={{
                                display:
                                    "grid",
                                gridTemplateColumns:
                                    "repeat(auto-fit,minmax(180px,1fr))",
                                gap: 12,
                            }}
                        >
                            {/* Search */}

                            <div
                                style={{
                                    gridColumn:
                                        "span 2",
                                }}
                            >
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize:
                                            13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    Search
                                </label>

                                <input
                                    value={
                                        query
                                    }
                                    onChange={(
                                        e
                                    ) =>
                                        setQuery(
                                            e
                                                .target
                                                .value
                                        )
                                    }
                                    placeholder="Search current affairs..."
                                    style={{
                                        width:
                                            "100%",
                                        boxSizing:
                                            "border-box",
                                        padding:
                                            "11px 13px",
                                        border:
                                            "1px solid #cbd5e1",
                                        borderRadius:
                                            10,
                                        outline:
                                            "none",
                                    }}
                                />
                            </div>

                            {/* Exam */}

                            <div>
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize:
                                            13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    Exam
                                </label>

                                <select
                                    value={
                                        exam
                                    }
                                    onChange={(
                                        e
                                    ) => {
                                        setExam(
                                            e
                                                .target
                                                .value
                                        );
                                        setPage(
                                            1
                                        );
                                    }}
                                    style={{
                                        width:
                                            "100%",
                                        padding:
                                            "11px 13px",
                                        border:
                                            "1px solid #cbd5e1",
                                        borderRadius:
                                            10,
                                        background:
                                            "#ffffff",
                                    }}
                                >
                                    {EXAMS.map(
                                        (
                                            item
                                        ) => (
                                            <option
                                                key={
                                                    item
                                                }
                                                value={
                                                    item
                                                }
                                            >
                                                {
                                                    item
                                                }
                                            </option>
                                        )
                                    )}
                                </select>
                            </div>

                            {/* Language */}

                            <div>
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize:
                                            13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    Language
                                </label>

                                <select
                                    value={
                                        language
                                    }
                                    onChange={(
                                        e
                                    ) =>
                                        setLanguage(
                                            e
                                                .target
                                                .value
                                        )
                                    }
                                    style={{
                                        width:
                                            "100%",
                                        padding:
                                            "11px 13px",
                                        border:
                                            "1px solid #cbd5e1",
                                        borderRadius:
                                            10,
                                        background:
                                            "#ffffff",
                                    }}
                                >
                                    {LANGUAGES.map(
                                        (
                                            item
                                        ) => (
                                            <option
                                                key={
                                                    item.value
                                                }
                                                value={
                                                    item.value
                                                }
                                            >
                                                {
                                                    item.label
                                                }
                                            </option>
                                        )
                                    )}
                                </select>
                            </div>

                            {/* Category */}

                            <div>
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize:
                                            13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    Category
                                </label>

                                <select
                                    value={
                                        category
                                    }
                                    onChange={(
                                        e
                                    ) =>
                                        setCategory(
                                            e
                                                .target
                                                .value
                                        )
                                    }
                                    style={{
                                        width:
                                            "100%",
                                        padding:
                                            "11px 13px",
                                        border:
                                            "1px solid #cbd5e1",
                                        borderRadius:
                                            10,
                                        background:
                                            "#ffffff",
                                    }}
                                >
                                    <option value="">
                                        All Categories
                                    </option>

                                    {CATEGORIES.map(
                                        (
                                            item
                                        ) => (
                                            <option
                                                key={
                                                    item
                                                }
                                                value={
                                                    item
                                                }
                                            >
                                                {
                                                    item
                                                }
                                            </option>
                                        )
                                    )}
                                </select>
                            </div>

                            {/* Bihar */}

                            <div
                                style={{
                                    display:
                                        "flex",
                                    alignItems:
                                        "flex-end",
                                }}
                            >
                                <label
                                    style={{
                                        display:
                                            "flex",
                                        alignItems:
                                            "center",
                                        gap: 8,
                                        fontSize:
                                            14,
                                        fontWeight:
                                            600,
                                        cursor:
                                            "pointer",
                                        paddingBottom:
                                            10,
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={
                                            biharOnly
                                        }
                                        onChange={(
                                            e
                                        ) =>
                                            setBiharOnly(
                                                e
                                                    .target
                                                    .checked
                                            )
                                        }
                                    />

                                    Bihar Only
                                </label>
                            </div>
                        </div>

                        <div
                            style={{
                                marginTop:
                                    16,
                                display:
                                    "flex",
                                gap: 10,
                            }}
                        >
                            <button
                                type="submit"
                                disabled={
                                    loading ||
                                    paymentLoading
                                }
                                style={{
                                    border:
                                        0,
                                    borderRadius:
                                        10,
                                    padding:
                                        "11px 20px",
                                    background:
                                        "#2563eb",
                                    color:
                                        "#ffffff",
                                    fontWeight:
                                        700,
                                    cursor:
                                        "pointer",
                                    opacity:
                                        loading ||
                                        paymentLoading
                                            ? 0.6
                                            : 1,
                                }}
                            >
                                {loading
                                    ? "Loading..."
                                    : "Search News"}
                            </button>

                            <button
                                type="button"
                                onClick={() => {
                                    setQuery(
                                        "India"
                                    );
                                    setCategory(
                                        ""
                                    );
                                    setBiharOnly(
                                        false
                                    );
                                }}
                                style={{
                                    border:
                                        "1px solid #cbd5e1",
                                    borderRadius:
                                        10,
                                    padding:
                                        "11px 20px",
                                    background:
                                        "#ffffff",
                                    cursor:
                                        "pointer",
                                    fontWeight:
                                        600,
                                }}
                            >
                                Reset
                            </button>
                        </div>
                    </form>
                </section>

                {/* ==================================================
                    PAYMENT STATUS
                ================================================== */}

                {paymentMessage && (
                    <div
                        style={{
                            background:
                                "#eff6ff",
                            border:
                                "1px solid #bfdbfe",
                            color:
                                "#1e40af",
                            borderRadius:
                                12,
                            padding:
                                "12px 15px",
                            marginBottom:
                                18,
                            fontSize:
                                14,
                            fontWeight:
                                600,
                        }}
                    >
                        {paymentLoading
                            ? "💳 "
                            : "ℹ️ "}
                        {
                            paymentMessage
                        }
                    </div>
                )}

                {/* ==================================================
                    ERROR
                ================================================== */}

                {error && (
                    <div
                        style={{
                            background:
                                "#fef2f2",
                            border:
                                "1px solid #fecaca",
                            color:
                                "#991b1b",
                            borderRadius:
                                12,
                            padding:
                                14,
                            marginBottom:
                                18,
                        }}
                    >
                        <strong>
                            News लोड नहीं हो सके
                        </strong>

                        <div
                            style={{
                                marginTop:
                                    5,
                            }}
                        >
                            {error}
                        </div>

                        <button
                            type="button"
                            onClick={() =>
                                fetchNews(
                                    {
                                        requestedPage:
                                            page,
                                    }
                                )
                            }
                            style={{
                                marginTop:
                                    10,
                                border:
                                    0,
                                borderRadius:
                                    8,
                                padding:
                                    "8px 14px",
                                background:
                                    "#991b1b",
                                color:
                                    "#ffffff",
                                cursor:
                                    "pointer",
                            }}
                        >
                            दोबारा प्रयास करें
                        </button>
                    </div>
                )}

                {/* ==================================================
                    LOADING
                ================================================== */}

                {loading && (
                    <div
                        style={{
                            textAlign:
                                "center",
                            padding:
                                40,
                            color:
                                "#64748b",
                        }}
                    >
                        News loading...
                    </div>
                )}

                {/* ==================================================
                    EMPTY
                ================================================== */}

                {!loading &&
                    !error &&
                    articles.length ===
                        0 && (
                        <div
                            style={{
                                background:
                                    "#ffffff",
                                border:
                                    "1px solid #e2e8f0",
                                borderRadius:
                                    16,
                                padding:
                                    40,
                                textAlign:
                                    "center",
                                color:
                                    "#64748b",
                            }}
                        >
                            कोई Current Affairs
                            नहीं मिला।
                        </div>
                    )}

                {/* ==================================================
                    ARTICLE LIST
                ================================================== */}

                {!loading &&
                    articles.length >
                        0 && (
                        <div
                            style={{
                                display:
                                    "grid",
                                gap: 16,
                            }}
                        >
                            {articles.map(
                                (
                                    article,
                                    index
                                ) => (
                                    <article
                                        key={
                                            article.id ||
                                            article.url ||
                                            index
                                        }
                                        style={{
                                            background:
                                                "#ffffff",
                                            border:
                                                "1px solid #e2e8f0",
                                            borderRadius:
                                                16,
                                            overflow:
                                                "hidden",
                                        }}
                                    >
                                        <div
                                            style={{
                                                display:
                                                    "flex",
                                                gap: 18,
                                                padding:
                                                    18,
                                            }}
                                        >
                                            {article.image_url && (
                                                <img
                                                    src={
                                                        article.image_url
                                                    }
                                                    alt=""
                                                    style={{
                                                        width:
                                                            150,
                                                        height:
                                                            100,
                                                        objectFit:
                                                            "cover",
                                                        borderRadius:
                                                            10,
                                                        flexShrink:
                                                            0,
                                                    }}
                                                    onError={(
                                                        e
                                                    ) => {
                                                        e.currentTarget.style.display =
                                                            "none";
                                                    }}
                                                />
                                            )}

                                            <div
                                                style={{
                                                    flex: 1,
                                                    minWidth:
                                                        0,
                                                }}
                                            >
                                                <div
                                                    style={{
                                                        display:
                                                            "flex",
                                                        flexWrap:
                                                            "wrap",
                                                        gap: 7,
                                                        marginBottom:
                                                            8,
                                                    }}
                                                >
                                                    <span
                                                        style={{
                                                            background:
                                                                "#dbeafe",
                                                            color:
                                                                "#1d4ed8",
                                                            borderRadius:
                                                                999,
                                                            padding:
                                                                "4px 9px",
                                                            fontSize:
                                                                11,
                                                            fontWeight:
                                                                700,
                                                        }}
                                                    >
                                                        {
                                                            article.exam
                                                        }
                                                    </span>

                                                    <span
                                                        style={{
                                                            background:
                                                                "#f1f5f9",
                                                            color:
                                                                "#475569",
                                                            borderRadius:
                                                                999,
                                                            padding:
                                                                "4px 9px",
                                                            fontSize:
                                                                11,
                                                            fontWeight:
                                                                700,
                                                        }}
                                                    >
                                                        {
                                                            article.category ||
                                                            "General"
                                                        }
                                                    </span>

                                                    {article.bihar_relevant && (
                                                        <span
                                                            style={{
                                                                background:
                                                                    "#dcfce7",
                                                                color:
                                                                    "#166534",
                                                                borderRadius:
                                                                    999,
                                                                padding:
                                                                    "4px 9px",
                                                                fontSize:
                                                                    11,
                                                                fontWeight:
                                                                    700,
                                                            }}
                                                        >
                                                            Bihar
                                                        </span>
                                                    )}
                                                </div>

                                                <h2
                                                    style={{
                                                        margin:
                                                            "0 0 8px",
                                                        fontSize:
                                                            19,
                                                        lineHeight:
                                                            1.4,
                                                    }}
                                                >
                                                    {
                                                        article.title
                                                    }
                                                </h2>

                                                {article.description && (
                                                    <p
                                                        style={{
                                                            margin:
                                                                "0 0 10px",
                                                            color:
                                                                "#475569",
                                                            lineHeight:
                                                                1.6,
                                                        }}
                                                    >
                                                        {
                                                            article.description
                                                        }
                                                    </p>
                                                )}

                                                <div
                                                    style={{
                                                        display:
                                                            "flex",
                                                        flexWrap:
                                                            "wrap",
                                                        alignItems:
                                                            "center",
                                                        justifyContent:
                                                            "space-between",
                                                        gap: 10,
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontSize:
                                                                12,
                                                            color:
                                                                "#64748b",
                                                        }}
                                                    >
                                                        {article.source &&
                                                            `${article.source} • `}
                                                        {
                                                            formatDate(
                                                                article.published_at
                                                            )
                                                        }
                                                    </div>

                                                    <div
                                                        style={{
                                                            display:
                                                                "flex",
                                                            gap: 8,
                                                        }}
                                                    >
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                openArticle(
                                                                    article
                                                                )
                                                            }
                                                            style={{
                                                                border:
                                                                    "1px solid #2563eb",
                                                                color:
                                                                    "#2563eb",
                                                                background:
                                                                    "#ffffff",
                                                                borderRadius:
                                                                    8,
                                                                padding:
                                                                    "8px 12px",
                                                                cursor:
                                                                    "pointer",
                                                                fontWeight:
                                                                    700,
                                                            }}
                                                        >
                                                            Read & MCQs
                                                        </button>

                                                        {article.url && (
                                                            <a
                                                                href={
                                                                    article.url
                                                                }
                                                                target="_blank"
                                                                rel="noreferrer"
                                                                style={{
                                                                    border:
                                                                        "1px solid #cbd5e1",
                                                                    color:
                                                                        "#334155",
                                                                    background:
                                                                        "#ffffff",
                                                                    borderRadius:
                                                                        8,
                                                                    padding:
                                                                        "8px 12px",
                                                                    textDecoration:
                                                                        "none",
                                                                    fontWeight:
                                                                        600,
                                                                }}
                                                            >
                                                                Source
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </article>
                                )
                            )}
                        </div>
                    )}

                {/* ==================================================
                    PAGINATION
                ================================================== */}

                {!loading &&
                    totalPages >
                        1 && (
                        <div
                            style={{
                                display:
                                    "flex",
                                justifyContent:
                                    "center",
                                alignItems:
                                    "center",
                                gap: 10,
                                marginTop:
                                    24,
                            }}
                        >
                            <button
                                type="button"
                                disabled={
                                    page <=
                                    1
                                }
                                onClick={() =>
                                    changePage(
                                        page -
                                            1
                                    )
                                }
                                style={{
                                    padding:
                                        "9px 14px",
                                    border:
                                        "1px solid #cbd5e1",
                                    borderRadius:
                                        8,
                                    background:
                                        "#ffffff",
                                    cursor:
                                        page <=
                                        1
                                            ? "not-allowed"
                                            : "pointer",
                                }}
                            >
                                ← Previous
                            </button>

                            <span
                                style={{
                                    fontSize:
                                        14,
                                    fontWeight:
                                        700,
                                }}
                            >
                                {page} /{" "}
                                {
                                    totalPages
                                }
                            </span>

                            <button
                                type="button"
                                disabled={
                                    page >=
                                    totalPages
                                }
                                onClick={() =>
                                    changePage(
                                        page +
                                            1
                                    )
                                }
                                style={{
                                    padding:
                                        "9px 14px",
                                    border:
                                        "1px solid #cbd5e1",
                                    borderRadius:
                                        8,
                                    background:
                                        "#ffffff",
                                    cursor:
                                        page >=
                                        totalPages
                                            ? "not-allowed"
                                            : "pointer",
                                }}
                            >
                                Next →
                            </button>
                        </div>
                    )}
            </main>

            {/* ======================================================
                ARTICLE MODAL
            ====================================================== */}

            {selectedArticle && (
                <div
                    style={{
                        position:
                            "fixed",
                        inset: 0,
                        background:
                            "rgba(15,23,42,0.65)",
                        zIndex: 100,
                        display:
                            "flex",
                        alignItems:
                            "center",
                        justifyContent:
                            "center",
                        padding: 20,
                    }}
                    onClick={
                        closeArticle
                    }
                >
                    <div
                        style={{
                            width:
                                "min(900px, 100%)",
                            maxHeight:
                                "90vh",
                            overflowY:
                                "auto",
                            background:
                                "#ffffff",
                            borderRadius:
                                18,
                            padding:
                                24,
                        }}
                        onClick={(
                            e
                        ) =>
                            e.stopPropagation()
                        }
                    >
                        <div
                            style={{
                                display:
                                    "flex",
                                justifyContent:
                                    "space-between",
                                gap: 15,
                                alignItems:
                                    "flex-start",
                            }}
                        >
                            <div>
                                <div
                                    style={{
                                        fontSize:
                                            12,
                                        color:
                                            "#64748b",
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    {
                                        selectedArticle.category
                                    }{" "}
                                    •{" "}
                                    {
                                        selectedArticle.exam
                                    }
                                </div>

                                <h2
                                    style={{
                                        margin:
                                            0,
                                        lineHeight:
                                            1.4,
                                    }}
                                >
                                    {
                                        selectedArticle.title
                                    }
                                </h2>
                            </div>

                            <button
                                type="button"
                                onClick={
                                    closeArticle
                                }
                                style={{
                                    border:
                                        0,
                                    background:
                                        "#f1f5f9",
                                    borderRadius:
                                        8,
                                    width:
                                        36,
                                    height:
                                        36,
                                    cursor:
                                        "pointer",
                                    fontSize:
                                        20,
                                }}
                            >
                                ×
                            </button>
                        </div>

                        {selectedArticle.image_url && (
                            <img
                                src={
                                    selectedArticle.image_url
                                }
                                alt=""
                                style={{
                                    width:
                                        "100%",
                                    maxHeight:
                                        350,
                                    objectFit:
                                        "cover",
                                    borderRadius:
                                        12,
                                    marginTop:
                                        18,
                                }}
                            />
                        )}

                        {selectedArticle.description && (
                            <p
                                style={{
                                    color:
                                        "#475569",
                                    lineHeight:
                                        1.7,
                                    marginTop:
                                        18,
                                }}
                            >
                                {
                                    selectedArticle.description
                                }
                            </p>
                        )}

                        <div
                            style={{
                                display:
                                    "flex",
                                gap: 10,
                                flexWrap:
                                    "wrap",
                                marginTop:
                                    18,
                            }}
                        >
                            <button
                                type="button"
                                disabled={
                                    mcqLoading ||
                                    paymentLoading
                                }
                                onClick={() =>
                                    loadArticleMCQs(
                                        selectedArticle.id
                                    )
                                }
                                style={{
                                    border:
                                        0,
                                    background:
                                        "#2563eb",
                                    color:
                                        "#ffffff",
                                    borderRadius:
                                        9,
                                    padding:
                                        "10px 16px",
                                    cursor:
                                        "pointer",
                                    fontWeight:
                                        700,
                                    opacity:
                                        mcqLoading ||
                                        paymentLoading
                                            ? 0.6
                                            : 1,
                                }}
                            >
                                {mcqLoading
                                    ? "MCQs Loading..."
                                    : "Generate / View MCQs"}
                            </button>

                            {selectedArticle.url && (
                                <a
                                    href={
                                        selectedArticle.url
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                    style={{
                                        border:
                                            "1px solid #cbd5e1",
                                        borderRadius:
                                            9,
                                        padding:
                                            "10px 16px",
                                        textDecoration:
                                            "none",
                                        color:
                                            "#334155",
                                        fontWeight:
                                            700,
                                    }}
                                >
                                    Open Source
                                </a>
                            )}
                        </div>

                        {mcqError && (
                            <div
                                style={{
                                    background:
                                        "#fef2f2",
                                    color:
                                        "#991b1b",
                                    border:
                                        "1px solid #fecaca",
                                    borderRadius:
                                        10,
                                    padding:
                                        12,
                                    marginTop:
                                        16,
                                }}
                            >
                                {
                                    mcqError
                                }
                            </div>
                        )}

                        {mcqVisible && (
                            <section
                                style={{
                                    marginTop:
                                        24,
                                }}
                            >
                                <h3>
                                    MCQ Practice
                                </h3>

                                {mcqs.length ===
                                0 ? (
                                    <div
                                        style={{
                                            background:
                                                "#f8fafc",
                                            borderRadius:
                                                10,
                                            padding:
                                                15,
                                            color:
                                                "#64748b",
                                        }}
                                    >
                                        इस article के
                                        लिए अभी MCQs
                                        उपलब्ध नहीं हैं।
                                    </div>
                                ) : (
                                    <div
                                        style={{
                                            display:
                                                "grid",
                                            gap: 14,
                                        }}
                                    >
                                        {mcqs.map(
                                            (
                                                mcq,
                                                index
                                            ) => (
                                                <div
                                                    key={
                                                        mcq.id ||
                                                        index
                                                    }
                                                    style={{
                                                        border:
                                                            "1px solid #e2e8f0",
                                                        borderRadius:
                                                            12,
                                                        padding:
                                                            16,
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontWeight:
                                                                800,
                                                            marginBottom:
                                                                10,
                                                        }}
                                                    >
                                                        Q
                                                        {index +
                                                            1}
                                                        .{" "}
                                                        {
                                                            mcq.question
                                                        }
                                                    </div>

                                                    {Array.isArray(
                                                        mcq.options
                                                    ) &&
                                                        mcq.options.map(
                                                            (
                                                                option,
                                                                optionIndex
                                                            ) => (
                                                                <div
                                                                    key={
                                                                        optionIndex
                                                                    }
                                                                    style={{
                                                                        padding:
                                                                            "8px 10px",
                                                                        background:
                                                                            "#f8fafc",
                                                                        borderRadius:
                                                                            7,
                                                                        marginBottom:
                                                                            6,
                                                                    }}
                                                                >
                                                                    {
                                                                        String.fromCharCode(
                                                                            65 +
                                                                                optionIndex
                                                                        )
                                                                    }
                                                                    .{" "}
                                                                    {
                                                                        option
                                                                    }
                                                                </div>
                                                            )
                                                        )}

                                                    {mcq.explanation && (
                                                        <div
                                                            style={{
                                                                marginTop:
                                                                    10,
                                                                fontSize:
                                                                    13,
                                                                color:
                                                                    "#475569",
                                                            }}
                                                        >
                                                            <strong>
                                                                Explanation:
                                                            </strong>{" "}
                                                            {
                                                                mcq.explanation
                                                            }
                                                        </div>
                                                    )}
                                                </div>
                                            )
                                        )}
                                    </div>
                                )}
                            </section>
                        )}
                    </div>
                </div>
            )}

            {/* ======================================================
                PAYMENT OVERLAY
            ====================================================== */}

            {paymentLoading && (
                <div
                    style={{
                        position:
                            "fixed",
                        inset: 0,
                        zIndex: 90,
                        pointerEvents:
                            "none",
                    }}
                >
                    <div
                        style={{
                            position:
                                "absolute",
                            bottom: 20,
                            left: "50%",
                            transform:
                                "translateX(-50%)",
                            background:
                                "#0f172a",
                            color:
                                "#ffffff",
                            borderRadius:
                                12,
                            padding:
                                "12px 18px",
                            boxShadow:
                                "0 10px 30px rgba(0,0,0,.25)",
                            fontSize:
                                14,
                            fontWeight:
                                700,
                        }}
                    >
                        💳 ₹1 News Access
                        Payment
                    </div>
                </div>
            )}
        </div>
    );
}

