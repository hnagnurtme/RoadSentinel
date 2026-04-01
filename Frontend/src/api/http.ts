export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly responseText?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function requestJson<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 10_000, ...requestInit } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...requestInit,
      headers: {
        "Content-Type": "application/json",
        ...requestInit.headers,
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      const responseText = await response.text();
      throw new ApiError(`Request failed with status ${response.status}`, response.status, responseText);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timeout", 408);
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}
