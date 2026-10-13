import axios from "axios";

const API_URL =
    import.meta.env.VITE_API_URL ||
    "http://127.0.0.1:8000";

const api = axios.create({
    baseURL: API_URL,
    timeout: 15000,
    headers: {
        "Content-Type": "application/json",
    },
});

/*
|--------------------------------------------------------------------------
| Automatically attach JWT token
|--------------------------------------------------------------------------
*/

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("token");

        if (token) {
            config.headers.Authorization =
                `Bearer ${token}`;
        }

        return config;
    },
    (error) => Promise.reject(error)
);

/*
|--------------------------------------------------------------------------
| Global auth handling
|--------------------------------------------------------------------------
*/

api.interceptors.response.use(
    (response) => response,

    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem("token");
            localStorage.removeItem("user");

            window.location.href = "/login";
        }

        return Promise.reject(error);
    }
);

export default api;