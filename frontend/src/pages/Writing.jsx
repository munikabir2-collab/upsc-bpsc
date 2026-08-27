import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

/*
|--------------------------------------------------------------------------
| MUNI48 - WRITING.JSX
|--------------------------------------------------------------------------
|
| ANSWER WRITING
| POST /writing/questions/generate
| GET  /writing/questions
| POST /writing/questions/{id}/generate-answer
| POST /writing/questions/{id}/submit
| GET  /writing/questions/{id}/submissions
|
| ESSAY WRITING
| POST /writing/essays/generate
| GET  /writing/essays
| POST /writing/essays/{id}/submit
| GET  /writing/essays/{id}/submissions
|
| WRITING SUBSCRIPTION
| GET  /writing/subscription/status
| POST /writing/payment/create-order
| POST /writing/payment/verify
|
| PLAN
| ₹39 = 7 Days = 10 Answer Submissions
|--------------------------------------------------------------------------
*/

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const EXAMS = ["UPSC", "BPSC"];

const CATEGORIES = [
  "General",
  "Polity & Governance",
  "Economy",
  "History",
  "Geography",
  "Environment",
  "Science & Technology",
  "Social Issues",
  "International Relations",
  "Ethics",
];

const QUESTION_TYPES = [
  {
    value: "short",
    label: "Short Answer",
  },
  {
    value: "long",
    label: "Long Answer",
  },
];

const TARGET_WORDS = [150, 250];

const LANGUAGES = [
  {
    value: "hi",
    label: "हिंदी",
  },
  {
    value: "en",
    label: "English",
  },
];

/* =========================================================================
   WRITING SUBSCRIPTION PLAN
========================================================================= */

const WEEKLY_PLAN = {
  name: "Weekly Writing Plan",
  plan: "weekly",
  amount: 39,
  duration_days: 7,
  answer_limit: 10,
};

/* =========================================================================
   API HELPER
========================================================================= */

async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("token");

  const headers = {
    Accept: "application/json",

    ...(options.body
      ? {
          "Content-Type": "application/json",
        }
      : {}),

    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
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
      `Backend server से connection नहीं हो पाया। सुनिश्चित करें कि FastAPI server ${API_URL} पर चल रहा है।`
    );
  }

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    let message =
      `Request failed (${response.status})`;

    if (data?.detail) {
      if (Array.isArray(data.detail)) {
        message = data.detail
          .map(
            (item) =>
              item.msg ||
              JSON.stringify(item)
          )
          .join(", ");
      } else if (
        typeof data.detail === "string"
      ) {
        message = data.detail;
      }
    }

    throw new Error(message);
  }

  return data;
}

/* =========================================================================
   HELPERS
========================================================================= */

function getWordCount(text = "") {
  return text.trim()
    ? text.trim().split(/\s+/).length
    : 0;
}

function getScoreClass(score) {
  if (score >= 75) return "score-excellent";
  if (score >= 60) return "score-good";
  if (score >= 40) return "score-average";
  return "score-low";
}

function formatDate(value) {
  if (!value) return "";

  try {
    return new Date(value).toLocaleString(
      "en-IN",
      {
        dateStyle: "medium",
        timeStyle: "short",
      }
    );
  } catch {
    return value;
  }
}

/* =========================================================================
   MAIN COMPONENT
========================================================================= */

