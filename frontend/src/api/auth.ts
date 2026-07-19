import { apiClient } from "./client";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  shop_id: string;
  email: string;
  shop_name: string;
}

export async function signup(shop_name: string, email: string, password: string) {
  const { data } = await apiClient.post<TokenResponse>("/auth/signup", { shop_name, email, password });
  return data;
}

export async function login(email: string, password: string) {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", { email, password });
  return data;
}

export async function getCurrentUser() {
  const { data } = await apiClient.get<CurrentUser>("/auth/me");
  return data;
}
