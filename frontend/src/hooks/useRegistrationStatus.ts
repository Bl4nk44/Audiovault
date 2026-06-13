import { useQuery } from "@tanstack/react-query";

import { getRegistrationStatus } from "../services/auth";

/** Public registration status — used by the login/register pages to gate the sign-up flow. */
export const useRegistrationStatus = () =>
  useQuery({
    queryKey: ["registration-status"],
    queryFn: getRegistrationStatus,
    staleTime: 5 * 60 * 1000,
  });