export default function Writing() {
  /* -----------------------------------------------------------------------
     MAIN MODE
  ----------------------------------------------------------------------- */

  const [mode, setMode] =
    useState("answer");

  /* -----------------------------------------------------------------------
     COMMON
  ----------------------------------------------------------------------- */

  const [exam, setExam] =
    useState("UPSC");

  const [language, setLanguage] =
    useState("hi");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  /* =========================================================================
     WRITING SUBSCRIPTION
  ========================================================================= */

  const [subscription, setSubscription] =
    useState(null);

  const [loadingSubscription, setLoadingSubscription] =
    useState(false);

  const [buyingSubscription, setBuyingSubscription] =
    useState(false);

  /* =========================================================================
     ANSWER WRITING
  ========================================================================= */

  const [category, setCategory] =
    useState("General");

  const [questionType, setQuestionType] =
    useState("short");

  const [targetWords, setTargetWords] =
    useState(150);

  const [questions, setQuestions] =
    useState([]);

  const [selectedQuestion, setSelectedQuestion] =
    useState(null);

  const [answer, setAnswer] =
    useState("");

  const [modelAnswer, setModelAnswer] =
    useState(null);

  const [answerEvaluation, setAnswerEvaluation] =
    useState(null);

  const [answerSubmissions, setAnswerSubmissions] =
    useState([]);

  const [loadingQuestions, setLoadingQuestions] =
    useState(false);

  const [loadingModelAnswer, setLoadingModelAnswer] =
    useState(false);

  const [submittingAnswer, setSubmittingAnswer] =
    useState(false);

  const [loadingAnswerHistory, setLoadingAnswerHistory] =
    useState(false);

  /* =========================================================================
     ESSAY WRITING
  ========================================================================= */

  const [essays, setEssays] =
    useState([]);

  const [selectedEssay, setSelectedEssay] =
    useState(null);

  const [essayTopic, setEssayTopic] =
    useState("");

  const [essayText, setEssayText] =
    useState("");

  const [essayEvaluation, setEssayEvaluation] =
    useState(null);

  const [essaySubmissions, setEssaySubmissions] =
    useState([]);

  const [loadingEssays, setLoadingEssays] =
    useState(false);

  const [generatingEssay, setGeneratingEssay] =
    useState(false);

  const [submittingEssay, setSubmittingEssay] =
    useState(false);

  const [loadingEssayHistory, setLoadingEssayHistory] =
    useState(false);

  /* =========================================================================
     RESET MESSAGE
  ========================================================================= */

  const clearMessages = useCallback(() => {
    setError("");
    setSuccess("");
  }, []);

  /* =========================================================================
     FETCH SUBSCRIPTION
  ========================================================================= */

  const fetchSubscription = useCallback(
    async () => {
      setLoadingSubscription(true);

      try {
        const data = await apiRequest(
          "/writing/subscription/status"
        );

        const subscriptionData =
          data?.subscription ||
          data?.data ||
          data;

        setSubscription(
          subscriptionData || null
        );
      } catch (err) {
        /*
         * Subscription endpoint unavailable होने पर
         * Writing page पूरी तरह block नहीं होगी।
         */
        console.error(
          "Writing subscription status error:",
          err
        );

        setSubscription(null);
      } finally {
        setLoadingSubscription(false);
      }
    },
    []
  );

  /* =========================================================================
     SUBSCRIPTION HELPERS
  ========================================================================= */

  const isSubscriptionActive =
    Boolean(
      subscription?.is_active
    );

  const answerLimit =
    Number(
      subscription?.answer_limit ??
        subscription?.total_answers ??
        WEEKLY_PLAN.answer_limit
    );

  const answersUsed =
    Number(
      subscription?.answers_used ??
        subscription?.used_answers ??
        0
    );

  const remainingAnswers =
    Math.max(
      0,
      Number(
        subscription?.remaining_answers ??
          answerLimit - answersUsed
      )
    );

  const subscriptionExpiresAt =
    subscription?.expires_at ||
    subscription?.expiresAt;

  const hasAnswerAccess =
    isSubscriptionActive &&
    remainingAnswers > 0;

  const usagePercentage =
    answerLimit > 0
      ? Math.min(
          100,
          Math.max(
            0,
            (remainingAnswers /
              answerLimit) *
              100
          )
        )
      : 0;

  /* =========================================================================
     BUY ₹39 WEEKLY PLAN
  ========================================================================= */

  const buyWritingSubscription =
    async () => {
      clearMessages();

      setBuyingSubscription(true);

      try {
        const order =
          await apiRequest(
            "/writing/payment/create-order",
            {
              method: "POST",

              body: JSON.stringify({
                plan: "weekly",
              }),
            }
          );

        if (!order?.order_id) {
          throw new Error(
            "Razorpay order ID नहीं मिला।"
          );
        }

        if (!window.Razorpay) {
          throw new Error(
            "Razorpay SDK load नहीं हुआ। कृपया index.html में Razorpay script जोड़ें।"
          );
        }

        const options = {
          key:
            order.key_id ||
            import.meta.env
              .VITE_RAZORPAY_KEY_ID,

          amount: Number(order.amount),

          currency:
            order.currency || "INR",

          name: "MUNI48",

          description:
            "Writing Practice - 7 Days / 10 Answers",

          order_id:
            order.order_id,

          handler:
            async function (
              response
            ) {
              try {
                const verification =
                  await apiRequest(
                    "/writing/payment/verify",
                    {
                      method: "POST",

                      body: JSON.stringify({
                        plan: "weekly",

                        razorpay_order_id:
                          response.razorpay_order_id,

                        razorpay_payment_id:
                          response.razorpay_payment_id,

                        razorpay_signature:
                          response.razorpay_signature,
                      }),
                    }
                  );

                const verifiedSubscription =
                  verification?.subscription ||
                  verification?.data ||
                  verification;

                setSubscription(
                  verifiedSubscription
                );

                setSuccess(
                  "🎉 ₹39 Writing Plan activate हो गया। आपको 7 दिन और 10 answers मिल गए हैं।"
                );

                await fetchSubscription();
              } catch (err) {
                setError(
                  err.message ||
                    "Payment verify नहीं हो पाया।"
                );
              } finally {
                setBuyingSubscription(
                  false
                );
              }
            },

          modal: {
            ondismiss:
              function () {
                setBuyingSubscription(
                  false
                );
              },
          },

          theme: {
            color: "#172033",
          },
        };

        const razorpay =
          new window.Razorpay(
            options
          );

        razorpay.on(
          "payment.failed",
          function (
            response
          ) {
            setError(
              response?.error
                ?.description ||
                "Payment failed."
            );

            setBuyingSubscription(
              false
            );
          }
        );

        razorpay.open();
      } catch (err) {
        setError(
          err.message ||
            "Subscription order create नहीं हो पाया।"
        );

        setBuyingSubscription(false);
      }
    };

  /* =========================================================================
     GET QUESTIONS
  ========================================================================= */

  const fetchQuestions =
    useCallback(async () => {
      setLoadingQuestions(true);
      setError("");

      try {
        const data =
          await apiRequest(
            `/writing/questions?exam=${encodeURIComponent(
              exam
            )}`
          );

        const list =
          Array.isArray(data)
            ? data
            : data?.questions ||
              data?.items ||
              data?.data ||
              [];

        setQuestions(list);
      } catch (err) {
        setError(
          err.message ||
            "Questions load नहीं हो सके।"
        );
      } finally {
        setLoadingQuestions(false);
      }
    }, [exam]);

  /* =========================================================================
     GET ESSAYS
  ========================================================================= */

  const fetchEssays =
    useCallback(async () => {
      setLoadingEssays(true);
      setError("");

      try {
        const data =
          await apiRequest(
            `/writing/essays?exam=${encodeURIComponent(
              exam
            )}&language=${encodeURIComponent(
              language
            )}`
          );

        const list =
          Array.isArray(data)
            ? data
            : data?.essays ||
              data?.items ||
              data?.data ||
              [];

        setEssays(list);
      } catch (err) {
        setError(
          err.message ||
            "Essays load नहीं हो सके।"
        );
      } finally {
        setLoadingEssays(false);
      }
    }, [exam, language]);

  /* =========================================================================
     INITIAL LOAD
  ========================================================================= */

  useEffect(() => {
    fetchSubscription();

    if (mode === "answer") {
      fetchQuestions();
    } else {
      fetchEssays();
    }
  }, [
    mode,
    fetchQuestions,
    fetchEssays,
    fetchSubscription,
  ]);

  /* =========================================================================
     GENERATE QUESTION
  ========================================================================= */

  const generateQuestion =
    async () => {
      clearMessages();

      setLoading(true);

      try {
        const payload = {
          exam,
          category,
          question_type:
            questionType,
          language,
          target_words:
            Number(targetWords),
        };

        const data =
          await apiRequest(
            "/writing/questions/generate",
            {
              method: "POST",

              body: JSON.stringify(
                payload
              ),
            }
          );

        const question =
          data?.question ||
          data?.data ||
          data;

        setSelectedQuestion(
          question
        );

        setAnswer("");
        setModelAnswer(null);
        setAnswerEvaluation(null);
        setAnswerSubmissions([]);

        setSuccess(
          "नया answer-writing question generate हो गया।"
        );

        await fetchQuestions();
      } catch (err) {
        setError(
          err.message ||
            "Question generate नहीं हो पाया।"
        );
      } finally {
        setLoading(false);
      }
    };

  /* =========================================================================
     SELECT QUESTION
  ========================================================================= */

  const selectQuestion =
    (question) => {
      clearMessages();

      setSelectedQuestion(
        question
      );

      setAnswer("");
      setModelAnswer(null);
      setAnswerEvaluation(null);
      setAnswerSubmissions([]);

      /*
       * Load submission history
       */
      if (question?.id) {
        fetchAnswerSubmissions(
          question.id
        );
      }
    };

  /* =========================================================================
     GENERATE MODEL ANSWER
  ========================================================================= */

  const generateModelAnswer =
    async () => {
      if (!selectedQuestion?.id) {
        setError(
          "पहले कोई question select करें।"
        );
        return;
      }

      clearMessages();

      setLoadingModelAnswer(true);

      try {
        const data =
          await apiRequest(
            `/writing/questions/${selectedQuestion.id}/generate-answer`,
            {
              method: "POST",

              body: JSON.stringify({
                language,
              }),
            }
          );

        setModelAnswer(
          data?.answer ||
            data?.model_answer ||
            data
        );

        setSuccess(
          "AI model answer generate हो गया।"
        );
      } catch (err) {
        setError(
          err.message ||
            "Model answer generate नहीं हो पाया।"
        );
      } finally {
        setLoadingModelAnswer(false);
      }
    };

  /* =========================================================================
     SUBMIT ANSWER
  ========================================================================= */

  const submitAnswer =
    async () => {
      if (!selectedQuestion?.id) {
        setError(
          "पहले question select करें।"
        );
        return;
      }

      if (!hasAnswerAccess) {
        setError(
          "आपके पास active Writing Plan नहीं है या आपके 10 answer submissions समाप्त हो गए हैं। ₹39 में 7 दिन और 10 answers प्राप्त करें।"
        );
        return;
      }

      if (!answer.trim()) {
        setError(
          "कृपया अपना answer लिखें।"
        );
        return;
      }

      clearMessages();

      setSubmittingAnswer(true);

      try {
        const data =
          await apiRequest(
            `/writing/questions/${selectedQuestion.id}/submit`,
            {
              method: "POST",

              body: JSON.stringify({
                answer:
                  answer.trim(),
              }),
            }
          );

        const evaluation =
          data?.evaluation ||
          data;

        setAnswerEvaluation(
          evaluation
        );

        const finalScore =
          data?.score ??
          evaluation?.score ??
          0;

        const finalMaxScore =
          selectedQuestion?.target_words ===
          250
            ? 15
            : 10;

        setSuccess(
          `Answer submit हो गया। Score: ${finalScore}/${finalMaxScore}`
        );

        /*
         * Refresh subscription so
         * remaining answer count updates.
         */
        await fetchSubscription();

        await fetchAnswerSubmissions(
          selectedQuestion.id
        );
      } catch (err) {
        setError(
          err.message ||
            "Answer submit नहीं हो पाया।"
        );
      } finally {
        setSubmittingAnswer(false);
      }
    };

  /* =========================================================================
     ANSWER SUBMISSIONS
  ========================================================================= */

  const fetchAnswerSubmissions =
    async (questionId) => {
      if (!questionId) return;

      setLoadingAnswerHistory(
        true
      );

      try {
        const data =
          await apiRequest(
            `/writing/questions/${questionId}/submissions`
          );

        const list =
          Array.isArray(data)
            ? data
            : data?.submissions ||
              data?.items ||
              data?.data ||
              [];

        setAnswerSubmissions(
          list
        );
      } catch (err) {
        setError(
          err.message ||
            "Answer history load नहीं हो सकी।"
        );
      } finally {
        setLoadingAnswerHistory(
          false
        );
      }
    };

  /* =========================================================================
     GENERATE ESSAY
  ========================================================================= */

  const generateEssay =
    async () => {
      clearMessages();

      const topic =
        essayTopic.trim();

      if (!topic) {
        setError(
          language === "hi"
            ? "कृपया essay topic दर्ज करें।"
            : "Please enter an essay topic."
        );

        return;
      }

      setGeneratingEssay(true);

      try {
        const payload = {
          exam,
          language,
          topic,
          target_words: 1000,
        };

        const data =
          await apiRequest(
            "/writing/essays/generate",
            {
              method: "POST",

              body: JSON.stringify(
                payload
              ),
            }
          );

        const essayObject = {
          ...data,

          id:
            data?.id ??
            data?.essay_id,

          topic:
            data?.topic ??
            topic,

          target_words: 1000,
        };

        if (!essayObject.id) {
          throw new Error(
            "Essay generate हुआ लेकिन essay ID नहीं मिला।"
          );
        }

        setSelectedEssay(
          essayObject
        );

        setEssayTopic(
          data?.topic ?? topic
        );

        setEssayText(
          typeof data?.essay ===
            "string"
            ? data.essay
            : ""
        );

        setEssayEvaluation(null);
        setEssaySubmissions([]);

        setSuccess(
          "Essay generate हो गया। Target: 1000 words"
        );

        await fetchEssays();
      } catch (err) {
        setError(
          err.message ||
            "Essay generate नहीं हो पाया।"
        );
      } finally {
        setGeneratingEssay(
          false
        );
      }
    };

  /* =========================================================================
     SELECT ESSAY
  ========================================================================= */

  const selectEssay =
    (essay) => {
      clearMessages();

      setSelectedEssay(essay);

      setEssayTopic(
        essay?.topic || ""
      );

      setEssayText(
        essay?.essay ||
          essay?.content ||
          ""
      );

      setEssayEvaluation(null);
      setEssaySubmissions([]);

      if (essay?.id) {
        fetchEssaySubmissions(
          essay.id
        );
      }
    };

  /* =========================================================================
     SUBMIT ESSAY
  ========================================================================= */

  const submitEssay =
    async () => {
      if (!selectedEssay?.id) {
        setError(
          "पहले कोई essay select/generate करें।"
        );
        return;
      }

      if (!essayText.trim()) {
        setError(
          "कृपया essay editor में अपना पूरा essay लिखें।"
        );
        return;
      }

      const wordCount =
        getWordCount(essayText);

      if (wordCount < 20) {
        setError(
          "Essay बहुत छोटा है। कृपया कम से कम एक वास्तविक essay लिखें।"
        );
        return;
      }

      clearMessages();

      setSubmittingEssay(true);

      try {
        const data =
          await apiRequest(
            `/writing/essays/${selectedEssay.id}/submit`,
            {
              method: "POST",

              body: JSON.stringify({
                essay:
                  essayText.trim(),
              }),
            }
          );

        const evaluation =
          data?.evaluation ||
          data;

        setEssayEvaluation({
          ...evaluation,

          score:
            data?.score ??
            evaluation?.score ??
            0,

          percentage:
            data?.percentage ??
            evaluation?.percentage ??
            0,

          word_count:
            data?.word_count ??
            evaluation?.word_count ??
            wordCount,

          target_words:
            data?.target_words ??
            evaluation?.target_words ??
            1000,
        });

        const finalEssayScore =
          data?.score ??
          evaluation?.score ??
          0;

        const finalEssayMaxScore =
          data?.max_score ??
          evaluation?.max_score ??
          selectedEssay?.max_marks ??
          10;

        setSuccess(
          `Essay submit हो गया। Score: ${finalEssayScore}/${finalEssayMaxScore}`
        );

        await fetchEssaySubmissions(
          selectedEssay.id
        );
      } catch (err) {
        setError(
          err.message ||
            "Essay submit नहीं हो पाया।"
        );
      } finally {
        setSubmittingEssay(false);
      }
    };

  /* =========================================================================
     ESSAY SUBMISSIONS
  ========================================================================= */

  const fetchEssaySubmissions =
    async (essayId) => {
      if (!essayId) return;

      setLoadingEssayHistory(
        true
      );

      try {
        const data =
          await apiRequest(
            `/writing/essays/${essayId}/submissions`
          );

        const list =
          Array.isArray(data)
            ? data
            : data?.submissions ||
              data?.items ||
              data?.data ||
              [];

        setEssaySubmissions(
          list
        );
      } catch (err) {
        setError(
          err.message ||
            "Essay history load नहीं हो सकी।"
        );
      } finally {
        setLoadingEssayHistory(
          false
        );
      }
    };

  /* =========================================================================
     WORD COUNT
  ========================================================================= */

  const answerWordCount =
    useMemo(
      () =>
        getWordCount(answer),
      [answer]
    );

  const essayWordCount =
    useMemo(
      () =>
        getWordCount(essayText),
      [essayText]
    );

  /* =========================================================================
     RENDER
  ========================================================================= */

  return (
    <div className="writing-page">

      {/* =====================================================================
          HEADER
      ===================================================================== */}

      <div className="writing-header">

        <div>
          <h1>
            ✍️ Answer Writing
          </h1>

          <p>
            UPSC एवं BPSC Mains के लिए
            AI-powered answer और essay practice
          </p>
        </div>

        <div className="header-controls">

          <select
            value={exam}
            onChange={(e) => {
              setExam(
                e.target.value
              );

              setSelectedQuestion(
                null
              );

              setSelectedEssay(
                null
              );

              setEssayTopic("");
              setEssayText("");
            }}
          >
            {EXAMS.map(
              (item) => (
                <option
                  key={item}
                  value={item}
                >
                  {item}
                </option>
              )
            )}
          </select>

          <select
            value={language}
            onChange={(e) =>
              setLanguage(
                e.target.value
              )
            }
          >
            {LANGUAGES.map(
              (item) => (
                <option
                  key={item.value}
                  value={item.value}
                >
                  {item.label}
                </option>
              )
            )}
          </select>

        </div>
      </div>

      {/* =====================================================================
          ALERTS
      ===================================================================== */}

      {error && (
        <div className="writing-alert error">

          <span>⚠️</span>

          <span>
            {error}
          </span>

          <button
            onClick={() =>
              setError("")
            }
          >
            ×
          </button>

        </div>
      )}

      {success && (
        <div className="writing-alert success">

          <span>✅</span>

          <span>
            {success}
          </span>

          <button
            onClick={() =>
              setSuccess("")
            }
          >
            ×
          </button>

        </div>
      )}

      {/* =====================================================================
          MODE TABS
      ===================================================================== */}

      <div className="writing-tabs">

        <button
          className={
            mode === "answer"
              ? "active"
              : ""
          }
          onClick={() => {
            clearMessages();
            setMode("answer");
          }}
        >
          📝 Answer Writing
        </button>

        <button
          className={
            mode === "essay"
              ? "active"
              : ""
          }
          onClick={() => {
            clearMessages();
            setMode("essay");
          }}
        >
          📖 Essay Writing
        </button>

      </div>

      {/* =====================================================================
          ANSWER WRITING MODE
      ===================================================================== */}

      {mode === "answer" && (
        <div className="writing-layout">

          {/* -----------------------------------------------------------------
              SIDEBAR
          ----------------------------------------------------------------- */}

          <aside className="writing-sidebar">

            {/* ===============================================================
                SUBSCRIPTION PANEL
            =============================================================== */}

            <div className="panel subscription-panel">

              <div className="subscription-heading">

                <div>
                  <h3>
                    ✍️ Writing Plan
                  </h3>

                  <span>
                    Answer Practice
                  </span>
                </div>

                <div className="price-badge">
                  ₹39
                </div>

              </div>

              {loadingSubscription ? (
                <div className="loading">
                  Subscription loading...
                </div>
              ) : isSubscriptionActive ? (
                <>
                  <div className="subscription-active">

                    <strong>
                      ✅ Plan Active
                    </strong>

                    <span>
                      Weekly Writing Plan
                    </span>

                  </div>

                  <div className="subscription-info">

                    <div>
                      <span>
                        Plan
                      </span>

                      <strong>
                        ₹39 / 7 Days
                      </strong>
                    </div>

                    <div>
                      <span>
                        Answers
                      </span>

                      <strong>
                        {remainingAnswers} /{" "}
                        {answerLimit}
                      </strong>
                    </div>

                    {subscriptionExpiresAt && (
                      <div>
                        <span>
                          Expires
                        </span>

                        <strong>
                          {formatDate(
                            subscriptionExpiresAt
                          )}
                        </strong>
                      </div>
                    )}

                  </div>

                  {/* ANSWER USAGE */}

                  <div className="answer-usage">

                    <div className="answer-usage-header">

                      <span>
                        Remaining Answers
                      </span>

                      <strong>
                        {remainingAnswers}/
                        {answerLimit}
                      </strong>

                    </div>

                    <div className="usage-bar">

                      <div
                        className="usage-bar-fill"
                        style={{
                          width: `${usagePercentage}%`,
                        }}
                      />

                    </div>

                  </div>

                  {remainingAnswers ===
                    0 && (
                    <button
                      className="primary-btn subscription-buy-btn"
                      onClick={
                        buyWritingSubscription
                      }
                      disabled={
                        buyingSubscription
                      }
                    >
                      {buyingSubscription
                        ? "Processing..."
                        : "🔄 Buy Again ₹39"}
                    </button>
                  )}

                </>
              ) : (
                <>
                  <div className="subscription-price">

                    <span>
                      ₹
                    </span>

                    <strong>
                      39
                    </strong>

                    <small>
                      / 7 Days
                    </small>

                  </div>

                  <p className="subscription-description">
                    UPSC/BPSC Mains answer
                    writing practice के लिए
                    7 दिनों का access और
                    10 answer submissions।
                  </p>

                  <div className="subscription-features">

                    <div>
                      ✓ 10 Answer Submissions
                    </div>

                    <div>
                      ✓ AI Evaluation
                    </div>

                    <div>
                      ✓ AI Model Answer
                    </div>

                    <div>
                      ✓ Submission History
                    </div>

                    <div>
                      ✓ UPSC + BPSC
                    </div>

                    <div>
                      ✓ Hindi + English
                    </div>

                  </div>

                  <button
                    className="primary-btn subscription-buy-btn"
                    onClick={
                      buyWritingSubscription
                    }
                    disabled={
                      buyingSubscription
                    }
                  >
                    {buyingSubscription
                      ? "Processing..."
                      : "💳 Buy ₹39 Plan"}
                  </button>

                </>
              )}

            </div>

            {/* ===============================================================
                GENERATE QUESTION
            =============================================================== */}

            <div className="panel">

              <h3>
                Generate Question
              </h3>

              <label>
                Exam
              </label>

              <select
                value={exam}
                onChange={(e) =>
                  setExam(
                    e.target.value
                  )
                }
              >
                {EXAMS.map(
                  (item) => (
                    <option
                      key={item}
                      value={item}
                    >
                      {item}
                    </option>
                  )
                )}
              </select>

              <label>
                Category
              </label>

              <select
                value={category}
                onChange={(e) =>
                  setCategory(
                    e.target.value
                  )
                }
              >
                {CATEGORIES.map(
                  (item) => (
                    <option
                      key={item}
                      value={item}
                    >
                      {item}
                    </option>
                  )
                )}
              </select>

              <label>
                Question Type
              </label>

              <select
                value={questionType}
                onChange={(e) =>
                  setQuestionType(
                    e.target.value
                  )
                }
              >
                {QUESTION_TYPES.map(
                  (item) => (
                    <option
                      key={item.value}
                      value={item.value}
                    >
                      {item.label}
                    </option>
                  )
                )}
              </select>

              <label>
                Target Words
              </label>

              <div className="word-options">

                {TARGET_WORDS.map(
                  (words) => (
                    <button
                      key={words}
                      type="button"
                      className={
                        Number(
                          targetWords
                        ) === words
                          ? "selected"
                          : ""
                      }
                      onClick={() =>
                        setTargetWords(
                          words
                        )
                      }
                    >
                      {words}
                    </button>
                  )
                )}

              </div>

              <button
                className="primary-btn"
                onClick={
                  generateQuestion
                }
                disabled={loading}
              >
                {loading
                  ? "Generating..."
                  : "✨ Generate Question"}
              </button>

            </div>

            {/* ===============================================================
                QUESTION HISTORY
            =============================================================== */}

            <div className="panel">

              <div className="panel-title-row">

                <h3>
                  Questions
                </h3>

                <button
                  className="icon-btn"
                  onClick={
                    fetchQuestions
                  }
                  disabled={
                    loadingQuestions
                  }
                  title="Refresh"
                >
                  ↻
                </button>

              </div>

              {loadingQuestions ? (
                <div className="loading">
                  Questions loading...
                </div>
              ) : questions.length ===
                0 ? (
                <div className="empty">
                  अभी कोई question नहीं है।
                </div>
              ) : (
                <div className="question-list">

                  {questions.map(
                    (
                      question,
                      index
                    ) => {

                      const id =
                        question?.id ??
                        question?.question_id ??
                        index;

                      return (
                        <button
                          key={id}
                          className={
                            selectedQuestion?.id ===
                            question?.id
                              ? "question-item active"
                              : "question-item"
                          }
                          onClick={() =>
                            selectQuestion(
                              question
                            )
                          }
                        >

                          <span className="question-number">
                            #{index + 1}
                          </span>

                          <span className="question-preview">
                            {question?.question ||
                              question?.text ||
                              question?.title ||
                              "Question"}
                          </span>

                          <span className="question-meta">
                            {question?.target_words ||
                              targetWords}{" "}
                            words
                          </span>

                        </button>
                      );
                    }
                  )}

                </div>
              )}

            </div>

          </aside>

          {/* -----------------------------------------------------------------
              MAIN ANSWER AREA
          ----------------------------------------------------------------- */}

          <main className="writing-main">

            {!selectedQuestion ? (
              <div className="empty-main">

                <div className="empty-icon">
                  📝
                </div>

                <h2>
                  अपना पहला question generate करें
                </h2>

                <p>
                  बाईं ओर से exam, category
                  और target words चुनकर
                  question generate करें।
                </p>

                <button
                  className="primary-btn"
                  onClick={
                    generateQuestion
                  }
                  disabled={loading}
                >
                  ✨ Generate Question
                </button>

              </div>
            ) : (
              <>

                {/* QUESTION CARD */}

                <section className="content-card question-card">

                  <div className="card-top">

                    <div>

                      <span className="badge">
                        {exam}
                      </span>

                      <span className="badge">
                        {selectedQuestion?.category ||
                          category}
                      </span>

                      <span className="badge">
                        {selectedQuestion?.target_words ||
                          targetWords}{" "}
                        Words
                      </span>

                    </div>

                    <span className="question-id">
                      Question #
                      {selectedQuestion?.id}
                    </span>

                  </div>

                  <h2>
                    {selectedQuestion?.question ||
                      selectedQuestion?.text ||
                      selectedQuestion?.title}
                  </h2>

                  {selectedQuestion?.instructions && (
                    <div className="instructions">

                      <strong>
                        निर्देश:
                      </strong>{" "}

                      {selectedQuestion.instructions}

                    </div>
                  )}

                </section>

                {/* ANSWER EDITOR */}

                <section className="content-card">

                  <div className="editor-header">

                    <div>

                      <h3>
                        Your Answer
                      </h3>

                      <span
                        className={
                          answerWordCount >
                          Number(
                            selectedQuestion?.target_words ||
                              targetWords
                          )
                            ? "word-count over"
                            : "word-count"
                        }
                      >
                        {answerWordCount} /{" "}
                        {selectedQuestion?.target_words ||
                          targetWords}{" "}
                        words
                      </span>

                    </div>

                    <button
                      className="secondary-btn"
                      onClick={
                        generateModelAnswer
                      }
                      disabled={
                        loadingModelAnswer
                      }
                    >
                      {loadingModelAnswer
                        ? "Generating..."
                        : "🤖 AI Model Answer"}
                    </button>

                  </div>

                  <textarea
                    className="answer-editor"
                    value={answer}
                    onChange={(e) =>
                      setAnswer(
                        e.target.value
                      )
                    }
                    placeholder={
                      language === "hi"
                        ? "यहाँ अपना उत्तर लिखें..."
                        : "Write your answer here..."
                    }
                  />

                  <div className="editor-footer">

                    <div className="submit-credit-info">

                      <span>
                        {answerWordCount} words
                      </span>

                      {isSubscriptionActive && (
                        <span className="credit-text">
                          {remainingAnswers} answers
                          remaining
                        </span>
                      )}

                    </div>

                    <button
                      className="primary-btn"
                      onClick={
                        hasAnswerAccess
                          ? submitAnswer
                          : buyWritingSubscription
                      }
                      disabled={
                        submittingAnswer ||
                        buyingSubscription ||
                        (
                          hasAnswerAccess &&
                          !answer.trim()
                        )
                      }
                    >
                      {submittingAnswer
                        ? "Evaluating..."
                        : buyingSubscription
                          ? "Processing..."
                          : !hasAnswerAccess
                            ? "🔒 Buy ₹39 Plan"
                            : "🚀 Submit Answer"}
                    </button>

                  </div>

                </section>

                {/* MODEL ANSWER */}

                {modelAnswer && (
                  <section className="content-card model-answer">

                    <div className="section-title">

                      <h3>
                        🤖 AI Model Answer
                      </h3>

                      <button
                        className="icon-btn"
                        onClick={() =>
                          setModelAnswer(
                            null
                          )
                        }
                      >
                        ×
                      </button>

                    </div>

                    <div className="model-answer-text">

                      {typeof modelAnswer ===
                      "string"
                        ? modelAnswer
                        : modelAnswer?.answer ||
                          modelAnswer?.model_answer ||
                          JSON.stringify(
                            modelAnswer,
                            null,
                            2
                          )}

                    </div>

                  </section>
                )}

                {/* ANSWER EVALUATION */}

                {answerEvaluation && (
                  <EvaluationCard
                    evaluation={
                      answerEvaluation
                    }
                    title="AI Answer Evaluation"
                  />
                )}

                {/* ANSWER HISTORY */}

                <section className="content-card">

                  <div className="section-title">

                    <h3>
                      📊 Submission History
                    </h3>

                    <button
                      className="secondary-btn"
                      onClick={() =>
                        fetchAnswerSubmissions(
                          selectedQuestion.id
                        )
                      }
                    >
                      Refresh
                    </button>

                  </div>

                  {loadingAnswerHistory ? (
                    <div className="loading">
                      Loading history...
                    </div>
                  ) : answerSubmissions.length ===
                    0 ? (
                    <div className="empty">
                      अभी कोई submission नहीं है।
                    </div>
                  ) : (
                    <div className="submission-list">

                      {answerSubmissions.map(
                        (
                          submission
                        ) => (
                          <div
                            className="submission-row"
                            key={
                              submission.id
                            }
                          >

                            <div>

                              <strong>
                                Submission #
                                {
                                  submission.id
                                }
                              </strong>

                              <small>
                                {formatDate(
                                  submission.created_at ||
                                    submission.createdAt
                                )}
                              </small>

                            </div>

                            <div
                              className={`submission-score ${getScoreClass(
                                submission.score ||
                                  0
                              )}`}
                            >
                              {submission.score ?? 0}
                              /
                              {submission.max_score ??
                                submission.max_marks ??
                                10}
                            </div>

                          </div>
                        )
                      )}

                    </div>
                  )}

                </section>

              </>
            )}

          </main>
        </div>
      )}

      {/* =====================================================================
          ESSAY MODE
      ===================================================================== */}

      {mode === "essay" && (
        <div className="writing-layout">

          <aside className="writing-sidebar">

            {/* ===============================================================
                ESSAY GENERATOR
            =============================================================== */}

            <div className="panel">

              <h3>
                📖 Essay Practice
              </h3>

              <div className="essay-info">

                <div>
                  <span>
                    Exam
                  </span>

                  <strong>
                    {exam}
                  </strong>
                </div>

                <div>
                  <span>
                    Language
                  </span>

                  <strong>
                    {language === "hi"
                      ? "हिंदी"
                      : "English"}
                  </strong>
                </div>

                <div>
                  <span>
                    Target
                  </span>

                  <strong>
                    1000 Words
                  </strong>
                </div>

              </div>

              <label>
                Essay Topic
              </label>

              <textarea
                className="essay-topic-input"
                value={essayTopic}
                onChange={(e) =>
                  setEssayTopic(
                    e.target.value
                  )
                }
                placeholder={
                  language === "hi"
                    ? "जैसे: भारत में कृत्रिम बुद्धिमत्ता के अवसर और चुनौतियाँ"
                    : "e.g. Opportunities and challenges of Artificial Intelligence in India"
                }
                rows={4}
              />

              <div className="topic-counter">
                {essayTopic.trim()
                  ? getWordCount(
                      essayTopic
                    )
                  : 0}{" "}
                words
              </div>

              <p className="hint">
                {language === "hi"
                  ? "विषय दर्ज करें। AI उसी विषय पर लगभग 1000 शब्दों का UPSC/BPSC Mains essay तैयार करेगा।"
                  : "Enter a topic. AI will generate an approximately 1000-word UPSC/BPSC Mains essay on the exact topic."}
              </p>

              <button
                className="primary-btn"
                onClick={
                  generateEssay
                }
                disabled={
                  generatingEssay ||
                  !essayTopic.trim()
                }
              >
                {generatingEssay
                  ? "Generating..."
                  : "✨ Generate Essay"}
              </button>

            </div>

            {/* ===============================================================
                ESSAY LIST
            =============================================================== */}

            <div className="panel">

              <div className="panel-title-row">

                <h3>
                  Saved Essays
                </h3>

                <button
                  className="icon-btn"
                  onClick={
                    fetchEssays
                  }
                  disabled={
                    loadingEssays
                  }
                  title="Refresh"
                >
                  ↻
                </button>

              </div>

              {loadingEssays ? (
                <div className="loading">
                  Essays loading...
                </div>
              ) : essays.length ===
                0 ? (
                <div className="empty">
                  अभी कोई essay नहीं है।
                </div>
              ) : (
                <div className="essay-list">

                  {essays.map(
                    (
                      essay,
                      index
                    ) => {

                      const id =
                        essay?.id ??
                        essay?.essay_id ??
                        index;

                      return (
                        <button
                          key={id}
                          className={
                            selectedEssay?.id ===
                            essay?.id
                              ? "essay-item active"
                              : "essay-item"
                          }
                          onClick={() =>
                            selectEssay(
                              essay
                            )
                          }
                        >

                          <span className="essay-item-topic">
                            📄{" "}
                            {essay?.topic ||
                              `Essay ${
                                index + 1
                              }`}
                          </span>

                          <small>
                            {essay?.target_words ||
                              1000}{" "}
                            words
                          </small>

                        </button>
                      );
                    }
                  )}

                </div>
              )}

            </div>

          </aside>

          <main className="writing-main">

            {!selectedEssay ? (
              <div className="empty-main">

                <div className="empty-icon">
                  📖
                </div>

                <h2>
                  Essay Practice शुरू करें
                </h2>

                <p>
                  बाईं ओर Essay Topic दर्ज
                  करके Generate Essay पर
                  click करें।
                </p>

                <button
                  className="primary-btn"
                  onClick={
                    generateEssay
                  }
                  disabled={
                    generatingEssay ||
                    !essayTopic.trim()
                  }
                >
                  {generatingEssay
                    ? "Generating..."
                    : "✨ Generate Essay"}
                </button>

              </div>
            ) : (
              <>

                {/* ESSAY TOPIC */}

                <section className="content-card">

                  <div className="card-top">

                    <div>

                      <span className="badge">
                        {exam}
                      </span>

                      <span className="badge">
                        Essay
                      </span>

                      <span className="badge">
                        1000 Words
                      </span>

                    </div>

                    <span className="question-id">
                      Essay #
                      {selectedEssay?.id}
                    </span>

                  </div>

                  <h2 className="essay-topic-title">
                    {selectedEssay?.topic ||
                      essayTopic ||
                      "Essay"}
                  </h2>

                  {selectedEssay?.introduction && (
                    <div className="essay-introduction">

                      <strong>
                        Introduction:
                      </strong>

                      <p>
                        {
                          selectedEssay.introduction
                        }
                      </p>

                    </div>
                  )}

                </section>

                {/* ESSAY EDITOR */}

                <section className="content-card">

                  <div className="editor-header">

                    <div>

                      <h3>
                        Your Essay
                      </h3>

                      <span
                        className={
                          essayWordCount > 1000
                            ? "word-count over"
                            : "word-count"
                        }
                      >
                        {essayWordCount} / 1000
                        words
                      </span>

                    </div>

                    <button
                      className="secondary-btn"
                      onClick={() => {
                        setEssayText("");
                        setEssayEvaluation(
                          null
                        );
                        setEssaySubmissions(
                          []
                        );
                        setSelectedEssay(
                          null
                        );
                        setEssayTopic("");
                      }}
                    >
                      🆕 New Essay
                    </button>

                  </div>

                  <textarea
                    className="essay-editor"
                    value={essayText}
                    onChange={(e) =>
                      setEssayText(
                        e.target.value
                      )
                    }
                    placeholder={
                      language === "hi"
                        ? "यहाँ अपना पूरा essay लिखें..."
                        : "Write your complete essay here..."
                    }
                  />

                  <div className="editor-footer">

                    <div className="essay-word-status">

                      <span>
                        {essayWordCount} words
                      </span>

                      {essayWordCount < 1000 && (
                        <span className="warning-text">
                          Target: 1000 words
                        </span>
                      )}

                      {essayWordCount >= 1000 && (
                        <span className="success-text">
                          ✓ Target reached
                        </span>
                      )}

                    </div>

                    <button
                      className="primary-btn"
                      onClick={
                        submitEssay
                      }
                      disabled={
                        submittingEssay ||
                        !essayText.trim()
                      }
                    >
                      {submittingEssay
                        ? "AI Evaluating..."
                        : "🚀 Submit Essay"}
                    </button>

                  </div>

                </section>

                {/* ESSAY METADATA */}

                {(selectedEssay?.dimensions
                  ?.length > 0 ||
                  selectedEssay?.examples
                    ?.length > 0 ||
                  selectedEssay?.way_forward) && (
                  <section className="content-card">

                    <h3>
                      📌 Essay Guidance
                    </h3>

                    {selectedEssay
                      ?.dimensions
                      ?.length > 0 && (
                      <div className="guidance-section">

                        <h4>
                          Dimensions
                        </h4>

                        <ul>

                          {selectedEssay.dimensions.map(
                            (
                              item,
                              index
                            ) => (
                              <li
                                key={
                                  index
                                }
                              >
                                {item}
                              </li>
                            )
                          )}

                        </ul>

                      </div>
                    )}

                    {selectedEssay
                      ?.examples
                      ?.length > 0 && (
                      <div className="guidance-section">

                        <h4>
                          Examples
                        </h4>

                        <ul>

                          {selectedEssay.examples.map(
                            (
                              item,
                              index
                            ) => (
                              <li
                                key={
                                  index
                                }
                              >
                                {item}
                              </li>
                            )
                          )}

                        </ul>

                      </div>
                    )}

                    {selectedEssay?.way_forward && (
                      <div className="way-forward">

                        <h4>
                          Way Forward
                        </h4>

                        <p>
                          {
                            selectedEssay.way_forward
                          }
                        </p>

                      </div>
                    )}

                  </section>
                )}

                {/* ESSAY EVALUATION */}

                {essayEvaluation && (
                  <EvaluationCard
                    evaluation={
                      essayEvaluation
                    }
                    title="AI Essay Evaluation"
                    essay
                  />
                )}

                {/* ESSAY HISTORY */}

                <section className="content-card">

                  <div className="section-title">

                    <h3>
                      📊 Essay Submission History
                    </h3>

                    <button
                      className="secondary-btn"
                      onClick={() =>
                        fetchEssaySubmissions(
                          selectedEssay.id
                        )
                      }
                    >
                      Refresh
                    </button>

                  </div>

                  {loadingEssayHistory ? (
                    <div className="loading">
                      Loading history...
                    </div>
                  ) : essaySubmissions.length ===
                    0 ? (
                    <div className="empty">
                      अभी कोई submission नहीं है।
                    </div>
                  ) : (
                    <div className="submission-list">

                      {essaySubmissions.map(
                        (
                          submission
                        ) => (
                          <div
                            className="submission-row"
                            key={
                              submission.id
                            }
                          >

                            <div>

                              <strong>
                                Submission #
                                {
                                  submission.id
                                }
                              </strong>

                              <small>
                                {
                                  submission.word_count ??
                                  0
                                }{" "}
                                words
                              </small>

                            </div>

                            <div
                              className={`submission-score ${getScoreClass(
                                submission.score ||
                                  0
                              )}`}
                            >
                              {submission.score ?? 0}
                              /
                              {submission.max_score ??
                                submission.max_marks ??
                                10}
                            </div>

                          </div>
                        )
                      )}

                    </div>
                  )}

                </section>

              </>
            )}

          </main>
        </div>
      )}

      {/* =====================================================================
          INLINE STYLES
      ===================================================================== */}

      <style>{`

        * {
          box-sizing: border-box;
        }

        .writing-page {
          min-height: 100vh;
          padding: 24px;
          background: #f5f7fb;
          color: #172033;
        }

        .writing-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 20px;
          margin-bottom: 20px;
        }

        .writing-header h1 {
          margin: 0;
          font-size: 30px;
          font-weight: 800;
        }

        .writing-header p {
          margin: 7px 0 0;
          color: #667085;
        }

        .header-controls {
          display: flex;
          gap: 10px;
        }

        select {
          width: 100%;
          border: 1px solid #d7dce5;
          border-radius: 9px;
          padding: 10px 12px;
          background: white;
          color: #172033;
          outline: none;
        }

        .header-controls select {
          width: auto;
          min-width: 120px;
        }

        label {
          display: block;
          margin: 15px 0 7px;
          font-size: 13px;
          font-weight: 700;
          color: #475467;
        }

        .writing-alert {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 13px 15px;
          border-radius: 10px;
          margin-bottom: 18px;
          font-size: 14px;
        }

        .writing-alert.error {
          background: #fff1f1;
          border: 1px solid #ffcaca;
          color: #b42318;
        }

        .writing-alert.success {
          background: #ecfdf3;
          border: 1px solid #abefc6;
          color: #027a48;
        }

        .writing-alert button {
          margin-left: auto;
          border: 0;
          background: transparent;
          font-size: 20px;
          cursor: pointer;
        }

        .writing-tabs {
          display: flex;
          gap: 8px;
          background: white;
          padding: 6px;
          border: 1px solid #e4e7ec;
          border-radius: 12px;
          width: fit-content;
          margin-bottom: 20px;
        }

        .writing-tabs button {
          border: 0;
          background: transparent;
          padding: 10px 18px;
          border-radius: 8px;
          font-weight: 700;
          cursor: pointer;
          color: #667085;
        }

        .writing-tabs button.active {
          background: #172033;
          color: white;
        }

        .writing-layout {
          display: grid;
          grid-template-columns: 320px minmax(0, 1fr);
          gap: 20px;
          align-items: start;
        }

        .writing-sidebar {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .panel,
        .content-card {
          background: white;
          border: 1px solid #e4e7ec;
          border-radius: 14px;
          box-shadow:
            0 2px 8px rgba(
              16,
              24,
              40,
              0.04
            );
        }

        .panel {
          padding: 18px;
        }

        .panel h3 {
          margin: 0 0 15px;
          font-size: 17px;
        }

        .panel-title-row,
        .section-title,
        .editor-header,
        .card-top,
        .editor-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .word-options {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }

        .word-options button {
          padding: 9px;
          border: 1px solid #d7dce5;
          border-radius: 8px;
          background: white;
          cursor: pointer;
          font-weight: 700;
        }

        .word-options button.selected {
          background: #172033;
          color: white;
          border-color: #172033;
        }

        .primary-btn,
        .secondary-btn {
          border: 0;
          border-radius: 9px;
          padding: 10px 15px;
          font-weight: 700;
          cursor: pointer;
          transition: 0.2s;
        }

        .primary-btn {
          background: #172033;
          color: white;
        }

        .primary-btn:hover {
          opacity: 0.9;
        }

        .primary-btn:disabled,
        .secondary-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .secondary-btn {
          background: #eef2f6;
          color: #344054;
        }

        .icon-btn {
          border: 0;
          background: #f2f4f7;
          border-radius: 7px;
          width: 32px;
          height: 32px;
          cursor: pointer;
          font-size: 18px;
        }

        .question-list,
        .essay-list {
          display: flex;
          flex-direction: column;
          gap: 7px;
        }

        .question-item,
        .essay-item {
          width: 100%;
          text-align: left;
          border: 1px solid transparent;
          background: #f8fafc;
          border-radius: 9px;
          padding: 10px;
          cursor: pointer;
        }

        .question-item:hover,
        .essay-item:hover,
        .question-item.active,
        .essay-item.active {
          background: #eef2ff;
          border-color: #c7d2fe;
        }

        .question-number {
          display: block;
          font-size: 11px;
          color: #667085;
          margin-bottom: 4px;
        }

        .question-preview {
          display: block;
          font-size: 13px;
          line-height: 1.45;
          color: #344054;
        }

        .question-meta {
          display: block;
          margin-top: 5px;
          font-size: 11px;
          color: #667085;
        }

        .essay-item {
          display: flex;
          justify-content: space-between;
          gap: 8px;
        }

        .essay-item small {
          color: #667085;
          white-space: nowrap;
        }

        .essay-item-topic {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .writing-main {
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .content-card {
          padding: 20px;
        }

        .card-top {
          margin-bottom: 16px;
        }

        .card-top > div {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          padding: 5px 9px;
          border-radius: 999px;
          background: #eef2f6;
          color: #475467;
          font-size: 11px;
          font-weight: 700;
        }

        .question-id {
          font-size: 12px;
          color: #667085;
        }

        .question-card h2 {
          margin: 0;
          line-height: 1.6;
          font-size: 21px;
        }

        .essay-topic-title {
          margin: 0;
          line-height: 1.6;
          font-size: 21px;
        }

        .instructions {
          margin-top: 15px;
          padding: 12px;
          border-radius: 9px;
          background: #f8fafc;
          color: #475467;
          font-size: 14px;
        }

        .editor-header {
          margin-bottom: 12px;
        }

        .editor-header h3 {
          margin: 0 0 5px;
        }

        .word-count {
          color: #667085;
          font-size: 12px;
        }

        .word-count.over {
          color: #b42318;
          font-weight: 700;
        }

        .answer-editor,
        .essay-editor {
          width: 100%;
          resize: vertical;
          min-height: 280px;
          border: 1px solid #d7dce5;
          border-radius: 10px;
          padding: 15px;
          font-family: inherit;
          font-size: 15px;
          line-height: 1.75;
          outline: none;
        }

        .essay-editor {
          min-height: 550px;
        }

        .answer-editor:focus,
        .essay-editor:focus,
        .essay-topic-input:focus {
          border-color: #98a2b3;
          box-shadow:
            0 0 0 3px rgba(
              16,
              24,
              40,
              0.06
            );
        }

        .editor-footer {
          margin-top: 12px;
        }

        .submit-credit-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .credit-text {
          color: #027a48;
          font-size: 12px;
          font-weight: 700;
        }

        .model-answer-text {
          white-space: pre-wrap;
          line-height: 1.8;
          color: #344054;
          padding: 15px;
          border-radius: 10px;
          background: #f8fafc;
        }

        .empty-main {
          min-height: 600px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          text-align: center;
          background: white;
          border: 1px solid #e4e7ec;
          border-radius: 14px;
          padding: 40px;
        }

        .empty-icon {
          font-size: 55px;
          margin-bottom: 15px;
        }

        .empty-main h2 {
          margin: 0;
        }

        .empty-main p {
          color: #667085;
          max-width: 500px;
          line-height: 1.6;
        }

        .empty {
          text-align: center;
          padding: 20px 10px;
          color: #98a2b3;
          font-size: 13px;
        }

        .loading {
          padding: 20px;
          text-align: center;
          color: #667085;
          font-size: 13px;
        }

        .submission-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .submission-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          padding: 12px;
          border-radius: 9px;
          background: #f8fafc;
        }

        .submission-row strong,
        .submission-row small {
          display: block;
        }

        .submission-row small {
          margin-top: 4px;
          color: #667085;
          font-size: 11px;
        }

        .submission-score {
          font-weight: 800;
          font-size: 17px;
        }

        .score-excellent {
          color: #027a48;
        }

        .score-good {
          color: #087443;
        }

        .score-average {
          color: #b54708;
        }

        .score-low {
          color: #b42318;
        }

        /* ================================================================
           SUBSCRIPTION
        ================================================================ */

        .subscription-panel {
          border: 1px solid #dbe3f0;
        }

        .subscription-heading {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
        }

        .subscription-heading h3 {
          margin: 0 0 3px;
        }

        .subscription-heading span {
          color: #667085;
          font-size: 11px;
        }

        .price-badge {
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 52px;
          height: 40px;
          border-radius: 10px;
          background: #172033;
          color: white;
          font-weight: 900;
          font-size: 15px;
        }

        .subscription-price {
          display: flex;
          align-items: baseline;
          gap: 4px;
          margin: 10px 0;
        }

        .subscription-price span {
          font-size: 20px;
          font-weight: 700;
        }

        .subscription-price strong {
          font-size: 36px;
          font-weight: 900;
        }

        .subscription-price small {
          color: #667085;
        }

        .subscription-description {
          color: #667085;
          font-size: 13px;
          line-height: 1.6;
          margin: 8px 0 14px;
        }

        .subscription-features {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin: 15px 0;
          font-size: 13px;
          color: #344054;
        }

        .subscription-active {
          padding: 11px;
          border-radius: 9px;
          background: #ecfdf3;
          color: #027a48;
          margin-bottom: 12px;
        }

        .subscription-active strong,
        .subscription-active span {
          display: block;
        }

        .subscription-active span {
          margin-top: 3px;
          font-size: 11px;
          color: #087443;
        }

        .subscription-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .subscription-info div {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          padding: 8px 0;
          border-bottom: 1px solid #eef0f3;
        }

        .subscription-info span {
          color: #667085;
          font-size: 12px;
        }

        .subscription-info strong {
          font-size: 12px;
        }

        .answer-usage {
          margin-top: 15px;
        }

        .answer-usage-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 7px;
          font-size: 12px;
        }

        .usage-bar {
          height: 7px;
          background: #eaecf0;
          border-radius: 999px;
          overflow: hidden;
        }

        .usage-bar-fill {
          height: 100%;
          background: #172033;
          border-radius: 999px;
          transition: width 0.3s ease;
        }

        .subscription-buy-btn {
          width: 100%;
          margin-top: 8px;
        }

        /* ================================================================
           ESSAY
        ================================================================ */

        .essay-info {
          display: grid;
          gap: 10px;
        }

        .essay-info div {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          padding: 9px 0;
          border-bottom: 1px solid #eef0f3;
        }

        .essay-info span {
          color: #667085;
          font-size: 13px;
        }

        .essay-info strong {
          font-size: 13px;
        }

        .essay-topic-input {
          width: 100%;
          min-height: 100px;
          resize: vertical;
          border: 1px solid #d7dce5;
          border-radius: 9px;
          padding: 11px 12px;
          background: white;
          color: #172033;
          font-family: inherit;
          font-size: 13px;
          line-height: 1.6;
          outline: none;
        }

        .topic-counter {
          margin-top: 5px;
          text-align: right;
          color: #98a2b3;
          font-size: 11px;
        }

        .hint {
          color: #667085;
          font-size: 12px;
          line-height: 1.5;
          margin: 10px 0 15px;
        }

        .essay-introduction {
          margin-top: 18px;
          padding: 14px;
          background: #f8fafc;
          border-radius: 10px;
          color: #475467;
          line-height: 1.7;
        }

        .essay-introduction p {
          margin: 7px 0 0;
        }

        .guidance-section {
          margin-top: 15px;
        }

        .guidance-section h4,
        .way-forward h4 {
          margin: 0 0 8px;
        }

        .guidance-section ul {
          margin: 0;
          padding-left: 20px;
          color: #475467;
          line-height: 1.7;
        }

        .way-forward {
          margin-top: 15px;
          padding: 14px;
          background: #f8fafc;
          border-radius: 10px;
        }

        .way-forward p {
          margin: 0;
          color: #475467;
          line-height: 1.7;
        }

        .essay-word-status {
          display: flex;
          gap: 12px;
          align-items: center;
          font-size: 13px;
        }

        .warning-text {
          color: #b54708;
        }

        .success-text {
          color: #027a48;
          font-weight: 700;
        }

        /* ================================================================
           EVALUATION
        ================================================================ */

        .evaluation-card {
          background: white;
          border: 1px solid #e4e7ec;
          border-radius: 14px;
          padding: 20px;
        }

        .evaluation-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 20px;
          margin-bottom: 20px;
        }

        .evaluation-score {
          text-align: center;
          min-width: 100px;
        }

        .evaluation-score-number {
          font-size: 34px;
          font-weight: 900;
        }

        .evaluation-score-label {
          color: #667085;
          font-size: 12px;
        }

        .evaluation-grid {
          display: grid;
          grid-template-columns: repeat(
            3,
            minmax(0, 1fr)
          );
          gap: 10px;
          margin-bottom: 18px;
        }

        .evaluation-metric {
          padding: 12px;
          background: #f8fafc;
          border-radius: 9px;
        }

        .evaluation-metric span {
          display: block;
          font-size: 11px;
          color: #667085;
          margin-bottom: 5px;
        }

        .evaluation-metric strong {
          font-size: 18px;
        }

        .evaluation-columns {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }

        .evaluation-section {
          padding: 15px;
          border-radius: 10px;
          background: #f8fafc;
        }

        .evaluation-section h4 {
          margin: 0 0 10px;
        }

        .evaluation-section ul {
          margin: 0;
          padding-left: 20px;
          line-height: 1.65;
          color: #475467;
        }

        .feedback-box {
          margin-top: 15px;
          padding: 15px;
          background: #eef2ff;
          border-radius: 10px;
          line-height: 1.65;
        }

        .model-improvement {
          margin-top: 15px;
          padding: 15px;
          background: #ecfdf3;
          border-radius: 10px;
          line-height: 1.65;
        }

        @media (max-width: 1000px) {

          .writing-layout {
            grid-template-columns: 1fr;
          }

          .writing-sidebar {
            display: grid;
            grid-template-columns: 1fr 1fr;
          }

        }

        @media (max-width: 700px) {

          .writing-page {
            padding: 12px;
          }

          .writing-header {
            flex-direction: column;
          }

          .header-controls {
            width: 100%;
          }

          .header-controls select {
            flex: 1;
          }

          .writing-sidebar {
            display: flex;
          }

          .evaluation-grid {
            grid-template-columns: 1fr 1fr;
          }

          .evaluation-columns {
            grid-template-columns: 1fr;
          }

          .editor-header,
          .editor-footer {
            align-items: flex-start;
            flex-direction: column;
          }

          .essay-editor {
            min-height: 400px;
          }

          .subscription-heading {
            align-items: flex-start;
          }

        }

      `}</style>

    </div>
  );
}

