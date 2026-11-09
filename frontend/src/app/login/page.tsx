import { Suspense } from "react";
import { AuthFlow } from "@/components/auth/auth-flow";

export const metadata = { title: "Log in" };
export default function LoginPage() {
  return <Suspense><AuthFlow intent="login" /></Suspense>;
}
