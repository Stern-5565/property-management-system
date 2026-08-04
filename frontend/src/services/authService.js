/**
 * Thin wrapper around the /api/auth/* endpoints - the pattern every future
 * module's service file follows (see documentation/progress-log.md): a
 * service module owns "how do I call this part of the API", components and
 * contexts never call apiClient directly.
 */
import { apiClient } from "../api/client";

export async function login(email, password) {
  const { data } = await apiClient.post("/auth/login", { Email: email, Password: password });
  return data; // { access_token, refresh_token, token_type }
}

export async function refresh(refreshToken) {
  const { data } = await apiClient.post("/auth/refresh", { refresh_token: refreshToken });
  return data; // { access_token, token_type }
}

export async function logout() {
  await apiClient.post("/auth/logout");
}

export async function getCurrentUser() {
  const { data } = await apiClient.get("/auth/me");
  return data; // { UserId, Username, Email, EmployeeId, EmployeeName, IsActive, LastLoginAt, Roles }
}

export async function changePassword(currentPassword, newPassword) {
  await apiClient.post("/auth/change-password", {
    CurrentPassword: currentPassword,
    NewPassword: newPassword,
  });
}
