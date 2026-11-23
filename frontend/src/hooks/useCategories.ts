import { useEffect, useState } from "react";
import { api } from "../services/api";

/** Category labels from the backend model, so the UI never hardcodes them. */
export function useCategories(): string[] {
  const [categories, setCategories] = useState<string[]>([]);
  useEffect(() => {
    api
      .getCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);
  return categories;
}
