import React, {
    useCallback,
    useEffect,
    useRef,
    useState,
} from "react";

/*
|--------------------------------------------------------------------------
| MUNI48 - NEWS / CURRENT AFFAIRS
|--------------------------------------------------------------------------
| Features:
| - UPSC / BPSC
| - Hindi / English
| - Category
| - Bihar only
| - News search
| - â‚¹1 Razorpay daily access
| - Existing MCQ GET
| - MCQ generation POST JSON
| - 402 => Razorpay
| - Payment verification
| - Defensive API handling
|--------------------------------------------------------------------------
*/

const API_URL = import.meta.env.PROD
    ? "https://upsc-bpsc.onrender.com"
    : (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000");

const RAZORPAY_SCRIPT =
    "https://checkout.razorpay.com/v1/checkout.js";

const PAGE_SIZE = 20;
const MCQ_COUNT = 5;

const EXAMS = ["UPSC", "BPSC"];

const LANGUAGES = [
    {
        value: "en",
        label: "English",
    },
    {
        value: "hi",
        label: "à¤¹à¤¿à¤‚à¤¦à¥€",
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
| HELPERS
|--------------------------------------------------------------------------
*/


function getToken() {
    return (
        localStorage.getItem("access_token") ||
        sessionStorage.getItem("access_token") ||
        localStorage.getItem("token") ||
        sessionStorage.getItem("token") ||
        localStorage.getItem("jwt") ||
        sessionStorage.getItem("jwt") ||
        ""
    );
}

function getUser() {
    try {
        return JSON.parse(
            localStorage.getItem("user") ||
            sessionStorage.getItem("user") ||
            "null"
        );
    } catch {
        return null;
    }
}


function getErrorMessage(
    data,
    fallback = "Request failed."
) {
    if (!data) {
        return fallback;
    }

    if (typeof data === "string") {
        return data;
    }

    const detail = data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (
        detail &&
        typeof detail === "object"
    ) {
        if (detail.message) {
            return String(detail.message);
        }

        if (detail.detail) {
            return String(detail.detail);
        }

        if (detail.error) {
            return String(detail.error);
        }

        try {
            return JSON.stringify(detail);
        } catch {
            return fallback;
        }
    }

    if (data?.message) {
        return String(data.message);
    }

    if (data?.error) {
        return String(data.error);
    }

    return fallback;
}

function extract402Detail(data) {
    if (!data) {
        return null;
    }

    if (
        typeof data.detail === "object" &&
        data.detail !== null
    ) {
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

function isPaymentRequired(
    status,
    data
) {
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
        Boolean(
            detail.payment_endpoint
        ) ||
        Number(detail.amount) === 1
    );
}

/*
|--------------------------------------------------------------------------
| ARTICLE ID
|--------------------------------------------------------------------------
*/

function getArticleId(article) {
    if (!article) {
        return "";
    }

    return (
        article.id ??
        article.article_id ??
        article.news_id ??
        article.uuid ??
        ""
    );
}

/*
|--------------------------------------------------------------------------
| NORMALIZE OPTIONS
|--------------------------------------------------------------------------
*/

function normalizeOptions(options) {
    if (Array.isArray(options)) {
        return options.map((item) =>
            typeof item === "object" &&
            item !== null
                ? item.text ??
                  item.value ??
                  item.label ??
                  JSON.stringify(item)
                : String(item)
        );
    }

    if (
        options &&
        typeof options === "object"
    ) {
        return Object.entries(
            options
        ).map(
            ([key, value]) => {
                if (
                    typeof value ===
                    "object"
                ) {
                    return (
                        value?.text ??
                        value?.value ??
                        value?.label ??
                        `${key}: ${JSON.stringify(
                            value
                        )}`
                    );
                }

                return String(value);
            }
        );
    }

    return [];
}

/*
|--------------------------------------------------------------------------
| NORMALIZE MCQ
|--------------------------------------------------------------------------
*/

function normalizeMcq(item) {
    if (!item) {
        return null;
    }

    const question =
        item.question ??
        item.question_text ??
        item.text ??
        item.questionText ??
        "";

    const options =
        normalizeOptions(
            item.options ??
                item.choices ??
                item.answers
        );

    const correctAnswer =
        item.correct_answer ??
        item.correct_option ??
        item.correctAnswer ??
        item.answer ??
        item.answer_text ??
        "";

    const explanation =
        item.explanation ??
        item.solution ??
        item.reason ??
        "";

    return {
        ...item,
        question: String(question),
        options,
        correct_answer:
            correctAnswer === null ||
            correctAnswer === undefined
                ? ""
                : String(correctAnswer),
        explanation:
            explanation === null ||
            explanation === undefined
                ? ""
                : String(explanation),
    };
}

/*
|--------------------------------------------------------------------------
| NORMALIZE MCQ LIST
|--------------------------------------------------------------------------
*/

function normalizeMcqs(data) {
    let raw = [];

    if (Array.isArray(data)) {
        raw = data;
    } else if (
        Array.isArray(data?.mcqs)
    ) {
        raw = data.mcqs;
    } else if (
        Array.isArray(data?.questions)
    ) {
        raw = data.questions;
    } else if (
        Array.isArray(data?.data)
    ) {
        raw = data.data;
    } else if (
        Array.isArray(data?.results)
    ) {
        raw = data.results;
    }

    return raw
        .map(normalizeMcq)
        .filter(
            (item) =>
                item &&
                item.question &&
                item.question.trim()
        );
}

/*
|--------------------------------------------------------------------------
| LOAD RAZORPAY
|--------------------------------------------------------------------------
*/

function loadRazorpayScript() {
    return new Promise((resolve, reject) => {
        if (typeof window !== "undefined" && window.Razorpay) {
            resolve(true);
            return;
        }

        const existing = document.querySelector(
            `script[src="${RAZORPAY_SCRIPT}"]`
        );

        if (existing) {
            existing.addEventListener("load", () => {
                window.Razorpay
                    ? resolve(true)
                    : reject(new Error("Razorpay SDK unavailable."));
            }, { once: true });

            existing.addEventListener("error", () => {
                reject(new Error("Razorpay SDK failed to load."));
            }, { once: true });

            return;
        }

        const script = document.createElement("script");
        script.src = RAZORPAY_SCRIPT;
        script.async = true;

        script.onload = () => {
            window.Razorpay
                ? resolve(true)
                : reject(new Error("Razorpay SDK unavailable."));
        };

        script.onerror = () => {
            reject(new Error("Unable to load Razorpay SDK."));
        };

        document.body.appendChild(script);
    });
}
/*
|--------------------------------------------------------------------------
| MAIN
|--------------------------------------------------------------------------
*/

export default function News() {
    /*
    |--------------------------------------------------------------------------
    | FILTERS
    |--------------------------------------------------------------------------
    */

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

    /*
    |--------------------------------------------------------------------------
    | NEWS
    |--------------------------------------------------------------------------
    */

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

    /*
    |--------------------------------------------------------------------------
    | PAYMENT
    |--------------------------------------------------------------------------
    */

    const [
        paymentLoading,
        setPaymentLoading,
    ] = useState(false);

    const [
        paymentMessage,
        setPaymentMessage,
    ] = useState("");

    const [hasAccess, setHasAccess] =
        useState(false);

    /*
    |--------------------------------------------------------------------------
    | ARTICLE / MCQ
    |--------------------------------------------------------------------------
    */

    const [
        selectedArticle,
        setSelectedArticle,
    ] = useState(null);

    const [mcqs, setMcqs] =
        useState([]);

    const [
        mcqLoading,
        setMcqLoading,
    ] = useState(false);

    const [
        mcqError,
        setMcqError,
    ] = useState("");

    const [
        mcqVisible,
        setMcqVisible,
    ] = useState(false);

    /*
    |--------------------------------------------------------------------------
    | REFS
    |--------------------------------------------------------------------------
    */

    const paymentPromiseRef =
        useRef(null);

    const paymentCooldownUntil =
        useRef(0);

    const newsRequestRef =
        useRef(0);

    const initialLoadRef =
        useRef(false);

    /*
    |--------------------------------------------------------------------------
    | HEADERS
    |--------------------------------------------------------------------------
    */

    const getHeaders =
        useCallback(() => {
            const token =
                getToken();

            const headers = {
                Accept:
                    "application/json",
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
    | API REQUEST
    |--------------------------------------------------------------------------
    */

    const apiRequest =
        useCallback(
            async (
                endpoint,
                options = {}
            ) => {
                const url =
                    endpoint.startsWith(
                        "http"
                    )
                        ? endpoint
                        : `${API_URL}${endpoint}`;

                let response;

                try {
                    response =
                        await fetch(
                            url,
                            {
                                ...options,

                                headers: {
                                    ...getHeaders(),
                                    ...(options.headers ||
                                        {}),
                                },
                            }
                        );
                } catch (
                    networkError
                ) {
                    throw new Error(
                        `Backend connection failed. ${networkError?.message || ""}`
                    );
                }

                const contentType =
                    response.headers.get(
                        "content-type"
                    ) || "";

                let data = null;

                if (
                    contentType.includes(
                        "application/json"
                    )
                ) {
                    try {
                        data =
                            await response.json();
                    } catch {
                        data = null;
                    }
                } else {
                    try {
                        const text =
                            await response.text();

                        data =
                            text || null;
                    } catch {
                        data = null;
                    }
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
| CREATE PAYMENT ORDER
|--------------------------------------------------------------------------
*/

const verifyPayment = useCallback(
    async (paymentData = {}) => {
        const {
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        } = paymentData;

        if (
            !razorpay_order_id ||
            !razorpay_payment_id ||
            !razorpay_signature
        ) {
            throw new Error(
                "Payment verification details are incomplete."
            );
        }

        const { response, data } = await apiRequest(
            "/news/payment/verify",
            {
                method: "POST",
                body: JSON.stringify({
                    razorpay_order_id,
                    razorpay_payment_id,
                    razorpay_signature,
                }),
            }
        );

        if (response.status === 401) {
            throw new Error(
                "Session expired. Please login again."
            );
        }

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data,
                    `Payment verification failed (${response.status}).`
                )
            );
        }

        const result = data?.data ?? data?.result ?? data;

        if (result?.success === false) {
            throw new Error(
                result?.message || "Payment verification failed."
            );
        }

        return result;
    },
    [apiRequest]
);
const createPaymentOrder = useCallback(
    async () => {
        const {
            response,
            data,
        } = await apiRequest(
            "/news/payment/create-order",
            {
                method: "POST",
            }
        );

        // Session expired
        if (response.status === 401) {
            throw new Error(
                "Session expired. Please login again."
            );
        }

        // Backend returned an error
        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data,
                    `Unable to create payment order (${response.status}).`
                )
            );
        }

        // Normalize direct or nested response
        let orderData = data;

        for (let i = 0; i < 3; i++) {
            if (
                orderData &&
                typeof orderData === "object" &&
                !Array.isArray(orderData) &&
                (
                    orderData.order_id ||
                    orderData.orderId ||
                    orderData.id
                )
            ) {
                break;
            }

            if (
                !orderData ||
                typeof orderData !== "object" ||
                Array.isArray(orderData)
            ) {
                break;
            }

            const nested =
                orderData.data ??
                orderData.order ??
                orderData.result;

            if (
                !nested ||
                typeof nested !== "object" ||
                Array.isArray(nested)
            ) {
                break;
            }

            orderData = nested;
        }

        // Validate response
        if (
            !orderData ||
            typeof orderData !== "object" ||
            Array.isArray(orderData)
        ) {
            throw new Error(
                "Invalid payment order response from server."
            );
        }

        // Validate Razorpay order ID
        const orderId =
            orderData.order_id ??
            orderData.orderId ??
            orderData.id;

        if (
            typeof orderId !== "string" ||
            !orderId.trim()
        ) {
            throw new Error(
                "Razorpay Order ID missing from server."
            );
        }

        // Validate Razorpay Key ID
        const keyId =
            orderData.key_id ??
            orderData.keyId;

        if (
            typeof keyId !== "string" ||
            !keyId.trim()
        ) {
            throw new Error(
                "Razorpay Key ID missing from server."
            );
        }

        // Return normalized order data
        return {
            ...orderData,
            order_id: orderId,
            key_id: keyId,
            amount: Number(
                orderData.amount ?? 100
            ),
            currency:
                orderData.currency ?? "INR",
        };
    },
    [apiRequest]
);


    /*
    |--------------------------------------------------------------------------
    | RAZORPAY PAYMENT
    |--------------------------------------------------------------------------
    */

    const openRazorpayPayment =
        useCallback(
            async (afterPayment) => {
                if (
                    paymentPromiseRef.current
                ) {
                    return paymentPromiseRef.current;
                }

                if (
                    Date.now() <
                    paymentCooldownUntil.current
                ) {
                    setPaymentMessage(
                        "Please wait a few seconds before retrying payment."
                    );

                    return;
                }

                const promise =
                    (async () => {
                        setPaymentLoading(
                            true
                        );

                        try {
                            setPaymentMessage(
                                "Preparing â‚¹1 payment..."
                            );

                            await loadRazorpayScript();

                            const order =
                                await createPaymentOrder();

                            /*
                             * ALREADY ACTIVE
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
                                    "âœ“ Today's access is already active."
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
                                order?.key_id ??
                                order?.keyId;

                            const orderId =
                                order?.order_id ??
                                order?.orderId ??
                                order?.id;

                            const amount =
                                Number(
                                    order?.amount ??
                                        100
                                );

                            const currency =
                                order?.currency ??
                                "INR";

                            if (!keyId) {
                                throw new Error(
                                    "Razorpay Key ID missing from server."
                                );
                            }

                            if (!orderId) {
                                throw new Error(
                                    "Razorpay Order ID missing from server."
                                );
                            }

                            await new Promise(
                                (
                                    resolve,
                                    reject
                                ) => {
                                    let finished =
                                        false;

                                    const finish =
                                        (
                                            callback
                                        ) => {
                                            if (
                                                finished
                                            ) {
                                                return;
                                            }

                                            finished =
                                                true;

                                            callback();
                                        };

                                    const currentUser =
                                        getUser();

                                    const options =
                                        {
                                            key:
                                                keyId,

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
                                                        currentUser?.name ||
                                                        "",

                                                    email:
                                                        currentUser?.email ||
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
                                                            "Payment received. Verifying..."
                                                        );

                                                        const verified =
                                                            await verifyPayment(
                                                                {
                                                                    razorpay_order_id:
                                                                        paymentResponse
                                                                            ?.razorpay_order_id,

                                                                    razorpay_payment_id:
                                                                        paymentResponse
                                                                            ?.razorpay_payment_id,

                                                                    razorpay_signature:
                                                                        paymentResponse
                                                                            ?.razorpay_signature,
                                                                }
                                                            );

                                                        if (
                                                            verified?.has_access !==
                                                                true &&
                                                            verified?.access_active !==
                                                                true
                                                        ) {
                                                            throw new Error(
                                                                "Payment verified but access is not active."
                                                            );
                                                        }

                                                        setHasAccess(
                                                            true
                                                        );

                                                        setPaymentMessage(
                                                            "âœ“ â‚¹1 payment verified."
                                                        );

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
                                                        verificationError
                                                    ) {
                                                        finish(
                                                            () =>
                                                                reject(
                                                                    verificationError
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
                                            const description =
                                                paymentError
                                                    ?.error
                                                    ?.description ||
                                                "Payment failed.";

                                            setPaymentMessage(
                                                description
                                            );

                                            paymentCooldownUntil.current =
                                                Date.now() +
                                                10000;

                                            finish(
                                                () =>
                                                    reject(
                                                        new Error(
                                                            description
                                                        )
                                                    )
                                            );
                                        }
                                    );

                                    razorpay.open();
                                }
                            );
                        } catch (
                            paymentError
                        ) {
                            console.error(
                                "Payment error:",
                                paymentError
                            );

                            setPaymentMessage(
                                paymentError?.message ||
                                    "Unable to process â‚¹1 payment."
                            );

                            throw paymentError;
                        } finally {
                            setPaymentLoading(
                                false
                            );

                            paymentCooldownUntil.current =
                                Date.now() +
                                3000;
                        }
                    })();

                paymentPromiseRef.current =
                    promise;

                try {
                    return await promise;
                } finally {
                    paymentPromiseRef.current =
                        null;
                }
            },
            [
                createPaymentOrder,
                verifyPayment,
            ]
        );

    /*
    |--------------------------------------------------------------------------
    | FETCH NEWS
    |--------------------------------------------------------------------------
    */

    const fetchNews =
        useCallback(
            async ({
                requestedPage = 1,
                silent = false,
                allowPayment = true,
            } = {}) => {
                const requestId =
                    ++newsRequestRef.current;

                if (!silent) {
                    setLoading(true);
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
                    String(PAGE_SIZE)
                );

                params.set(
                    "language",
                    language
                );

                params.set(
                    "exam",
                    exam
                );

                if (category) {
                    params.set(
                        "category",
                        category
                    );
                }

                if (biharOnly) {
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

                    if (
                        requestId !==
                        newsRequestRef.current
                    ) {
                        return;
                    }

                    /*
                     * 402
                     */

                    if (
                        allowPayment &&
                        isPaymentRequired(
                            response.status,
                            data
                        )
                    ) {
                        setLoading(false);

                        setPaymentMessage(
                            "Today's News access requires â‚¹1 payment."
                        );

                        await openRazorpayPayment(
                            async () => {
                                await fetchNews(
                                    {
                                        requestedPage,
                                        silent: false,
                                        allowPayment: false,
                                    }
                                );
                            }
                        );

                        return;
                    }

                    /*
                     * 401
                     */

                    if (
                        response.status ===
                        401
                    ) {
                        throw new Error(
                            "Session expired. Please login again."
                        );
                    }

                    /*
                     * ERROR
                     */

                    if (!response.ok) {
                        throw new Error(
                            `Request failed (${response.status}). ${getErrorMessage(
                                data,
                                "News load failed."
                            )}`
                        );
                    }

                    /*
                     * SUCCESS
                     */

                    const resultArticles =
                        Array.isArray(
                            data?.articles
                        )
                            ? data.articles
                            : Array.isArray(
                                  data?.results
                              )
                            ? data.results
                            : [];

                    setArticles(
                        resultArticles
                    );

                    setTotal(
                        Number(
                            data?.total ??
                                data?.filtered_results ??
                                resultArticles.length
                        )
                    );

                    setPage(
                        Number(
                            data?.page ??
                                requestedPage
                        )
                    );

                    setHasAccess(
                        true
                    );

                    setPaymentMessage("");
                } catch (
                    fetchError
                ) {
                    console.error(
                        "News fetch error:",
                        fetchError
                    );

                    setError(
                        fetchError?.message ||
                            "News load failed."
                    );
                } finally {
                    if (!silent) {
                        setLoading(false);
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
    | LOAD / GENERATE MCQS
    |--------------------------------------------------------------------------
    */

    const loadArticleMCQs =
        useCallback(
            async (
                articleId,
                allowPayment = true
            ) => {
                /*
                 * IMPORTANT:
                 * Never allow undefined article ID.
                 */

                if (
                    articleId ===
                        undefined ||
                    articleId ===
                        null ||
                    String(
                        articleId
                    ).trim() === ""
                ) {
                    setMcqVisible(true);
                    setMcqError(
                        language === "hi"
                            ? "à¤‡à¤¸ article à¤•à¤¾ valid ID à¤¨à¤¹à¥€à¤‚ à¤®à¤¿à¤²à¤¾à¥¤"
                            : "Valid article ID was not found."
                    );
                    return;
                }

                const safeArticleId =
                    encodeURIComponent(
                        String(
                            articleId
                        )
                    );

                setMcqLoading(true);
                setMcqError("");
                setMcqVisible(true);

                try {
                    /*
                     * ======================================================
                     * STEP 1
                     * GET EXISTING MCQs
                     * ======================================================
                     */

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
                        response:
                            getResponse,
                        data:
                            getData,
                    } =
                        await apiRequest(
                            `/news/${safeArticleId}/mcqs?${params.toString()}`
                        );

                    console.log(
                        "MCQ GET:",
                        {
                            status:
                                getResponse.status,
                            data:
                                getData,
                        }
                    );

                    /*
                     * PAYMENT
                     */

                    if (
                        allowPayment &&
                        isPaymentRequired(
                            getResponse.status,
                            getData
                        )
                    ) {
                        setMcqLoading(
                            false
                        );

                        setPaymentMessage(
                            language === "hi"
                                ? "à¤†à¤œ à¤•à¥‡ MCQ access à¤•à¥‡ à¤²à¤¿à¤ â‚¹1 payment à¤†à¤µà¤¶à¥à¤¯à¤• à¤¹à¥ˆà¥¤"
                                : "Today's MCQ access requires â‚¹1 payment."
                        );

                        await openRazorpayPayment(
                            async () => {
                                await loadArticleMCQs(
                                    articleId,
                                    false
                                );
                            }
                        );

                        return;
                    }

                    /*
                     * AUTH
                     */

                    if (
                        getResponse.status ===
                        401
                    ) {
                        throw new Error(
                            language === "hi"
                                ? "Session à¤¸à¤®à¤¾à¤ªà¥à¤¤ à¤¹à¥‹ à¤—à¤¯à¤¾ à¤¹à¥ˆà¥¤ à¤•à¥ƒà¤ªà¤¯à¤¾ à¤«à¤¿à¤° à¤¸à¥‡ login à¤•à¤°à¥‡à¤‚à¥¤"
                                : "Session expired. Please login again."
                        );
                    }

                    /*
                     * Other GET errors
                     */

                    if (
                        !getResponse.ok
                    ) {
                        throw new Error(
                            getErrorMessage(
                                getData,
                                language === "hi"
                                    ? `MCQ load à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤¸à¤•à¥‡ (${getResponse.status}).`
                                    : `MCQs could not be loaded (${getResponse.status}).`
                            )
                        );
                    }

                    /*
                     * EXISTING MCQS
                     */

                    const existingMcqs =
                        normalizeMcqs(
                            getData
                        );

                    if (
                        existingMcqs.length >
                        0
                    ) {
                        setMcqs(
                            existingMcqs
                        );

                        setMcqVisible(
                            true
                        );

                        setMcqLoading(
                            false
                        );

                        setPaymentMessage(
                            ""
                        );

                        return;
                    }

                    /*
                     * ======================================================
                     * STEP 2
                     * GENERATE
                     * ======================================================
                     */

                    setMcqError("");

                    setPaymentMessage(
                        language === "hi"
                            ? "MCQs generate à¤¹à¥‹ à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚..."
                            : "Generating MCQs..."
                    );

                    const generateBody = {
                        exam:
                            exam.toUpperCase(),

                        language:
                            language,

                        count:
                            MCQ_COUNT,

                        difficulty:
                            "Medium",

                        question_type:
                            "single_correct",
                    };

                    console.log(
                        "MCQ POST URL:",
                        `${API_URL}/news/${safeArticleId}/mcqs/generate`
                    );

                    console.log(
                        "MCQ POST BODY:",
                        generateBody
                    );

                    const {
                        response:
                            generateResponse,
                        data:
                            generateData,
                    } =
                        await apiRequest(
                            `/news/${safeArticleId}/mcqs/generate`,
                            {
                                method:
                                    "POST",

                                body:
                                    JSON.stringify(
                                        generateBody
                                    ),
                            }
                        );

                    console.log(
                        "MCQ POST RESPONSE:",
                        {
                            status:
                                generateResponse.status,
                            data:
                                generateData,
                        }
                    );

                    /*
                     * PAYMENT ON POST
                     */

                    if (
                        allowPayment &&
                        isPaymentRequired(
                            generateResponse.status,
                            generateData
                        )
                    ) {
                        setMcqLoading(
                            false
                        );

                        setPaymentMessage(
                            language === "hi"
                                ? "MCQ generate à¤•à¤°à¤¨à¥‡ à¤•à¥‡ à¤²à¤¿à¤ â‚¹1 payment à¤†à¤µà¤¶à¥à¤¯à¤• à¤¹à¥ˆà¥¤"
                                : "MCQ generation requires â‚¹1 payment."
                        );

                        await openRazorpayPayment(
                            async () => {
                                await loadArticleMCQs(
                                    articleId,
                                    false
                                );
                            }
                        );

                        return;
                    }

                    /*
                     * 401
                     */

                    if (
                        generateResponse.status ===
                        401
                    ) {
                        throw new Error(
                            language === "hi"
                                ? "Session à¤¸à¤®à¤¾à¤ªà¥à¤¤ à¤¹à¥‹ à¤—à¤¯à¤¾ à¤¹à¥ˆà¥¤ à¤•à¥ƒà¤ªà¤¯à¤¾ à¤«à¤¿à¤° à¤¸à¥‡ login à¤•à¤°à¥‡à¤‚à¥¤"
                                : "Session expired. Please login again."
                        );
                    }

                    /*
                     * 422
                     */

                    if (
                        generateResponse.status ===
                        422
                    ) {
                        console.error(
                            "MCQ 422:",
                            generateData
                        );

                        throw new Error(
                            getErrorMessage(
                                generateData,
                                language === "hi"
                                    ? "MCQ request validation failed."
                                    : "MCQ request validation failed."
                            )
                        );
                    }

                    /*
                     * OTHER ERROR
                     */

                    if (
                        !generateResponse.ok
                    ) {
                        throw new Error(
                            getErrorMessage(
                                generateData,
                                language === "hi"
                                    ? `MCQs generate à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤¸à¤•à¥‡ (${generateResponse.status}).`
                                    : `MCQs could not be generated (${generateResponse.status}).`
                            )
                        );
                    }

                    /*
                     * POST RESPONSE
                     */

                    let generatedMcqs =
                        normalizeMcqs(
                            generateData
                        );

                    /*
                     * Some backend implementations
                     * return only status after POST.
                     *
                     * Therefore GET again.
                     */

                    if (
                        generatedMcqs.length ===
                        0
                    ) {
                        const {
                            response:
                                retryResponse,
                            data:
                                retryData,
                        } =
                            await apiRequest(
                                `/news/${safeArticleId}/mcqs?${params.toString()}`
                            );

                        console.log(
                            "MCQ RETRY GET:",
                            {
                                status:
                                    retryResponse.status,
                                data:
                                    retryData,
                            }
                        );

                        if (
                            retryResponse.ok
                        ) {
                            generatedMcqs =
                                normalizeMcqs(
                                    retryData
                                );
                        }
                    }

                    /*
                     * FINAL
                     */

                    setMcqs(
                        generatedMcqs
                    );

                    setMcqVisible(
                        true
                    );

                    if (
                        generatedMcqs.length ===
                        0
                    ) {
                        throw new Error(
                            language === "hi"
                                ? "MCQ generation complete à¤¹à¥à¤†, à¤²à¥‡à¤•à¤¿à¤¨ backend à¤¨à¥‡ à¤•à¥‹à¤ˆ valid MCQ return à¤¨à¤¹à¥€à¤‚ à¤•à¤¿à¤¯à¤¾à¥¤"
                                : "MCQ generation completed, but the backend returned no valid MCQs."
                        );
                    }

                    setPaymentMessage("");
                } catch (
                    mcqFetchError
                ) {
                    console.error(
                        "MCQ ERROR:",
                        mcqFetchError
                    );

                    setMcqVisible(true);

                    setMcqError(
                        mcqFetchError?.message ||
                            (language === "hi"
                                ? "MCQs load à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤¸à¤•à¥‡à¥¤"
                                : "MCQs could not be loaded.")
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
    | INITIAL LOAD / FILTER CHANGE
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
    | SEARCH
    |--------------------------------------------------------------------------
    */

    const handleSearch =
        async (event) => {
            event?.preventDefault();

            await fetchNews({
                requestedPage: 1,
            });
        };

    /*
    |--------------------------------------------------------------------------
    | PAGINATION
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

    const changePage =
        async (nextPage) => {
            if (
                nextPage < 1 ||
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
                behavior: "smooth",
            });
        };

    /*
    |--------------------------------------------------------------------------
    | OPEN ARTICLE
    |--------------------------------------------------------------------------
    */

    const openArticle =
        (article) => {
            if (!article) {
                return;
            }

            const articleId =
                getArticleId(
                    article
                );

            console.log(
                "OPEN ARTICLE:",
                {
                    article,
                    articleId,
                }
            );

            setSelectedArticle(
                article
            );

            setMcqs([]);

            setMcqError("");

            setMcqVisible(
                false
            );

            /*
             * Automatically load/generate MCQs.
             *
             * This makes "Read & MCQs"
             * work immediately.
             */

            if (articleId) {
                loadArticleMCQs(
                    articleId
                );
            } else {
                setMcqVisible(
                    true
                );

                setMcqError(
                    language === "hi"
                        ? "Article ID à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆà¥¤"
                        : "Article ID is missing."
                );
            }
        };

    /*
    |--------------------------------------------------------------------------
    | CLOSE
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
    | DATE
    |--------------------------------------------------------------------------
    */

    const formatDate =
        (value) => {
            if (!value) {
                return "";
            }

            try {
                const date =
                    new Date(value);

                if (
                    Number.isNaN(
                        date.getTime()
                    )
                ) {
                    return "";
                }

                return date.toLocaleDateString(
                    language === "hi"
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

    const user =
        getUser();

    /*
    |--------------------------------------------------------------------------
    | TRANSLATIONS
    |--------------------------------------------------------------------------
    */

    const t = {
        title:
            language === "hi"
                ? "à¤¸à¤®à¤¸à¤¾à¤®à¤¯à¤¿à¤•à¥€"
                : "Current Affairs",

        subtitle:
            language === "hi"
                ? "UPSC à¤à¤µà¤‚ BPSC à¤•à¥€ à¤¤à¥ˆà¤¯à¤¾à¤°à¥€ à¤•à¥‡ à¤²à¤¿à¤ AI-à¤•à¥à¤¯à¥‚à¤°à¥‡à¤Ÿà¥‡à¤¡ à¤¸à¤®à¤¸à¤¾à¤®à¤¯à¤¿à¤•à¥€"
                : "AI-curated current affairs for UPSC & BPSC preparation",

        search:
            language === "hi"
                ? "à¤–à¥‹à¤œà¥‡à¤‚"
                : "Search News",

        searchPlaceholder:
            language === "hi"
                ? "Current Affairs à¤–à¥‹à¤œà¥‡à¤‚..."
                : "Search current affairs...",

        exam:
            language === "hi"
                ? "à¤ªà¤°à¥€à¤•à¥à¤·à¤¾"
                : "Exam",

        language:
            language === "hi"
                ? "à¤­à¤¾à¤·à¤¾"
                : "Language",

        category:
            language === "hi"
                ? "à¤¶à¥à¤°à¥‡à¤£à¥€"
                : "Category",

        bihar:
            language === "hi"
                ? "à¤•à¥‡à¤µà¤² à¤¬à¤¿à¤¹à¤¾à¤°"
                : "Bihar Only",

        reset:
            language === "hi"
                ? "à¤°à¥€à¤¸à¥‡à¤Ÿ"
                : "Reset",

        readMcq:
            language === "hi"
                ? "à¤ªà¤¢à¤¼à¥‡à¤‚ à¤”à¤° MCQs"
                : "Read & MCQs",

        source:
            language === "hi"
                ? "à¤¸à¥à¤°à¥‹à¤¤"
                : "Source",

        previous:
            language === "hi"
                ? "â† à¤ªà¤¿à¤›à¤²à¤¾"
                : "â† Previous",

        next:
            language === "hi"
                ? "à¤…à¤—à¤²à¤¾ â†’"
                : "Next â†’",

        loading:
            language === "hi"
                ? "à¤²à¥‹à¤¡ à¤¹à¥‹ à¤°à¤¹à¤¾ à¤¹à¥ˆ..."
                : "Loading...",

        noNews:
            language === "hi"
                ? "à¤•à¥‹à¤ˆ Current Affairs à¤¨à¤¹à¥€à¤‚ à¤®à¤¿à¤²à¤¾à¥¤"
                : "No current affairs found.",

        mcqPractice:
            language === "hi"
                ? "MCQ à¤…à¤­à¥à¤¯à¤¾à¤¸"
                : "MCQ Practice",

        generateMcq:
            language === "hi"
                ? "MCQs Generate / View à¤•à¤°à¥‡à¤‚"
                : "Generate / View MCQs",

        mcqLoading:
            language === "hi"
                ? "MCQs Generate à¤¹à¥‹ à¤°à¤¹à¥‡ à¤¹à¥ˆà¤‚..."
                : "Generating MCQs...",

        noMcq:
            language === "hi"
                ? "à¤‡à¤¸ article à¤•à¥‡ à¤²à¤¿à¤ à¤…à¤­à¥€ MCQs à¤‰à¤ªà¤²à¤¬à¥à¤§ à¤¨à¤¹à¥€à¤‚ à¤¹à¥ˆà¤‚à¥¤"
                : "No MCQs are currently available for this article.",

        explanation:
            language === "hi"
                ? "à¤µà¥à¤¯à¤¾à¤–à¥à¤¯à¤¾:"
                : "Explanation:",

        answer:
            language === "hi"
                ? "à¤¸à¤¹à¥€ à¤‰à¤¤à¥à¤¤à¤°:"
                : "Answer:",

        openSource:
            language === "hi"
                ? "Source à¤–à¥‹à¤²à¥‡à¤‚"
                : "Open Source",
    };

    /*
    |--------------------------------------------------------------------------
    | RENDER
    |--------------------------------------------------------------------------
    */

    return (
        <div
            style={{
                minHeight: "100vh",
                background: "#f8fafc",
                color: "#0f172a",
                paddingBottom: 60,
            }}
        >
            {/* HEADER */}

            <header
                style={{
                    background: "#ffffff",
                    borderBottom:
                        "1px solid #e2e8f0",
                    position: "sticky",
                    top: 0,
                    zIndex: 20,
                }}
            >
                <div
                    style={{
                        maxWidth: 1200,
                        margin: "0 auto",
                        padding:
                            "16px 20px",
                        display: "flex",
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
                                fontSize: 24,
                                fontWeight: 800,
                            }}
                        >
                            Muni48
                        </h1>

                        <div
                            style={{
                                fontSize: 13,
                                color:
                                    "#64748b",
                                marginTop: 3,
                            }}
                        >
                            {t.title}
                        </div>
                    </div>

                    <div
                        style={{
                            display: "flex",
                            alignItems:
                                "center",
                            gap: 10,
                        }}
                    >
                        <span
                            style={{
                                fontSize: 13,
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
                                    fontSize: 12,
                                    fontWeight: 700,
                                }}
                            >
                                âœ“ Access
                            </span>
                        )}
                    </div>
                </div>
            </header>

            {/* MAIN */}

            <main
                style={{
                    maxWidth: 1200,
                    margin: "0 auto",
                    padding:
                        "24px 20px",
                }}
            >
                {/* FILTER */}

                <section
                    style={{
                        background:
                            "#ffffff",
                        border:
                            "1px solid #e2e8f0",
                        borderRadius: 16,
                        padding: 20,
                        marginBottom: 20,
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
                            {/* SEARCH */}

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
                                        fontSize: 13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    {t.search}
                                </label>

                                <input
                                    value={
                                        query
                                    }
                                    onChange={(
                                        event
                                    ) =>
                                        setQuery(
                                            event
                                                .target
                                                .value
                                        )
                                    }
                                    placeholder={
                                        t.searchPlaceholder
                                    }
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

                            {/* EXAM */}

                            <div>
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize: 13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    {t.exam}
                                </label>

                                <select
                                    value={
                                        exam
                                    }
                                    onChange={(
                                        event
                                    ) => {
                                        setExam(
                                            event
                                                .target
                                                .value
                                        );

                                        setPage(
                                            1
                                        );

                                        setMcqs(
                                            []
                                        );

                                        setMcqVisible(
                                            false
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

                            {/* LANGUAGE */}

                            <div>
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize: 13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    {t.language}
                                </label>

                                <select
                                    value={
                                        language
                                    }
                                    onChange={(
                                        event
                                    ) => {
                                        setLanguage(
                                            event
                                                .target
                                                .value
                                        );

                                        setPage(
                                            1
                                        );

                                        setMcqs(
                                            []
                                        );

                                        setMcqVisible(
                                            false
                                        );

                                        setMcqError(
                                            ""
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

                            {/* CATEGORY */}

                            <div>
                                <label
                                    style={{
                                        display:
                                            "block",
                                        fontSize: 13,
                                        fontWeight:
                                            700,
                                        marginBottom:
                                            6,
                                    }}
                                >
                                    {t.category}
                                </label>

                                <select
                                    value={
                                        category
                                    }
                                    onChange={(
                                        event
                                    ) => {
                                        setCategory(
                                            event
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
                                    <option value="">
                                        {language ===
                                        "hi"
                                            ? "à¤¸à¤­à¥€ à¤¶à¥à¤°à¥‡à¤£à¤¿à¤¯à¤¾à¤"
                                            : "All Categories"}
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

                            {/* BIHAR */}

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
                                        fontSize: 14,
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
                                            event
                                        ) => {
                                            setBiharOnly(
                                                event
                                                    .target
                                                    .checked
                                            );

                                            setPage(
                                                1
                                            );
                                        }}
                                    />

                                    {t.bihar}
                                </label>
                            </div>
                        </div>

                        <div
                            style={{
                                marginTop: 16,
                                display: "flex",
                                gap: 10,
                                flexWrap:
                                    "wrap",
                            }}
                        >
                            <button
                                type="submit"
                                disabled={
                                    loading ||
                                    paymentLoading
                                }
                                style={{
                                    border: 0,
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
                                        loading ||
                                        paymentLoading
                                            ? "not-allowed"
                                            : "pointer",
                                    opacity:
                                        loading ||
                                        paymentLoading
                                            ? 0.6
                                            : 1,
                                }}
                            >
                                {loading
                                    ? t.loading
                                    : t.search}
                            </button>

                            <button
                                type="button"
                                disabled={
                                    loading ||
                                    paymentLoading
                                }
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

                                    setPage(
                                        1
                                    );

                                    setMcqs(
                                        []
                                    );

                                    setMcqVisible(
                                        false
                                    );

                                    setMcqError(
                                        ""
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
                                {t.reset}
                            </button>
                        </div>
                    </form>
                </section>

                {/* PAYMENT MESSAGE */}

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
                            marginBottom: 18,
                            fontSize: 14,
                            fontWeight: 600,
                        }}
                    >
                        {paymentLoading
                            ? "ðŸ’³ "
                            : "â„¹ï¸ "}
                        {paymentMessage}
                    </div>
                )}

                {/* ERROR */}

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
                            padding: 14,
                            marginBottom: 18,
                        }}
                    >
                        <strong>
                            {language ===
                            "hi"
                                ? "News à¤²à¥‹à¤¡ à¤¨à¤¹à¥€à¤‚ à¤¹à¥‹ à¤¸à¤•à¥‡"
                                : "News could not be loaded"}
                        </strong>

                        <div
                            style={{
                                marginTop: 5,
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
                                marginTop: 10,
                                border: 0,
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
                            {language ===
                            "hi"
                                ? "à¤¦à¥‹à¤¬à¤¾à¤°à¤¾ à¤ªà¥à¤°à¤¯à¤¾à¤¸ à¤•à¤°à¥‡à¤‚"
                                : "Retry"}
                        </button>
                    </div>
                )}

                {/* LOADING */}

                {loading && (
                    <div
                        style={{
                            textAlign:
                                "center",
                            padding: 40,
                            color:
                                "#64748b",
                        }}
                    >
                        {t.loading}
                    </div>
                )}

                {/* EMPTY */}

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
                                padding: 40,
                                textAlign:
                                    "center",
                                color:
                                    "#64748b",
                            }}
                        >
                            {t.noNews}
                        </div>
                    )}

                {/* ARTICLES */}

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
                                ) => {
                                    const articleId =
                                        getArticleId(
                                            article
                                        );

                                    return (
                                        <article
                                            key={
                                                articleId ||
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
                                                            width: 150,
                                                            height: 100,
                                                            objectFit:
                                                                "cover",
                                                            borderRadius:
                                                                10,
                                                            flexShrink:
                                                                0,
                                                        }}
                                                        onError={(
                                                            event
                                                        ) => {
                                                            event.currentTarget.style.display =
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
                                                            {article.exam ||
                                                                exam}
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
                                                            {article.category ||
                                                                "General"}
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
                                                                `${article.source} â€¢ `}

                                                            {formatDate(
                                                                article.published_at
                                                            )}
                                                        </div>

                                                        <div
                                                            style={{
                                                                display:
                                                                    "flex",
                                                                gap: 8,
                                                                flexWrap:
                                                                    "wrap",
                                                            }}
                                                        >
                                                            <button
                                                                type="button"
                                                                disabled={
                                                                    paymentLoading ||
                                                                    !articleId
                                                                }
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
                                                                        paymentLoading ||
                                                                        !articleId
                                                                            ? "not-allowed"
                                                                            : "pointer",
                                                                    fontWeight:
                                                                        700,
                                                                    opacity:
                                                                        !articleId
                                                                            ? 0.5
                                                                            : 1,
                                                                }}
                                                            >
                                                                {t.readMcq}
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
                                                                    {t.source}
                                                                </a>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </article>
                                    );
                                }
                            )}
                        </div>
                    )}

                {/* PAGINATION */}

                {!loading &&
                    totalPages > 1 && (
                        <div
                            style={{
                                display:
                                    "flex",
                                justifyContent:
                                    "center",
                                alignItems:
                                    "center",
                                gap: 10,
                                marginTop: 24,
                            }}
                        >
                            <button
                                type="button"
                                disabled={
                                    page <=
                                        1 ||
                                    loading ||
                                    paymentLoading
                                }
                                onClick={() =>
                                    changePage(
                                        page - 1
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
                                        "pointer",
                                }}
                            >
                                {t.previous}
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
                                        totalPages ||
                                    loading ||
                                    paymentLoading
                                }
                                onClick={() =>
                                    changePage(
                                        page + 1
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
                                        "pointer",
                                }}
                            >
                                {t.next}
                            </button>
                        </div>
                    )}
            </main>

            {/* ==========================================================
                ARTICLE + MCQ MODAL
            ========================================================== */}

            {selectedArticle && (
                <div
                    style={{
                        position: "fixed",
                        inset: 0,
                        background:
                            "rgba(15,23,42,0.65)",
                        zIndex: 100,
                        display: "flex",
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
                            padding: 24,
                            boxSizing:
                                "border-box",
                        }}
                        onClick={(
                            event
                        ) =>
                            event.stopPropagation()
                        }
                    >
                        {/* HEADER */}

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
                            <div
                                style={{
                                    minWidth: 0,
                                }}
                            >
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
                                        selectedArticle.category ||
                                        "General"
                                    }{" "}
                                    â€¢{" "}
                                    {
                                        selectedArticle.exam ||
                                        exam
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
                                    border: 0,
                                    background:
                                        "#f1f5f9",
                                    borderRadius:
                                        8,
                                    width: 36,
                                    height: 36,
                                    cursor:
                                        "pointer",
                                    fontSize:
                                        20,
                                    flexShrink:
                                        0,
                                }}
                            >
                                Ã—
                            </button>
                        </div>

                        {/* IMAGE */}

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
                                onError={(
                                    event
                                ) => {
                                    event.currentTarget.style.display =
                                        "none";
                                }}
                            />
                        )}

                        {/* DESCRIPTION */}

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

                        {/* MCQ BUTTON */}

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
                                onClick={() => {
                                    const id =
                                        getArticleId(
                                            selectedArticle
                                        );

                                    loadArticleMCQs(
                                        id
                                    );
                                }}
                                style={{
                                    border: 0,
                                    background:
                                        "#2563eb",
                                    color:
                                        "#ffffff",
                                    borderRadius:
                                        9,
                                    padding:
                                        "10px 16px",
                                    cursor:
                                        mcqLoading ||
                                        paymentLoading
                                            ? "not-allowed"
                                            : "pointer",
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
                                    ? t.mcqLoading
                                    : t.generateMcq}
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
                                    {
                                        t.openSource
                                    }
                                </a>
                            )}
                        </div>

                        {/* MCQ ERROR */}

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
                                    padding: 12,
                                    marginTop:
                                        16,
                                }}
                            >
                                <div>
                                    {
                                        mcqError
                                    }
                                </div>

                                <button
                                    type="button"
                                    disabled={
                                        paymentLoading ||
                                        mcqLoading
                                    }
                                    onClick={() => {
                                        const id =
                                            getArticleId(
                                                selectedArticle
                                            );

                                        loadArticleMCQs(
                                            id
                                        );
                                    }}
                                    style={{
                                        display:
                                            "block",
                                        marginTop:
                                            10,
                                        border: 0,
                                        background:
                                            "#991b1b",
                                        color:
                                            "#ffffff",
                                        borderRadius:
                                            8,
                                        padding:
                                            "7px 12px",
                                        cursor:
                                            "pointer",
                                    }}
                                >
                                    {language ===
                                    "hi"
                                        ? "MCQ à¤«à¤¿à¤° à¤¸à¥‡ Generate à¤•à¤°à¥‡à¤‚"
                                        : "Retry MCQs"}
                                </button>
                            </div>
                        )}

                        {/* MCQ SECTION */}

                        {mcqVisible && (
                            <section
                                style={{
                                    marginTop:
                                        24,
                                }}
                            >
                                <div
                                    style={{
                                        display:
                                            "flex",
                                        justifyContent:
                                            "space-between",
                                        alignItems:
                                            "center",
                                        gap: 10,
                                        marginBottom:
                                            14,
                                    }}
                                >
                                    <h3
                                        style={{
                                            margin:
                                                0,
                                        }}
                                    >
                                        {
                                            t.mcqPractice
                                        }
                                    </h3>

                                    <span
                                        style={{
                                            background:
                                                "#dbeafe",
                                            color:
                                                "#1d4ed8",
                                            borderRadius:
                                                999,
                                            padding:
                                                "5px 10px",
                                            fontSize:
                                                12,
                                            fontWeight:
                                                700,
                                        }}
                                    >
                                        {language ===
                                        "hi"
                                            ? "à¤¹à¤¿à¤‚à¤¦à¥€"
                                            : "English"}
                                    </span>
                                </div>

                                {mcqLoading ? (
                                    <div
                                        style={{
                                            background:
                                                "#f8fafc",
                                            borderRadius:
                                                10,
                                            padding:
                                                25,
                                            textAlign:
                                                "center",
                                            color:
                                                "#64748b",
                                        }}
                                    >
                                        {t.mcqLoading}
                                    </div>
                                ) : mcqs.length ===
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
                                        {
                                            t.noMcq
                                        }
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
                                                        mcq.mcq_id ||
                                                        `${index}-${mcq.question}`
                                                    }
                                                    style={{
                                                        border:
                                                            "1px solid #e2e8f0",
                                                        borderRadius:
                                                            12,
                                                        padding:
                                                            16,
                                                        background:
                                                            "#ffffff",
                                                    }}
                                                >
                                                    <div
                                                        style={{
                                                            fontWeight:
                                                                800,
                                                            marginBottom:
                                                                10,
                                                            lineHeight:
                                                                1.6,
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
                                                            ) => {
                                                                const letter =
                                                                    String.fromCharCode(
                                                                        65 +
                                                                            optionIndex
                                                                    );

                                                                return (
                                                                    <div
                                                                        key={
                                                                            `${index}-${optionIndex}`
                                                                        }
                                                                        style={{
                                                                            padding:
                                                                                "10px 12px",
                                                                            background:
                                                                                "#f8fafc",
                                                                            border:
                                                                                "1px solid #e2e8f0",
                                                                            borderRadius:
                                                                                8,
                                                                            marginBottom:
                                                                                7,
                                                                            lineHeight:
                                                                                1.5,
                                                                        }}
                                                                    >
                                                                        <strong>
                                                                            {
                                                                                letter
                                                                            }
                                                                            .
                                                                        </strong>{" "}
                                                                        {
                                                                            option
                                                                        }
                                                                    </div>
                                                                );
                                                            }
                                                        )}

                                                    {mcq.explanation && (
                                                        <div
                                                            style={{
                                                                marginTop:
                                                                    12,
                                                                fontSize:
                                                                    13,
                                                                color:
                                                                    "#475569",
                                                                lineHeight:
                                                                    1.6,
                                                                background:
                                                                    "#f8fafc",
                                                                padding:
                                                                    10,
                                                                borderRadius:
                                                                    8,
                                                            }}
                                                        >
                                                            <strong>
                                                                {
                                                                    t.explanation
                                                                }
                                                            </strong>{" "}
                                                            {
                                                                mcq.explanation
                                                            }
                                                        </div>
                                                    )}

                                                    {mcq.correct_answer && (
                                                        <div
                                                            style={{
                                                                marginTop:
                                                                    10,
                                                                fontSize:
                                                                    13,
                                                                fontWeight:
                                                                    700,
                                                                color:
                                                                    "#166534",
                                                                background:
                                                                    "#dcfce7",
                                                                padding:
                                                                    "8px 10px",
                                                                borderRadius:
                                                                    8,
                                                            }}
                                                        >
                                                            {
                                                                t.answer
                                                            }{" "}
                                                            {
                                                                mcq.correct_answer
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

            {/* PAYMENT STATUS */}

            {paymentLoading && (
                <div
                    style={{
                        position: "fixed",
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
                            fontSize: 14,
                            fontWeight:
                                700,
                            whiteSpace:
                                "nowrap",
                        }}
                    >
                        ðŸ’³ â‚¹1 News Access
                        Payment
                    </div>
                </div>
            )}
        </div>
    );
}

