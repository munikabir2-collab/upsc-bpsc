
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

/*
|--------------------------------------------------------------------------
| CONFIGURATION
|--------------------------------------------------------------------------
*/

const API_URL =
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000";

const PRACTICE_PAGE_SIZE = 20;

/*
|--------------------------------------------------------------------------
| LANGUAGE
|--------------------------------------------------------------------------
*/

const getStoredLanguage = () => {
    const stored =
        localStorage.getItem("language") ||
        localStorage.getItem("appLanguage") ||
        "hi";

    return String(stored).toLowerCase() === "en"
        ? "en"
        : "hi";
};

const normalizeLanguage = (value) => {
    const language =
        String(value || "").toLowerCase();

    if (
        language === "en" ||
        language === "english"
    ) {
        return "en";
    }

    return "hi";
};

/*
|--------------------------------------------------------------------------
| AUTH
|--------------------------------------------------------------------------
*/

const getToken = () => {
    return (
        localStorage.getItem("token") ||
        sessionStorage.getItem("token") ||
        ""
    );
};

/*
|--------------------------------------------------------------------------
| ERROR HANDLER
|--------------------------------------------------------------------------
*/

const getErrorMessage = (
    error,
    language = "hi"
) => {
    const isHindi =
        normalizeLanguage(language) === "hi";

    if (error?.response) {
        const detail =
            error.response.data?.detail;

        if (Array.isArray(detail)) {
            return (
                detail
                    .map((item) => item?.msg)
                    .filter(Boolean)
                    .join(", ") ||
                (
                    isHindi
                        ? "अमान्य अनुरोध।"
                        : "Invalid request."
                )
            );
        }

        if (typeof detail === "string") {
            return detail;
        }

        if (
            typeof error.response.data?.message ===
            "string"
        ) {
            return error.response.data.message;
        }

        if (error.response.status === 400) {
            return (
                isHindi
                    ? "MCQ अनुरोध पूरा नहीं हो सका।"
                    : "Unable to process this MCQ request."
            );
        }

        if (error.response.status === 401) {
            return (
                isHindi
                    ? "आपका session समाप्त हो गया है। कृपया दोबारा login करें।"
                    : "Your session has expired. Please login again."
            );
        }

        if (error.response.status === 403) {
            return (
                isHindi
                    ? "आपको इस content को access करने की अनुमति नहीं है।"
                    : "You do not have permission to access this content."
            );
        }

        if (error.response.status === 404) {
            return (
                isHindi
                    ? "MCQ service या article नहीं मिला।"
                    : "MCQ service or article was not found."
            );
        }

        if (error.response.status >= 500) {
            return (
                isHindi
                    ? "Server error हुआ है। कृपया कुछ देर बाद प्रयास करें।"
                    : "Server error. Please try again later."
            );
        }

        return (
            isHindi
                ? `Request असफल हुआ (${error.response.status})।`
                : `Request failed (${error.response.status}).`
        );
    }

    if (error?.request) {
        return (
            isHindi
                ? "Muni48 server से connection नहीं हो सका। सुनिश्चित करें कि backend चल रहा है।"
                : "Unable to connect to the Muni48 server. Make sure the backend is running."
        );
    }

    return (
        error?.message ||
        (
            isHindi
                ? "कुछ गलत हुआ।"
                : "Something went wrong."
        )
    );
};

/*
|--------------------------------------------------------------------------
| NORMALIZE API RESPONSE
|--------------------------------------------------------------------------
*/

const normalizeQuestions = (data) => {
    if (Array.isArray(data)) {
        return data;
    }

    if (
        Array.isArray(
            data?.questions
        )
    ) {
        return data.questions;
    }

    if (
        Array.isArray(
            data?.mcqs
        )
    ) {
        return data.mcqs;
    }

    if (
        Array.isArray(
            data?.results
        )
    ) {
        return data.results;
    }

    if (
        Array.isArray(
            data?.data
        )
    ) {
        return data.data;
    }

    /*
    |--------------------------------------------------------------------------
    | Single MCQ object
    |--------------------------------------------------------------------------
    */

    if (
        data &&
        typeof data === "object" &&
        (
            data.question ||
            data.question_text ||
            data.text
        )
    ) {
        return [data];
    }

    return [];
};

/*
|--------------------------------------------------------------------------
| QUESTION HELPERS
|--------------------------------------------------------------------------
*/

const getQuestionText = (
    question
) => {
    return (
        question?.question ||
        question?.question_text ||
        question?.text ||
        question?.title ||
        "Question"
    );
};

const getOptions = (
    question
) => {
    if (
        Array.isArray(
            question?.options
        )
    ) {
        return question.options;
    }

    if (
        question?.options &&
        typeof question.options === "object"
    ) {
        return Object.entries(
            question.options
        ).map(
            ([key, value]) => ({
                key:
                    String(key)
                        .toUpperCase(),

                value:
                    typeof value === "object"
                        ? (
                              value?.text ??
                              value?.value ??
                              ""
                          )
                        : value,
            })
        );
    }

    const options = [];

    [
        "A",
        "B",
        "C",
        "D",
    ].forEach(
        (key) => {
            const lower =
                key.toLowerCase();

            if (
                question?.[key] !==
                undefined
            ) {
                options.push({
                    key,
                    value:
                        question[key],
                });

                return;
            }

            if (
                question?.[lower] !==
                undefined
            ) {
                options.push({
                    key,
                    value:
                        question[lower],
                });

                return;
            }

            const optionKey =
                `option_${lower}`;

            if (
                question?.[
                    optionKey
                ] !== undefined
            ) {
                options.push({
                    key,
                    value:
                        question[
                            optionKey
                        ],
                });
            }
        }
    );

    return options;
};

const getOptionKey = (
    option,
    index
) => {
    if (
        option &&
        typeof option === "object"
    ) {
        return String(
            option?.key ||
            option?.label ||
            option?.id ||
            String.fromCharCode(
                65 + index
            )
        ).toUpperCase();
    }

    return String.fromCharCode(
        65 + index
    );
};

const getOptionValue = (
    option
) => {
    if (
        option &&
        typeof option === "object"
    ) {
        return (
            option?.value ??
            option?.text ??
            option?.option ??
            option?.label ??
            ""
        );
    }

    return option ?? "";
};

/*
|--------------------------------------------------------------------------
| CORRECT ANSWER
|--------------------------------------------------------------------------
*/

