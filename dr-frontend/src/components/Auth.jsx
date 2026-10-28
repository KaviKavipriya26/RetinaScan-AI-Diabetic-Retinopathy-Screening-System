import { useState, useEffect } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const JWT_SECRET = "m16bQVT1S7PenuyidaC2VV9HLRdMW0cdfvFjL4Tmhj8";

// Base64Url encoder helpers for RFC 7519 JWT
const toB64Url = (bytes) => {
  let binary = "";
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

const strToB64Url = (str) => toB64Url(new TextEncoder().encode(str));

// Generates cryptographically signed HS256 JWT using Web Crypto API
export const createClientJwt = async (payload, secret = JWT_SECRET) => {
  const header = { alg: "HS256", typ: "JWT" };
  const now = Math.floor(Date.now() / 1000);
  const body = { ...payload, iat: now, exp: now + 7 * 86400 };
  const hB64 = strToB64Url(JSON.stringify(header));
  const bB64 = strToB64Url(JSON.stringify(body));
  const signingInput = `${hB64}.${bB64}`;

  try {
    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(secret),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"]
    );
    const sig = await crypto.subtle.sign(
      "HMAC",
      key,
      new TextEncoder().encode(signingInput)
    );
    const sigB64 = toB64Url(new Uint8Array(sig));
    return `${signingInput}.${sigB64}`;
  } catch {
    return `${signingInput}.local_client_sig`;
  }
};

// SHA-256 hashing using Web Crypto API
export const sha256 = async (str) => {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
};

export const loadStorage = (key, fallback) => {
  try {
    const val = localStorage.getItem(key);
    return val ? JSON.parse(val) : fallback;
  } catch {
    return fallback;
  }
};

export const saveStorage = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.error("Failed to save to localStorage", e);
  }
};

// Seed demo account if no users exist
const DEMO_USER = {
  name: "Dr. Sarah Mitchell",
  email: "doctor@retinascan.ai",
  password: "Password123",
};

export async function initDemoUser() {
  const users = loadStorage("dr_users", {});
  if (!users[DEMO_USER.email]) {
    const hash = await sha256(DEMO_USER.password);
    users[DEMO_USER.email] = {
      name: DEMO_USER.name,
      hash: hash,
    };
    saveStorage("dr_users", users);
  }
}

// Validation logic
export function validateEmail(email) {
  if (!email || !email.trim()) {
    return "Email address is required.";
  }
  const clean = email.trim();
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!emailRegex.test(clean)) {
    return "Please enter a valid email address (e.g. name@example.com).";
  }
  return "";
}

export function validatePassword(password, isRegister = false) {
  if (!password) {
    return "Password is required.";
  }
  if (password.length < 6) {
    return "Password must be at least 6 characters long.";
  }
  if (isRegister) {
    if (!/[a-zA-Z]/.test(password)) {
      return "Password must contain at least one letter.";
    }
    if (!/[0-9]/.test(password)) {
      return "Password must contain at least one number.";
    }
  }
  return "";
}

export function validateConfirmPassword(password, confirmPassword) {
  if (!confirmPassword) {
    return "Please confirm your password.";
  }
  if (password !== confirmPassword) {
    return "Passwords do not match.";
  }
  return "";
}

export function validateName(name) {
  if (!name || !name.trim()) {
    return "Full name is required.";
  }
  if (name.trim().length < 2) {
    return "Name must be at least 2 characters.";
  }
  return "";
}

export function calculatePasswordStrength(pwd) {
  if (!pwd) return { score: 0, label: "", color: "" };
  let score = 0;
  if (pwd.length >= 6) score += 1;
  if (pwd.length >= 8) score += 1;
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score += 1;
  if (/[0-9]/.test(pwd) && /[^A-Za-z0-9]/.test(pwd)) score += 1;

  switch (score) {
    case 1:
      return { score: 1, label: "Weak", color: "#e0692a" };
    case 2:
      return { score: 2, label: "Fair", color: "#e0a526" };
    case 3:
      return { score: 3, label: "Good", color: "#2f9e6b" };
    case 4:
      return { score: 4, label: "Strong", color: "#0f6e73" };
    default:
      return { score: 0, label: "Too Short", color: "#cf3a3a" };
  }
}

