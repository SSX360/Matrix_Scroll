(function () {
  var config = window.MATRIXSCROLL_RUNTIME || {}
  var SUPABASE_URL = config.supabaseUrl || ""
  var SUPABASE_ANON_KEY = config.supabaseAnonKey || ""
  var SSX360_PORTAL = (config.ssx360PortalUrl || "https://ssx360.com").replace(/\/+$/, "")

  var supabaseClient = null
  var currentUser = null
  var identityKeys = []
  var entitlement = null
  var isSignUpMode = false

  var viewAuth = document.getElementById("view-auth")
  var viewDashboard = document.getElementById("view-dashboard")
  var configBanner = document.getElementById("config-banner")
  var authForm = document.getElementById("auth-form")
  var authTitle = document.getElementById("auth-title")
  var authEmailInput = document.getElementById("auth-email")
  var authPasswordInput = document.getElementById("auth-password")
  var btnSubmitAuth = document.getElementById("btn-submit-auth")
  var authToggleMsg = document.getElementById("auth-toggle-msg")
  var authToggleLink = document.getElementById("auth-toggle-link")
  var authErrorFeedback = document.getElementById("auth-error-feedback")
  var dashUserEmail = document.getElementById("dash-user-email")
  var dashStatusBadge = document.getElementById("dash-status-badge")
  var boxStatusBadge = document.getElementById("box-status-badge")
  var btnSignout = document.getElementById("btn-signout")
  var keyRegisterForm = document.getElementById("key-register-form")
  var regFeedback = document.getElementById("reg-feedback")
  var keysListContainer = document.getElementById("keys-list-container")
  var billingActionBox = document.getElementById("billing-action-box")
  var billingManageBox = document.getElementById("billing-manage-box")
  var btnUpgradeCheckout = document.getElementById("btn-upgrade-checkout")
  var btnManageBilling = document.getElementById("btn-manage-billing")
  var billingErrorFeedback = document.getElementById("billing-error-feedback")

  function showError(el, msg) {
    el.textContent = msg
    el.className = "auth-feedback error"
    el.style.display = "block"
  }

  function showSuccess(el, msg) {
    el.textContent = msg
    el.className = "auth-feedback success"
    el.style.display = "block"
  }

  function isVerifiedEntitlement(record) {
    if (!record) return false
    return record.state === "active" || record.state === "trial"
  }

  function initSupabase() {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !window.supabase) {
      if (configBanner) {
        configBanner.style.display = "block"
        configBanner.textContent =
          "Hosted identity is temporarily unavailable. Email mission@ssx360.com or use the contact form on ssx360.com."
      }
      return false
    }

    supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    if (configBanner) configBanner.style.display = "none"

    supabaseClient.auth.onAuthStateChange(function (_event, session) {
      currentUser = session?.user || null
      if (currentUser) {
        loadDashboardData()
      } else {
        identityKeys = []
        entitlement = null
        refreshUI()
      }
    })

    supabaseClient.auth.getSession().then(function (result) {
      currentUser = result.data.session?.user || null
      if (currentUser) loadDashboardData()
      else refreshUI()
    })

    return true
  }

  async function loadDashboardData() {
    if (!supabaseClient || !currentUser) return

    var keysResult = await supabaseClient
      .from("matrixscroll_identity_keys")
      .select("*")
      .order("created_at", { ascending: false })

    if (!keysResult.error && keysResult.data) {
      identityKeys = keysResult.data
    }

    var entResult = await supabaseClient
      .from("digital_rain_entitlements")
      .select("state, plan, license_id")
      .eq("user_id", currentUser.id)
      .maybeSingle()

    entitlement = entResult.error ? null : entResult.data
    refreshUI()
  }

  function setupAuthToggle() {
    authToggleLink.addEventListener("click", function (e) {
      e.preventDefault()
      isSignUpMode = !isSignUpMode
      if (isSignUpMode) {
        authTitle.textContent = "Create authority account"
        btnSubmitAuth.textContent = "Sign up"
        authToggleMsg.textContent = "Already have an account?"
        authToggleLink.textContent = "Sign in"
      } else {
        authTitle.textContent = "Claim your hosted identity"
        btnSubmitAuth.textContent = "Sign in"
        authToggleMsg.textContent = "Don't have an account?"
        authToggleLink.textContent = "Sign up"
      }
      authErrorFeedback.style.display = "none"
    })
  }

  function setupAuthForm() {
    authForm.addEventListener("submit", async function (e) {
      e.preventDefault()
      authErrorFeedback.style.display = "none"

      if (!supabaseClient) {
        showError(authErrorFeedback, "Supabase is not configured.")
        return
      }

      var email = authEmailInput.value.trim()
      var password = authPasswordInput.value

      try {
        var result = isSignUpMode
          ? await supabaseClient.auth.signUp({ email, password })
          : await supabaseClient.auth.signInWithPassword({ email, password })

        if (result.error) {
          showError(authErrorFeedback, result.error.message)
          return
        }

        if (isSignUpMode && !result.data.session) {
          showSuccess(
            authErrorFeedback,
            "Check your email to confirm your account, then sign in here.",
          )
        }
      } catch (err) {
        showError(authErrorFeedback, err.message || "Authentication failed.")
      }
    })
  }

  function setupSignout() {
    btnSignout.addEventListener("click", async function () {
      if (supabaseClient) await supabaseClient.auth.signOut()
      currentUser = null
      identityKeys = []
      entitlement = null
      refreshUI()
    })
  }

  function setupKeyRegister() {
    keyRegisterForm.addEventListener("submit", async function (e) {
      e.preventDefault()
      regFeedback.style.display = "none"

      if (!supabaseClient || !currentUser) return

      var payload = {
        user_id: currentUser.id,
        actor: document.getElementById("reg-actor").value.trim(),
        device_id: document.getElementById("reg-device").value.trim(),
        public_key: document.getElementById("reg-pubkey").value.trim(),
      }

      var result = await supabaseClient.from("matrixscroll_identity_keys").insert(payload)
      if (result.error) {
        showError(regFeedback, result.error.message)
        return
      }

      showSuccess(regFeedback, "Signing key registered.")
      keyRegisterForm.reset()
      loadDashboardData()
    })
  }

  function setupBilling() {
    btnUpgradeCheckout.addEventListener("click", function () {
      billingErrorFeedback.style.display = "none"
      window.location.href = SSX360_PORTAL + "/signup?from=matrixscroll-authority"
    })

    btnManageBilling.addEventListener("click", function () {
      window.location.href = SSX360_PORTAL + "/account?from=matrixscroll-authority"
    })
  }

  async function removeKey(keyId) {
    if (!supabaseClient) return
    var result = await supabaseClient.from("matrixscroll_identity_keys").delete().eq("id", keyId)
    if (result.error) {
      alert("Failed to revoke key: " + result.error.message)
      return
    }
    loadDashboardData()
  }

  function renderKeysList() {
    keysListContainer.innerHTML = ""

    if (identityKeys.length === 0) {
      keysListContainer.innerHTML =
        '<div class="empty-keys-msg">No keys registered yet. Register your first key above.</div>'
      return
    }

    identityKeys.forEach(function (k) {
      var item = document.createElement("div")
      item.className = "key-item"
      item.innerHTML =
        '<div class="key-meta"><span>Actor: <strong>' +
        escapeHtml(k.actor) +
        "</strong> (" +
        escapeHtml(k.device_id) +
        ')</span><button type="button" class="btn-remove" data-key-id="' +
        k.id +
        '">Revoke</button></div><div class="key-val">' +
        escapeHtml(k.public_key) +
        "</div>"
      keysListContainer.appendChild(item)
    })

    keysListContainer.querySelectorAll(".btn-remove").forEach(function (btn) {
      btn.addEventListener("click", function () {
        removeKey(btn.dataset.keyId)
      })
    })
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
  }

  function refreshUI() {
    if (currentUser) {
      viewAuth.style.display = "none"
      viewDashboard.style.display = "block"
      dashUserEmail.textContent = currentUser.email || "Signed in"

      var verified = isVerifiedEntitlement(entitlement)

      if (verified) {
        dashStatusBadge.className = "status-badge verified"
        dashStatusBadge.textContent = "Verified"
        boxStatusBadge.className = "status-badge verified"
        boxStatusBadge.textContent = "Verified identity issuer active"
        billingActionBox.style.display = "none"
        billingManageBox.style.display = "block"
      } else {
        dashStatusBadge.className = "status-badge unverified"
        dashStatusBadge.textContent = "Unverified"
        boxStatusBadge.className = "status-badge unverified"
        boxStatusBadge.textContent = "Unverified issuer identity"
        billingActionBox.style.display = "block"
        billingManageBox.style.display = "none"
      }

      renderKeysList()
    } else {
      viewAuth.style.display = "block"
      viewDashboard.style.display = "none"
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupAuthToggle()
    setupAuthForm()
    setupSignout()
    setupKeyRegister()
    setupBilling()
    initSupabase()
  })
})()