/* ===========================================================================
   EVALUATION CARD
=========================================================================== */

function EvaluationCard({
  evaluation,
  title = "AI Evaluation",
  essay = false,
}) {
  if (!evaluation) return null;

  const score =
    Number(
      evaluation.score ?? 0
    );

  const maxScore =
    Number(
      evaluation.max_score ?? 100
    );

  const percentage =
    Number(
      evaluation.percentage ??
        (
          maxScore > 0
            ? Math.round(
                (score /
                  maxScore) *
                  100
              )
            : score
        )
    );

  const wordCount =
    Number(
      evaluation.word_count ?? 0
    );

  const targetWords =
    Number(
      evaluation.target_words ??
        (essay ? 1000 : 150)
    );

  const metrics = [
    [
      "Content",
      evaluation.content_score,
    ],
    [
      "Structure",
      evaluation.structure_score,
    ],
    [
      "Introduction",
      evaluation.introduction_score,
    ],
    [
      "Conclusion",
      evaluation.conclusion_score,
    ],
    [
      "Current Affairs",
      evaluation.current_affairs_score,
    ],
    [
      "Analysis",
      evaluation.analysis_score,
    ],
    [
      "Presentation",
      evaluation.presentation_score,
    ],
  ];

  return (
    <section className="evaluation-card">

      <div className="evaluation-top">

        <div>

          <h3>
            {title}
          </h3>

          <p
            style={{
              margin: "5px 0 0",
              color: "#667085",
              fontSize: "13px",
            }}
          >
            AI-powered evaluation
          </p>

        </div>

        <div
          className={`evaluation-score ${getScoreClass(
            score
          )}`}
        >

          <div className="evaluation-score-number">
            {score}
          </div>

          <div className="evaluation-score-label">
            /{maxScore} • {percentage}%
          </div>

        </div>

      </div>

      <div className="evaluation-grid">

        {metrics.map(
          ([label, value]) => (
            <div
              className="evaluation-metric"
              key={label}
            >

              <span>
                {label}
              </span>

              <strong>
                {Number(
                  value ?? 0
                )}
              </strong>

            </div>
          )
        )}

      </div>

      <div
        className="evaluation-metric"
        style={{
          marginBottom: 16,
        }}
      >

        <span>
          Word Count
        </span>

        <strong>
          {wordCount} / {targetWords}
        </strong>

      </div>

      <div className="evaluation-columns">

        <EvaluationList
          title="✅ Strengths"
          items={
            evaluation.strengths
          }
        />

        <EvaluationList
          title="⚠️ Weaknesses"
          items={
            evaluation.weaknesses
          }
        />

        <EvaluationList
          title="📌 Missing Points"
          items={
            evaluation.missing_points
          }
        />

        <EvaluationList
          title="💡 Improvement Tips"
          items={
            evaluation.improvement_tips
          }
        />

      </div>

      {evaluation.feedback && (
        <div className="feedback-box">

          <strong>
            Feedback
          </strong>

          <div>
            {evaluation.feedback}
          </div>

        </div>
      )}

      {Array.isArray(
        evaluation.suggestions
      ) &&
        evaluation.suggestions.length >
          0 && (
          <EvaluationList
            title="📝 Suggestions"
            items={
              evaluation.suggestions
            }
          />
        )}

      {evaluation.model_improvement && (
        <div className="model-improvement">

          <strong>
            🎯 Model Improvement
          </strong>

          <div>
            {evaluation.model_improvement}
          </div>

        </div>
      )}

    </section>
  );
}

/* ===========================================================================
   EVALUATION LIST
=========================================================================== */

function EvaluationList({
  title,
  items,
}) {
  if (
    !Array.isArray(items) ||
    items.length === 0
  ) {
    return null;
  }

  return (
    <div className="evaluation-section">

      <h4>
        {title}
      </h4>

      <ul>

        {items.map(
          (
            item,
            index
          ) => (
            <li key={index}>
              {item}
            </li>
          )
        )}

      </ul>

    </div>
  );
}


