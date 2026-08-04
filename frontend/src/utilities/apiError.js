/**
 * Every backend error response shares one shape (see
 * backend/app/core/exceptions.py):
 *
 *   { "error": { "code": "...", "message": "...", "details": {...} } }
 *
 * This pulls a human-readable message out of that shape (or an Axios/
 * network-level failure) so components never need to know the difference
 * between "the API responded with an error" and "the request never made it
 * to the API at all".
 */
export function getErrorMessage(error) {
  const backendMessage = error?.response?.data?.error?.message;
  if (backendMessage) {
    return backendMessage;
  }
  if (error?.response) {
    return `Request failed (${error.response.status}).`;
  }
  if (error?.request) {
    return "Could not reach the server. Check your connection and try again.";
  }
  return error?.message || "Something went wrong.";
}

export function getErrorCode(error) {
  return error?.response?.data?.error?.code ?? null;
}
