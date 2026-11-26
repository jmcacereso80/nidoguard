/** Tema Liquid Glass para los formularios de Clerk (crear cuenta, iniciar sesion y codigo por correo). */
const glass = {
  background: "rgba(255,255,255,0.66)",
  backdropFilter: "blur(28px) saturate(1.5)",
  WebkitBackdropFilter: "blur(28px) saturate(1.5)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 14px 36px rgba(24,59,86,0.18), inset 0 1px 0 rgba(255,255,255,0.95)",
};

export const clerkAppearance = {
  layout: { logoPlacement: "none" as const, socialButtonsVariant: "blockButton" as const },
  variables: {
    colorPrimary: "#183B56",
    colorText: "#102B40",
    colorTextSecondary: "#526574",
    colorBackground: "transparent",
    colorInputBackground: "rgba(255,255,255,0.7)",
    colorInputText: "#102B40",
    colorDanger: "#B3402F",
    colorSuccess: "#2F6B4A",
    fontFamily: "'Manrope Variable', system-ui, sans-serif",
    fontWeight: { normal: 500, medium: 700, bold: 800 },
    borderRadius: "18px",
  },
  elements: {
    rootBox: { width: "100%" },
    cardBox: { width: "100%", boxShadow: "none", background: "transparent" },
    card: { ...glass, borderRadius: "30px", padding: "28px 22px" },
    headerTitle: { fontWeight: 800, fontSize: "26px", letterSpacing: "-0.5px" },
    headerSubtitle: { color: "#526574" },
    formButtonPrimary: {
      minHeight: "54px", borderRadius: "999px", fontWeight: 800, fontSize: "16px", textTransform: "none" as const,
      background: "linear-gradient(150deg, rgba(115,153,181,0.92), rgba(24,59,86,0.97))",
      border: "1px solid rgba(255,255,255,0.35)",
      boxShadow: "0 12px 26px rgba(24,59,86,0.28), inset 0 1px 0 rgba(255,255,255,0.4)",
    },
    socialButtonsBlockButton: { minHeight: "52px", borderRadius: "999px", background: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.85)", fontWeight: 700 },
    formFieldInput: { minHeight: "52px", borderRadius: "18px", border: "1px solid rgba(255,255,255,0.85)", boxShadow: "inset 0 1px 2px rgba(24,59,86,0.08)", fontWeight: 600 },
    formFieldLabel: { fontWeight: 700, color: "#102B40" },
    otpCodeFieldInput: { minHeight: "56px", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.85)", fontWeight: 800, fontSize: "22px" },
    footerActionLink: { color: "#183B56", fontWeight: 800 },
    formResendCodeLink: { color: "#183B56", fontWeight: 800 },
    identityPreview: { borderRadius: "999px", background: "rgba(255,255,255,0.7)", border: "1px solid rgba(255,255,255,0.85)" },
    footer: { background: "transparent" },
  },
};
