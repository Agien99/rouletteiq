import apiConfig from "../config/api";

async function apiRequest(
  path,
  options = {}
) {
  if (!apiConfig.baseUrl) {
    throw new Error(
      "FastAPI backend URL has " +
      "not been configured."
    );
  }

  let response;

  try {
    response = await fetch(
      `${apiConfig.baseUrl}${path}`,
      {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(document.cookie.split(";").map(x => x.trim()).find(x => x.startsWith("rouletteiq_csrf=")) ? {
            "x-csrf-token": decodeURIComponent(document.cookie.split(";").map(x => x.trim()).find(x => x.startsWith("rouletteiq_csrf=")).slice("rouletteiq_csrf=".length))
          } : {}),
          ...options.headers,
        },
      }
    );
  } catch {
    throw new Error(
      "Unable to connect to the " +
      "FastAPI server."
    );
  }

  let data = null;

  try {
    data =
      await response.json();
  } catch {
    // Response has no JSON body.
  }

  if (!response.ok) {
    let message =
      "API request failed.";

    if (
      typeof data?.message ===
      "string"
    ) {
      message =
        data.message;
    } else if (
      typeof data?.detail ===
      "string"
    ) {
      message =
        data.detail;
    } else if (
      Array.isArray(
        data?.detail
      )
    ) {
      message =
        data.detail
          .map(
            (item) =>
              item.msg
          )
          .filter(Boolean)
          .join(", ");
    }

    if (
      response.status === 404
    ) {
      message =
        message ||
        "Requested data was not found.";
    }

    if (
      response.status >= 500
    ) {
      message =
        "The backend server encountered " +
        "an unexpected error.";
    }

    throw new Error(
      message
    );
  }

  return data;
}

export async function createSession() {
  return apiRequest("/sessions", {
    method: "POST",
  });
}

export async function submitInitialSpins(
  sessionId,
  spins
) {
  return apiRequest(
    `/sessions/${sessionId}/initial-spins`,
    {
      method: "POST",
      body: JSON.stringify({
        spins,
      }),
    }
  );
}

export async function addSessionSpin(
  sessionId,
  number
) {
  return apiRequest(
    `/sessions/${sessionId}/spins`,
    {
      method: "POST",
      body: JSON.stringify({
        number,
      }),
    }
  );
}

export async function getSessionSpins(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/spins`
  );
}

export async function generatePrediction(
  sessionId,
  strategy = "v1",
  recentWindow = 10
) {
  return apiRequest(
    `/sessions/${sessionId}/predictions`,
    {
      method: "POST",
      body: JSON.stringify({
        strategy,
        recent_window: recentWindow,
      }),
    }
  );
}

export async function getLatestPrediction(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/predictions/latest`
  );
}

export async function getSessionStatistics(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/stats`
  );
}

export async function getSessionEvaluation(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/evaluation`
  );
}

export async function getStrategyComparison(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/comparison`
  );
}

export async function getMLPerformance(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/ml-performance`
  );
}

export async function endSession(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}/end`,
    {
      method: "POST",
    }
  );
}

export async function getSessions() {
  return apiRequest(
    "/sessions"
  );
}

export async function getSession(
  sessionId
) {
  return apiRequest(
    `/sessions/${sessionId}`
  );
}