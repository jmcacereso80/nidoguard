import { SignIn } from "@clerk/nextjs";
import { AuthShell } from "@/components/AuthShell";

export default function Page() {
  return <AuthShell back><SignIn fallbackRedirectUrl="/inicio" /></AuthShell>;
}
