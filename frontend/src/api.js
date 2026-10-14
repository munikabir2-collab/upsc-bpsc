import axios from "axios";

const API = import.meta.env.PROD
  ? "https://upsc-bpsc.onrender.com"
  : (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000");

function getToken() {
  return localStorage.getItem("token") || sessionStorage.getItem("token");
}

export async function startNewsPayment() {
  const token = getToken();

  const r = await fetch(`${API}/news/payment/create-order`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  const order = await r.json();

  if (!r.ok) throw new Error("Order create nahi hua");
  if (order.has_access || order.access_active) return;

  return new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.order_id,
      name: "ExamExpress",
      description: "Today's News access",
      handler: async (resp) => {
        const v = await fetch(`${API}/news/payment/verify`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(resp),
        });
        if (v.ok) resolve();
        else reject(new Error("Payment verify fail hua"));
      },
      modal: { ondismiss: () => reject(new Error("Payment cancel kiya")) },
    });
    rzp.open();
  });
}

export async function apiFetch(path, options = {}, alreadyRetried = false) {
  const token = getToken();

  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });

  if (res.status === 402 && !alreadyRetried) {
    const err = await res.clone().json().catch(() => null);
    if (err?.detail?.code === "NEWS_PAYMENT_REQUIRED") {
      try {
        await startNewsPayment();
        return apiFetch(path, options, true);
      } catch (e) {
        return res;
      }
    }
  }
  return res;
}

export const http = axios.create({ baseURL: API, timeout: 15000 });

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (res) => res,
  async (error) => {
    const cfg = error.config;
    const code = error.response?.data?.detail?.code;
    if (
      error.response?.status === 402 &&
      code === "NEWS_PAYMENT_REQUIRED" &&
      cfg &&
      !cfg._retried
    ) {
      cfg._retried = true;
      try {
        await startNewsPayment();
      } catch (e) {
        return Promise.reject(error);
      }
      return http(cfg);
    }
    return Promise.reject(error);
  }
);

export default http;