const getCorrectAnswer = (
    question
) => {
    return (
        question?.correct_answer ??
        question?.correctAnswer ??
        question?.answer ??
        question?.correct_option ??
        question?.correctOption ??
        null
    );
};

/*
|--------------------------------------------------------------------------
| EXPLANATION
|--------------------------------------------------------------------------
*/

const getExplanation = (
    question
) => {
    return (
        question?.explanation ||
        question?.answer_explanation ||
        question?.answerExplanation ||
        question?.solution ||
        ""
    );
};

/*
|--------------------------------------------------------------------------
| ARTICLE ID
|--------------------------------------------------------------------------
*/

const getArticleId = (
    question
) => {
    if (!question) {
        return null;
    }

    return (
        question?.article_id ??
        question?.articleId ??
        question?.news_id ??
        question?.newsId ??
        question?.current_affair_id ??
        question?.currentAffairId ??
        question?.article?.id ??
        question?.news?.id ??
        null
    );
};

/*
|--------------------------------------------------------------------------
| NORMALIZE ANSWER
|--------------------------------------------------------------------------
*/

const normalizeAnswerKey = (
    value,
    options = []
) => {
    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    let normalized = String(value)
        .trim()
        .toLowerCase();

    if (!normalized) {
        return "";
    }

    /*
    |--------------------------------------------------------------------------
    | Remove common prefixes
    |--------------------------------------------------------------------------
    */

    normalized =
        normalized
            .replace(
                /^option\s+/i,
                ""
            )
            .replace(
                /^answer\s+/i,
                ""
            )
            .replace(
                /^उत्तर\s+/i,
                ""
            )
            .trim();

    /*
    |--------------------------------------------------------------------------
    | Direct A/B/C/D
    |--------------------------------------------------------------------------
    */

    if (
        [
            "a",
            "b",
            "c",
            "d",
        ].includes(
            normalized
        )
    ) {
        return normalized.toUpperCase();
    }

    /*
    |--------------------------------------------------------------------------
    | Match option key
    |--------------------------------------------------------------------------
    */

    const optionByKey =
        options.find(
            (
                option,
                index
            ) => {
                const key =
                    getOptionKey(
                        option,
                        index
                    ).toLowerCase();

                return (
                    key ===
                    normalized
                );
            }
        );

    if (optionByKey) {
        const index =
            options.indexOf(
                optionByKey
            );

        return getOptionKey(
            optionByKey,
            index
        ).toUpperCase();
    }

    /*
    |--------------------------------------------------------------------------
    | Match option text
    |--------------------------------------------------------------------------
    */

    const optionByText =
        options.find(
            (option) => {
                const text =
                    String(
                        getOptionValue(
                            option
                        )
                    )
                        .trim()
                        .toLowerCase();

                return (
                    text ===
                    normalized
                );
            }
        );

    if (optionByText) {
        const index =
            options.indexOf(
                optionByText
            );

        return getOptionKey(
            optionByText,
            index
        ).toUpperCase();
    }

    /*
    |--------------------------------------------------------------------------
    | B. India Meteorological Department
    |--------------------------------------------------------------------------
    */

    const letterMatch =
        normalized.match(
            /^([abcd])[\.\:\-\)\s]/
        );

    if (letterMatch) {
        return letterMatch[1]
            .toUpperCase();
    }

    /*
    |--------------------------------------------------------------------------
    | Search beginning of option text
    |--------------------------------------------------------------------------
    */

    const optionByStart =
        options.find(
            (option) => {
                const text =
                    String(
                        getOptionValue(
                            option
                        )
                    )
                        .trim()
                        .toLowerCase();

                return (
                    normalized ===
                        text ||
                    normalized.startsWith(
                        `${text} `
                    ) ||
                    text.startsWith(
                        `${normalized} `
                    )
                );
            }
        );

    if (optionByStart) {
        const index =
            options.indexOf(
                optionByStart
            );

        return getOptionKey(
            optionByStart,
            index
        ).toUpperCase();
    }

    return "";
};

/*
|--------------------------------------------------------------------------
| NORMALIZE ONE QUESTION
|--------------------------------------------------------------------------
*/

const normalizeQuestion = (
    question
) => {
    if (
        !question ||
        typeof question !== "object"
    ) {
        return null;
    }

    const options =
        getOptions(question);

    if (
        !Array.isArray(options) ||
        options.length < 4
    ) {
        return null;
    }

    /*
    |--------------------------------------------------------------------------
    | Force A/B/C/D order
    |--------------------------------------------------------------------------
    */

    const normalizedOptions =
        [
            "A",
            "B",
            "C",
            "D",
        ].map(
            (
                expectedKey,
                index
            ) => {
                const found =
                    options.find(
                        (
                            option,
                            optionIndex
                        ) =>
                            getOptionKey(
                                option,
                                optionIndex
                            ) ===
                            expectedKey
                    );

                if (found) {
                    return {
                        key:
                            expectedKey,

                        value:
                            getOptionValue(
                                found
                            ),
                    };
                }

                const positional =
                    options[index];

                return {
                    key:
                        expectedKey,

                    value:
                        getOptionValue(
                            positional
                        ),
                };
            }
        );

    /*
    |--------------------------------------------------------------------------
    | Article relationship
    |--------------------------------------------------------------------------
    */

    const articleId =
        getArticleId(
            question
        );

    return {
        ...question,

        article_id:
            articleId,

        question:
            getQuestionText(
                question
            ),

        options:
            normalizedOptions,

        correct_answer:
            getCorrectAnswer(
                question
            ),

        explanation:
            getExplanation(
                question
            ),
    };
};

/*
|--------------------------------------------------------------------------
| NORMALIZE QUESTION LIST
|--------------------------------------------------------------------------
*/

const normalizeQuestionList = (
    data
) => {
    return normalizeQuestions(data)
        .map(
            normalizeQuestion
        )
        .filter(Boolean);
};

/*
|--------------------------------------------------------------------------
| COMPONENT
|--------------------------------------------------------------------------
*/

