
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

/*
|--------------------------------------------------------------------------
| CONFIG
|--------------------------------------------------------------------------
*/

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const PAGE_SIZE = 20;

const RAZORPAY_KEY =
  import.meta.env.VITE_RAZORPAY_KEY_ID || "";

/*
|--------------------------------------------------------------------------
| CATEGORIES
|--------------------------------------------------------------------------
*/

const CATEGORIES = [
  {
    value: "General",
    hi: "सामान्य",
    en: "General",
  },
  {
    value: "Polity & Governance",
    hi: "राजव्यवस्था एवं शासन",
    en: "Polity & Governance",
  },
  {
    value: "Economy",
    hi: "अर्थव्यवस्था",
    en: "Economy",
  },
  {
    value: "Education",
    hi: "शिक्षा",
    en: "Education",
  },
  {
    value: "Security",
    hi: "सुरक्षा",
    en: "Security",
  },
  {
    value: "Environment",
    hi: "पर्यावरण",
    en: "Environment",
  },
  {
    value: "Science & Technology",
    hi: "विज्ञान एवं प्रौद्योगिकी",
    en: "Science & Technology",
  },
  {
    value: "Agriculture",
    hi: "कृषि",
    en: "Agriculture",
  },
  {
    value: "Health",
    hi: "स्वास्थ्य",
    en: "Health",
  },
  {
    value: "Social Issues",
    hi: "सामाजिक मुद्दे",
    en: "Social Issues",
  },
  {
    value: "History & Culture",
    hi: "इतिहास एवं संस्कृति",
    en: "History & Culture",
  },
  {
    value: "Geography",
    hi: "भूगोल",
    en: "Geography",
  },
  {
    value: "International Relations",
    hi: "अंतरराष्ट्रीय संबंध",
    en: "International Relations",
  },
  {
    value: "Disaster Management",
    hi: "आपदा प्रबंधन",
    en: "Disaster Management",
  },
  {
    value: "Ethics",
    hi: "नैतिकता",
    en: "Ethics",
  },
];

/*
|--------------------------------------------------------------------------
| TRANSLATIONS
|--------------------------------------------------------------------------
*/

const TRANSLATIONS = {
  hi: {
    title: "समसामयिकी",
    subtitle:
      "UPSC एवं BPSC की तैयारी के लिए AI-क्यूरेटेड समसामयिकी",

    searchPlaceholder: "समसामयिकी खोजें...",
    search: "खोजें",

    filters: "फ़िल्टर",
    activeFilters: "सक्रिय फ़िल्टर",
    reset: "रीसेट",

    exam: "परीक्षा",
    allExams: "सभी परीक्षाएँ",

    category: "श्रेणी",
    allCategories: "सभी श्रेणियाँ",

    language: "भाषा",

    hindi: "हिंदी",
    english: "English",

    bihar: "बिहार केवल",

    noNews: "कोई समसामयिकी नहीं मिली",
    noNewsDescription:
      "चयनित फ़िल्टर के लिए कोई समाचार उपलब्ध नहीं है।",

    loading: "समसामयिकी लोड हो रही है...",
    refresh: "रिफ्रेश",
    readMore: "और पढ़ें",

    articleDetails: "समाचार विवरण",

    examQuestions:
      "इस समाचार पर आधारित परीक्षा-उन्मुख प्रश्न",

    newsMCQs: "समाचार MCQs",

    noMCQ:
      "इस समाचार के लिए अभी कोई MCQ उपलब्ध नहीं है।",

    generateMCQ: "MCQs बनाएँ",
    generating: "बनाया जा रहा है...",

    unlockNews: "आज की समसामयिकी अनलॉक करें",

    unlockDescription:
      "आज की UPSC एवं BPSC समसामयिकी पढ़ने के लिए केवल ₹1 का भुगतान करें।",

    payRead:
      "₹1 भुगतान करें और आज की खबरें पढ़ें",

    processing: "प्रोसेसिंग...",

    securePayment:
      "Razorpay के माध्यम से सुरक्षित भुगतान",

    paymentSuccess:
      "भुगतान सफल हुआ।",

    paymentFailed:
      "भुगतान विफल हुआ।",

    paymentStartFailed:
      "भुगतान शुरू नहीं किया जा सका।",

    articleIdMissing:
      "समाचार ID उपलब्ध नहीं है।",

    mcqGenerationFailed:
      "MCQs बनाए नहीं जा सके।",

    newsLoadFailed:
      "समसामयिकी लोड नहीं की जा सकी।",

    razorpayNotLoaded:
      "Razorpay SDK लोड नहीं हुआ है।",

    razorpayKeyMissing:
      "Razorpay key उपलब्ध नहीं है।",

    invalidOrder:
      "अमान्य Razorpay order response।",

    currentAffairs: "समसामयिकी",

    readTodaysNews:
      "आज की समसामयिकी पढ़ें",

    date: "तिथि",
    source: "स्रोत",

    relatedQuestions:
      "संबंधित परीक्षा प्रश्न",

    examOriented:
      "परीक्षा-उन्मुख प्रश्न",

    retry: "पुनः प्रयास करें",
    error: "त्रुटि",

    showing: "दिखाए जा रहे हैं",
    of: "में से",
    results: "परिणाम",

    previous: "पिछला",
    next: "अगला",

    openSource: "स्रोत खोलें",
    close: "बंद करें",

    answer: "उत्तर",
    explanation: "व्याख्या",

    dailyAccess: "दैनिक एक्सेस",
    oneDay: "24 घंटे",

    price: "कीमत",
    includes: "शामिल",

    noImage: "कोई चित्र उपलब्ध नहीं है",

    paymentChecking:
      "भुगतान की जाँच की जा रही है...",

    paymentCancelled:
      "भुगतान रद्द कर दिया गया।",
  },

  en: {
    title: "Current Affairs",

    subtitle:
      "AI-curated current affairs for UPSC & BPSC preparation",

    searchPlaceholder:
      "Search current affairs...",

    search: "Search",

    filters: "Filters",
    activeFilters: "Active Filters",
    reset: "Reset",

    exam: "Exam",
    allExams: "All Exams",

    category: "Category",
    allCategories: "All Categories",

    language: "Language",

    hindi: "हिंदी",
    english: "English",

    bihar: "Bihar Only",

    noNews: "No current affairs found",

    noNewsDescription:
      "No news is available for the selected filters.",

    loading:
      "Loading current affairs...",

    refresh: "Refresh",
    readMore: "Read More",

    articleDetails: "Article Details",

    examQuestions:
      "Exam-oriented questions based on this article",

    newsMCQs: "News MCQs",

    noMCQ:
      "No MCQs are currently available for this article.",

    generateMCQ: "Generate MCQs",

    generating: "Generating...",

    unlockNews:
      "Unlock Today's Current Affairs",

    unlockDescription:
      "Pay only ₹1 to read today's UPSC & BPSC Current Affairs.",

    payRead:
      "Pay ₹1 & Read Today's News",

    processing: "Processing...",

    securePayment:
      "Secure payment via Razorpay",

    paymentSuccess:
      "Payment successful.",

    paymentFailed:
      "Payment failed.",

    paymentStartFailed:
      "Unable to start payment.",

    articleIdMissing:
      "Article ID is not available.",

    mcqGenerationFailed:
      "Unable to generate MCQs.",

    newsLoadFailed:
      "Unable to load current affairs.",

    razorpayNotLoaded:
      "Razorpay SDK is not loaded.",

    razorpayKeyMissing:
      "Razorpay key is missing.",

    invalidOrder:
      "Invalid Razorpay order response.",

    currentAffairs:
      "Current Affairs",

    readTodaysNews:
      "Read Today's Current Affairs",

    date: "Date",
    source: "Source",

    relatedQuestions:
      "Related Exam Questions",

    examOriented:
      "Exam-oriented Questions",

    retry: "Retry",
    error: "Error",

    showing: "Showing",
    of: "of",
    results: "results",

    previous: "Previous",
    next: "Next",

    openSource: "Open Source",
    close: "Close",

    answer: "Answer",
    explanation: "Explanation",

    dailyAccess: "Daily Access",
    oneDay: "24 Hours",

    price: "Price",
    includes: "Includes",

    noImage: "No image available",

    paymentChecking:
      "Checking payment...",

    paymentCancelled:
      "Payment was cancelled.",
  },
};

