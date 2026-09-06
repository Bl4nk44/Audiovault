export interface ProviderInfo {
  name: string;
  display_name: string;
  connected: boolean;
  username: string | null;
  supports_recommendations: boolean;
  connects_with_token: boolean;
}

export interface ProvidersResponse {
  preference: string;
  providers: ProviderInfo[];
}