function MCQs() {
    const [
        questions,
        setQuestions,
    ] = useState([]);

    const [
        loading,
        setLoading,
    ] = useState(true);

    const [
        refreshing,
        setRefreshing,
    ] = useState(false);

    const [
        error,
        setError,
    ] = useState("");

    const [
        currentIndex,
        setCurrentIndex,
    ] = useState(0);

    const [
        selectedAnswer,
        setSelectedAnswer,
    ] = useState(null);

    const [
        submitted,
        setSubmitted,
    ] = useState(false);

    const [
        score,
        setScore,
    ] = useState(0);

    const [
        showExplanation,
        setShowExplanation,
    ] = useState(false);

    const [
        generating,
        setGenerating,
    ] = useState(false);

    const [
        language,
        setLanguage,
    ] = useState(
        getStoredLanguage()
    );

    const isHindi =
        normalizeLanguage(
            language
        ) === "hi";

    /*
    |--------------------------------------------------------------------------
    | CHANGE LANGUAGE
    |--------------------------------------------------------------------------
    */

    const handleLanguageChange =
        () => {
            const nextLanguage =
                language === "hi"
                    ? "en"
                    : "hi";

            localStorage.setItem(
                "language",
                nextLanguage
            );

            localStorage.setItem(
                "appLanguage",
                nextLanguage
            );

            setLanguage(
                nextLanguage
            );
        };

    /*
    |--------------------------------------------------------------------------
    | CURRENT QUESTION
    |--------------------------------------------------------------------------
    */

    const currentQuestion =
        questions[
            currentIndex
        ] || null;

    const options =
        useMemo(
            () =>
                currentQuestion
                    ? getOptions(
                          currentQuestion
                      )
                    : [],
            [currentQuestion]
        );

    const correctAnswer =
        currentQuestion
            ? getCorrectAnswer(
                  currentQuestion
              )
            : null;

    const selectedKey =
        normalizeAnswerKey(
            selectedAnswer,
            options
        );

    const correctKey =
        normalizeAnswerKey(
            correctAnswer,
            options
        );

    const answerIsCorrect =
        submitted &&
        selectedKey !== "" &&
        correctKey !== "" &&
        selectedKey === correctKey;

    /*
    |--------------------------------------------------------------------------
    | LOAD PRACTICE QUESTIONS
    |--------------------------------------------------------------------------
    */

    const loadQuestions =
        useCallback(
            async (
                isRefresh = false
            ) => {
                if (isRefresh) {
                    setRefreshing(true);
                } else {
                    setLoading(true);
                }

                setError("");

                try {
                    const token =
                        getToken();

                    const currentLanguage =
                        normalizeLanguage(
                            language
                        );

                    const response =
                        await axios.get(
                            `${API_URL}/news/mcqs/practice`,
                            {
                                timeout: 20000,

                                headers: {
                                    Accept:
                                        "application/json",

                                    ...(token
                                        ? {
                                              Authorization:
                                                  `Bearer ${token}`,
                                          }
                                        : {}),
                                },

                                params: {
                                    page: 1,

                                    page_size:
                                        PRACTICE_PAGE_SIZE,

                                    language:
                                        currentLanguage,
                                },
                            }
                        );

                    console.log(
                        "Practice MCQ API:",
                        response.data
                    );

                    const normalized =
                        normalizeQuestionList(
                            response.data
                        );

                    setQuestions(
                        normalized
                    );

                    setCurrentIndex(0);

                    setSelectedAnswer(
                        null
                    );

                    setSubmitted(
                        false
                    );

                    setScore(0);

                    setShowExplanation(
                        false
                    );

                } catch (err) {
                    console.error(
                        "Failed to load MCQs:",
                        err
                    );

                    setError(
                        getErrorMessage(
                            err,
                            language
                        )
                    );
                } finally {
                    setLoading(false);
                    setRefreshing(false);
                }
            },
            [language]
        );

    /*
    |--------------------------------------------------------------------------
    | INITIAL LOAD + LANGUAGE CHANGE
    |--------------------------------------------------------------------------
    */

    useEffect(() => {
        loadQuestions();
    }, [loadQuestions]);

    /*
    |--------------------------------------------------------------------------
    | SELECT ANSWER
    |--------------------------------------------------------------------------
    */

    const handleSelectAnswer =
        (answerKey) => {
            if (submitted) {
                return;
            }

            setSelectedAnswer(
                answerKey
            );
        };

    /*
    |--------------------------------------------------------------------------
    | SUBMIT ANSWER
    |--------------------------------------------------------------------------
    */

    const handleSubmitAnswer =
        () => {
            if (
                !currentQuestion ||
                !selectedAnswer
            ) {
                return;
            }

            const selected =
                normalizeAnswerKey(
                    selectedAnswer,
                    options
                );

            const correct =
                normalizeAnswerKey(
                    correctAnswer,
                    options
                );

            const isCorrect =
                selected !== "" &&
                correct !== "" &&
                selected === correct;

            setSubmitted(true);

            if (isCorrect) {
                setScore(
                    (previous) =>
                        previous + 1
                );
            }
        };

    /*
    |--------------------------------------------------------------------------
    | NEXT
    |--------------------------------------------------------------------------
    */

    const handleNext = () => {
        if (
            currentIndex >=
            questions.length - 1
        ) {
            return;
        }

        setCurrentIndex(
            (previous) =>
                previous + 1
        );

        setSelectedAnswer(
            null
        );

        setSubmitted(false);

        setShowExplanation(
            false
        );
    };

    /*
    |--------------------------------------------------------------------------
    | PREVIOUS
    |--------------------------------------------------------------------------
    */

    const handlePrevious =
        () => {
            if (
                currentIndex <= 0
            ) {
                return;
            }

            setCurrentIndex(
                (previous) =>
                    previous - 1
            );

            setSelectedAnswer(
                null
            );

            setSubmitted(false);

            setShowExplanation(
                false
            );
        };

    /*
    |--------------------------------------------------------------------------
    | GENERATE MCQs FROM CURRENT ARTICLE
    |--------------------------------------------------------------------------
    */

    const handleGenerateForArticle =
        async () => {
            if (!currentQuestion) {
                return;
            }

            const articleId =
                getArticleId(
                    currentQuestion
                );

            console.log(
                "Current MCQ:",
                currentQuestion
            );

            console.log(
                "Detected article ID:",
                articleId
            );

            if (
                articleId ===
                    null ||
                articleId ===
                    undefined ||
                articleId === ""
            ) {
                setError(
                    isHindi
                        ? "यह प्रश्न किसी news article से linked नहीं है।"
                        : "This question is not linked to a news article."
                );

                return;
            }

            setGenerating(true);

            setError("");

            try {
                const token =
                    getToken();

                const currentLanguage =
                    normalizeLanguage(
                        language
                    );

                const response =
                    await axios.post(
                        `${API_URL}/news/${articleId}/mcqs/generate`,
                        {},
                        {
                            timeout: 60000,

                            headers: {
                                Accept:
                                    "application/json",

                                "Content-Type":
                                    "application/json",

                                ...(token
                                    ? {
                                          Authorization:
                                              `Bearer ${token}`,
                                      }
                                    : {}),
                            },

                            params: {
                                language:
                                    currentLanguage,
                            },
                        }
                    );

                console.log(
                    "Generated MCQ response:",
                    response.data
                );

                const generated =
                    normalizeQuestionList(
                        response.data
                    );

                /*
                |--------------------------------------------------------------------------
                | Generated questions available
                |--------------------------------------------------------------------------
                */

                if (
                    generated.length >
                    0
                ) {
                    const linkedGenerated =
                        generated.map(
                            (
                                question
                            ) => ({
                                ...question,

                                article_id:
                                    getArticleId(
                                        question
                                    ) ??
                                    articleId,

                                language:
                                    currentLanguage,
                            })
                        );

                    setQuestions(
                        linkedGenerated
                    );

                    setCurrentIndex(0);

                    setSelectedAnswer(
                        null
                    );

                    setSubmitted(
                        false
                    );

                    setScore(0);

                    setShowExplanation(
                        false
                    );

                    return;
                }

                /*
                |--------------------------------------------------------------------------
                | Reload if backend returns success
                |--------------------------------------------------------------------------
                */

                await loadQuestions(
                    true
                );

            } catch (err) {
                console.error(
                    "Failed to generate article MCQs:",
                    err
                );

                setError(
                    getErrorMessage(
                        err,
                        language
                    )
                );
            } finally {
                setGenerating(false);
            }
        };

    /*
    |--------------------------------------------------------------------------
    | LOADING
    |--------------------------------------------------------------------------
    */

    if (loading) {
        return (
            <main
                style={styles.page}
            >
                <div
                    style={
                        styles.container
                    }
                >
                    <div
                        style={
                            styles.loadingCard
                        }
                    >
                        <div
                            style={
                                styles.spinner
                            }
                        />

                        <h2
                            style={
                                styles.loadingTitle
                            }
                        >
                            {isHindi
                                ? "MCQ लोड हो रहे हैं..."
                                : "Loading MCQs..."}
                        </h2>

                        <p
                            style={
                                styles.loadingText
                            }
                        >
                            {isHindi
                                ? "आपके अभ्यास प्रश्न तैयार किए जा रहे हैं।"
                                : "Preparing your practice questions."}
                        </p>
                    </div>
                </div>
            </main>
        );
    }

    /*
    |--------------------------------------------------------------------------
    | ERROR WITH NO QUESTIONS
    |--------------------------------------------------------------------------
    */

    if (
        error &&
        questions.length === 0
    ) {
        return (
            <main
                style={styles.page}
            >
                <div
                    style={
                        styles.container
                    }
                >
                    <header
                        style={
                            styles.topBar
                        }
                    >
                        <Link
                            to="/dashboard"
                            style={
                                styles.backLink
                            }
                        >
                            ←{" "}
                            {isHindi
                                ? "डैशबोर्ड"
                                : "Dashboard"}
                        </Link>

                        <div
                            style={
                                styles.brand
                            }
                        >
                            <div
                                style={
                                    styles.logo
                                }
                            >
                                M
                            </div>

                            <div>
                                <div
                                    style={
                                        styles.brandName
                                    }
                                >
                                    Muni48
                                </div>

                                <div
                                    style={
                                        styles.brandSub
                                    }
                                >
                                    Civil Services
                                </div>
                            </div>
                        </div>

                        <div
                            style={
                                styles.headerActions
                            }
                        >
                            <button
                                type="button"
                                onClick={
                                    handleLanguageChange
                                }
                                style={
                                    styles.languageButton
                                }
                            >
                                {isHindi
                                    ? "🇬🇧 English"
                                    : "🇮🇳 हिंदी"}
                            </button>
                        </div>
                    </header>

                    <div
                        style={
                            styles.errorCard
                        }
                    >
                        <div
                            style={
                                styles.errorIcon
                            }
                        >
                            !
                        </div>

                        <h2
                            style={
                                styles.errorTitle
                            }
                        >
                            {isHindi
                                ? "MCQ लोड नहीं हो सके"
                                : "Unable to load MCQs"}
                        </h2>

                        <p
                            style={
                                styles.errorText
                            }
                        >
                            {error}
                        </p>

                        <button
                            type="button"
                            onClick={() =>
                                loadQuestions(
                                    true
                                )
                            }
                            style={
                                styles.primaryButton
                            }
                        >
                            {refreshing
                                ? (
                                    isHindi
                                        ? "दोबारा प्रयास..."
                                        : "Retrying..."
                                )
                                : (
                                    isHindi
                                        ? "दोबारा प्रयास करें"
                                        : "Retry"
                                )}
                        </button>
                    </div>
                </div>
            </main>
        );
    }

    /*
    |--------------------------------------------------------------------------
    | EMPTY
    |--------------------------------------------------------------------------
    */

    if (
        questions.length === 0
    ) {
        return (
            <main
                style={styles.page}
            >
                <div
                    style={
                        styles.container
                    }
                >
                    <header
                        style={
                            styles.topBar
                        }
                    >
                        <Link
                            to="/dashboard"
                            style={
                                styles.backLink
                            }
                        >
                            ←{" "}
                            {isHindi
                                ? "डैशबोर्ड"
                                : "Dashboard"}
                        </Link>

                        <div
                            style={
                                styles.brand
                            }
                        >
                            <div
                                style={
                                    styles.logo
                                }
                            >
                                M
                            </div>

                            <div>
                                <div
                                    style={
                                        styles.brandName
                                    }
                                >
                                    Muni48
                                </div>

                                <div
                                    style={
                                        styles.brandSub
                                    }
                                >
                                    Civil Services
                                </div>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={
                                handleLanguageChange
                            }
                            style={
                                styles.languageButton
                            }
                        >
                            {isHindi
                                ? "🇬🇧 English"
                                : "🇮🇳 हिंदी"}
                        </button>
                    </header>

                    <div
                        style={
                            styles.emptyCard
                        }
                    >
                        <div
                            style={
                                styles.emptyIcon
                            }
                        >
                            🎯
                        </div>

                        <h1
                            style={
                                styles.emptyTitle
                            }
                        >
                            {isHindi
                                ? "कोई MCQ उपलब्ध नहीं है"
                                : "No MCQs available"}
                        </h1>

                        <p
                            style={
                                styles.emptyText
                            }
                        >
                            {isHindi
                                ? "अभी कोई अभ्यास प्रश्न उपलब्ध नहीं है।"
                                : "There are no practice questions available right now."}
                        </p>

                        <button
                            type="button"
                            onClick={() =>
                                loadQuestions(
                                    true
                                )
                            }
                            style={
                                styles.primaryButton
                            }
                        >
                            {isHindi
                                ? "रिफ्रेश"
                                : "Refresh"}
                        </button>
                    </div>
                </div>
            </main>
        );
    }

    /*
    |--------------------------------------------------------------------------
    | MAIN UI
    |--------------------------------------------------------------------------
    */

    return (
        <main
            style={styles.page}
        >
            <div
                style={
                    styles.container
                }
            >

                {/* HEADER */}

                <header
                    style={
                        styles.topBar
                    }
                >
                    <Link
                        to="/dashboard"
                        style={
                            styles.backLink
                        }
                    >
                        ←{" "}
                        {isHindi
                            ? "डैशबोर्ड"
                            : "Dashboard"}
                    </Link>

                    <div
                        style={
                            styles.brand
                        }
                    >
                        <div
                            style={
                                styles.logo
                            }
                        >
                            M
                        </div>

                        <div>
                            <div
                                style={
                                    styles.brandName
                                }
                            >
                                Muni48
                            </div>

                            <div
                                style={
                                    styles.brandSub
                                }
                            >
                                Civil Services
                            </div>
                        </div>
                    </div>

                    <div
                        style={
                            styles.headerActions
                        }
                    >
                        <button
                            type="button"
                            onClick={
                                handleLanguageChange
                            }
                            style={
                                styles.languageButton
                            }
                        >
                            {isHindi
                                ? "🇬🇧 English"
                                : "🇮🇳 हिंदी"}
                        </button>

                        <button
                            type="button"
                            onClick={() =>
                                loadQuestions(
                                    true
                                )
                            }
                            disabled={
                                refreshing
                            }
                            style={
                                styles.refreshButton
                            }
                        >
                            ↻{" "}
                            {refreshing
                                ? (
                                    isHindi
                                        ? "रिफ्रेश..."
                                        : "Refreshing"
                                )
                                : (
                                    isHindi
                                        ? "रिफ्रेश"
                                        : "Refresh"
                                )}
                        </button>
                    </div>
                </header>

                {/* TITLE */}

                <section
                    style={
                        styles.headingSection
                    }
                >
                    <div>
                        <div
                            style={
                                styles.eyebrow
                            }
                        >
                            {isHindi
                                ? "अभ्यास"
                                : "PRACTICE"}
                        </div>

                        <h1
                            style={
                                styles.title
                            }
                        >
                            {isHindi
                                ? "MCQ अभ्यास"
                                : "MCQ Practice"}
                        </h1>

                        <p
                            style={
                                styles.subtitle
                            }
                        >
                            {isHindi
                                ? "UPSC और BPSC समसामयिकी के अपने ज्ञान का परीक्षण करें।"
                                : "Test your UPSC & BPSC current affairs knowledge."}
                        </p>
                    </div>

                    <div
                        style={
                            styles.scoreBox
                        }
                    >
                        <span
                            style={
                                styles.scoreLabel
                            }
                        >
                            {isHindi
                                ? "स्कोर"
                                : "Score"}
                        </span>

                        <strong
                            style={
                                styles.score
                            }
                        >
                            {score}
                        </strong>

                        <span
                            style={
                                styles.scoreTotal
                            }
                        >
                            /{" "}
                            {
                                questions.length
                            }
                        </span>
                    </div>
                </section>

                {/* ERROR */}

                {error && (
                    <div
                        role="alert"
                        style={
                            styles.inlineError
                        }
                    >
                        <span>
                            {error}
                        </span>

                        <button
                            type="button"
                            onClick={() =>
                                setError(
                                    ""
                                )
                            }
                            style={
                                styles.closeError
                            }
                        >
                            ×
                        </button>
                    </div>
                )}

                {/* PROGRESS */}

                <div
                    style={
                        styles.progressWrapper
                    }
                >
                    <div
                        style={
                            styles.progressHeader
                        }
                    >
                        <span>
                            {isHindi
                                ? "प्रश्न"
                                : "Question"}{" "}
                            {currentIndex +
                                1}{" "}
                            {isHindi
                                ? "में से"
                                : "of"}{" "}
                            {
                                questions.length
                            }
                        </span>

                        <span>
                            {Math.round(
                                (
                                    (
                                        currentIndex +
                                        1
                                    ) /
                                    questions.length
                                ) *
                                    100
                            )}
                            %
                        </span>
                    </div>

                    <div
                        style={
                            styles.progressTrack
                        }
                    >
                        <div
                            style={{
                                ...styles.progressBar,

                                width:
                                    `${
                                        (
                                            (
                                                currentIndex +
                                                1
                                            ) /
                                            questions.length
                                        ) *
                                        100
                                    }%`,
                            }}
                        />
                    </div>
                </div>

                {/* QUESTION */}

                <section
                    style={
                        styles.questionCard
                    }
                >
                    <div
                        style={
                            styles.questionNumber
                        }
                    >
                        {isHindi
                            ? "प्रश्न"
                            : "Question"}{" "}
                        {currentIndex +
                            1}
                    </div>

                    <h2
                        style={
                            styles.questionText
                        }
                    >
                        {getQuestionText(
                            currentQuestion
                        )}
                    </h2>

                    {/* OPTIONS */}

                    <div
                        style={
                            styles.options
                        }
                    >
                        {options.map(
                            (
                                option,
                                index
                            ) => {
                                const optionKey =
                                    getOptionKey(
                                        option,
                                        index
                                    );

                                const optionValue =
                                    getOptionValue(
                                        option
                                    );

                                const isSelected =
                                    selectedKey ===
                                    optionKey;

                                const isCorrect =
                                    submitted &&
                                    correctKey ===
                                        optionKey;

                                const isWrong =
                                    submitted &&
                                    isSelected &&
                                    !isCorrect;

                                return (
                                    <button
                                        key={`${optionKey}-${index}`}
                                        type="button"
                                        disabled={
                                            submitted
                                        }
                                        onClick={() =>
                                            handleSelectAnswer(
                                                optionKey
                                            )
                                        }
                                        style={{
                                            ...styles.option,

                                            ...(isSelected
                                                ? styles.optionSelected
                                                : {}),

                                            ...(isCorrect
                                                ? styles.optionCorrect
                                                : {}),

                                            ...(isWrong
                                                ? styles.optionWrong
                                                : {}),
                                        }}
                                    >
                                        <span
                                            style={{
                                                ...styles.optionKey,

                                                ...(isSelected
                                                    ? styles.optionKeySelected
                                                    : {}),

                                                ...(isCorrect
                                                    ? styles.optionKeyCorrect
                                                    : {}),

                                                ...(isWrong
                                                    ? styles.optionKeyWrong
                                                    : {}),
                                            }}
                                        >
                                            {
                                                optionKey
                                            }
                                        </span>

                                        <span
                                            style={
                                                styles.optionText
                                            }
                                        >
                                            {
                                                optionValue
                                            }
                                        </span>

                                        {submitted &&
                                            isCorrect && (
                                                <span
                                                    style={
                                                        styles.answerMark
                                                    }
                                                >
                                                    ✓
                                                </span>
                                            )}

                                        {submitted &&
                                            isWrong && (
                                                <span
                                                    style={
                                                        styles.answerMark
                                                    }
                                                >
                                                    ✕
                                                </span>
                                            )}
                                    </button>
                                );
                            }
                        )}
                    </div>

                    {/* SUBMIT */}

                    {!submitted ? (
                        <button
                            type="button"
                            onClick={
                                handleSubmitAnswer
                            }
                            disabled={
                                !selectedAnswer
                            }
                            style={{
                                ...styles.primaryButton,

                                ...(!selectedAnswer
                                    ? styles.buttonDisabled
                                    : {}),
                            }}
                        >
                            {isHindi
                                ? "उत्तर जमा करें"
                                : "Submit Answer"}
                        </button>
                    ) : (
                        <div
                            style={
                                styles.resultBox
                            }
                        >
                            {answerIsCorrect ? (
                                <>
                                    <div
                                        style={
                                            styles.resultCorrect
                                        }
                                    >
                                        ✓{" "}
                                        {isHindi
                                            ? "सही उत्तर!"
                                            : "Correct!"}
                                    </div>

                                    <p
                                        style={
                                            styles.resultText
                                        }
                                    >
                                        {isHindi
                                            ? "बहुत अच्छा।"
                                            : "Excellent work."}
                                    </p>
                                </>
                            ) : (
                                <>
                                    <div
                                        style={
                                            styles.resultWrong
                                        }
                                    >
                                        ✕{" "}
                                        {isHindi
                                            ? "गलत उत्तर"
                                            : "Incorrect"}
                                    </div>

                                    <p
                                        style={
                                            styles.resultText
                                        }
                                    >
                                        {isHindi
                                            ? "सही उत्तर और व्याख्या देखें।"
                                            : "Review the correct answer and explanation."}
                                    </p>
                                </>
                            )}

                            {correctKey && (
                                <p
                                    style={
                                        styles.correctAnswerText
                                    }
                                >
                                    {isHindi
                                        ? "सही उत्तर:"
                                        : "Correct Answer:"}{" "}
                                    <strong>
                                        {
                                            correctKey
                                        }
                                    </strong>
                                </p>
                            )}

                            {getExplanation(
                                currentQuestion
                            ) && (
                                <button
                                    type="button"
                                    onClick={() =>
                                        setShowExplanation(
                                            (
                                                previous
                                            ) =>
                                                !previous
                                        )
                                    }
                                    style={
                                        styles.explanationButton
                                    }
                                >
                                    {showExplanation
                                        ? (
                                            isHindi
                                                ? "व्याख्या छिपाएँ"
                                                : "Hide Explanation"
                                        )
                                        : (
                                            isHindi
                                                ? "व्याख्या देखें"
                                                : "Show Explanation"
                                        )}
                                </button>
                            )}

                            {showExplanation &&
                                getExplanation(
                                    currentQuestion
                                ) && (
                                    <div
                                        style={
                                            styles.explanation
                                        }
                                    >
                                        <strong>
                                            {isHindi
                                                ? "व्याख्या"
                                                : "Explanation"}
                                        </strong>

                                        <p>
                                            {getExplanation(
                                                currentQuestion
                                            )}
                                        </p>
                                    </div>
                                )}
                        </div>
                    )}

                    {/* NAVIGATION */}

                    <div
                        style={
                            styles.navigation
                        }
                    >
                        <button
                            type="button"
                            onClick={
                                handlePrevious
                            }
                            disabled={
                                currentIndex ===
                                0
                            }
                            style={{
                                ...styles.secondaryButton,

                                ...(currentIndex ===
                                0
                                    ? styles.buttonDisabled
                                    : {}),
                            }}
                        >
                            ←{" "}
                            {isHindi
                                ? "पिछला"
                                : "Previous"}
                        </button>

                        {currentIndex <
                        questions.length -
                            1 ? (
                            <button
                                type="button"
                                onClick={
                                    handleNext
                                }
                                disabled={
                                    !submitted
                                }
                                style={{
                                    ...styles.primaryButton,

                                    ...(!submitted
                                        ? styles.buttonDisabled
                                        : {}),
                                }}
                            >
                                {isHindi
                                    ? "अगला"
                                    : "Next"}{" "}
                                →
                            </button>
                        ) : (
                            <button
                                type="button"
                                onClick={() =>
                                    loadQuestions(
                                        true
                                    )
                                }
                                style={
                                    styles.primaryButton
                                }
                            >
                                {isHindi
                                    ? "नया अभ्यास"
                                    : "New Practice"}
                            </button>
                        )}
                    </div>
                </section>

                {/* ARTICLE GENERATION */}

                <section
                    style={
                        styles.generateCard
                    }
                >
                    <div>
                        <div
                            style={
                                styles.generateIcon
                            }
                        >
                            📰
                        </div>
                    </div>

                    <div
                        style={
                            styles.generateContent
                        }
                    >
                        <h3
                            style={
                                styles.generateTitle
                            }
                        >
                            {isHindi
                                ? "समसामयिकी से MCQ बनाएँ"
                                : "Generate MCQs from Current Affairs"}
                        </h3>

                        <p
                            style={
                                styles.generateText
                            }
                        >
                            {isHindi
                                ? "यदि यह प्रश्न किसी news article से linked है, तो उसी article से नए MCQs बनाए जा सकते हैं।"
                                : "If this question is linked to a news article, you can generate fresh MCQs from that article."}
                        </p>

                        <button
                            type="button"
                            onClick={
                                handleGenerateForArticle
                            }
                            disabled={
                                generating
                            }
                            style={{
                                ...styles.secondaryButton,

                                ...(generating
                                    ? styles.buttonDisabled
                                    : {}),
                            }}
                        >
                            {generating
                                ? (
                                    isHindi
                                        ? "MCQ बनाए जा रहे हैं..."
                                        : "Generating..."
                                )
                                : (
                                    isHindi
                                        ? "Article से MCQ बनाएँ"
                                        : "Generate Article MCQs"
                                )}
                        </button>
                    </div>
                </section>

                {/* FOOTER */}

                <footer
                    style={
                        styles.footer
                    }
                >
                    © 2026 Muni48 ·{" "}
                    {isHindi
                        ? "UPSC एवं BPSC तैयारी प्लेटफ़ॉर्म"
                        : "UPSC & BPSC Preparation Platform"}
                </footer>
            </div>
        </main>
    );
}