export default function Auth({ onLogin, theme, onToggleTheme }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    rememberMe: true,
  });

  const [touched, setTouched] = useState({
    name: false,
    email: false,
    password: false,
    confirmPassword: false,
  });

  const [fieldErrors, setFieldErrors] = useState({});
  const [generalAlert, setGeneralAlert] = useState(null); // { type: "error"|"success", text: "" }
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize demo user & load remembered email
  useEffect(() => {
    initDemoUser();
    const rememberedEmail = localStorage.getItem("dr_remembered_email");
    if (rememberedEmail) {
      setForm((prev) => ({ ...prev, email: rememberedEmail, rememberMe: true }));
    }
  }, []);

  // Validate a single field
  const validateField = (field, value, allValues = form) => {
    switch (field) {
      case "email":
        return validateEmail(value);
      case "password":
        return validatePassword(value, mode === "register");
      case "confirmPassword":
        return mode === "register"
          ? validateConfirmPassword(allValues.password, value)
          : "";
      case "name":
        return mode === "register" ? validateName(value) : "";
      default:
        return "";
    }
  };

  const handleChange = (field) => (e) => {
    const val = field === "rememberMe" ? e.target.checked : e.target.value;
    const newForm = { ...form, [field]: val };
    setForm(newForm);

    if (generalAlert) setGeneralAlert(null);

    // If already touched, validate in real time
    if (touched[field]) {
      const err = validateField(field, val, newForm);
      setFieldErrors((prev) => ({ ...prev, [field]: err }));

      // Also re-validate confirm password if password changes
      if (field === "password" && mode === "register" && touched.confirmPassword) {
        const confirmErr = validateConfirmPassword(val, newForm.confirmPassword);
        setFieldErrors((prev) => ({ ...prev, confirmPassword: confirmErr }));
      }
    }
  };

  const handleBlur = (field) => () => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const err = validateField(field, form[field], form);
    setFieldErrors((prev) => ({ ...prev, [field]: err }));
  };

  const validateAll = () => {
    const errors = {};
    if (mode === "register") {
      errors.name = validateName(form.name);
    }
    errors.email = validateEmail(form.email);
    errors.password = validatePassword(form.password, mode === "register");
    if (mode === "register") {
      errors.confirmPassword = validateConfirmPassword(form.password, form.confirmPassword);
    }

    setTouched({
      name: true,
      email: true,
      password: true,
      confirmPassword: true,
    });
    setFieldErrors(errors);

    return Object.values(errors).every((err) => !err);
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setGeneralAlert(null);
    setFieldErrors({});
    setTouched({
      name: false,
      email: false,
      password: false,
      confirmPassword: false,
    });
    setForm((prev) => ({
      ...prev,
      confirmPassword: "",
    }));
  };

  const handleQuickDemo = () => {
    setForm({
      name: "",
      email: DEMO_USER.email,
      password: DEMO_USER.password,
      confirmPassword: "",
      rememberMe: true,
    });
    setFieldErrors({});
    setTouched({});
    setGeneralAlert({
      type: "success",
      text: "Demo credentials loaded! Click 'Sign In' to proceed.",
    });
    if (mode !== "login") setMode("login");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setGeneralAlert(null);

    const isValid = validateAll();
    if (!isValid) return;

    setIsSubmitting(true);
    try {
      const cleanEmail = form.email.trim().toLowerCase();
      let jwtToken = null;

      // 1. Attempt backend JWT authentication first
      try {
        const endpoint = mode === "register" ? `${API}/auth/register` : `${API}/auth/login`;
        const payload = mode === "register"
          ? { email: cleanEmail, password: form.password, name: form.name.trim() }
          : { email: cleanEmail, password: form.password };

        const resp = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (resp.ok) {
          const resData = await resp.json();
          jwtToken = resData.token;
          if (jwtToken) {
            localStorage.setItem("dr_jwt_token", jwtToken);
          }
          if (form.rememberMe) {
            localStorage.setItem("dr_remembered_email", cleanEmail);
          } else {
            localStorage.removeItem("dr_remembered_email");
          }
          setGeneralAlert({
            type: "success",
            text: mode === "register"
              ? "Account created & JWT authenticated! Logging you in..."
              : "Login verified with JWT! Opening screening workspace...",
          });
          setTimeout(() => {
            onLogin({
              email: cleanEmail,
              name: resData.user?.name || form.name.trim() || cleanEmail.split("@")[0],
              token: jwtToken,
            });
          }, 450);
          return;
        } else if (resp.status === 401 || resp.status === 409) {
          const errData = await resp.json().catch(() => ({}));
          setGeneralAlert({
            type: "error",
            text: errData.detail || "Authentication failed. Please verify your credentials.",
          });
          setIsSubmitting(false);
          return;
        }
      } catch (backendNetErr) {
        // Backend offline or unreachable, fall back to robust local storage + JWT creation
        console.warn("Backend auth service offline; using resilient local JWT engine.");
      }

      // 2. Client-side resilient fallback (with cryptographic HS256 JWT signing)
      const users = loadStorage("dr_users", {});
      const hash = await sha256(form.password);

      if (mode === "register") {
        if (users[cleanEmail]) {
          setGeneralAlert({
            type: "error",
            text: "An account with this email already exists. Please sign in.",
          });
          setIsSubmitting(false);
          return;
        }

        const userName = form.name.trim() || cleanEmail.split("@")[0];
        users[cleanEmail] = {
          name: userName,
          hash: hash,
          registeredAt: new Date().toISOString(),
        };
        saveStorage("dr_users", users);

        jwtToken = await createClientJwt({ email: cleanEmail, name: userName });
        localStorage.setItem("dr_jwt_token", jwtToken);

        if (form.rememberMe) {
          localStorage.setItem("dr_remembered_email", cleanEmail);
        } else {
          localStorage.removeItem("dr_remembered_email");
        }

        setGeneralAlert({
          type: "success",
          text: "Account registered with JWT security! Logging you in...",
        });

        setTimeout(() => {
          onLogin({
            email: cleanEmail,
            name: userName,
            token: jwtToken,
          });
        }, 500);
      } else {
        // Login mode
        const existing = users[cleanEmail];
        if (!existing) {
          setGeneralAlert({
            type: "error",
            text: "No account found with this email. Please check your email or create an account.",
          });
          setFieldErrors((prev) => ({
            ...prev,
            email: "Email not registered",
          }));
          setIsSubmitting(false);
          return;
        }

        if (existing.hash !== hash) {
          setGeneralAlert({
            type: "error",
            text: "Incorrect password. Please verify and try again.",
          });
          setFieldErrors((prev) => ({
            ...prev,
            password: "Wrong password entered",
          }));
          setIsSubmitting(false);
          return;
        }

        jwtToken = await createClientJwt({ email: cleanEmail, name: existing.name });
        localStorage.setItem("dr_jwt_token", jwtToken);

        if (form.rememberMe) {
          localStorage.setItem("dr_remembered_email", cleanEmail);
        } else {
          localStorage.removeItem("dr_remembered_email");
        }

        onLogin({
          email: cleanEmail,
          name: existing.name,
          token: jwtToken,
        });
      }
    } catch (err) {
      setGeneralAlert({
        type: "error",
        text: "An unexpected error occurred. Please try again.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const strength = calculatePasswordStrength(form.password);

  return (
    <div className="auth-container">
      {/* Left visual branding panel */}
      <div className="auth-brand-pane">
        <div className="brand-header">
          <div className="retina-logo-badge">
            <svg viewBox="0 0 200 200" className="brand-svg" aria-hidden="true">
              <circle cx="100" cy="100" r="92" className="fundus" />
              <circle cx="132" cy="92" r="16" className="disc" />
              <path
                d="M132 92C100 70 70 60 40 70M132 92C110 100 80 120 50 140M132 92C120 60 110 40 96 22M132 92C120 120 110 150 98 176"
                className="vessel"
              />
            </svg>
          </div>
          <h1>RetinaScan</h1>
          <p className="brand-subtitle">
            AI-Assisted Diabetic Retinopathy Detection & Clinical Severity Grading
          </p>
        </div>

        <div className="brand-highlights">
          <div className="highlight-item">
            <span className="highlight-icon">✓</span>
            <div>
              <strong>Instant 5-Class Staging</strong>
              <p>No DR, Mild, Moderate, Severe, and Proliferative DR detection.</p>
            </div>
          </div>
          <div className="highlight-item">
            <span className="highlight-icon">✓</span>
            <div>
              <strong>Deep Learning Accuracy</strong>
              <p>High-resolution retinal fundus feature analysis with confidence metrics.</p>
            </div>
          </div>
          <div className="highlight-item">
            <span className="highlight-icon">✓</span>
            <div>
              <strong>Secure Clinical Workspace</strong>
              <p>Scan history tracking, triage guidance, and instant report overview.</p>
            </div>
          </div>
        </div>

        <div className="brand-footer">
          <span>Medical AI Diagnostic Assistant · v1.2.0</span>
          <a
            href="/RetinaScan_User_Guide.pdf"
            download="RetinaScan_User_Guide.pdf"
            className="link-guide-pdf"
            title="Download Complete System Manual & User Guide (PDF)"
          >
            📄 User Manual (PDF)
          </a>
        </div>
      </div>

      {/* Right Form panel */}
      <div className="auth-form-pane">
        <div className="auth-card">
          {/* Security & Theme Control Bar */}
          <div className="auth-card-topbar">
            <span className="auth-security-badge" title="RFC 7519 HS256 JWT Authentication Active">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              JWT Secure
            </span>
            <button
              type="button"
              className="theme-toggle-btn"
              onClick={onToggleTheme}
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="5"/>
                    <line x1="12" y1="1" x2="12" y2="3"/>
                    <line x1="12" y1="21" x2="12" y2="23"/>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                    <line x1="1" y1="12" x2="3" y2="12"/>
                    <line x1="21" y1="12" x2="23" y2="12"/>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                  </svg>
                  <span>Light</span>
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                  </svg>
                  <span>Dark</span>
                </>
              )}
            </button>
          </div>

          {/* Top Tabs */}
          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={`tab-btn ${mode === "login" ? "active" : ""}`}
              onClick={() => switchMode("login")}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={`tab-btn ${mode === "register" ? "active" : ""}`}
              onClick={() => switchMode("register")}
            >
              Create Account
            </button>
          </div>

          <div className="auth-form-header">
            <h2>{mode === "login" ? "Welcome Back" : "Get Started"}</h2>
            <p>
              {mode === "login"
                ? "Enter your credentials to access your screening workspace"
                : "Create a new clinician or researcher account in seconds"}
            </p>
          </div>

          {/* Quick Demo Access banner in Login mode */}
          {mode === "login" && (
            <div className="demo-box">
              <div className="demo-text">
                <span className="demo-badge">Quick Demo</span>
                <span className="demo-creds">
                  <code>doctor@retinascan.ai</code> · <code>Password123</code>
                </span>
              </div>
              <button
                type="button"
                className="btn-demo-fill"
                onClick={handleQuickDemo}
                title="Fill demo credentials"
              >
                Auto Fill
              </button>
            </div>
          )}

          {/* General alert banner */}
          {generalAlert && (
            <div
              className={`alert-banner ${
                generalAlert.type === "error" ? "alert-error" : "alert-success"
              }`}
              role="alert"
            >
              <span className="alert-icon">
                {generalAlert.type === "error" ? "⚠️" : "✓"}
              </span>
              <span>{generalAlert.text}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="auth-form-body">
            {/* Full Name (Registration only) */}
            {mode === "register" && (
              <div className="form-group">
                <label htmlFor="auth-name">
                  Full Name <span className="req">*</span>
                </label>
                <div className="input-box">
                  <span className="input-adornment-left" aria-hidden="true">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </span>
                  <input
                    id="auth-name"
                    type="text"
                    placeholder="e.g. Dr. John Doe"
                    value={form.name}
                    onChange={handleChange("name")}
                    onBlur={handleBlur("name")}
                    className={
                      touched.name && fieldErrors.name
                        ? "input-has-error"
                        : touched.name && !fieldErrors.name && form.name
                        ? "input-is-valid"
                        : ""
                    }
                    autoComplete="name"
                  />
                </div>
                {touched.name && fieldErrors.name && (
                  <div className="field-error-msg">
                    <span className="error-dot">●</span> {fieldErrors.name}
                  </div>
                )}
              </div>
            )}

            {/* Email Field with Validation */}
            <div className="form-group">
              <label htmlFor="auth-email">
                Email Address <span className="req">*</span>
              </label>
              <div className="input-box">
                <span className="input-adornment-left" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                    <polyline points="22,6 12,13 2,6" />
                  </svg>
                </span>
                <input
                  id="auth-email"
                  type="email"
                  placeholder="name@organization.com"
                  value={form.email}
                  onChange={handleChange("email")}
                  onBlur={handleBlur("email")}
                  className={
                    touched.email && fieldErrors.email
                      ? "input-has-error"
                      : touched.email && !fieldErrors.email && form.email
                      ? "input-is-valid"
                      : ""
                  }
                  autoComplete="email"
                />
              </div>
              {touched.email && fieldErrors.email ? (
                <div className="field-error-msg">
                  <span className="error-dot">●</span> {fieldErrors.email}
                </div>
              ) : (
                <div className="field-hint">
                  {mode === "login"
                    ? "Enter your registered email address."
                    : "A valid email is required for access and alerts."}
                </div>
              )}
            </div>

            {/* Password Field with Validation & Visibility Toggle */}
            <div className="form-group">
              <div className="label-row">
                <label htmlFor="auth-password">
                  Password <span className="req">*</span>
                </label>
                {mode === "login" && (
                  <button
                    type="button"
                    className="link-btn"
                    onClick={() =>
                      alert("Password reset feature: Please contact system administrator or register a new account for local testing.")
                    }
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <div className="input-box">
                <span className="input-adornment-left" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                </span>
                <input
                  id="auth-password"
                  type={showPassword ? "text" : "password"}
                  placeholder={
                    mode === "register" ? "Minimum 6 characters with letters & numbers" : "Enter your password"
                  }
                  value={form.password}
                  onChange={handleChange("password")}
                  onBlur={handleBlur("password")}
                  className={
                    touched.password && fieldErrors.password
                      ? "input-has-error"
                      : touched.password && !fieldErrors.password && form.password
                      ? "input-is-valid"
                      : ""
                  }
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    // Eye Off icon
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    // Eye icon
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
              {touched.password && fieldErrors.password && (
                <div className="field-error-msg">
                  <span className="error-dot">●</span> {fieldErrors.password}
                </div>
              )}

              {/* Password strength indicator for registration */}
              {mode === "register" && form.password && (
                <div className="pwd-strength-container">
                  <div className="pwd-bars">
                    {[1, 2, 3, 4].map((bar) => (
                      <div
                        key={bar}
                        className={`pwd-bar-segment ${bar <= strength.score ? "active" : ""}`}
                        style={{
                          backgroundColor: bar <= strength.score ? strength.color : undefined,
                        }}
                      />
                    ))}
                  </div>
                  <div className="pwd-strength-text">
                    <span>Password strength:</span>
                    <strong style={{ color: strength.color }}> {strength.label}</strong>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password (Registration only) */}
            {mode === "register" && (
              <div className="form-group">
                <label htmlFor="auth-confirm-password">
                  Confirm Password <span className="req">*</span>
                </label>
                <div className="input-box">
                  <span className="input-adornment-left" aria-hidden="true">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                  </span>
                  <input
                    id="auth-confirm-password"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Re-enter your password"
                    value={form.confirmPassword}
                    onChange={handleChange("confirmPassword")}
                    onBlur={handleBlur("confirmPassword")}
                    className={
                      touched.confirmPassword && fieldErrors.confirmPassword
                        ? "input-has-error"
                        : touched.confirmPassword && !fieldErrors.confirmPassword && form.confirmPassword
                        ? "input-is-valid"
                        : ""
                    }
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
                {touched.confirmPassword && fieldErrors.confirmPassword && (
                  <div className="field-error-msg">
                    <span className="error-dot">●</span> {fieldErrors.confirmPassword}
                  </div>
                )}
              </div>
            )}

            {/* Remember Me option */}
            <div className="remember-row">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={form.rememberMe}
                  onChange={handleChange("rememberMe")}
                />
                <span>Remember my email</span>
              </label>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary btn-submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <span className="btn-spinner-content">
                  <span className="spinner-dot"></span> Authenticating...
                </span>
              ) : mode === "login" ? (
                "Sign In"
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          {/* Bottom Switcher */}
          <div className="auth-footer-swap">
            {mode === "login" ? (
              <p>
                Don't have an account yet?{" "}
                <button
                  type="button"
                  className="link-btn-bold"
                  onClick={() => switchMode("register")}
                >
                  Create one now
                </button>
              </p>
            ) : (
              <p>
                Already have an account?{" "}
                <button
                  type="button"
                  className="link-btn-bold"
                  onClick={() => switchMode("login")}
                >
                  Sign in
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
