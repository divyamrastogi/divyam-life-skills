// Brand palette for the notification email. Email clients strip <link> and
// most <style>, so email HTML must inline every value — it can't read a
// stylesheet. Edit these to match the brand. If the site has a design-token
// file, keep this in sync with it (this is a hand-maintained mirror).

export const theme = {
  // Header background + primary text
  ink: "#18181B",
  muted: "#52525B",
  mutedDark: "#27272A",
  faint: "#A8A29E",
  onDark: "#A1A1AA",
  white: "#ffffff",

  bg: "#FAF7F2",
  surface2: "#FAFAF9",
  surface3: "#F5F5F4",
  line: "#EDEBE9",

  // Accent — used for the eyebrow and the quote bar. Set to the brand colour.
  accent: "#FF5F57",

  // System font stack (webfonts are unreliable in email).
  font:
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif",
} as const;