/*
|--------------------------------------------------------------------------
| PAYMENT REQUIRED ERROR
|--------------------------------------------------------------------------
*/

class PaymentRequiredError extends Error {
  constructor(detail = {}) {
    super(
      detail?.message ||
        "Today's current affairs require payment."
    );

    this.name = "PaymentRequiredError";
    this.code = "NEWS_PAYMENT_REQUIRED";
    this.paymentRequired = true;

    this.amount =
      Number(detail?.amount ?? 1);

    this.currency =
      detail?.currency || "INR";

    this.paymentEndpoint =
      detail?.payment_endpoint ||
      "/news/payment/create-order";
  }
}

/*
|--------------------------------------------------------------------------
| HELPERS
|--------------------------------------------------------------------------
*/

function safeString(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  if (typeof value === "string") {
    return value;
  }

  if (
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

function getErrorMessage(
  error,
  language = "en"
) {
  if (!error) {
    return language === "hi"
      ? "कुछ गलत हो गया।"
      : "Something went wrong.";
  }

  if (
    error instanceof Error &&
    error.message
  ) {
    return error.message;
  }

  if (typeof error === "string") {
    return error;
  }

  if (
    typeof error === "object"
  ) {
    if (error.detail) {
      if (
        typeof error.detail ===
        "string"
      ) {
        return error.detail;
      }

      if (
        Array.isArray(
          error.detail
        )
      ) {
        return error.detail
          .map((item) => {
            if (
              typeof item === "string"
            ) {
              return item;
            }

            return (
              item?.msg ||
              item?.message ||
              JSON.stringify(item)
            );
          })
          .join(", ");
      }

      if (
        typeof error.detail ===
        "object"
      ) {
        return (
          error.detail.message ||
          error.detail.msg ||
          error.detail.error ||
          JSON.stringify(
            error.detail
          )
        );
      }
    }

    if (error.message) {
      return safeString(
        error.message
      );
    }

    if (error.error) {
      return safeString(
        error.error
      );
    }

    try {
      return JSON.stringify(error);
    } catch {
      return language === "hi"
        ? "अनुरोध विफल हुआ।"
        : "Request failed.";
    }
  }

  return safeString(error);
}

function getCategoryLabel(
  category,
  language
) {
  const found =
    CATEGORIES.find(
      (item) =>
        item.value === category
    );

  if (!found) {
    return safeString(category);
  }

  return (
    found[language] ||
    found.en
  );
}

function getArticleId(article) {
  return (
    article?.id ??
    article?.article_id ??
    article?.news_id ??
    article?.current_affair_id ??
    null
  );
}

function getArticleTitle(article) {
  if (!article) {
    return "";
  }

  if (
    typeof article.title ===
    "object"
  ) {
    return (
      article.title?.[
        article.language
      ] ||
      article.title?.en ||
      article.title?.hi ||
      ""
    );
  }

  return (
    article.title ||
    article.headline ||
    article.name ||
    "Untitled"
  );
}

function getArticleDescription(
  article
) {
  if (!article) {
    return "";
  }

  if (
    typeof article.description ===
    "object"
  ) {
    return (
      article.description?.[
        article.language
      ] ||
      article.description?.en ||
      article.description?.hi ||
      ""
    );
  }

  return (
    article.description ||
    article.summary ||
    article.content ||
    ""
  );
}

function getArticleImage(article) {
  return (
    article?.urlToImage ||
    article?.image_url ||
    article?.image ||
    article?.thumbnail ||
    article?.imageUrl ||
    ""
  );
}

function getArticleSource(article) {
  if (!article) {
    return "";
  }

  if (
    typeof article.source ===
    "object"
  ) {
    return (
      article.source?.name ||
      article.source?.title ||
      ""
    );
  }

  return (
    article.source ||
    article.source_name ||
    article.publisher ||
    ""
  );
}

function getArticleDate(article) {
  return (
    article?.published_at ||
    article?.publishedAt ||
    article?.date ||
    article?.created_at ||
    ""
  );
}

function getArticleCategory(article) {
  return (
    article?.category ||
    article?.classification ||
    "General"
  );
}

function getArticleExam(article) {
  const exam =
    article?.exam ||
    article?.exams ||
    "UPSC + BPSC";

  if (Array.isArray(exam)) {
    return exam.join(" + ");
  }

  return safeString(exam);
}

function getArticleScore(article) {
  return (
    article?.score ??
    article?.relevance_score ??
    article?.news_score ??
    null
  );
}

function getArticleUrl(article) {
  return (
    article?.url ||
    article?.article_url ||
    article?.source_url ||
    ""
  );
}

function formatDate(
  date,
  language
) {
  if (!date) {
    return "";
  }

  try {
    const parsed =
      new Date(date);

    if (
      Number.isNaN(
        parsed.getTime()
      )
    ) {
      return safeString(date);
    }

    return new Intl.DateTimeFormat(
      language === "hi"
        ? "hi-IN"
        : "en-IN",
      {
        dateStyle: "medium",
      }
    ).format(parsed);
  } catch {
    return safeString(date);
  }
}

/*
|--------------------------------------------------------------------------
| AUTH
|--------------------------------------------------------------------------
*/

function getToken() {
  return (
    localStorage.getItem(
      "token"
    ) ||
    localStorage.getItem(
      "access_token"
    ) ||
    localStorage.getItem(
      "auth_token"
    ) ||
    ""
  );
}

/*
|--------------------------------------------------------------------------
| API FETCH
|--------------------------------------------------------------------------
*/

async function apiFetch(
  endpoint,
  options = {}
) {
  const token = getToken();

  const headers = {
    Accept:
      "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization =
      `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(
      `${API_URL}${endpoint}`,
      {
        ...options,
        headers,
      }
    );
  } catch (error) {
    throw new Error(
      error?.message ||
        "Unable to connect to the server."
    );
  }

  const contentType =
    response.headers.get(
      "content-type"
    ) || "";

  let data = null;

  try {
    if (
      contentType.includes(
        "application/json"
      )
    ) {
      data =
        await response.json();
    } else {
      data =
        await response.text();
    }
  } catch {
    data = null;
  }

  /*
  |--------------------------------------------------------------------------
  | 402 PAYMENT REQUIRED
  |--------------------------------------------------------------------------
  */

  if (
    response.status === 402
  ) {
    const detail =
      data?.detail &&
      typeof data.detail ===
        "object"
        ? data.detail
        : data;

    throw new PaymentRequiredError(
      detail || {}
    );
  }

  /*
  |--------------------------------------------------------------------------
  | NORMAL HTTP ERROR
  |--------------------------------------------------------------------------
  */

  if (!response.ok) {
    let message = "";

    if (
      data &&
      typeof data ===
        "object" &&
      data.detail
    ) {
      if (
        typeof data.detail ===
        "string"
      ) {
        message =
          data.detail;
      } else if (
        Array.isArray(
          data.detail
        )
      ) {
        message =
          data.detail
            .map((item) => {
              if (
                typeof item ===
                "string"
              ) {
                return item;
              }

              if (item?.msg) {
                const location =
                  Array.isArray(
                    item.loc
                  )
                    ? item.loc.join(
                        "."
                      )
                    : "";

                return location
                  ? `${location}: ${item.msg}`
                  : item.msg;
              }

              return JSON.stringify(
                item
              );
            })
            .join("; ");
      } else if (
        typeof data.detail ===
        "object"
      ) {
        message =
          data.detail.message ||
          data.detail.error ||
          data.detail.msg ||
          JSON.stringify(
            data.detail
          );
      }
    }

    if (!message) {
      if (
        typeof data ===
        "string"
      ) {
        message = data;
      } else if (
        data &&
        typeof data ===
          "object"
      ) {
        message =
          data.message ||
          data.error ||
          "";
      }
    }

    throw new Error(
      message ||
        `Request failed (${response.status})`
    );
  }

  return data;
}

/*
|--------------------------------------------------------------------------
| NORMALIZE RAZORPAY ORDER
|--------------------------------------------------------------------------
*/

function normalizeRazorpayOrder(
  response
) {
  if (!response) {
    return null;
  }

  const rawOrder =
    response?.order ||
    response?.data?.order ||
    response?.data ||
    response;

  if (
    !rawOrder ||
    typeof rawOrder !==
      "object"
  ) {
    return null;
  }

  const id =
    rawOrder?.id ||
    rawOrder?.order_id ||
    rawOrder?.razorpay_order_id ||
    response?.order_id ||
    response?.razorpay_order_id ||
    response?.data?.order_id ||
    response?.data?.razorpay_order_id ||
    "";

  const amount =
    rawOrder?.amount ??
    response?.amount ??
    response?.data?.amount ??
    100;

  const currency =
    rawOrder?.currency ||
    response?.currency ||
    response?.data?.currency ||
    "INR";

  return {
    ...rawOrder,
    id,
    amount,
    currency,
  };
}

/*
|--------------------------------------------------------------------------
| MAIN COMPONENT
|--------------------------------------------------------------------------
*/

export default function News() {
  const [exam, setExam] =
    useState("UPSC");

  const [category, setCategory] =
    useState("ALL");

  const [language, setLanguage] =
    useState("en");

  const [biharOnly, setBiharOnly] =
    useState(false);

  const [searchQuery, setSearchQuery] =
    useState("");

  const [page, setPage] =
    useState(1);

  const [articles, setArticles] =
    useState([]);

  const [total, setTotal] =
    useState(0);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [
    paymentRequired,
    setPaymentRequired,
  ] = useState(false);

  const [
    paymentLoading,
    setPaymentLoading,
  ] = useState(false);

  const [
    paymentError,
    setPaymentError,
  ] = useState("");

  const [
    selectedArticle,
    setSelectedArticle,
  ] = useState(null);

  const [
    generatingMCQ,
    setGeneratingMCQ,
  ] = useState(null);

  const [
    mcqError,
    setMcqError,
  ] = useState("");

  const t =
    TRANSLATIONS[language] ||
    TRANSLATIONS.en;

  /*
  |--------------------------------------------------------------------------
  | TOTAL PAGES
  |--------------------------------------------------------------------------
  */

  const totalPages = useMemo(() => {
    if (
      !total ||
      total <= 0
    ) {
      return 1;
    }

    return Math.max(
      1,
      Math.ceil(
        total / PAGE_SIZE
      )
    );
  }, [total]);

  /*
  |--------------------------------------------------------------------------
  | LOAD NEWS
  |--------------------------------------------------------------------------
  */

  const loadNews = useCallback(
    async ({
      targetPage = 1,
      silent = false,
    } = {}) => {
      if (!silent) {
        setLoading(true);
      }

      setError("");

      try {
        const params =
          new URLSearchParams();

        params.set(
          "page",
          String(targetPage)
        );

        params.set(
          "page_size",
          String(PAGE_SIZE)
        );

        params.set(
          "language",
          language
        );

        if (exam !== "ALL") {
          params.set(
            "exam",
            exam
          );
        }

        if (category !== "ALL") {
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

        if (
          searchQuery.trim()
        ) {
          params.set(
            "query",
            searchQuery.trim()
          );
        }

        let data;

        try {
          data =
            await apiFetch(
              `/news/search?${params.toString()}`
            );
        } catch (
          primaryError
        ) {
          if (
            primaryError?.paymentRequired ===
              true ||
            primaryError?.code ===
              "NEWS_PAYMENT_REQUIRED"
          ) {
            throw primaryError;
          }

          if (
            exam === "UPSC" &&
            category === "ALL" &&
            !biharOnly &&
            !searchQuery.trim()
          ) {
            data =
              await apiFetch(
                `/news/upsc?page=${targetPage}&page_size=${PAGE_SIZE}&language=${language}`
              );
          } else if (
            exam === "BPSC" &&
            biharOnly &&
            category === "ALL" &&
            !searchQuery.trim()
          ) {
            data =
              await apiFetch(
                `/news/bpsc?page=${targetPage}&page_size=${PAGE_SIZE}&language=${language}`
              );
          } else {
            throw primaryError;
          }
        }

        const resultArticles =
          Array.isArray(
            data?.articles
          )
            ? data.articles
            : Array.isArray(
                data?.results
              )
            ? data.results
            : Array.isArray(
                data?.data
              )
            ? data.data
            : Array.isArray(data)
            ? data
            : [];

        const resultTotal =
          Number(
            data?.total ??
              data?.filtered_results ??
              data?.total_results ??
              data?.raw_total_results ??
              resultArticles.length
          );

        setArticles(
          resultArticles
        );

        setTotal(
          Number.isFinite(
            resultTotal
          )
            ? resultTotal
            : resultArticles.length
        );

        setPaymentRequired(
          Boolean(
            data?.payment_required ||
              data?.requires_payment ||
              data?.locked
          )
        );
      } catch (err) {
        console.error(
          "News loading error:",
          err
        );

        if (
          err?.paymentRequired ===
            true ||
          err?.code ===
            "NEWS_PAYMENT_REQUIRED"
        ) {
          setArticles([]);
          setTotal(0);
          setError("");
          setPaymentError("");
          setPaymentRequired(true);
          return;
        }

        setArticles([]);
        setTotal(0);
        setPaymentRequired(false);

        setError(
          getErrorMessage(
            err,
            language
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [
      language,
      exam,
      category,
      biharOnly,
      searchQuery,
    ]
  );

  /*
  |--------------------------------------------------------------------------
  | INITIAL / FILTER LOAD
  |--------------------------------------------------------------------------
  */

  useEffect(() => {
    loadNews({
      targetPage: page,
    });
  }, [
    page,
    language,
    exam,
    category,
    biharOnly,
    loadNews,
  ]);

  /*
  |--------------------------------------------------------------------------
  | FILTER HANDLERS
  |--------------------------------------------------------------------------
  */

  function handleExamChange(
    value
  ) {
    setExam(value);
    setPage(1);
    setSelectedArticle(null);
    setPaymentError("");
  }

  function handleCategoryChange(
    value
  ) {
    setCategory(value);
    setPage(1);
    setSelectedArticle(null);
    setPaymentError("");
  }

  function handleLanguageChange(
    value
  ) {
    setLanguage(value);
    setPage(1);
    setSelectedArticle(null);
    setPaymentError("");
  }

  function handleBiharChange(
    event
  ) {
    const checked =
      event.target.checked;

    setBiharOnly(checked);
    setPage(1);
    setSelectedArticle(null);

    if (
      checked &&
      exam === "ALL"
    ) {
      setExam("BPSC");
    }
  }

  /*
  |--------------------------------------------------------------------------
  | SEARCH
  |--------------------------------------------------------------------------
  */

  function handleSearch(event) {
    event.preventDefault();

    setPage(1);

    loadNews({
      targetPage: 1,
    });
  }

  /*
  |--------------------------------------------------------------------------
  | RESET
  |--------------------------------------------------------------------------
  */

  function resetFilters() {
    setExam("UPSC");
    setCategory("ALL");
    setLanguage("en");
    setBiharOnly(false);
    setSearchQuery("");
    setPage(1);
    setSelectedArticle(null);
    setError("");
    setPaymentError("");
    setPaymentRequired(false);
  }

  /*
  |--------------------------------------------------------------------------
  | REFRESH
  |--------------------------------------------------------------------------
  */

  function refreshNews() {
    loadNews({
      targetPage: page,
    });
  }

  /*
  |--------------------------------------------------------------------------
  | PAGINATION
  |--------------------------------------------------------------------------
  */

  function goToPage(
    nextPage
  ) {
    if (
      nextPage < 1 ||
      nextPage > totalPages ||
      loading
    ) {
      return;
    }

    setPage(nextPage);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }

  /*
  |--------------------------------------------------------------------------
  | OPEN ARTICLE
  |--------------------------------------------------------------------------
  */

  async function openArticle(
    article
  ) {
    setMcqError("");

    const id =
      getArticleId(article);

    if (id) {
      try {
        const data =
          await apiFetch(
            `/news/${id}`
          );

        const detail =
          data?.article ||
          data?.news ||
          data?.data ||
          data;

        if (
          detail &&
          typeof detail ===
            "object"
        ) {
          setSelectedArticle({
            ...article,
            ...detail,
          });

          return;
        }
      } catch (err) {
        console.warn(
          "Article detail unavailable:",
          err
        );
      }
    }

    setSelectedArticle(article);
  }

  function closeArticle() {
    setSelectedArticle(null);
    setMcqError("");
  }

  /*
  |--------------------------------------------------------------------------
  | GENERATE MCQS
  |--------------------------------------------------------------------------
  */

  async function generateMCQs(
    article
  ) {
    const id =
      getArticleId(article);

    if (!id) {
      setMcqError(
        t.articleIdMissing
      );
      return;
    }

    setGeneratingMCQ(id);
    setMcqError("");

    try {
      const data =
        await apiFetch(
          `/news/${id}/mcqs/generate`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              language,
              exam:
                exam === "ALL"
                  ? "UPSC"
                  : exam,
              category:
                category === "ALL"
                  ? "General"
                  : category,
            }),
          }
        );

      const mcqs =
        data?.mcqs ||
        data?.questions ||
        data?.data?.mcqs ||
        [];

      setSelectedArticle(
        (current) => ({
          ...(current || article),
          mcqs:
            Array.isArray(mcqs)
              ? mcqs
              : [],
        })
      );
    } catch (err) {
      console.error(
        "MCQ generation error:",
        err
      );

      setMcqError(
        getErrorMessage(
          err,
          language
        ) ||
          t.mcqGenerationFailed
      );
    } finally {
      setGeneratingMCQ(null);
    }
  }

  /*
  |--------------------------------------------------------------------------
  | RAZORPAY PAYMENT
  |--------------------------------------------------------------------------
  */

  async function payForNews() {
    if (paymentLoading) {
      return;
    }

    setPaymentLoading(true);
    setPaymentError("");

    try {
      /*
      |--------------------------------------------------------------------------
      | CHECK RAZORPAY SDK
      |--------------------------------------------------------------------------
      */

      if (
        typeof window ===
          "undefined" ||
        !window.Razorpay
      ) {
        throw new Error(
          t.razorpayNotLoaded
        );
      }

      /*
      |--------------------------------------------------------------------------
      | FRONTEND KEY
      |--------------------------------------------------------------------------
      */

      if (!RAZORPAY_KEY) {
        console.warn(
          "VITE_RAZORPAY_KEY_ID is empty."
        );
      }

      /*
      |--------------------------------------------------------------------------
      | CREATE ORDER
      |--------------------------------------------------------------------------
      */

      const orderResponse =
        await apiFetch(
          "/news/payment/create-order",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              report_type:
                "current_affairs",

              amount: 1,

              exam:
                exam === "ALL"
                  ? "UPSC"
                  : exam,

              category:
                category === "ALL"
                  ? "General"
                  : category,

              language,
            }),
          }
        );

      console.log(
        "========== RAZORPAY ORDER RESPONSE =========="
      );

      console.log(
        "Full response:",
        orderResponse
      );

      /*
      |--------------------------------------------------------------------------
      | FREE RESPONSE
      |--------------------------------------------------------------------------
      */

      if (
        orderResponse?.free ===
        true
      ) {
        setPaymentRequired(false);
        setPaymentError("");
        setPage(1);

        await loadNews({
          targetPage: 1,
        });

        return;
      }

      /*
      |--------------------------------------------------------------------------
      | NORMALIZE ORDER
      |--------------------------------------------------------------------------
      */

      const order =
        normalizeRazorpayOrder(
          orderResponse
        );

      /*
      |--------------------------------------------------------------------------
      | RAZORPAY KEY
      |--------------------------------------------------------------------------
      */

      const razorpayKey =
        orderResponse?.key ||
        orderResponse?.razorpay_key ||
        orderResponse?.razorpayKey ||
        orderResponse?.data?.key ||
        orderResponse?.data?.razorpay_key ||
        RAZORPAY_KEY;

      console.log(
        "Normalized order:",
        order
      );

      console.log(
        "Razorpay key:",
        razorpayKey
      );

      /*
      |--------------------------------------------------------------------------
      | KEY VALIDATION
      |--------------------------------------------------------------------------
      */

      if (!razorpayKey) {
        throw new Error(
          t.razorpayKeyMissing
        );
      }

      /*
      |--------------------------------------------------------------------------
      | ORDER VALIDATION
      |--------------------------------------------------------------------------
      */

      if (
        !order ||
        !order.id
      ) {
        console.error(
          "❌ INVALID RAZORPAY ORDER",
          {
            response:
              orderResponse,
            normalizedOrder:
              order,
          }
        );

        throw new Error(
          t.invalidOrder
        );
      }

      console.log(
        "✅ Razorpay Order ID:",
        order.id
      );

      console.log(
        "✅ Razorpay Amount:",
        order.amount
      );

      console.log(
        "✅ Razorpay Currency:",
        order.currency
      );

      /*
      |--------------------------------------------------------------------------
      | RAZORPAY OPTIONS
      |--------------------------------------------------------------------------
      */

      const options = {
        key: razorpayKey,

        amount:
          Number(
            order.amount
          ) || 100,

        currency:
          order.currency ||
          "INR",

        name:
          "UPSC & BPSC",

        description:
          "Current Affairs - 1 Day Access",

        order_id:
          order.id,

        prefill: {
          name:
            localStorage.getItem(
              "user_name"
            ) || "",

          email:
            localStorage.getItem(
              "user_email"
            ) || "",

          contact:
            localStorage.getItem(
              "user_phone"
            ) || "",
        },

        notes: {
          product:
            "current_affairs",

          exam:
            exam === "ALL"
              ? "UPSC"
              : exam,

          category:
            category === "ALL"
              ? "General"
              : category,

          language,
        },

        theme: {
          color:
            "#4F46E5",
        },

        handler:
          async function (
            razorpayResponse
          ) {
            console.log(
              "Razorpay success:",
              razorpayResponse
            );

            setPaymentLoading(true);
            setPaymentError("");

            try {
              /*
              |--------------------------------------------------------------------------
              | VERIFY PAYMENT
              |--------------------------------------------------------------------------
              */

              const verifyResponse =
                await apiFetch(
                  "/news/payment/verify",
                  {
                    method: "POST",

                    headers: {
                      "Content-Type":
                        "application/json",
                    },

                    body:
                      JSON.stringify({
                        report_type:
                          "current_affairs",

                        exam:
                          exam ===
                          "ALL"
                            ? "UPSC"
                            : exam,

                        category:
                          category ===
                          "ALL"
                            ? "General"
                            : category,

                        language,

                        razorpay_order_id:
                          razorpayResponse.razorpay_order_id,

                        razorpay_payment_id:
                          razorpayResponse.razorpay_payment_id,

                        razorpay_signature:
                          razorpayResponse.razorpay_signature,
                      }),
                  }
                );

              console.log(
                "Payment verification:",
                verifyResponse
              );

              if (
                verifyResponse?.success ===
                  false ||
                verifyResponse?.verified ===
                  false
              ) {
                throw new Error(
                  getErrorMessage(
                    verifyResponse,
                    language
                  )
                );
              }

              /*
              |--------------------------------------------------------------------------
              | PAYMENT SUCCESS
              |--------------------------------------------------------------------------
              */

              setPaymentRequired(
                false
              );

              setPaymentError("");
              setError("");
              setPage(1);

              /*
              |--------------------------------------------------------------------------
              | WAIT FOR ENTITLEMENT
              |--------------------------------------------------------------------------
              */

              await new Promise(
                (resolve) =>
                  setTimeout(
                    resolve,
                    700
                  )
              );

              await loadNews({
                targetPage: 1,
              });
            } catch (err) {
              console.error(
                "Payment verification error:",
                err
              );

              setPaymentError(
                getErrorMessage(
                  err,
                  language
                )
              );
            } finally {
              setPaymentLoading(
                false
              );
            }
          },

        modal: {
          ondismiss:
            function () {
              console.log(
                "Razorpay checkout closed"
              );

              setPaymentLoading(
                false
              );
            },
        },
      };

      /*
      |--------------------------------------------------------------------------
      | CREATE RAZORPAY INSTANCE
      |--------------------------------------------------------------------------
      */

      const razorpay =
        new window.Razorpay(
          options
        );

      razorpay.on(
        "payment.failed",
        function (response) {
          console.error(
            "Razorpay payment failed:",
            response?.error
          );

          setPaymentError(
            response?.error
              ?.description ||
              t.paymentFailed
          );

          setPaymentLoading(
            false
          );
        }
      );

      /*
      |--------------------------------------------------------------------------
      | OPEN CHECKOUT
      |--------------------------------------------------------------------------
      */

      razorpay.open();
    } catch (err) {
      console.error(
        "Payment start error:",
        err
      );

      setPaymentError(
        getErrorMessage(
          err,
          language
        ) ||
          t.paymentStartFailed
      );

      setPaymentLoading(false);
    }
  }

  /*
  |--------------------------------------------------------------------------
  | ACTIVE FILTER COUNT
  |--------------------------------------------------------------------------
  */

  const activeFilterCount =
    [
      exam !== "ALL",
      category !== "ALL",
      language !== "en",
      biharOnly,
      Boolean(
        searchQuery.trim()
      ),
    ].filter(Boolean).length;

  /*
  |--------------------------------------------------------------------------
  | RENDER
  |--------------------------------------------------------------------------
  */

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">

        {/* HEADER */}

        <div className="mb-7">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-2 inline-flex items-center rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700">
                UPSC & BPSC
              </div>

              <h1 className="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl">
                {t.title}
              </h1>

              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
                {t.subtitle}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() =>
                  handleLanguageChange(
                    "hi"
                  )
                }
                className={`rounded-xl px-4 py-2.5 text-sm font-bold transition ${
                  language === "hi"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                हिंदी
              </button>

              <button
                type="button"
                onClick={() =>
                  handleLanguageChange(
                    "en"
                  )
                }
                className={`rounded-xl px-4 py-2.5 text-sm font-bold transition ${
                  language === "en"
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                English
              </button>
            </div>
          </div>
        </div>

        {/* SEARCH */}

        <form
          onSubmit={handleSearch}
          className="mb-6"
        >
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lg">
                🔍
              </span>

              <input
                type="search"
                value={searchQuery}
                onChange={(event) =>
                  setSearchQuery(
                    event.target.value
                  )
                }
                placeholder={
                  t.searchPlaceholder
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-11 py-3.5 text-sm font-medium text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-indigo-600 px-6 py-3.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {t.search}
            </button>
          </div>
        </form>

        {/* FILTERS */}

        <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xl">
                ⚙️
              </span>

              <h2 className="font-extrabold text-slate-900">
                {t.filters}
              </h2>

              {activeFilterCount >
                0 && (
                <span className="rounded-full bg-indigo-100 px-2.5 py-1 text-xs font-bold text-indigo-700">
                  {
                    activeFilterCount
                  }
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={
                resetFilters
              }
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
            >
              {t.reset}
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">

            {/* EXAM */}

            <div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-slate-500">
                {t.exam}
              </label>

              <select
                value={exam}
                onChange={(event) =>
                  handleExamChange(
                    event.target.value
                  )
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              >
                <option value="ALL">
                  {t.allExams}
                </option>

                <option value="UPSC">
                  UPSC
                </option>

                <option value="BPSC">
                  BPSC
                </option>
              </select>
            </div>

            {/* CATEGORY */}

            <div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-slate-500">
                {t.category}
              </label>

              <select
                value={category}
                onChange={(event) =>
                  handleCategoryChange(
                    event.target.value
                  )
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              >
                <option value="ALL">
                  {t.allCategories}
                </option>

                {CATEGORIES.map(
                  (item) => (
                    <option
                      key={
                        item.value
                      }
                      value={
                        item.value
                      }
                    >
                      {
                        item[
                          language
                        ]
                      }
                    </option>
                  )
                )}
              </select>
            </div>

            {/* LANGUAGE */}

            <div>
              <label className="mb-1.5 block text-xs font-bold uppercase tracking-wide text-slate-500">
                {t.language}
              </label>

              <select
                value={language}
                onChange={(event) =>
                  handleLanguageChange(
                    event.target.value
                  )
                }
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              >
                <option value="hi">
                  हिंदी
                </option>

                <option value="en">
                  English
                </option>
              </select>
            </div>

            {/* BIHAR */}

            <div className="flex items-end">
              <label className="flex min-h-[46px] w-full cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 transition hover:bg-slate-100">
                <input
                  type="checkbox"
                  checked={
                    biharOnly
                  }
                  onChange={
                    handleBiharChange
                  }
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />

                <span className="text-sm font-semibold text-slate-700">
                  🇮🇳 {t.bihar}
                </span>
              </label>
            </div>
          </div>
        </div>

        {/* ACTIVE FILTERS */}

        <div className="mb-5 flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wide text-slate-400">
            {t.activeFilters}:
          </span>

          {exam !== "ALL" && (
            <span className="rounded-full bg-indigo-100 px-3 py-1.5 text-xs font-bold text-indigo-700">
              {exam}
            </span>
          )}

          {category !== "ALL" && (
            <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-semibold text-emerald-700">
              {getCategoryLabel(
                category,
                language
              )}
            </span>
          )}

          <span className="rounded-full bg-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700">
            {language === "hi"
              ? "हिंदी"
              : "English"}
          </span>

          {biharOnly && (
            <span className="rounded-full bg-orange-100 px-3 py-1.5 text-xs font-semibold text-orange-700">
              🇮🇳 {t.bihar}
            </span>
          )}

          {searchQuery.trim() && (
            <span className="max-w-[250px] truncate rounded-full bg-purple-100 px-3 py-1.5 text-xs font-semibold text-purple-700">
              🔍{" "}
              {searchQuery}
            </span>
          )}
        </div>

        {/* PAYMENT */}

        {paymentRequired &&
          !loading && (
            <div className="mb-6 overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-lg">
              <div className="bg-gradient-to-r from-indigo-600 to-violet-600 p-6 text-white">
                <div className="flex items-start gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-3xl">
                    🔐
                  </div>

                  <div>
                    <h2 className="text-xl font-extrabold">
                      {
                        t.unlockNews
                      }
                    </h2>

                    <p className="mt-1 text-sm leading-6 text-indigo-100">
                      {
                        t.unlockDescription
                      }
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-6">
                <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl bg-slate-50 p-4">
                    <p className="text-xs font-semibold text-slate-500">
                      {
                        t.dailyAccess
                      }
                    </p>

                    <p className="mt-1 text-lg font-extrabold text-slate-900">
                      {
                        t.oneDay
                      }
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-50 p-4">
                    <p className="text-xs font-semibold text-slate-500">
                      {t.price}
                    </p>

                    <p className="mt-1 text-lg font-extrabold text-slate-900">
                      ₹1
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-50 p-4">
                    <p className="text-xs font-semibold text-slate-500">
                      {t.includes}
                    </p>

                    <p className="mt-1 text-lg font-extrabold text-slate-900">
                      {
                        t.newsMCQs
                      }
                    </p>
                  </div>
                </div>

                {paymentError && (
                  <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                    ⚠️{" "}
                    {
                      paymentError
                    }
                  </div>
                )}

                <button
                  type="button"
                  onClick={
                    payForNews
                  }
                  disabled={
                    paymentLoading
                  }
                  className="w-full rounded-xl bg-indigo-600 px-6 py-3.5 text-sm font-extrabold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {paymentLoading
                    ? t.processing
                    : t.payRead}
                </button>

                <p className="mt-3 text-center text-xs text-slate-500">
                  🔒{" "}
                  {
                    t.securePayment
                  }
                </p>
              </div>
            </div>
          )}

        {/* ERROR */}

        {error &&
          !loading &&
          !paymentRequired && (
            <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-5">
              <div className="flex gap-4">
                <div className="text-2xl">
                  ⚠️
                </div>

                <div className="flex-1">
                  <h2 className="font-bold text-red-800">
                    {t.error}
                  </h2>

                  <p className="mt-1 break-words text-sm leading-6 text-red-700">
                    {error}
                  </p>

                  <button
                    type="button"
                    onClick={
                      refreshNews
                    }
                    className="mt-4 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-red-700"
                  >
                    {t.retry}
                  </button>
                </div>
              </div>
            </div>
          )}

        {/* LOADING */}

        {loading && (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {Array.from({
              length: 6,
            }).map(
              (_, index) => (
                <div
                  key={index}
                  className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                >
                  <div className="h-52 animate-pulse bg-slate-200" />

                  <div className="space-y-4 p-5">
                    <div className="flex gap-2">
                      <div className="h-6 w-20 animate-pulse rounded-full bg-slate-200" />
                      <div className="h-6 w-28 animate-pulse rounded-full bg-slate-200" />
                    </div>

                    <div className="h-6 w-4/5 animate-pulse rounded bg-slate-200" />

                    <div className="h-4 w-full animate-pulse rounded bg-slate-200" />

                    <div className="h-4 w-11/12 animate-pulse rounded bg-slate-200" />

                    <div className="h-10 w-32 animate-pulse rounded-lg bg-slate-200" />
                  </div>
                </div>
              )
            )}
          </div>
        )}

        {/* EMPTY */}

        {!loading &&
          !error &&
          !paymentRequired &&
          articles.length ===
            0 && (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-14 text-center shadow-sm">
              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-3xl">
                📰
              </div>

              <h2 className="text-xl font-extrabold text-slate-900">
                {t.noNews}
              </h2>

              <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-500">
                {
                  t.noNewsDescription
                }
              </p>

              <button
                type="button"
                onClick={
                  resetFilters
                }
                className="mt-5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-indigo-700"
              >
                {t.retry}
              </button>
            </div>
          )}

        {/* RESULTS */}

        {!loading &&
          !error &&
          !paymentRequired &&
          articles.length >
            0 && (
            <>
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-slate-500">
                  {t.showing}{" "}
                  <span className="font-bold text-slate-900">
                    {
                      articles.length
                    }
                  </span>{" "}
                  {t.of}{" "}
                  <span className="font-bold text-slate-900">
                    {total ||
                      articles.length}
                  </span>{" "}
                  {t.results}
                </p>

                <button
                  type="button"
                  onClick={
                    refreshNews
                  }
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                >
                  ↻ {t.refresh}
                </button>
              </div>

              {/* NEWS GRID */}

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {articles.map(
                  (
                    article,
                    index
                  ) => {
                    const id =
                      getArticleId(
                        article
                      );

                    const title =
                      getArticleTitle(
                        article
                      );

                    const description =
                      getArticleDescription(
                        article
                      );

                    const image =
                      getArticleImage(
                        article
                      );

                    const source =
                      getArticleSource(
                        article
                      );

                    const date =
                      getArticleDate(
                        article
                      );

                    const articleCategory =
                      getArticleCategory(
                        article
                      );

                    const articleExam =
                      getArticleExam(
                        article
                      );

                    const score =
                      getArticleScore(
                        article
                      );

                    const externalUrl =
                      getArticleUrl(
                        article
                      );

                    return (
                      <article
                        key={
                          id ??
                          `${page}-${index}`
                        }
                        className="group overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:shadow-lg"
                      >
                        <div className="relative h-52 overflow-hidden bg-slate-100">
                          {image ? (
                            <img
                              src={image}
                              alt={title}
                              loading="lazy"
                              className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                              onError={(
                                event
                              ) => {
                                event.currentTarget.style.display =
                                  "none";
                              }}
                            />
                          ) : (
                            <div className="flex h-full items-center justify-center text-slate-400">
                              <div className="text-center">
                                <div className="text-4xl">
                                  📰
                                </div>

                                <p className="mt-2 text-xs font-medium">
                                  {
                                    t.noImage
                                  }
                                </p>
                              </div>
                            </div>
                          )}

                          <div className="absolute left-4 top-4 flex flex-wrap gap-2">
                            <span className="rounded-full bg-white/95 px-3 py-1 text-xs font-extrabold text-indigo-700 shadow-sm backdrop-blur">
                              {
                                articleExam
                              }
                            </span>
                          </div>
                        </div>

                        <div className="p-5">
                          <div className="mb-3 flex flex-wrap gap-2">
                            <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-700">
                              {getCategoryLabel(
                                articleCategory,
                                language
                              )}
                            </span>

                            {score !==
                              null &&
                              score !==
                                undefined && (
                                <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-700">
                                  Score:{" "}
                                  {safeString(
                                    score
                                  )}
                                </span>
                              )}
                          </div>

                          <h2 className="line-clamp-3 text-xl font-extrabold leading-snug text-slate-900">
                            {title}
                          </h2>

                          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-500">
                            {source && (
                              <span>
                                📰{" "}
                                {source}
                              </span>
                            )}

                            {date && (
                              <span>
                                📅{" "}
                                {formatDate(
                                  date,
                                  language
                                )}
                              </span>
                            )}
                          </div>

                          {description && (
                            <p className="mt-4 line-clamp-4 text-sm leading-6 text-slate-600">
                              {
                                description
                              }
                            </p>
                          )}

                          <div className="mt-5 flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() =>
                                openArticle(
                                  article
                                )
                              }
                              className="rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200"
                            >
                              {
                                t.readMore
                              }
                            </button>

                            {id && (
                              <button
                                type="button"
                                disabled={
                                  generatingMCQ ===
                                  id
                                }
                                onClick={() =>
                                  generateMCQs(
                                    article
                                  )
                                }
                                className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2.5 text-sm font-bold text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {generatingMCQ ===
                                id
                                  ? t.generating
                                  : t.generateMCQ}
                              </button>
                            )}

                            {externalUrl && (
                              <a
                                href={
                                  externalUrl
                                }
                                target="_blank"
                                rel="noopener noreferrer"
                                className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                              >
                                ↗{" "}
                                {
                                  t.openSource
                                }
                              </a>
                            )}
                          </div>
                        </div>
                      </article>
                    );
                  }
                )}
              </div>

              {/* PAGINATION */}

              {totalPages >
                1 && (
                <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
                    <button
                      type="button"
                      disabled={
                        page <= 1 ||
                        loading
                      }
                      onClick={() =>
                        goToPage(
                          page - 1
                        )
                      }
                      className="w-full rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
                    >
                      ←{" "}
                      {
                        t.previous
                      }
                    </button>

                    <div className="text-sm font-bold text-slate-600">
                      Page{" "}
                      <span className="text-indigo-600">
                        {page}
                      </span>{" "}
                      of{" "}
                      <span className="text-indigo-600">
                        {
                          totalPages
                        }
                      </span>
                    </div>

                    <button
                      type="button"
                      disabled={
                        page >=
                          totalPages ||
                        loading
                      }
                      onClick={() =>
                        goToPage(
                          page + 1
                        )
                      }
                      className="w-full rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 sm:w-auto"
                    >
                      {t.next} →
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

        {/* ARTICLE MODAL */}

        {selectedArticle && (
          <div
            className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 p-4 backdrop-blur-sm"
            onMouseDown={(
              event
            ) => {
              if (
                event.target ===
                event.currentTarget
              ) {
                closeArticle();
              }
            }}
          >
            <div className="mx-auto my-8 max-w-4xl overflow-hidden rounded-3xl bg-white shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 sm:px-7">
                <h2 className="text-lg font-extrabold text-slate-900">
                  {
                    t.articleDetails
                  }
                </h2>

                <button
                  type="button"
                  onClick={
                    closeArticle
                  }
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-lg font-bold text-slate-600 transition hover:bg-slate-200"
                  aria-label={
                    t.close
                  }
                >
                  ×
                </button>
              </div>

              <div className="max-h-[80vh] overflow-y-auto">
                {getArticleImage(
                  selectedArticle
                ) && (
                  <img
                    src={getArticleImage(
                      selectedArticle
                    )}
                    alt={getArticleTitle(
                      selectedArticle
                    )}
                    className="h-64 w-full object-cover sm:h-80"
                  />
                )}

                <div className="p-5 sm:p-7">
                  <div className="mb-4 flex flex-wrap gap-2">
                    <span className="rounded-full bg-indigo-100 px-3 py-1.5 text-xs font-bold text-indigo-700">
                      {getArticleExam(
                        selectedArticle
                      )}
                    </span>

                    <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-xs font-bold text-emerald-700">
                      {getCategoryLabel(
                        getArticleCategory(
                          selectedArticle
                        ),
                        language
                      )}
                    </span>
                  </div>

                  <h1 className="text-2xl font-black leading-tight text-slate-900 sm:text-3xl">
                    {getArticleTitle(
                      selectedArticle
                    )}
                  </h1>

                  <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
                    {getArticleSource(
                      selectedArticle
                    ) && (
                      <span>
                        📰{" "}
                        {
                          getArticleSource(
                            selectedArticle
                          )
                        }
                      </span>
                    )}

                    {getArticleDate(
                      selectedArticle
                    ) && (
                      <span>
                        📅{" "}
                        {formatDate(
                          getArticleDate(
                            selectedArticle
                          ),
                          language
                        )}
                      </span>
                    )}
                  </div>

                  <div className="mt-6 whitespace-pre-line text-sm leading-7 text-slate-700">
                    {getArticleDescription(
                      selectedArticle
                    )}
                  </div>

                  {/* MCQS */}

                  <div className="mt-8 border-t border-slate-200 pt-7">
                    <div className="mb-5">
                      <h3 className="text-xl font-black text-slate-900">
                        📝{" "}
                        {
                          t.examQuestions
                        }
                      </h3>

                      <p className="mt-1 text-sm text-slate-500">
                        {
                          t.examQuestions
                        }
                      </p>
                    </div>

                    {Array.isArray(
                      selectedArticle.mcqs
                    ) &&
                    selectedArticle
                      .mcqs.length >
                      0 ? (
                      <div className="space-y-5">
                        {selectedArticle.mcqs.map(
                          (
                            mcq,
                            index
                          ) => (
                            <div
                              key={
                                mcq?.id ??
                                index
                              }
                              className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                            >
                              <p className="font-bold leading-7 text-slate-900">
                                {index +
                                  1}
                                .{" "}
                                {mcq?.question ||
                                  mcq?.question_text ||
                                  mcq?.text ||
                                  ""}
                              </p>

                              {Array.isArray(
                                mcq?.options
                              ) && (
                                <div className="mt-4 space-y-2">
                                  {mcq.options.map(
                                    (
                                      option,
                                      optionIndex
                                    ) => (
                                      <div
                                        key={
                                          optionIndex
                                        }
                                        className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700"
                                      >
                                        <span className="mr-2 font-bold text-indigo-600">
                                          {String.fromCharCode(
                                            65 +
                                              optionIndex
                                          )}
                                          .
                                        </span>

                                        {typeof option ===
                                        "string"
                                          ? option
                                          : option?.text ||
                                            option?.label ||
                                            ""}
                                      </div>
                                    )
                                  )}
                                </div>
                              )}

                              {mcq?.answer && (
                                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                                  <p className="text-sm font-bold text-emerald-800">
                                    {
                                      t.answer
                                    }
                                    :{" "}
                                    {safeString(
                                      mcq.answer
                                    )}
                                  </p>
                                </div>
                              )}

                              {mcq?.explanation && (
                                <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50 p-3">
                                  <p className="text-sm leading-6 text-blue-800">
                                    <strong>
                                      {
                                        t.explanation
                                      }:
                                    </strong>{" "}
                                    {safeString(
                                      mcq.explanation
                                    )}
                                  </p>
                                </div>
                              )}
                            </div>
                          )
                        )}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
                        {t.noMCQ}
                      </div>
                    )}

                    {mcqError && (
                      <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-700">
                        {
                          mcqError
                        }
                      </div>
                    )}

                    <div className="mt-6 flex flex-wrap gap-3">
                      {getArticleId(
                        selectedArticle
                      ) && (
                        <button
                          type="button"
                          disabled={
                            generatingMCQ ===
                            getArticleId(
                              selectedArticle
                            )
                          }
                          onClick={() =>
                            generateMCQs(
                              selectedArticle
                            )
                          }
                          className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {generatingMCQ ===
                          getArticleId(
                            selectedArticle
                          )
                            ? t.generating
                            : t.generateMCQ}
                        </button>
                      )}

                      {getArticleUrl(
                        selectedArticle
                      ) && (
                        <a
                          href={getArticleUrl(
                            selectedArticle
                          )}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                        >
                          ↗{" "}
                          {
                            t.openSource
                          }
                        </a>
                      )}

                      <button
                        type="button"
                        onClick={
                          closeArticle
                        }
                        className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                      >
                        {t.close}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

