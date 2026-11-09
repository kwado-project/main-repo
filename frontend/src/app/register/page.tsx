import { Suspense } from "react";
import { AuthFlow } from "@/components/auth/auth-flow";

export const metadata = { title: "Create your account" };
export default function RegisterPage() {
  return <Suspense><AuthFlow intent="register" /></Suspense>;
}
