"use client";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { Me, useApi } from "@/lib/api";

export function useMe() {
  const api = useApi();
  const { isSignedIn, isLoaded } = useAuth();
  return useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/me"), enabled: isLoaded && !!isSignedIn });
}
