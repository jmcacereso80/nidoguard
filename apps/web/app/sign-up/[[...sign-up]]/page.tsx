import { SignUp } from "@clerk/nextjs";
import { AuthShell } from "@/components/AuthShell";

export default function Page() {
  return <AuthShell back><SignUp fallbackRedirectUrl="/inicio" /></AuthShell>;
}