/*
|--------------------------------------------------------------------------
| STYLES
|--------------------------------------------------------------------------
*/

const styles = {
    page: {
        minHeight: "100vh",

        background:
            "linear-gradient(135deg, #eff6ff 0%, #f8fafc 50%, #eef2ff 100%)",

        padding: "24px",

        boxSizing: "border-box",

        color: "#0f172a",
    },

    container: {
        width: "100%",

        maxWidth: "1000px",

        margin: "0 auto",
    },

    topBar: {
        display: "flex",

        alignItems: "center",

        justifyContent:
            "space-between",

        gap: "20px",

        marginBottom: "36px",
    },

    headerActions: {
        display: "flex",

        alignItems: "center",

        gap: "10px",
    },

    backLink: {
        color: "#2563eb",

        textDecoration: "none",

        fontSize: "14px",

        fontWeight: "700",
    },

    brand: {
        display: "flex",

        alignItems: "center",

        gap: "10px",
    },

    logo: {
        width: "42px",

        height: "42px",

        borderRadius: "12px",

        display: "flex",

        alignItems: "center",

        justifyContent:
            "center",

        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",

        color: "#ffffff",

        fontSize: "20px",

        fontWeight: "800",
    },

    brandName: {
        fontSize: "18px",

        fontWeight: "800",

        color: "#111827",
    },

    brandSub: {
        fontSize: "11px",

        color: "#64748b",
    },

    languageButton: {
        border:
            "1px solid #cbd5e1",

        background: "#ffffff",

        color: "#334155",

        borderRadius: "9px",

        padding: "9px 14px",

        cursor: "pointer",

        fontSize: "13px",

        fontWeight: "700",
    },

    refreshButton: {
        border:
            "1px solid #cbd5e1",

        background: "#ffffff",

        color: "#334155",

        borderRadius: "9px",

        padding: "9px 14px",

        cursor: "pointer",

        fontSize: "13px",

        fontWeight: "600",
    },

    headingSection: {
        display: "flex",

        justifyContent:
            "space-between",

        alignItems: "flex-end",

        gap: "20px",

        marginBottom: "28px",
    },

    eyebrow: {
        color: "#2563eb",

        fontSize: "11px",

        fontWeight: "800",

        letterSpacing: "1.5px",

        marginBottom: "6px",
    },

    title: {
        margin: 0,

        fontSize: "34px",

        fontWeight: "800",

        color: "#111827",
    },

    subtitle: {
        margin: "8px 0 0",

        color: "#64748b",

        fontSize: "15px",
    },

    scoreBox: {
        minWidth: "100px",

        background: "#ffffff",

        border:
            "1px solid #e2e8f0",

        borderRadius: "14px",

        padding: "12px 18px",

        textAlign: "center",

        boxShadow:
            "0 8px 25px rgba(15, 23, 42, 0.06)",
    },

    scoreLabel: {
        display: "block",

        color: "#64748b",

        fontSize: "11px",

        fontWeight: "700",

        textTransform:
            "uppercase",
    },

    score: {
        fontSize: "28px",

        color: "#2563eb",
    },

    scoreTotal: {
        color: "#94a3b8",

        fontSize: "14px",
    },

    progressWrapper: {
        marginBottom: "20px",
    },

    progressHeader: {
        display: "flex",

        justifyContent:
            "space-between",

        color: "#64748b",

        fontSize: "12px",

        fontWeight: "600",

        marginBottom: "7px",
    },

    progressTrack: {
        width: "100%",

        height: "7px",

        background: "#e2e8f0",

        borderRadius: "999px",

        overflow: "hidden",
    },

    progressBar: {
        height: "100%",

        background:
            "linear-gradient(90deg, #2563eb, #4f46e5)",

        borderRadius: "999px",

        transition:
            "width 0.3s ease",
    },

    questionCard: {
        background: "#ffffff",

        borderRadius: "18px",

        padding: "30px",

        border:
            "1px solid #e2e8f0",

        boxShadow:
            "0 15px 45px rgba(15, 23, 42, 0.07)",
    },

    questionNumber: {
        color: "#2563eb",

        fontSize: "12px",

        fontWeight: "800",

        textTransform:
            "uppercase",

        letterSpacing: "0.8px",

        marginBottom: "12px",
    },

    questionText: {
        margin: 0,

        fontSize: "21px",

        lineHeight: "1.55",

        color: "#111827",

        fontWeight: "700",
    },

    options: {
        display: "grid",

        gap: "12px",

        marginTop: "26px",

        marginBottom: "24px",
    },

    option: {
        width: "100%",

        display: "flex",

        alignItems: "center",

        gap: "13px",

        padding: "14px",

        borderRadius: "11px",

        border:
            "1px solid #cbd5e1",

        background: "#ffffff",

        cursor: "pointer",

        textAlign: "left",

        fontSize: "14px",

        color: "#334155",
    },

    optionSelected: {
        border:
            "2px solid #2563eb",

        background: "#eff6ff",
    },

    optionCorrect: {
        border:
            "2px solid #16a34a",

        background: "#f0fdf4",
    },

    optionWrong: {
        border:
            "2px solid #dc2626",

        background: "#fef2f2",
    },

    optionKey: {
        width: "32px",

        height: "32px",

        minWidth: "32px",

        borderRadius: "50%",

        display: "flex",

        alignItems: "center",

        justifyContent:
            "center",

        background: "#f1f5f9",

        color: "#475569",

        fontWeight: "800",

        fontSize: "12px",
    },

    optionKeySelected: {
        background: "#2563eb",

        color: "#ffffff",
    },

    optionKeyCorrect: {
        background: "#16a34a",

        color: "#ffffff",
    },

    optionKeyWrong: {
        background: "#dc2626",

        color: "#ffffff",
    },

    optionText: {
        flex: 1,

        lineHeight: "1.5",
    },

    answerMark: {
        fontSize: "18px",

        fontWeight: "800",
    },

    primaryButton: {
        border: "none",

        borderRadius: "10px",

        padding: "12px 20px",

        background:
            "linear-gradient(135deg, #2563eb, #4f46e5)",

        color: "#ffffff",

        cursor: "pointer",

        fontSize: "14px",

        fontWeight: "700",

        boxShadow:
            "0 7px 18px rgba(37, 99, 235, 0.18)",
    },

    secondaryButton: {
        border:
            "1px solid #cbd5e1",

        borderRadius: "10px",

        padding: "11px 18px",

        background: "#ffffff",

        color: "#334155",

        cursor: "pointer",

        fontSize: "14px",

        fontWeight: "700",
    },

    buttonDisabled: {
        opacity: 0.45,

        cursor: "not-allowed",

        boxShadow: "none",
    },

    resultBox: {
        marginTop: "8px",

        padding: "18px",

        borderRadius: "12px",

        background: "#f8fafc",

        border:
            "1px solid #e2e8f0",
    },

    resultCorrect: {
        color: "#15803d",

        fontSize: "18px",

        fontWeight: "800",
    },

    resultWrong: {
        color: "#b91c1c",

        fontSize: "18px",

        fontWeight: "800",
    },

    resultText: {
        margin: "6px 0 12px",

        color: "#64748b",

        fontSize: "13px",
    },

    correctAnswerText: {
        margin:
            "0 0 12px",

        color: "#334155",

        fontSize: "13px",
    },

    explanationButton: {
        border: "none",

        background:
            "transparent",

        color: "#2563eb",

        padding: 0,

        cursor: "pointer",

        fontSize: "13px",

        fontWeight: "700",
    },

    explanation: {
        marginTop: "14px",

        paddingTop: "14px",

        borderTop:
            "1px solid #e2e8f0",

        color: "#475569",

        fontSize: "13px",

        lineHeight: "1.6",
    },

    navigation: {
        display: "flex",

        justifyContent:
            "space-between",

        gap: "12px",

        marginTop: "24px",
    },

    generateCard: {
        display: "flex",

        gap: "18px",

        marginTop: "22px",

        padding: "22px",

        background: "#ffffff",

        border:
            "1px solid #e2e8f0",

        borderRadius: "16px",
    },

    generateIcon: {
        fontSize: "28px",
    },

    generateContent: {
        flex: 1,
    },

    generateTitle: {
        margin: 0,

        fontSize: "17px",

        color: "#111827",
    },

    generateText: {
        margin:
            "7px 0 15px",

        color: "#64748b",

        fontSize: "13px",

        lineHeight: "1.5",
    },

    inlineError: {
        display: "flex",

        justifyContent:
            "space-between",

        alignItems: "center",

        gap: "10px",

        marginBottom: "18px",

        padding: "12px 14px",

        borderRadius: "10px",

        background: "#fef2f2",

        border:
            "1px solid #fecaca",

        color: "#b91c1c",

        fontSize: "13px",
    },

    closeError: {
        border: "none",

        background:
            "transparent",

        color: "#b91c1c",

        cursor: "pointer",

        fontSize: "20px",
    },

    loadingCard: {
        maxWidth: "500px",

        margin: "120px auto",

        padding: "40px",

        textAlign: "center",

        background: "#ffffff",

        borderRadius: "18px",

        border:
            "1px solid #e2e8f0",

        boxShadow:
            "0 15px 45px rgba(15, 23, 42, 0.07)",
    },

    spinner: {
        width: "32px",

        height: "32px",

        margin:
            "0 auto 18px",

        borderRadius: "50%",

        border:
            "3px solid #dbeafe",

        borderTopColor:
            "#2563eb",

        animation:
            "spin 0.8s linear infinite",
    },

    loadingTitle: {
        margin: 0,

        color: "#111827",

        fontSize: "20px",
    },

    loadingText: {
        color: "#64748b",

        fontSize: "14px",
    },

    errorCard: {
        maxWidth: "550px",

        margin: "80px auto",

        padding: "35px",

        textAlign: "center",

        background: "#ffffff",

        borderRadius: "18px",

        border:
            "1px solid #fecaca",

        boxShadow:
            "0 15px 45px rgba(15, 23, 42, 0.07)",
    },

    errorIcon: {
        width: "42px",

        height: "42px",

        margin:
            "0 auto 14px",

        borderRadius: "50%",

        display: "flex",

        alignItems: "center",

        justifyContent:
            "center",

        background: "#dc2626",

        color: "#ffffff",

        fontWeight: "800",
    },

    errorTitle: {
        margin: 0,

        color: "#111827",

        fontSize: "21px",
    },

    errorText: {
        color: "#64748b",

        fontSize: "14px",

        lineHeight: "1.5",

        margin:
            "10px 0 20px",
    },

    emptyCard: {
        maxWidth: "550px",

        margin: "80px auto",

        padding: "40px",

        textAlign: "center",

        background: "#ffffff",

        borderRadius: "18px",

        border:
            "1px solid #e2e8f0",

        boxShadow:
            "0 15px 45px rgba(15, 23, 42, 0.07)",
    },

    emptyIcon: {
        fontSize: "45px",

        marginBottom: "12px",
    },

    emptyTitle: {
        margin: 0,

        fontSize: "24px",

        color: "#111827",
    },

    emptyText: {
        color: "#64748b",

        fontSize: "14px",

        margin:
            "10px 0 20px",
    },

    footer: {
        textAlign: "center",

        color: "#94a3b8",

        fontSize: "11px",

        marginTop: "30px",

        paddingBottom: "20px",
    },
};

export default MCQs;

